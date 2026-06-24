"""
Eurostat Bronze fetcher.

Enumerate-by-name (your strategy), made a little more robust:
a dataset qualifies if its English title contains a rail term OR its code
sits in the rail/transport families -- minus an explicit stop-list. This
catches the three folders you named (railway transport `rail_*`, regional
transport `tran_r_*`, transport safety `tran_sf_*`/`rail_ac_*`) without
relying on the title alone.

We land:
  * the TOC itself (the discovery artifact), and
  * each matched dataset as the RAW gzipped TSV exactly as the API returns it.

No unpivot, no flag stripping, no geo filter -- that is all Silver's job.

Robustness notes (why this file is not a bare `requests.get`):
  * Eurostat's dissemination CDN frequently drops connections from clients that
    send no `User-Agent` (observed as `RemoteDisconnected` mid-run). We therefore
    attach a descriptive UA and a connection/read/status retry policy with
    backoff so a single transient disconnect does not abort the whole source.
  * The TOC mixes `folder`, `table`, and `dataset` rows. Only `dataset` rows are
    fetchable through the SDMX 2.1 data endpoint; `table`/`folder` codes return
    HTTP 404 there. Discovery now reads the TOC type column and skips the
    non-fetchable rows, removing the 404 noise seen in earlier live checks.
"""
import logging
import os
import re

import requests
from requests.adapters import HTTPAdapter

try:  # urllib3 ships with requests; guard only for exotic installs
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover - urllib3 always present with requests
    Retry = None

from ..lander import RawLander, RawArtifact

logger = logging.getLogger("bronze.eurostat")

TOC_URL = "https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/txt?lang=en"
DATA_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
    "{code}/?format=TSV&compressed=true"
)
MAX_COLLECTION_DATASETS = int(os.environ.get("EUROSTAT_MAX_DATASETS", "300"))
MAX_DATASET_BYTES = int(os.environ.get("EUROSTAT_MAX_DATASET_BYTES", str(50 * 1024 * 1024)))
_DATASET_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

# A descriptive UA keeps Eurostat's CDN from silently closing the connection.
USER_AGENT = (
    "railway-bigdata-course/1.0 "
    "(+https://github.com/pol3et/railway-bigdata)"
)

RAIL_TITLE_TOKENS = ("rail", "railway")
# `rail_*` is a rail-only code family (always in scope). `tran_r_*` (regional
# transport) and `tran_sf_*` (transport safety) also cover road/air/sea/all-mode,
# so those are only taken when the English title actually names rail.
RAIL_ONLY_PREFIX = "rail_"
BROAD_TRANSPORT_PREFIXES = ("tran_r_", "tran_sf_")
STOP_TOKENS = ("trailer",)   # avoid road "trailer" false-positives

# TOC `type` column values. Only datasets are served by the SDMX data endpoint;
# folders and aggregated tables 404 there, so we never enqueue them.
SKIP_TYPES = ("folder", "table")


