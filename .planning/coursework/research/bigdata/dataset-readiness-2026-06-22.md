# Dataset Readiness Estimate

Date: 2026-06-22

Task: estimate when all parsers can collect real site data and when the project
can produce an analysis-ready dataset.

## Local Sources Read

- `docs/PARSER_WORK_LOG.md`
- `docs/GAP_REGISTER.md`
- `docs/TEST_FIRST_INTEGRATION_PLAN.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`
- `README.md`
- `TASK.md`
- `src/railway_lakehouse/pipeline.py`
- `src/railway_lakehouse/bronze/live_check.py`

## Findings

- Bronze live collection is already proven for RSS, KSH, one Eurostat dataset
  probe, and three confirmed World Bank rail indicators.
- GDELT, Statistik Austria, UIC, and historical GDELT are not yet reliable live
  sources: current evidence shows HTTP 429, empty HTTP 200, HTTP 404, and HTTP
  429 respectively.
- The project does not yet have an analysis-ready Gold dataset because GAP-004,
  GAP-006, and GAP-007 remain open.
- Spark evidence is still open under GAP-009.

## Estimate

- A first useful dataset can be produced before every parser is complete by using
  the already proven Bronze sources: RSS, KSH, Eurostat, and World Bank.
- Full parser reliability depends on external site behavior. UIC may become a
  documented access-limit case rather than a working public artifact if no
  current public resource is available.
- The user-facing milestone table is recorded in `docs/PARSER_WORK_LOG.md`.
- The practical milestone order is:
  1. close remaining Bronze parser reliability work;
  2. implement fixture-backed Bronze reads and Silver persistence;
  3. emit Gold Parquet with row/column counts;
  4. add Spark evidence.
