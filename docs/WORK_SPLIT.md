# Work Split And Gap Ownership

Date: 2026-06-21

This file is the planned collaboration map for classmates after the next session creates the GitHub-ready project structure.

## Sync Layers

The project has sync points where workstreams must agree before moving forward:

| Sync point | Purpose | Required before |
|---|---|---|
| S1: package/import contract | One import root and dependency setup. | Any large code move. |
| S2: data contracts | Bronze, Silver, Gold schemas stable. | Storage wiring and Spark jobs. |
| S3: local fixture E2E | Network-free full path works. | Live data runs. |
| S4: live Bronze/Silver/Gold run | Real data produces Gold artifact. | Report and presentation claims. |
| S5: Spark evidence | Big Data job output is generated. | Final course submission. |

## Workstream A - DevEx / Repo Owner

Goal: make the repo installable, testable, and contributor-friendly.

Owns:

- `pyproject.toml`
- `.gitignore`
- `CONTRIBUTING.md`
- test command,
- optional GitHub Actions,
- package layout migration support.

Initial tests:

- import package from installed editable mode,
- CLI/help import smoke,
- no accidental duplicate packages after migration.

Done when:

- `python -m pip install -e ".[test]"` works,
- `python -m pytest -q -m unit` runs,
- classmates can follow `README.md` setup without local path hacks.

## Workstream B - QA / Gap Register Owner

Goal: make failures actionable.

Owns:

- `docs/GAP_REGISTER.md`
- pytest markers,
- expected-failure policy,
- evidence format.

Initial tests:

- unit test suite exists,
- integration fixture suite exists,
- live tests are opt-in and cannot accidentally run long collectors.

Done when:

- every known failing test has a gap ID,
- every gap has owner, verification command, and closure criteria.

## Workstream C - Bronze Owner

Goal: one raw ingestion layer.

Owns:

- `RawArtifact`
- `RawLander`
- source scheduler,
- Eurostat,
- World Bank,
- GDELT,
- RSS,
- KSH,
- Statistik Austria,
- UIC,
- historical GDELT.

Initial tests:

- pure discovery/query functions,
- metadata/checksum helper,
- source adapters with mocked HTTP,
- scheduler imports all configured sources.

Done when:

- all source adapters live under one package,
- raw landing contract is unchanged,
- small Bronze fixture can be read by Silver.

## Workstream D - Silver Stats Owner

Goal: convert raw statistical sources into validated `StatFact` rows.

Owns:

- stats readers,
- source label parsing,
- crosswalk cache,
- deterministic merge.

Initial tests:

- Eurostat TSV melt,
- World Bank JSON parse,
- KSH/Statistik Austria/UIC parser contracts,
- crosswalk with LLM disabled,
- merge provenance.

Done when:

- fixture Bronze stats become Silver stats rows,
- unmapped labels are visible in an audit artifact,
- no numeric rows pass through an LLM.

## Workstream E - Silver News / Feature Audit Owner

Goal: convert news records into validated `NewsFeature` rows.

Owns:

- article input schema,
- Ollama prompt boundary,
- validation,
- event taxonomy,
- operator taxonomy,
- feature audit.

Initial tests:

- mocked Ollama extraction,
- bad JSON/model output handling,
- event/operator coercion,
- GDELT passthrough.

Done when:

- fixture news records become Silver news rows,
- extraction failures are logged and counted,
- feature coverage report exists.

## Workstream F - Gold Owner

Goal: produce analysis-ready feature matrix.

Owns:

- source priority policy,
- stats pivot,
- news aggregation,
- Gold Parquet writing,
- Gold loading contract for Spark.

Initial tests:

- conflict resolution,
- stats pivot,
- news aggregation,
- Parquet round trip.

Done when:

- fixture Silver inputs produce a Gold Parquet,
- output schema is documented,
- row/column counts are captured.

## Workstream G - Spark / Big Data Owner

Goal: prove Big Data technology usage.

Owns:

- Spark jobs,
- Spark output evidence,
- scalable read/write path,
- job documentation.

Initial tests:

- local Spark smoke if dependency/service is available,
- otherwise Spark job import/config tests and an opt-in marker.

Done when:

- a Spark job reads Gold/Silver data,
- output evidence includes row counts and generated files,
- command is documented in `README.md` and `docs/VERIFICATION.md`.

## Workstream H - Live Ops / Real Data Owner

Goal: run bounded real launches and document service/API issues.

Owns:

- `.env.example`,
- Docker Compose or service startup docs,
- live source runbook,
- real data evidence.

Initial tests:

- `docker compose ps` or service health checks,
- MinIO bucket access smoke,
- Ollama health check when needed,
- bounded live source pull.

Done when:

- a bounded real launch produces evidence,
- failed endpoints are listed with HTTP/status evidence,
- long-running collectors are controlled by explicit commands.

## Workstream I - Report / Presentation Owner

Goal: turn verified outputs into course deliverables.

Owns:

- report,
- presentation,
- charts/tables,
- practical-value narrative.

Initial checks:

- every claim links to an output file or command evidence,
- no fabricated source counts or model claims.

Done when:

- report and presentation use generated evidence,
- gaps are not hidden from the submission story.

## Assignment Rule

No one owns a gap by saying they will look at it. A person owns a gap only when they write:

- gap ID,
- planned files,
- expected test,
- verification command,
- sync point affected.
