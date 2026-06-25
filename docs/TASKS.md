# Task Board

Snapshot: 2026-06-25. Canonical named task list for `bigdata/course_proj`.

Each task has a stable slug name (e.g. `gold/first-real-result`). **The slug is the
cross-link key**: the same slugs are used in the team chat list, so a task named in
chat maps 1:1 to a row here. Detail lives in `STATE_AND_ROADMAP.md` (roadmap phases)
and `GAP_REGISTER.md` (gap IDs). Statuses are grounded in committed evidence; no task
is marked done without it.

Legend: `done` = verified · `todo` = on the active path · `later` = deferred until the
core is working end-to-end.

## Execution Stages (fan-out / fan-in)

Work is organized into stages. Inside a stage, tasks **fan out** (run in parallel,
different owners). Between stages there is a **fan-in barrier**: all parallel work in
the stage must be merged and the barrier condition met before the next stage starts.
Only the data spine (`①→②→⑦→⑧`) is strictly sequential.

```
STAGE 1  ── FAN-OUT · 4 parallel tracks ────────────────────────────────
  data:      ① bronze/local-stats-landing ─▶ ② gold/first-real-result   🏁
  contract:  silver/persist-contract        (freeze Silver Parquet schema+paths)
  storage:   ⑤ infra/minio-storage
  llm:       infra/ollama-model             (Qwen3-4B on the 1060, JSON works)
                              │
        ╔═════════════════════▼═════════════════════╗
        ║ FAN-IN A — sync: contract frozen           ║
        ║ + first real Gold committed                ║
        ║ + MinIO up + LLM verified on a sample      ║
        ╚═════════════════════╤═════════════════════╝
                              │
STAGE 2  ── FAN-OUT · 3 tracks on the frozen contract ──────────────────
  persist:   ③ silver/persist-outputs ─▶ ④ gold/load-from-silver
  news:      ⑥ silver/news-llm-extraction   (news features → Gold)
                              │
        ╔═════════════════════▼═════════════════════╗
        ║ FAN-IN B — sync: clean persisted           ║
        ║ Bronze→Silver→Gold (with news),            ║
        ║ row/col counts recorded                    ║
        ╚═════════════════════╤═════════════════════╝
                              │
STAGE 3  ── SPINE · sequential ─────────────────────────────────────────
  ⑦ spark/evidence-job ─▶ ⑧ report/draft
  (⚡ a Spark smoke run is allowed right after FAN-IN A on the stats-only Gold)
                              │
STAGE 4  ── FAN-OUT · deferred (volume + coverage) ─────────────────────
  bronze/gdelt-history-backfill ─▶ silver/gdelt-gkg-parser
  silver/stats-parsers-extra:  KSH ‖ StatAustria ‖ UIC
  bronze/scheduler-wiring
                              │
        ╔═════════════════════▼═════════════════════╗
        ║ FAN-IN C → re-run ⑦ spark on the larger    ║
        ║ dataset → finalize ⑧ report                ║
        ╚════════════════════════════════════════════╝
```

Stage ↔ roadmap mapping: Stage 1–2 ≈ `STATE_AND_ROADMAP.md` Phases A–C; Stage 3 =
Spark + report; Stage 4 = the deferred volume/coverage track.

The single most important unblocker is `silver/persist-contract`: once the Silver
Parquet schema and paths are frozen, `④`, `⑥`, and `silver/stats-parsers-extra` all
develop against it independently with no schema collisions.

## Done

