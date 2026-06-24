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

# A descriptive UA keeps Eurostat's CDN from silently closing the connection.
USER_AGENT = (
    "railway-bigdata-course/1.0 "
    "(+https://github.com/pol3et/railway-bigdata)"
)

RAIL_TITLE_TOKENS = ("rail", "railway")
RAIL_CODE_PREFIXES = ("rail_", "tran_r_", "tran_sf_")
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
        # when the TOC carries a type column, only datasets are fetchable
        if len(parts) >= 3 and _strip(parts[2]).lower() in SKIP_TYPES:
            continue
        if _qualifies(title, code_lc):
            found.add(code)
    logger.info("Discovered %d Eurostat rail datasets.", len(found))
    return sorted(found)


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
