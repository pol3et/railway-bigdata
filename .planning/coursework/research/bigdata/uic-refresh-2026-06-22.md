# UIC Refresh Research

Date: 2026-06-22

Task: `parser/uic-refresh`

## Local Research First

Files reviewed:

- `AGENTS.md`
- `README.md`
- `TASK.md`
- `WIRING.md`
- `docs/GAP_REGISTER.md`
- `docs/CODEMAP.md`
- `docs/DATA_CONTRACTS.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`
- `.planning/coursework/research/bigdata/undone-task-triage-2026-06-22.md`
- `src/railway_lakehouse/bronze/sources/uic.py`
- `src/railway_lakehouse/bronze/live_check.py`
- `tests/test_bronze_characterization.py`
- `tests/test_bronze_live_check.py`

## External Primary-Source Checks

- UIC identifies RAILISA as its official statistics tool for railway-company
  data and says it supports visualisation and downloads.
  Source: https://uic.org/support-activities/statistics/
- The public RAILISA list/download surface states that downloading data files
  requires annual access/subscription, with contact paths for UIC members and
  non-members.
  Source: https://uic-stats.uic.org/list/
- The RAILISA resources page exposes free statistical publications, including
  `Traffic Trends Among UIC Member Companies in 2024` and `Railway Statistics
  Synopsis - Edition 2025`.
  Source: https://uic-stats.uic.org/resources/
- The RAILISA API guide says REST access uses Basic or Token authentication.
  Source: https://uic-stats.uic.org/help_api_guide/

## Live Probes

Bounded direct probe command:

```powershell
@'
import requests
urls = [
    'https://uic-stats.uic.org/resources/help_resource/?id=12',
    'https://uic-stats.uic.org/resources/help_resource/?id=14',
    'https://uic.org/IMG/xls/uic_railway_statistics_synopsis.xls',
]
for url in urls:
    r = requests.get(url, timeout=30, headers={'User-Agent': 'railway-lakehouse-bronze/1.0'})
    print(url)
    print('status=', r.status_code, 'bytes=', len(r.content or b''), 'content-type=', r.headers.get('Content-Type'), 'prefix=', (r.content or b'')[:8])
'@ | python -
```

Observed output:

```text
https://uic-stats.uic.org/resources/help_resource/?id=12
status= 200 bytes= 591749 content-type= application/pdf prefix= b'%PDF-1.7'
https://uic-stats.uic.org/resources/help_resource/?id=14
status= 200 bytes= 1517491 content-type= application/pdf prefix= b'%PDF-1.5'
https://uic.org/IMG/xls/uic_railway_statistics_synopsis.xls
status= 404 bytes= 270 content-type= text/html; charset=iso-8859-1 prefix= b'<!DOCTYP'
```

## Findings

- The current `uic.py` seeds point at stale public XLS paths and skip all
  configured resources because the synopsis XLS URL returns HTTP 404.
- Current public UIC statistical artifacts found in this pass are PDFs exposed
  through `uic-stats.uic.org/resources/help_resource/`.
- Public RAILISA bulk selection downloads and the REST API are not safe to claim
  as open collector inputs without credentials/subscription.
- `live_check.py` has no UIC collector yet, so `parser/uic-refresh` needs source
  validation plus bounded local evidence support before any live UIC claim.

## Implementation Decision

- Refresh Bronze UIC seeds to the current free UIC statistical publication PDFs.
- Validate UIC responses by content signature so HTTP-200 HTML or empty bodies
  are rejected before landing.
- Record the RAILISA CSV/Excel/API access boundary in source metadata and docs.
- Add `uic` to the bounded live-check command as an explicit source; keep
  default live-check sources unchanged to avoid surprise network work.