def build_session(session: requests.Session | None = None) -> requests.Session:
    """Return a session with a descriptive UA and a retry/backoff policy.

    Idempotent: re-mounting on an already-prepared session is a no-op, so callers
    may pass their own session (e.g. tests) without losing the hardening.
    """
    session = session or requests.Session()
    # Be defensive: callers (and tests) may pass a minimal session object that
    # only implements `.get()`. Header/adapter hardening is best-effort so such
    # objects still work, while real `requests.Session`s get the full treatment.
    headers = getattr(session, "headers", None)
    if headers is not None:
        # Replace the default `python-requests/x.y` UA (which Eurostat's CDN
        # drops), but keep a UA the caller deliberately set.
        current_ua = headers.get("User-Agent", "")
        if not current_ua or current_ua.lower().startswith("python-requests"):
            headers["User-Agent"] = USER_AGENT
        headers.setdefault("Accept", "*/*")
    can_mount = callable(getattr(session, "mount", None))
    if (
        Retry is not None
        and can_mount
        and not getattr(session, "_railway_retry_mounted", False)
    ):
        retry = Retry(
            total=4,
            connect=4,
            read=4,
            status=3,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        # mark so a passed-in session is not re-mounted on every call
        session._railway_retry_mounted = True  # type: ignore[attr-defined]
    return session


def _strip(token: str) -> str:
    return token.strip().strip('"').strip("'")


def _valid_dataset_id(code: str) -> bool:
    return bool(_DATASET_ID_RE.fullmatch(code))


def _qualifies(title_lc: str, code_lc: str) -> bool:
    if any(s in title_lc for s in STOP_TOKENS):
        return False
    # the rail-only code family is always in scope
    if code_lc.startswith(RAIL_ONLY_PREFIX):
        return True
    has_rail_title = any(t in title_lc for t in RAIL_TITLE_TOKENS)
    # the broad regional/safety code spaces (tran_r_*, tran_sf_*) also carry
    # road/air/sea/all-mode datasets, so require the rail token in the title
    # rather than accepting the whole family on the code prefix alone.
    if code_lc.startswith(BROAD_TRANSPORT_PREFIXES):
        return has_rail_title
    # any other code: include only when the English title names rail
    return has_rail_title


def discover_rail_datasets(toc_text: str) -> list[str]:
    """Parse the tab-delimited TOC text and return matching dataset codes.

    Pure function (no network) so it can be unit-tested on a sample. When the TOC
    provides a `type` column (real Eurostat output), non-fetchable `folder`/`table`
    rows are skipped; two-column samples without a type column are unaffected.
    """
    found: set[str] = set()
    for line in toc_text.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        title = _strip(parts[0]).lower()
        code = _strip(parts[1])
        code_lc = code.lower()
        # skip folders/aggregated tables ('t_' tables); we want fetchable datasets
        if not code or code_lc.startswith("t_"):
            continue
        if not _valid_dataset_id(code):
            continue
        # when the TOC carries a type column, only datasets are fetchable
        if len(parts) >= 3 and _strip(parts[2]).lower() in SKIP_TYPES:
            continue
        if _qualifies(title, code_lc):
            found.add(code)
    logger.info("Discovered %d Eurostat rail datasets.", len(found))
    return sorted(found)


# Broad theme prefixes for the big-data Bronze net: transport, economy,
# labour/population/migration, living conditions / health / education / digital,
# and crime/safety. Prefix-based so it stays deterministic (no LLM, no titles).
EU_STATS_CODE_PREFIXES = (
    # transport
    "tran_", "rail_", "road_", "avia_", "iww_", "mar_", "mare_",
    # economy: national accounts, government finance, prices, business, trade
    "nama_", "nasa_", "gov_", "ei_", "sts_", "prc_", "irt_", "bop_",
    # labour, population, migration
    "demo_", "lfsi_", "lfsa_", "lfst_", "lfsq_", "lfso_", "une_", "earn_", "migr_",
    # quality of life: living conditions, health, education, digital, tourism
    "ilc_", "hlth_", "educ_", "isoc_", "tour_",
    # safety / crime
    "crim_",
)


# Regional / sub-national datasets we DO NOT want in the country-totals net.
# Eurostat marks regional (NUTS) breakdowns with the ``_r_`` infix
# (demo_r_, lfst_r_, tran_r_, ...), the ``10r`` regional national-accounts tag
# (nama_10r_*), and the metropolitan / urban-rural typologies (met_, urt_).
EU_STATS_REGIONAL_MARKERS = ("_r_", "10r", "_reg_")
EU_STATS_REGIONAL_PREFIXES = ("met_", "urt_", "tgs")


# Frequency suffixes that mark sub-annual datasets. We pull annual series only,
# so monthly (_m), quarterly (_q) and daily (_d) datasets are skipped at
# discovery (the Silver reader would drop them anyway, but this saves the
# download). The quarterly national-accounts family ``namq_`` is also dropped in
# favour of its annual counterpart ``nama_``.
EU_STATS_SUBANNUAL_SUFFIXES = ("_m", "_q", "_d")


def _is_subannual(code_lc: str) -> bool:
    return code_lc.endswith(EU_STATS_SUBANNUAL_SUFFIXES)


def _is_regional(code_lc: str) -> bool:
    if code_lc.startswith(EU_STATS_REGIONAL_PREFIXES):
        return True
    return any(m in code_lc for m in EU_STATS_REGIONAL_MARKERS)


# Transport theme, narrowed by request to rail and tran_* (safety /
# regional / modal-split), excluding aviation / maritime / inland-waterways / pipeline / road
# families and the tran_sf_avia / tran_sf_mar / tran_sf_road safety sub-themes. Regional
# and sub-annual transport series are still kept (no filters applied here).
EUROSTAT_TRANSPORT_PREFIXES = ("rail_", "tran_")

# Within the kept transport families, drop these sub-themes by request:
# maritime / road safety (and anything road/maritime/iww/pipeline is already
# excluded by leaving their prefixes out above).
EUROSTAT_TRANSPORT_EXCLUDE_PREFIXES = ("tran_sf_mar", "tran_sf_road", "tran_sf_avia")


def discover_transport_datasets(toc_text: str) -> list[str]:
    """Return every fetchable transport dataset (all sub-themes, incl. regional
    and sub-annual). Pure function; folder/table and ``t_`` rows are skipped."""
    found: set[str] = set()
    for line in toc_text.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code = _strip(parts[1])
        code_lc = code.lower()
        if not code or code_lc.startswith("t_"):
            continue
        if not _valid_dataset_id(code):
            continue
        if len(parts) >= 3 and _strip(parts[2]).lower() in SKIP_TYPES:
            continue
        if code_lc.startswith(EUROSTAT_TRANSPORT_EXCLUDE_PREFIXES):
            continue
        if code_lc.startswith(EUROSTAT_TRANSPORT_PREFIXES):
            found.add(code)
    logger.info("Discovered %d Eurostat transport datasets.", len(found))
    return sorted(found)


def discover_eu_datasets(toc_text: str) -> list[str]:
    """Broad, theme-based discovery for the big-data Bronze net.

    Returns every fetchable Eurostat *dataset* whose code starts with one of the
    theme prefixes in ``EU_STATS_CODE_PREFIXES`` (transport, economy, population,
    quality of life, safety). Regional / NUTS / metropolitan datasets are
    excluded so only country-level series are pulled. Pure function so it is
    unit-testable; folder/table rows and aggregated ``t_`` tables are skipped.
    """
    found: set[str] = set()
    for line in toc_text.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code = _strip(parts[1])
        code_lc = code.lower()
        if not code or code_lc.startswith("t_"):
            continue
        if not _valid_dataset_id(code):
            continue
        if len(parts) >= 3 and _strip(parts[2]).lower() in SKIP_TYPES:
            continue
        if _is_regional(code_lc):            # country totals only, skip NUTS/metro
            continue
        if _is_subannual(code_lc):           # annual series only, skip _m/_q/_d
            continue
        if code_lc.startswith(EU_STATS_CODE_PREFIXES):
            found.add(code)
    logger.info("Discovered %d Eurostat datasets across themes.", len(found))
    return sorted(found)


# Curated project allowlist: the specific NATIONAL, ANNUAL datasets we import.
# Replaces the broad prefix net so only relevant series are pulled (themes:
# rail/transport, economy, population, quality of life). Excluded by request:
# health, education, crime/justice, migration, road safety, internet use,
# life expectancy/fertility, employment (lfsi).
EUROSTAT_CURATED_DATASETS = (
    # --- transport / rail ---
    "rail_pa_total", "rail_go_total",
    "rail_if_line_tr", "rail_if_tracks", "rail_if_electri",
    "rail_eq_locon", "rail_eq_wagon",
    "rail_ac_catnmbr", "rail_ac_catvict",
    "rail_ec_emplo_a", "rail_ec_expend",
    "tran_hv_frmod", "tran_hv_psmod",
    "tran_sf_railvi", "tran_sf_railac",
    # --- economy & finance ---
    "nama_10_gdp", "nama_10_pc", "nama_10_a10",
    "gov_10dd_edpt1", "gov_10a_main",
    "prc_hicp_aind", "une_rt_a", "earn_nt_net",
    # --- population ---
    "demo_pjan", "demo_gind",
    # --- quality of life / living conditions ---
    "ilc_pw01", "ilc_pw05", "ilc_di12", "ilc_li02", "ilc_peps01", "ilc_mddd11",
    # --- urban audit: cities and greater cities (city-level geo) ---
    "urb_cpopstr", "urb_cecfi", "urb_ctran",
)


def datasets_for_collection(toc_text: str) -> list[str]:
    """Return the Eurostat dataset ids collected by Bronze.

    The production ingester and bounded live check use the same selection so the
    automatic-update path does not drift from the evidence path.
    """
    datasets = list(dict.fromkeys(
        list(EUROSTAT_CURATED_DATASETS) + discover_transport_datasets(toc_text)
    ))
    return [code for code in datasets if _valid_dataset_id(code)][:MAX_COLLECTION_DATASETS]


def _get_dataset_response(session, url: str, *, timeout: int, headers: dict | None = None):
    """Fetch a dataset with streaming when the session supports it."""
    kwargs = {"timeout": timeout}
    if headers is not None:
        kwargs["headers"] = headers
    try:
        return session.get(url, **kwargs, stream=True)
    except TypeError:
        # Test doubles and some minimal session objects accept narrower call
        # shapes than requests.Session.
        try:
            return session.get(url, **kwargs)
        except TypeError:
            return session.get(url, timeout=timeout)


def _bounded_dataset_content(response) -> bytes | None:
    length = response.headers.get("Content-Length")
    if length:
        try:
            if int(length) > MAX_DATASET_BYTES:
                return None
        except ValueError:
            pass

    iter_content = getattr(response, "iter_content", None)
    if callable(iter_content):
        chunks = []
        total = 0
        try:
            for chunk in iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_DATASET_BYTES:
                    close = getattr(response, "close", None)
                    if callable(close):
                        close()
                    return None
                chunks.append(chunk)
            return b"".join(chunks)
        except Exception:  # noqa: BLE001
            close = getattr(response, "close", None)
            if callable(close):
                close()
            raise

    content = response.content or b""
    if len(content) > MAX_DATASET_BYTES:
        return None
    return content


def _content_too_large(response) -> bool:
    return _bounded_dataset_content(response) is None


def ingest(lander: RawLander, session: requests.Session | None = None) -> list[str]:
    session = build_session(session)

    # 1) land the TOC itself, then discover from its bytes
    toc_resp = session.get(TOC_URL, timeout=60)
    toc_resp.raise_for_status()
    lander.land(RawArtifact(
        domain="stats", source="eurostat", dataset_id="_catalogue_toc",
        filename="toc_en.txt", content=toc_resp.content,
        source_url=TOC_URL, content_type="text/plain; charset=utf-8",
        http_status=toc_resp.status_code,
    ))
    codes = datasets_for_collection(toc_resp.text)

    # 2) land each dataset as raw gzipped TSV, unchanged
    landed = []
    for code in codes:
        url = DATA_URL.format(code=code)
        try:
            r = _get_dataset_response(session, url, timeout=120)
            if r.status_code != 200:
                logger.warning("Skipping %s (HTTP %s)", code, r.status_code)
                continue
            content = _bounded_dataset_content(r)
            if content is None:
                logger.warning(
                    "Skipping %s (dataset exceeds %d bytes)", code, MAX_DATASET_BYTES
                )
                continue
            if not content:
                logger.warning("Skipping %s (empty response)", code)
                continue
            path = lander.land(RawArtifact(
                domain="stats", source="eurostat", dataset_id=code,
                filename=f"{code}.tsv.gz", content=content,
                source_url=url,
                content_type=r.headers.get("Content-Type", "application/gzip"),
                http_status=r.status_code,
            ))
            landed.append(path)
        except Exception as exc:                       # noqa: BLE001
            logger.error("Eurostat fetch failed for %s: %s", code, exc)
    logger.info("Eurostat: landed %d/%d datasets.", len(landed), len(codes))
    return landed
