# State re-audit + live tests + data inventory — 2026-06-23

Skill: `research-orchestrator`.
Routed MCP providers: **Context7** (pandas / pyarrow / Apache Spark docs), **Tavily**
(recent breaking-change notes, data-catalog best practice), **Exa** (catalog/observability
patterns), **Ref** (exact Spark version/JDK requirements). Run as two background
orchestration workflows (`railway-state-audit`, 21 agents; `undocumented-gap-hunt`).

Trigger: a couple of PRs merged (`silver/persist-outputs` GAP-006, `bronze/local-stats-landing`
+ `gold/first-real-result`, `infra/minio-storage` GAP-010). User asked to re-analyze
state, prove parsers/storage, run all local + integration + live tests, add a data
inventory with samples to the dashboard, and find undocumented gaps.

## Local research first

- Read `docs/{TASKS,GAP_REGISTER,STATE_AND_ROADMAP,DATA_CONTRACTS}.md`, `AGENTS.md`,
  `README.md`, `pyproject.toml`, `docker-compose.yml`, `scripts/minio_smoke.py`,
  and all of `src/railway_lakehouse/**` (pipeline, bronze, silver, gold).
- Two prior PR-review research files present:
  `pr13-minio-storage-review-2026-06-23.md`, `all-pr-ship-pr-review-2026-06-23.md`.

## Verification evidence produced this session (real, on disk)

- `python -m pytest -q` → **87 passed** (77 unit + 10 integration); `-m live` / `-m spark`
  select **0** (no such pytest tests); `compileall src tests` clean.
  Env: Python 3.14.0, pandas 3.0.3, pyarrow 24.0.0, s3fs 2024.6.1, pytest 9.0.3.
- **Live MinIO**: `docker compose up -d` → `railway-minio` Up (9000/9001); compose
  `createbuckets` created `bronze`/`silver`/`gold` via `mc`; `python scripts/minio_smoke.py`
  → 32 B s3fs write/read round-trip on the **bronze** bucket, `roundtrip_ok=true`.
- **Live network Bronze**: `bronze.live_check --sources eurostat,worldbank` → World Bank
  PASSED (3 artifacts, ~17 MB: IS.RRS.TOTL.KM, IS.RRS.GOOD.MT.K6, catalogue); Eurostat
  FAILED on a transient `RemoteDisconnected` on the catalogue TOC fetch (network flake).
- **Live pipeline**: `pipeline --bronze-root <wb> --skip-news-extraction --news 0` →
  Silver crosswalk 2/2 mapped, merge kept 35112/35112; Gold **2,968 rows × 4 cols**
  `[geo, year, rail_freight_tonne_km, rail_network_length_km]`, 151 geos, 1995–2021,
  AT/HU 27 rows each. AT 1995 freight=13715, network=5672.
- **Silver persist**: 35,112 StatFact rows persisted via `silver/persist.py` and reloaded
  identically; uploaded to MinIO `silver` bucket (manual, 35,961 B) to demonstrate the
  lakehouse holds Silver objects.
- **Ollama**: not installed (`command not found`) → NewsFeature LLM extraction has never
  run; design-only + mocked in tests.

## Q1 — pandas 3.0 / pyarrow 24 / Python 3.14 gotchas (Context7 + Tavily)

- `read_parquet`/constructors now return the **default `str`** dtype, not `object`;
  `dtype == 'object'` checks fail — use `pandas.api.types.is_string_dtype`. Default `str`
  uses `NaN`, while `astype('string')`/`Int64`/`Float64` use `pd.NA`.
  https://pandas.pydata.org/docs/user_guide/migration-3-strings.html
- **Copy-on-Write is the only mode**: chained assignment silently no-ops (use `.loc`);
  inplace methods return `self`; `.values`/`.to_numpy()` are read-only; `use_nullable_dtypes`
  removed from `read_parquet`; `assert_frame_equal(check_dtype=True)` can break str/Int64/Float64
  goldens. https://pandas.pydata.org/docs/whatsnew/v3.0.0.html
- Floors: pandas 2.3.3 is first Python-3.14-compatible; pandas 3.0 needs pyarrow≥13/numpy≥1.26;
  pyarrow 24 ships cp314 wheels; pandas is not thread-safe under free-threaded 3.14.
  https://pandas.pydata.org/docs/whatsnew/v2.3.3.html
- **Action**: `pyproject` floors (`pandas>=2.2`, `pyarrow>=15`) have no upper bound, so the
  suite runs on bleeding-edge 3.0/24. It passes today; pin an upper bound or add a CI matrix
  to avoid silent future breakage.

## Q2 — data-inventory dashboard best practice (Tavily + Exa)

- Per-dataset card answers four questions fast: what is it, where from (source + bronze/silver/gold
  layer), is it healthy (the five observability pillars), and what does it look like (schema +
  small sample). Lead the row with identity + freshness + status; keep samples small and clearly
  labeled non-authoritative. Sources: Collibra asset pages
  (https://productresources.collibra.com/docs/collibra/latest/Content/Catalog/AssetPages/co_catalog-asset-pages.htm),
  OvalEdge template (https://www.ovaledge.com/blog/data-catalog-template),
  Soda observability pillars (https://docs.soda.io/data-observability),
  Atlan column stats (https://atlan.com/what-is-a-data-dictionary),
  Adobe Experience Platform 100-row preview
  (https://experienceleague.adobe.com/en/docs/experience-platform/catalog/datasets/user-guide).
- **Applied**: dashboard section 03 = layer tallies + a source→Gold reach matrix + bounded,
  clearly-labeled real sample rows for Gold / Silver StatFact / ArticleRecord.

## Q3 — Spark 3.5 JDK + minimal Parquet coverage job (Context7 + Ref)

- Spark 3.5.x runs on **Java 8/11/17**, Scala 2.12/2.13, Python 3.8+; Java 8 < 8u371 is
  deprecated as of 3.5.0. https://spark.apache.org/docs/3.5.6/index.html
- Minimal coverage pattern: `SparkSession.builder...getOrCreate()`, `spark.read.parquet(dir)`
  (self-describing schema), `df.count()` for rows, `df.printSchema()` for schema, `groupBy`
  for per-key counts; write evidence out.
  https://spark.apache.org/docs/3.5.6/api/python/getting_started/quickstart_df.html
- **Action**: only Java 1.8.0_491 is installed; pyspark is a declared-but-uninstalled extra.
  For the report, prefer JDK 17 + `pip install pyspark==3.5.*`.

## Adversarial verification (8/8 load-bearing claims CONFIRMED)

World Bank E2E to real Gold; Eurostat parsed-but-unmapped; news parses to ArticleRecord but
NewsFeature never ran; Gold reads in-memory (not persisted) Silver (GAP-007); KSH/StatAustria/UIC
Bronze-only, no Silver reader; live MinIO works; no Spark/pyspark/JDK17; 87 green.
Key correction surfaced: `merge.read_eurostat_tsv` uses the SDMX **dimension-key header** as the
label, so real Eurostat maps to nothing — the human-readable fixture overstates Eurostat's reach.

See `.planning/COURSEWORK_PROGRESS.md` and `docs/PROGRESS_LOG.md` for the session entry, and
`docs/GAP_REGISTER.md` for new gaps from `undocumented-gap-hunt`.
