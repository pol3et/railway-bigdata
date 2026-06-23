# Task Board

Snapshot: 2026-06-23. Canonical named task list for `bigdata/course_proj`.

Each task has a stable slug name (e.g. `gold/first-real-result`). **The slug is the
cross-link key**: the same slugs are used in the team chat list, so a task named in
chat maps 1:1 to a row here. Detail lives in `STATE_AND_ROADMAP.md` (roadmap phases)
and `GAP_REGISTER.md` (gap IDs). Statuses are grounded in committed evidence; no task
is marked done without it.

Legend: `done` = verified · `todo` = on the active path · `later` = deferred until the
core is working end-to-end.

## Done

| Task (slug) | RU title | Status | Maps to |
|---|---|---|---|
| `silver/stats-parsers` | Silver: Eurostat + World Bank → StatFact | done (2 of 5) | GAP-006 · orig. task #9 |
| `silver/news-parsers` | Silver: RSS + GDELT → ArticleRecord → NewsFeature | done (LLM mocked in tests) | GAP-006 · orig. task #10 |
| `gold/feature-matrix` | Gold: (geo, year) матрица + Parquet + counts | done on a 4-row fixture | orig. task #11 |

## Now — core path to the first real Gold result

Ordered. The first real Gold needs no LLM and no MinIO (`--skip-news-extraction`).

| # | Task (slug) | RU title | Status | Maps to |
|---|---|---|---|---|
| 1 | `bronze/local-stats-landing` | Приземлить реальные Eurostat + World Bank stats в локальное Bronze-дерево (раскладка как в фикстурах) | todo | Roadmap Phase A |
| 2 | `gold/first-real-result` | Прогнать pipeline по реальным stats → первый настоящий Gold Parquet + row/col counts | todo | Roadmap Phase A · **MILESTONE** |
| 3 | `silver/persist-outputs` | Персистить Silver stats/news в каноничные Parquet-пути | todo | GAP-006 · Phase B |
| 4 | `gold/load-from-silver` | Подключить `gold/run.py` к чтению персистнутого Silver + integration-тест | todo | GAP-007 · Phase B |
| 5 | `infra/minio-storage` | Поднять MinIO (Docker), включить живой lakehouse-путь чтения/записи | todo | GAP-010 · Phase C |
| 6 | `silver/news-llm-extraction` | Включить извлечение из новостей малой моделью (Qwen3-4B), two-pass: LLM классифицирует — детерминированно достаём числа | todo | GAP-006 · Phase C |
| 7 | `spark/evidence-job` | Spark-джоба читает реальный Gold Parquet, пишет evidence (версия, row counts, файлы) | todo | GAP-009 · orig. task #12 |
| 8 | `report/draft` | Черновик отчёта + презентации на основе Spark + Gold evidence | todo | GAP-011 |

## Later — backfill, volume, coverage (after the core is E2E)

| Task (slug) | RU title | Status | Maps to |
|---|---|---|---|
| `bronze/gdelt-history-backfill` | Бэкафилл истории GDELT до 100k+ статей (объём для Spark) | later | volume track |
| `silver/gdelt-gkg-parser` | Парсер GKG csv.zip → ArticleRecord (подключить `gdelt_passthrough`) | later | volume track |
| `silver/stats-parsers-extra` | KSH XLSX / Statistik Austria ODS / UIC PDF → StatFact | later | GAP-006 (extra) |
| `bronze/scheduler-wiring` | Завести KSH/StatAustria/UIC в `bronze/run.py` (автообновления) | later | GAP-005 |

See also: `STATE_AND_ROADMAP.md`, `GAP_REGISTER.md`, `WORK_SPLIT.md`.
