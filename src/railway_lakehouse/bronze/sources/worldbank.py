"""
World Bank Bronze fetcher.

Same enumerate-by-name idea against the World Bank indicator catalogue:
page through /v2/indicator, keep any whose name/note mentions rail, then
land the full time series (all countries, all years) as RAW JSON.

We request all countries deliberately -- the dataset is landed whole and
unchanged; the HU/AT focus is applied later in Silver. World Bank reaches
back to 1960, which helps cover Hungary in the pre-EU 1980s.

Two facts about this API shape the validation below:

  * The Indicators API answers HTTP 200 even for an invalid, deleted, or
    archived indicator id. The failure is reported only in the body as
    ``[{"message": [{"id": ..., "key": ..., "value": ...}]}]``. A status-code
    check therefore cannot catch it -- we must inspect the payload.
  * Substring discovery on the word "rail" is too greedy (it matches
    "trail", "trailer", "curtail", ...). We anchor on the word "rail*" and,
    independent of discovery, always pull a confirmed allowlist so a throttled
    or noisy catalogue never silently drops the indicators we actually rely on.
"""
import re
import logging
import requests

from ..lander import RawLander, RawArtifact

logger = logging.getLogger("bronze.worldbank")

CATALOGUE_URL = "https://api.worldbank.org/v2/indicator?format=json&per_page=20000"
SERIES_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/{indicator}"
    "?format=json&per_page=20000"
)

# Confirmed rail indicators -- each verified live (HTTP 200 with a real time
# series; e.g. Hungary 2021 goods = 11345.601 Mt-km, passengers = 5435.389
# Mp-km). These are always pulled, regardless of catalogue discovery, so a
# throttled catalogue can never regress us below this baseline.
CONFIRMED_RAIL_INDICATORS = [
    "IS.RRS.TOTL.KM",     # Rail lines (total route-km)
    "IS.RRS.GOOD.MT.K6",  # Railways, goods transported (million ton-km)
    "IS.RRS.PASG.KM",     # Railways, passengers carried (million passenger-km)
]

# Backwards-compatible alias: earlier code/tests refer to this name.
KNOWN_RAIL_INDICATORS = CONFIRMED_RAIL_INDICATORS

# Broad EU-stats indicator set for the big-data Bronze net: rail first (keeps the
# focused tests valid), then economy, population/demography, quality of life,
# health/education, safety and environment. Rules-only mapping downstream; dead
# or archived ids are skipped by series_has_observations() at land time.
EU_STATS_INDICATORS = [
    # --- transport (rail first) ---
    "IS.RRS.TOTL.KM", "IS.RRS.GOOD.MT.K6", "IS.RRS.PASG.KM",
    "IS.AIR.PSGR", "IS.AIR.GOOD.MT.K1", "IS.ROD.PAVE.ZS",
    # --- economy ---
    "NY.GDP.MKTP.CD", "NY.GDP.PCAP.CD", "NY.GDP.MKTP.KD.ZG", "NY.GNP.PCAP.CD",
    "FP.CPI.TOTL.ZG", "SL.UEM.TOTL.ZS", "GC.DOD.TOTL.GD.ZS",
    "NE.EXP.GNFS.ZS", "NE.IMP.GNFS.ZS", "BX.KLT.DINV.WD.GD.ZS",
    # --- population / demography ---
    "SP.POP.TOTL", "SP.POP.GROW", "SP.URB.TOTL.IN.ZS", "EN.POP.DNST",
    "SP.DYN.LE00.IN", "SP.DYN.TFRT.IN", "SP.DYN.IMRT.IN",
    # --- quality of life / health / education / digital ---
    "SE.XPD.TOTL.GD.ZS", "SH.XPD.CHEX.GD.ZS", "EG.ELC.ACCS.ZS",
    "SI.POV.GINI", "IT.NET.USER.ZS", "SH.STA.SUIC.P5",
    # --- safety ---
    "VC.IHR.PSRC.P5",
    # --- environment ---
    "EN.GHG.CO2.PC.CE.AR5", "EN.ATM.CO2E.PC",
]

# Word-anchored match: "rail", "railway(s)", "railroad(s)" -- but NOT
# "trail", "trailer", "curtail", "monorail", etc.
_RAIL_RE = re.compile(r"\brail\w*", re.IGNORECASE)
_INDICATOR_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _valid_indicator_id(indicator_id: str) -> bool:
    return bool(_INDICATOR_ID_RE.fullmatch(indicator_id))


