# Task Board

Snapshot: 2026-06-23. Canonical named task list for `bigdata/course_proj`.

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
| `silver/stats-parsers` | Silver: Eurostat + World Bank → StatFact | done (2 of 5) | GAP-006 · orig. task #9 |
| `silver/news-parsers` | Silver: RSS + GDELT → ArticleRecord → NewsFeature | done (LLM mocked in tests) | GAP-006 · orig. task #10 |
| `gold/feature-matrix` | Gold: (geo, year) матрица + Parquet + counts | done on a 4-row fixture | orig. task #11 |

## Now — active path

| Task (slug) | RU title | Stage | Depends on | Status | Maps to |
|---|---|---|---|---|---|
| `bronze/local-stats-landing` | Приземлить реальные Eurostat + World Bank stats в локальное Bronze-дерево | 1 | — | done | Phase A |
| `gold/first-real-result` | Прогнать pipeline по реальным stats → первый настоящий Gold Parquet + counts | 1 | `bronze/local-stats-landing` | done — live WB Bronze→Silver→Gold **2,968×4** (freight + network-km, 151 geos, 1995–2021) reproduced 2026-06-24; Eurostat still unmapped (GAP-013, Eurostat SDMX header) | Phase A · **MILESTONE** |
| `silver/persist-contract` | Заморозить схему и пути Parquet для локального Parquet-персиста Silver stats/news | 1 | — | done (frozen in `docs/DATA_CONTRACTS.md`) | GAP-006 · **unblocker** |
| `infra/minio-storage` | Поднять MinIO (Docker), включить живой lakehouse-путь | 1 | — | done + **live-proven 2026-06-24** (`docker compose up -d` + `scripts/minio_smoke.py` round-trip) | GAP-010 · Phase C |
| `infra/ollama-model` | Поставить Ollama + Qwen3-4B (q4_K_M) на GTX 1060, проверить JSON-извлечение на сэмпле | 1 | — | todo | LLM setup |
| `silver/persist-outputs` | Реализовать локальный персист Silver stats/news в Parquet по контракту | 2 | `silver/persist-contract` | done (`silver/persist.py` + tests; failure accounting remains in `silver/news-llm-extraction`) | GAP-006 |
| `gold/load-from-silver` | Подключить `gold/run.py` к чтению персистнутого Silver + integration-тест | 2 | `silver/persist-outputs` | todo | GAP-007 |
| `silver/news-llm-extraction` | Извлечение из новостей малой моделью, two-pass: LLM классифицирует → числа детерминированно; фичи новостей → Gold | 2 | `infra/ollama-model`, `silver/persist-contract` | todo | GAP-006 |
| `spark/evidence-job` | Spark-джоба читает реальный Gold, пишет evidence (версия, row counts, файлы) | 3 | `gold/first-real-result` (smoke); FAN-IN B (full) | todo | GAP-009 · orig. task #12 |
| `report/draft` | Черновик отчёта + презентации на основе Spark + Gold evidence | 3 | `spark/evidence-job` | todo | GAP-011 |

## Later — deferred (after the core is E2E)

| Task (slug) | RU title | Stage | Depends on | Status | Maps to |
|---|---|---|---|---|---|
| `bronze/gdelt-history-backfill` | Бэкафилл истории GDELT до 100k+ статей (объём) | 4 | `infra/minio-storage` | later | volume track |
| `silver/gdelt-gkg-parser` | Парсер GKG csv.zip → ArticleRecord (подключить `gdelt_passthrough`) | 4 | `bronze/gdelt-history-backfill` | later | volume track |
| `silver/stats-parsers-extra` | KSH XLSX / Statistik Austria ODS / UIC PDF → StatFact (3 параллельных парсера) | 4 | `silver/persist-contract` | later | GAP-006 (extra) |
| `bronze/scheduler-wiring` | Завести KSH/StatAustria/UIC в `bronze/run.py` (автообновления) | 4 | — | later | GAP-005 |

## Newly found gaps (re-audit 2026-06-24)

The `undocumented-gap-hunt` workflow surfaced **19 verified undocumented gaps**
(`GAP-012…030`, full list in `GAP_REGISTER.md`). Two touch the active path and should
be folded into the tasks above:

- **GAP-012** (high) — the documented Bronze→Gold reproduction recipe silently builds an
  empty Gold on a clean checkout (a committed `manifest.json` forces `live_check` run-id
  nesting). Fold into `gold/first-real-result` follow-up + `docs/VERIFICATION.md`.
- **GAP-013** (medium) — the live MinIO stats path reads Eurostat only and drops World
  Bank, so a genuinely-live Gold is feature-less. Fold into `gold/load-from-silver` /
  the live-MinIO wiring.
- Also relevant to `spark/evidence-job`: **GAP-017** (`pyspark>=3.5` resolves to Spark 4.x;
  pin 3.5.* + JDK 17) and **GAP-015/016** (Gold unit normalization + deterministic news schema).

See also: `STATE_AND_ROADMAP.md`, `GAP_REGISTER.md`, `WORK_SPLIT.md`.
