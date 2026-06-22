# Wiring Remaining Bronze Sources

The source files now all live under `src/railway_lakehouse/bronze/sources/`.

The remaining Bronze wiring gap is GAP-005: the scheduler in `src/railway_lakehouse/bronze/run.py` still runs only Eurostat, World Bank, GDELT, and RSS.

## Desired Scheduler Extension

```python
from .sources import (
    eurostat,
    worldbank,
    gdelt,
    rss_media,
    ksh,
    statistik_austria,
    uic,
    past_recordings,
)

def run_stats() -> None:
    lander = RawLander()
    eurostat.ingest(lander)
    worldbank.ingest(lander)
    ksh.ingest(lander)
    statistik_austria.ingest(lander)
    uic.ingest(lander)
```

`past_recordings.py` is a one-off historical seed, not a weekly job by default.

## Historical News Seed

Run only after MinIO/service setup exists:

```bash
python -m railway_lakehouse.bronze.sources.past_recordings --dry-run
python -m railway_lakehouse.bronze.sources.past_recordings --max-pages 3
python -m railway_lakehouse.bronze.sources.past_recordings --target-articles 100000 --max-pages 0
python -m railway_lakehouse.bronze.sources.past_recordings --engine master_v1 --start 1990-01-01 --end 2014-12-31 --max-pages 30
```

It lands under `bronze/news/gdelt_history/...` and partitions by `ingest_date=`.

## Live-Run Notes

- The dataset ids/URLs in `ksh.py` now have bounded live evidence as of 2026-06-22, but they are still not wired into the scheduler.
- The dataset ids/URLs in `statistik_austria.py` remain documented seeds, not guaranteed-live endpoints.
- `uic.py` now uses current public UIC RAILISA resource PDFs and has bounded live evidence; subscribed RAILISA CSV/Excel/API access is still not available without credentials.
- Reconfirm national portal codes before making report claims.
- All source adapters require network access and MinIO configuration.
- The deterministic fixture E2E path exists; still do not run long collectors unless explicitly requested and bounded by an evidence plan.
