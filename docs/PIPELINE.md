# Railway Lakehouse Pipeline

Three layers, one flow: Bronze raw landing -> Silver normalization/extraction -> Gold feature matrix.

## Current Package Structure

```text
src/railway_lakehouse/
  bronze/
  silver/
  gold/
  pipeline.py
```

## Data Contract

| Stage | Reads | Produces |
|---|---|---|
| Bronze | live APIs, RSS feeds, national portals | raw bytes + `.meta.json` under `bronze/<domain>/<source>/<dataset>/ingest_date=YYYY-MM-DD/` |
| Silver stats | raw Eurostat TSV / World Bank JSON / national files | long `StatFact(geo, year, feature, value, unit, source_system, source_dataset, source_column)` rows |
| Silver news | raw GDELT/RSS article records | `NewsFeature` rows |
| Gold | Silver stats and news rows | wide Parquet at `(geo, year)` grain |

## Verified Local Commands

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

## Intended Bronze Commands

Do not run these as part of routine tests; they use live endpoints and MinIO.

```bash
python -m railway_lakehouse.bronze.run stats
python -m railway_lakehouse.bronze.run news
python -m railway_lakehouse.bronze.sources.past_recordings --target-articles 100
```

## Intended Silver Stats Usage

```python
from railway_lakehouse.silver.stats import merge as M

frames = []
for dataset_id, df in read_bronze_eurostat().items():
    long = M.read_eurostat_tsv(df, dataset_id)
    long["source_system"] = "eurostat"
    frames.append(long)

labels = sorted({label for frame in frames for label in frame["source_column"]})
crosswalk = M.build_crosswalk(labels, use_llm=False)
stats_long = M.merge_sources(frames, crosswalk)
```

## Intended Silver News Usage

```python
from railway_lakehouse.silver.news import extract as N
from railway_lakehouse.silver.ollama_client import health_check

assert health_check(), "start Ollama first"
articles = read_bronze_news(limit=100)
news_rows = N.extract_batch(articles)
```

## Intended Gold Usage

```python
from railway_lakehouse.gold.run import build_from_silver

build_from_silver(stats_long, news_rows, "output/evidence/live/railway_ml.parquet")
```

## Verified Fixture Pipeline

The driver imports successfully:

```bash
python -c "import railway_lakehouse.pipeline"
```

GAP-004 is closed for deterministic local Bronze fixtures. The fixture command is:

```bash
python -m railway_lakehouse.pipeline --bronze-root tests\fixtures\bronze --news 1 --out output\evidence\fixture-e2e\railway_ml.parquet --crosswalk-path output\evidence\fixture-e2e\crosswalk_cache.json --skip-news-extraction
```

Recorded evidence:

- `output/evidence/fixture-e2e/railway_ml.parquet`
- `output/evidence/fixture-e2e/crosswalk_cache.json`
- Parquet readback: 4 rows, 3 columns for `AT/HU` and `2020/2021`.

The full live command still must not be claimed as proven until live services and evidence are recorded:


```bash
python -m railway_lakehouse.pipeline --news 100 --out output/evidence/live/railway_ml.parquet
```