def discover_rail_indicators(catalogue_json: list) -> list[str]:
    """Pure: extract indicator ids whose name/sourceNote mentions rail.

    catalogue_json is the parsed World Bank response: [meta, [indicators...]].
    The result is always unioned with the confirmed allowlist so discovery can
    only ever add to the baseline, never shrink it.
    """
    if not catalogue_json or len(catalogue_json) < 2 or not catalogue_json[1]:
        return list(CONFIRMED_RAIL_INDICATORS)
    ids = []
    for ind in catalogue_json[1]:
        text = f"{ind.get('name', '')} {ind.get('sourceNote', '')}"
        indicator_id = str(ind.get("id", ""))
        if _RAIL_RE.search(text) and _valid_indicator_id(indicator_id):
            ids.append(indicator_id)
    # union with the confirmed family so we never regress
    return sorted(set(ids) | set(CONFIRMED_RAIL_INDICATORS))


def is_error_payload(series_json) -> bool:
    """True if the parsed response is a World Bank API error envelope.

    The Indicators API returns HTTP 200 even for invalid/archived ids,
    signalling the problem only in the body, e.g.::

        [{"message": [{"id": "175", "key": "Invalid format",
                       "value": "The indicator was not found. ..."}]}]
    """
    return (
        isinstance(series_json, list)
        and len(series_json) >= 1
        and isinstance(series_json[0], dict)
        and "message" in series_json[0]
    )


def series_has_observations(series_json) -> bool:
    """True if the response carries a real time series (not error/empty).

    A valid series is ``[meta, [row, ...]]`` where ``meta`` does not report a
    zero total and the row list holds observation objects (dicts with a
    ``date``). Null ``value`` fields are fine -- an empty year is still a real
    observation slot; what we reject here is error envelopes and no-data
    bodies (``[meta, null]`` / ``total == 0``).
    """
    if is_error_payload(series_json):
        return False
    if not isinstance(series_json, list) or len(series_json) < 2:
        return False
    meta, rows = series_json[0], series_json[1]
    if not isinstance(rows, list) or not rows:
        return False
    if isinstance(meta, dict) and isinstance(meta.get("total"), int) and meta["total"] <= 0:
        return False
    first = rows[0]
    return isinstance(first, dict) and "date" in first


def indicators_for_collection(catalogue_json: list) -> list[str]:
    """Return the World Bank indicator ids collected by Bronze.

    This keeps production ingestion aligned with bounded live checks: a curated
    broad indicator set first, then any rail indicators discovered from the
    catalogue.
    """
    discovered = discover_rail_indicators(catalogue_json)
    indicators = list(dict.fromkeys(list(EU_STATS_INDICATORS) + discovered))
    return [indicator for indicator in indicators if _valid_indicator_id(indicator)]


def ingest(lander: RawLander, session: requests.Session | None = None) -> list[str]:
    session = session or requests.Session()

    # 1) land + parse the indicator catalogue
    cat = session.get(CATALOGUE_URL, timeout=120)
    cat.raise_for_status()
    lander.land(RawArtifact(
        domain="stats", source="worldbank", dataset_id="_catalogue_indicators",
        filename="indicators.json", content=cat.content,
        source_url=CATALOGUE_URL, content_type="application/json",
        http_status=cat.status_code,
    ))
    try:
        indicators = indicators_for_collection(cat.json())
    except Exception:                                   # noqa: BLE001
        indicators = list(dict.fromkeys(list(EU_STATS_INDICATORS) + list(CONFIRMED_RAIL_INDICATORS)))
    logger.info("World Bank: %d indicators to pull.", len(indicators))

    # 2) land each indicator's full series as raw JSON -- but only if it is a
    #    real time series. The API answers 200 with a {"message": ...} error
    #    envelope for archived/invalid ids; landing those would record a
    #    ~128-byte error blob as if it were collected data.
    landed = []
    for ind in indicators:
        url = SERIES_URL.format(indicator=ind)
        try:
            r = session.get(url, timeout=120)
            if r.status_code != 200 or not r.content:
                logger.warning("Skipping %s (HTTP %s)", ind, r.status_code)
                continue
            try:
                payload = r.json()
            except ValueError:
                logger.warning("Skipping %s (non-JSON response)", ind)
                continue
            if not series_has_observations(payload):
                logger.warning(
                    "Skipping %s (no time series; error/empty payload)", ind)
                continue
            path = lander.land(RawArtifact(
                domain="stats", source="worldbank", dataset_id=ind,
                filename=f"{ind}.json", content=r.content, source_url=url,
                content_type="application/json", http_status=r.status_code,
            ))
            landed.append(path)
        except Exception as exc:                        # noqa: BLE001
            logger.error("World Bank fetch failed for %s: %s", ind, exc)
    logger.info("World Bank: landed %d/%d indicators.", len(landed), len(indicators))
    return landed
