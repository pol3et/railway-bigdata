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
"""
import logging
import requests

from ..lander import RawLander, RawArtifact

logger = logging.getLogger("bronze.eurostat")

TOC_URL = "https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/txt?lang=en"
DATA_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
    "{code}/?format=TSV&compressed=true"
)

RAIL_TITLE_TOKENS = ("rail", "railway")
RAIL_CODE_PREFIXES = ("rail_", "tran_r_", "tran_sf_")
STOP_TOKENS = ("trailer",)   # avoid road "trailer" false-positives


def _qualifies(title_lc: str, code_lc: str) -> bool:
    if any(s in title_lc for s in STOP_TOKENS):
        return False
    if code_lc.startswith(RAIL_CODE_PREFIXES):
        return True
    if any(t in title_lc for t in RAIL_TITLE_TOKENS):
        # for the broad transport-safety/regional code spaces, require the
        # rail token in the title; otherwise accept any 'rail' title.
        return True
    return False


def discover_rail_datasets(toc_text: str) -> list[str]:
    """Parse the tab-delimited TOC text and return matching dataset codes.

    Pure function (no network) so it can be unit-tested on a sample.
    """
    found: set[str] = set()
    for line in toc_text.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        title = parts[0].strip().lower()
        code = parts[1].strip().strip('"').strip("'")
        code_lc = code.lower()
        # skip folders/tables ('t_' aggregated tables); we want datasets
        if not code or code_lc.startswith("t_"):
            continue
        if _qualifies(title, code_lc):
            found.add(code)
    logger.info("Discovered %d Eurostat rail datasets.", len(found))
    return sorted(found)


def ingest(lander: RawLander, session: requests.Session | None = None) -> list[str]:
    session = session or requests.Session()

    # 1) land the TOC itself, then discover from its bytes
    toc_resp = session.get(TOC_URL, timeout=60)
    toc_resp.raise_for_status()
    lander.land(RawArtifact(
        domain="stats", source="eurostat", dataset_id="_catalogue_toc",
        filename="toc_en.txt", content=toc_resp.content,
        source_url=TOC_URL, content_type="text/plain; charset=utf-8",
        http_status=toc_resp.status_code,
    ))
    codes = discover_rail_datasets(toc_resp.text)

    # 2) land each dataset as raw gzipped TSV, unchanged
    landed = []
    for code in codes:
        url = DATA_URL.format(code=code)
        try:
            r = session.get(url, timeout=120)
            if r.status_code != 200 or not r.content:
                logger.warning("Skipping %s (HTTP %s)", code, r.status_code)
                continue
            path = lander.land(RawArtifact(
                domain="stats", source="eurostat", dataset_id=code,
                filename=f"{code}.tsv.gz", content=r.content,
                source_url=url,
                content_type=r.headers.get("Content-Type", "application/gzip"),
                http_status=r.status_code,
            ))
            landed.append(path)
        except Exception as exc:                       # noqa: BLE001
            logger.error("Eurostat fetch failed for %s: %s", code, exc)
    logger.info("Eurostat: landed %d/%d datasets.", len(landed), len(codes))
    return landed