| Task (slug) | RU title | Status | Maps to |
|---|---|---|---|
| `silver/stats-parsers` | Silver: Eurostat + World Bank → StatFact | done (5 of 5 including KSH, UIC, and Statistik Austria extra parsers) | GAP-006 · orig. task #9 |
| `silver/news-parsers` | Silver: RSS + GDELT → ArticleRecord → NewsFeature | done (LLM mocked in tests) | GAP-006 · orig. task #10 |
| `gold/feature-matrix` | Gold: (geo, year) матрица + Parquet + counts | done on a 4-row fixture | orig. task #11 |
| `tests/s3-bronze-readback` | Deterministic s3/MinIO Bronze read-back coverage via fsspec memory:// | done (`tests/test_pipeline_s3_readback.py`; 6 unit tests; full suite 93 passed) | GAP-020 / GAP-014 |
| `spark/evidence-job` | Spark reads real Gold and writes evidence | done (`output/evidence/spark/manifest.json`; Spark 4.1.2; Gold 2,968×4 -> coverage 2,968×5; 1 part-file + `_SUCCESS`) | GAP-009 · orig. task #12 |
| `report/draft` | Report + presentation drafts from committed evidence | done (`output/report/REPORT.md`, `output/presentation/PRESENTATION.md`, `tests/test_report_evidence_links.py`) | GAP-011 |
| `silver/eurostat-to-gold` | Eurostat: resilient Bronze + dataset-aware SDMX → canonical features → Gold | done (PR #21) — 6 national rail datasets → Silver 9,744 rows → Gold **1,554×10** (8 mapped features, 42 geos, 1962–2025); evidence `output/evidence/eurostat-silver-gold/` | GAP-023 · 2nd real source |
| `bronze/broad-stats-pipeline` | Broaden production Eurostat + World Bank stats collection without drifting from live checks | done (PR #25) — production and bounded live-check selectors are shared; Eurostat has curated+transport bounds and size caps; World Bank pulls curated EU-stats indicators plus discovered rail IDs; review evidence produced 14 Bronze stats artifacts, 152,054 counted observations, and a stats-only 3,550×11 Gold smoke under `output/evidence/pr25-bigdata-live-*` | GAP-010 · stats volume |
| `silver/stats-ksh-xlsx-reader` | KSH XLSX → Silver `StatFact` | done — deterministic `openpyxl` reader registered as `ksh`; live KSH Bronze probe parsed all six current XLSX artifacts; `tests/test_silver_stats_ksh.py` passed 9 tests; full suite passed 136 tests, 1 skipped | GAP-006 · extra stats parser 1/3 |
| `silver/stats-uic-pdf-reader` | UIC PDF → Silver `StatFact` | done — deterministic `pdfplumber` table reader registered as `uic`; original PR #26 evidence parsed the current UIC synopsis PDF to 39 unified rows across AT/HU and 9 mapped features; GAP-041 removes the parser's AT/HU-only geo gate and adds a staging audit trail while keeping the golden stats path deterministic | GAP-006 · extra stats parser 2/3 |
| `silver/uic-pdf-widen-and-stage` | UIC PDF: widen geo + stage all rows + traffic-trends text | done — UIC parser now recognizes EU/adjacent ISO alpha-2/alpha-3 codes beyond AT/HU, stages table/header/unmapped rows and Traffic Trends text chunks to `silver/uic_staging`, and has Parquet round-trip coverage | GAP-041 · stats volume + audit trail |
| `spark/analysis-artifact-snapshot` | Spark correlation + regional analysis snapshot | done — rerunnable jobs added under `src/railway_lakehouse/spark_jobs/`; committed CSV/manifest snapshot moved to `output/evidence/analysis-artifacts/`; default committed Gold path now exists, and the jobs fail loudly until passed a wider Gold with rail-investment/regional columns | GAP-009 extension |

## Now — active path

| Task (slug) | RU title | Stage | Depends on | Status | Maps to |
|---|---|---|---|---|---|
| `bronze/local-stats-landing` | Приземлить реальные Eurostat + World Bank stats в локальное Bronze-дерево | 1 | — | done; PR #25 broadens the automatic stats net while keeping bounded live checks aligned with production selectors | Phase A |
| `gold/first-real-result` | Прогнать pipeline по реальным stats → первый настоящий Gold Parquet + counts | 1 | `bronze/local-stats-landing` | done — live WB Bronze→Silver→Gold **2,968×4** (freight + network-km, 151 geos, 1995–2021) reproduced 2026-06-24; Eurostat now mapped → Gold too (GAP-023, PR #21) | Phase A · **MILESTONE** |
| `silver/persist-contract` | Заморозить схему и пути Parquet для локального Parquet-персиста Silver stats/news | 1 | — | done (frozen in `docs/DATA_CONTRACTS.md`) | GAP-006 · **unblocker** |
| `infra/minio-storage` | Поднять MinIO (Docker), включить живой lakehouse-путь | 1 | — | done + **live-proven 2026-06-24** (`docker compose up -d` + `scripts/minio_smoke.py` round-trip) | GAP-010 · Phase C |
| `infra/ollama-model` | Поставить Ollama + Qwen3-4B (q4_K_M) на GTX 1060, проверить JSON-извлечение на сэмпле | 1 | — | done 2026-06-25 — Ollama 0.30.9 served `qwen3:4b` (Q4_K_M) on the GTX 1060; GAP-033 live sample passed and records the API digest in `output/evidence/news-extraction-sample/MANIFEST.md` | LLM setup |
| `silver/persist-outputs` | Реализовать локальный персист Silver stats/news в Parquet по контракту | 2 | `silver/persist-contract` | done (`silver/persist.py` + tests; failure accounting remains in `silver/news-llm-extraction`) | GAP-006 |
| `gold/load-from-silver` | Подключить `gold/run.py` к чтению персистнутого Silver + integration-тест | 2 | `silver/persist-outputs` | done (`gold.run` reads persisted Silver, writes Gold + counts; integration + CLI smoke passed) | GAP-007 |
| `silver/news-llm-extraction` | Извлечение из новостей малой моделью, two-pass: LLM классифицирует → числа детерминированно; фичи новостей → Gold | 2 | `infra/ollama-model`, `silver/persist-contract` | done for first live evidence 2026-06-25 — 40 real `NewsFeature` rows persisted and a news-only Gold traceability row written under `output/evidence/news-extraction-sample/`; wider Gold aggregation is closed by GAP-040, while quality/eval remains GAP-043 | GAP-033 |
| `spark/evidence-job` | Spark-джоба читает реальный Gold, пишет evidence (версия, row counts, файлы) | 3 | `gold/first-real-result` (smoke); FAN-IN B (full) | done — local Spark coverage evidence written to `output/evidence/spark/` (Spark 4.1.2; input 2,968×4; output 2,968×5; 1 part-file + `_SUCCESS`); PR #27 adds correlation/regional jobs plus an artifact snapshot, but full reruns require a wider Gold with investment/regional columns | GAP-009 · orig. task #12 |
| `report/draft` | Черновик отчёта + презентации на основе Spark + Gold evidence | 3 | `spark/evidence-job` | done — `output/report/REPORT.md` + `output/presentation/PRESENTATION.md`, guarded by `tests/test_report_evidence_links.py` | GAP-011 |

## Later — deferred (after the core is E2E)

| Task (slug) | RU title | Stage | Depends on | Status | Maps to |
|---|---|---|---|---|---|
| `bronze/gdelt-history-backfill` | Бэкафилл истории GDELT до 100k+ статей (объём) | 4 | `infra/minio-storage` | later | volume track |
| `silver/gdelt-gkg-parser` | Парсер GKG csv.zip → NewsFeature passthrough (transient `GKGRecord`) | 4 | `bronze/gdelt-history-backfill` for live volume | done — production Bronze reader parses GKG zip fixtures and routes deterministic passthrough; live volume feed remains later | GAP-031 · volume track |
| `silver/stats-parsers-extra` | KSH XLSX / Statistik Austria ODS / UIC PDF → StatFact (3 параллельных парсера) | 4 | `silver/persist-contract` | in_progress — KSH XLSX and UIC PDF done; Statistik Austria ODS pending | GAP-006 (extra) |
| `silver/gdelt-gkg-parser` | Парсер GKG csv.zip → ArticleRecord (подключить `gdelt_passthrough`) | 4 | `bronze/gdelt-history-backfill` | later | volume track |
| `silver/stats-parsers-extra` | KSH XLSX / Statistik Austria ODS / UIC PDF → StatFact (3 параллельных парсера) | 4 | `silver/persist-contract` | in_progress — KSH XLSX and UIC PDF done; UIC widen+staging audit trail done; Statistik Austria ODS pending | GAP-006 (extra) |
| `silver/stats-parsers-extra` | KSH XLSX / Statistik Austria ODS / UIC PDF → StatFact (3 параллельных парсера) | 4 | `silver/persist-contract` | done — KSH XLSX, UIC PDF, and Statistik Austria ODS readers are registered and tested | GAP-006 (extra) |
| `bronze/scheduler-wiring` | Завести KSH/StatAustria/UIC в `bronze/run.py` (автообновления) | 4 | — | later | GAP-005 |

## Newly found gaps (re-audit 2026-06-24)

The `undocumented-gap-hunt` workflow surfaced **19 verified undocumented gaps**
(`GAP-012…030`, full list in `GAP_REGISTER.md`). GAP-012 and GAP-013 are closed:

- **GAP-012** (closed 2026-06-24) — the documented Bronze→Gold reproduction
  recipe now uses `output/evidence/local-stats-bronze-regen`, and the pipeline
  raises on a missing/empty local `--bronze-root` instead of writing empty Gold.
- **GAP-013** (closed 2026-06-24) — the live MinIO stats path now reads World Bank
  JSON in addition to Eurostat (`_read_bronze_worldbank` reusing
  `silver.stats.load.load_worldbank_frame`) and WARNs on zero WB frames, so a
  genuinely-live Gold is no longer silently feature-less. Verified by a
  deterministic fsspec `memory://` integration test (`pytest -q -m integration
  tests/test_pipeline_live_stats_worldbank.py`).
- **GAP-014** (medium) — closed 2026-06-24 by forcing the s3/MinIO text read branch to
  decode UTF-8 from bytes and covering it in `tests/test_pipeline_s3_readback.py`.
- **GAP-020** (medium) — closed 2026-06-24 by deterministic fsspec memory:// unit tests
  for the s3 Bronze read-back branch; no Docker/MinIO required.
- Also relevant to `spark/evidence-job`: **GAP-017** pins the chosen Spark 4.1 Python
  packages (`pyspark==4.1.*`, `delta-spark==4.1.*`) and records the JDK 17/21 +
  `JAVA_HOME` requirement plus S3A Maven packages
  `org.apache.hadoop:hadoop-aws:3.4.1,software.amazon.awssdk:bundle:2.24.6`;
  **GAP-015/016** cover Gold unit normalization + deterministic news schema.

## Execution waves & contracts (2026-06-24)

Ordered batches with a **stop-and-sync** between each. Tasks in a wave run in parallel;
merge them all, then verify the wave **contract** (the audit checklist) before the next wave.
Mirrors the dashboard "Execution plan" section. Urgency: `[!]` urgent · `H` high · `M` mid · `L` low.

### Wave 1 — Unblock & pin (parallel)
- `[x]` GAP-012 — documented Bronze→Gold regen recipe fixed
- `[x]` GAP-017 / `[x]` GAP-018 — pinned the **Spark 4.1 stack** (`pyspark==4.1.*` + `delta-spark==4.1.*` + `hadoop-aws==3.4.1`) with **JDK 17/21** + `JAVA_HOME` documented (GAP-017), and bounded pandas/pyarrow majors + `constraints.txt` + env guard (GAP-018). (Spark 4.1 is the only line that supports the repo's Python 3.14.)
- `[x]` GAP-020 — s3/MinIO Bronze read-back path covered by fsspec memory:// tests (closed 2026-06-24; also closes GAP-014 UTF-8 read parity)

**Contract A (verify before Wave 2):**
- [x] On a clean checkout, the two documented commands regenerate the real Gold + `counts.json` (2,139×3; no empty Gold).
- [x] `pip install .[spark]` resolves a pyspark **4.1.x** (coherent with delta-spark 4.1.x + hadoop-aws 3.4.1 Maven coord) — **verified** (`--dry-run` → pyspark 4.1.2 + delta-spark 4.1.0); GAP-009 provisioned JDK 21 for the local Spark evidence run.
- [x] `python -m pytest -q` green; a guard test fails on a wrong-major pandas/pyarrow.

### Wave 2 — Spark fast track (parallel)
- `[x]` GAP-009 — `spark/evidence-job`: Spark reads real Gold → writes evidence
- `[x]` GAP-007 — Gold CLI reads persisted Silver and writes counts

**Contract B (verify before Wave 3):**
- [x] Spark job writes `output/evidence/spark/` with Spark version, in/out row+col counts, files written.
- [x] Recorded counts match the Gold Parquet; job is re-runnable.
- [x] Gold built from persisted Silver via `gold.run` (GAP-007), not in-memory.

### Wave 3 — Report kickoff (sequential) 🏁 END OF FAST TRACK
- `[x]` GAP-011 — `report/draft` grounded in Spark + Gold evidence (state WB-only/＋Eurostat scope honestly); drafts live under `output/report/` and `output/presentation/` with evidence-link test coverage.

### Wave 4 — Make the report full (parallel)
- `[x]` eurostat→Gold mapping (GAP-023) — **done (PR #21)**: 2nd real stats source, 8 mapped features → Gold 1,554×10 (evidence `output/evidence/eurostat-silver-gold/`)
- `[x]` `infra/ollama-model` + `silver/news-llm-extraction` — first live `qwen3:4b` news extraction evidence persisted (`output/evidence/news-extraction-sample/`); model-quality gates remain in Wave 6
- `[x]` GAP-013 (live-MinIO World Bank) — **closed 2026-06-24** (live stats path now reads WB + Eurostat)
- `[x]` GAP-019 (deployable automatic updates) — **closed 2026-06-24** (preflight-degrade scheduler + Compose `scheduler` service + systemd/cron runbook)

**Contract C (verify before Wave 5 / final report):**
- [ ] Gold carries ≥2 stats sources **and** `news_*` columns in one refreshed report-grade matrix. GAP-033 adds a bounded news-only Gold traceability file; the combined full matrix is still open.
- [ ] A live MinIO Bronze→Silver→Gold run completes end-to-end (no `--bronze-root`).
- [ ] A scheduled run lands fresh Bronze (automatic-updates demo).
- [x] Bounded stats-only review smoke proves Eurostat + World Bank can land together
  and build a wider Gold matrix locally (`output/evidence/pr25-bigdata-live-gold/`,
  no MinIO/Ollama/news/Spark claim).

### Wave 5 — Coverage · volume · polish (parallel, deferrable)
- `M` KSH/StatAustria/UIC Silver readers + GAP-005 scheduler wiring — KSH XLSX and UIC PDF readers done; StatAustria ODS still pending
- `M` GDELT history backfill (GKG parser/passthrough production-wired; live volume feed still later)
- `M` robustness: GAP-015/016/021/022/025/026 (GAP-014 closed 2026-06-24)
- `M` KSH/StatAustria/UIC Silver readers + GAP-005 scheduler wiring — all three extra Silver readers done; scheduler wiring still pending
- `M` GDELT history backfill + GKG parser (volume)
- `M` robustness: GAP-015/021/025 (GAP-014 closed 2026-06-24; GAP-016/022/026 closed by GAP-040)
- `L` GAP-028 CI, GAP-027/029/030 docs/ops
- → re-run Spark on the larger dataset → finalize report.

### Wave 6 — News & model preprocessing (GAP-031…044, added 2026-06-25)

Multi-model news feature pipeline (extract-wide in Silver → filter/dedup/cluster in Spark). Detailed specs: `GAP_TASKS.md`; design contract + the **8 must-fix review blockers** + single-box plan (Ryzen 5 1600 / GTX 1060 6 GB → **sequential model passes**, torch CPU-only on Py3.14): `SPEC_NEWS_PREPROCESSING.md`. Build **MVP-first**; model-heavy tasks are fast-follow gated on the MVP being green. Urgency: `P0` blocker · `P1` high · `P2` mid · `P3` deferred.

- `[x]` GAP-039 `silver/wide-newsfeature-contract` — wide schema + idempotent content-hash cache (43-field `NewsFeature`, digest-pinned cache, JSON failure sidecar)
- `[x]` GAP-050 `silver/llm-pipeline-engineering` — prompt + sequential cached runner + retries/failure accounting + lifecycle hooks + run manifest wired into the production news entrypoints
- `[x]` GAP-033 `silver/news-llm-extraction-live` — live `qwen3:4b` pass completed on 40 real articles; Silver Parquet, run manifest, empty failure sidecar, news-only Gold traceability, and human manifest committed under `output/evidence/news-extraction-sample/`
- `[x]` GAP-031 `silver/gdelt-gkg-parser` — transient `GKGRecord`, GKG csv.zip parser, production runner passthrough routing, fixture-only tests
- `[P1]` GAP-035 `silver/language-id` (fastText, CPU) ‖ GAP-034 `silver/sentiment-encoder` (XLM-R, CPU-first)
- `[P1]` GAP-040 `gold/widen-news-aggregation` (+GAP-016/022/026) ‖ GAP-043 `eval/news-model-quality-harness` ‖ GAP-044 `tests/parser-correctness-audit`
- `[P2]` GAP-032 `silver/news-capture-widening` ‖ `[x]` GAP-036 `silver/news-embeddings-dedup` (e5-base embeddings + production deterministic local dedup markers; Spark enforcement remains GAP-037/GAP-040) ‖ GAP-041 `silver/uic-pdf-widen-and-stage` ‖ GAP-042 `silver/stataustria-ods-reader`
- `[P2]` GAP-032 `silver/news-capture-widening` ‖ GAP-036 `silver/news-embeddings-dedup` (**e5/bge-m3, NOT LaBSE**) ‖ GAP-041 `silver/uic-pdf-widen-and-stage` ‖ GAP-042 `silver/stataustria-ods-reader`
- `[P3]` GAP-037 `spark/news-clustering` (separate artifact, not a Gold column — SPARK-21679) ‖ GAP-038 `silver/news-ner` (conditional) ‖ GAP-031-v2 live GKG history volume evidence
- `[P1]` GAP-035 `silver/language-id` (fastText, CPU) ‖ `[x]` GAP-034 `silver/sentiment-encoder` (pinned XLM-R, CPU-first) ‖ `[P1]` GAP-031 `silver/gdelt-gkg-parser` (v1: DOC-field recovery + wire passthrough)
- `[x]` GAP-042 `silver/stataustria-ods-reader` — deterministic Statistik Austria ODS reader registered as `statistik_austria`; freight and rolling-stock ODS fixtures parse to `StatFact`
- `[P1]` GAP-035 `silver/language-id` (fastText, CPU) ‖ GAP-034 `silver/sentiment-encoder` (XLM-R, CPU-first) ‖ GAP-031 `silver/gdelt-gkg-parser` (v1: DOC-field recovery + wire passthrough)
- `[x]` GAP-040 `gold/widen-news-aggregation` — deterministic language/confidence/rail_lines/GKG rollups + year-month option (+GAP-016/022/026)
- `[P1]` GAP-043 `eval/news-model-quality-harness` ‖ GAP-044 `tests/parser-correctness-audit`
- `[x]` GAP-035 `silver/language-id` — pinned Lingua EN/DE/HU detector populates `language` before the LLM; prompt/schema no longer include language
- `[P1]` GAP-034 `silver/sentiment-encoder` (XLM-R, CPU-first) ‖ GAP-031 `silver/gdelt-gkg-parser` (v1: DOC-field recovery + wire passthrough)
- `[P1]` GAP-040 `gold/widen-news-aggregation` (+GAP-016/022/026) ‖ GAP-043 `eval/news-model-quality-harness` ‖ GAP-044 `tests/parser-correctness-audit`
- `[x]` GAP-041 `silver/uic-pdf-widen-and-stage` — UIC geo gate widened beyond AT/HU; UIC table/text staging contract and Parquet round-trip added
- `[P2]` GAP-032 `silver/news-capture-widening` ‖ GAP-036 `silver/news-embeddings-dedup` (**e5/bge-m3, NOT LaBSE**) ‖ GAP-042 `silver/stataustria-ods-reader`
- `[P2]` GAP-032 `silver/news-capture-widening` ‖ GAP-036 `silver/news-embeddings-dedup` (**e5/bge-m3, NOT LaBSE**) ‖ GAP-041 `silver/uic-pdf-widen-and-stage`
- `[P3]` GAP-037 `spark/news-clustering` (separate artifact, not a Gold column — SPARK-21679) ‖ GAP-038 `silver/news-ner` (conditional) ‖ GAP-031-v2 GKG csv.zip history parser

**Contract D (verify before claiming the news-model track done):** `[x]` real `NewsFeature` rows reach Gold from a live Ollama run (GAP-033); `[x]` GDELT GKG parser/passthrough has fixture-backed production-runner coverage (GAP-031); `[ ]` the eval harness reports per-feature metrics on a held-out golden TEST set; `[ ]` dedup is shown to deflate inflated `(geo,year)` counts; `[x]` closed gaps sync `docs/TASKS.md` + `docs/index.html`.

### Wave 7 — Spark EDA → hypotheses → analysis → report (GAP-045…049, the finale)

The closing arc. Full plan + Contracts E/F: `docs/ROADMAP_NEWS_TO_REPORT.md`. **Strictly EDA-first: hypotheses are formed FROM the artifacts (GAP-048), never pre-listed.** Embedder default `multilingual-e5-base` (config knob). Investment X = Eurostat `rail_investment` (dense), news money secondary.

- `[x]` GAP-045 `add-macro-indicators` — closed 2026-06-25: `IS.VEH.PCAR.P3` + `PA.NUS.PPP` are in World Bank Bronze collection and deterministic Silver/Gold mapping. Evidence `output/evidence/macro-indicators-gap045/` proves `ppp_conversion_factor` for AT/HU; `cars_per_1000` is wired but current WB API has 0 AT/HU non-null rows, so H17 must report coverage.
- `[P1]` GAP-046 `spark-eda-harness` — iterative Spark EDA → artifacts only (all-pairs corr + YoY deltas + lag + panels + coverage + top-correlations) → `output/evidence/eda/`
- `[P1]` GAP-047 `analysis-integration` — `analysis_artifacts/` inbox + Spark `verify_analyses` (teammate claims recompute vs current Gold → confirmed/drifted/broken) + empty `docs/HYPOTHESES.md`
- `[P1]` GAP-048 `hypothesis-analyses-spark` — **form hypotheses from EDA**, then Spark analyses (corr/lag/panel/clustering; AT-vs-HU; investment↔everything+deltas)
- `[P1]` GAP-049 `final-eda-analysis-report` — report grounded in EDA + analysis evidence, deterministic checker, honest limitations

**Contract E (Session B):** every source parser → Silver → Gold; full feature matrix (rail + macro + news + UIC, geo-widened) builds end-to-end; all model passes run sequentially within the 6 GB budget.
**Contract F (Session C):** every report claim cites a committed `output/evidence/eda|analysis/` artifact; teammate analyses re-verified vs current Gold; hypotheses trace to EDA artifacts; limitations stated honestly.

See also: `GAP_TASKS.md` (detailed per-gap implementation specs + contracts), `STATE_AND_ROADMAP.md`, `GAP_REGISTER.md`, `WORK_SPLIT.md`.
