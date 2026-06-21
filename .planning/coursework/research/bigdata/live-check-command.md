# Bronze Live Check Command Research

Date: 2026-06-21

Task: add `python -m railway_lakehouse.bronze.live_check` so parser owners can run a bounded live Bronze collection check without MinIO.

## Local Sources Read

- `AGENTS.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/GAP_REGISTER.md`
- `docs/DATA_CONTRACTS.md`
- `docs/CODEMAP.md`
- `WIRING.md`
- `docs/WORKSTREAMS.md`
- Local search: `rg -n "live_check|live-check|manifest|Artifact|Landing|bronze/|rss|ksh|KSH|RSS|raw" .`

## Findings

- Bronze artifacts must remain raw bytes plus metadata sidecars.
- Required path layout is `bronze/<domain>/<source>/<dataset_id>/ingest_date=YYYY-MM-DD/<file>` plus `<file>.meta.json`.
- Existing `RawLander` writes to MinIO, so the live check needs a local writer with the same path semantics, not the scheduler.
- `docs/PARSER_WORK_LOG.md` identifies Wave 2 as this command shape and says RSS plus KSH are the current proven live sources.
- `docs/GAP_REGISTER.md` maps bounded live evidence to GAP-010 and national source scheduling to GAP-005.
- No Spark, Ollama, MinIO, scheduler, or long GDELT backfill is needed for this task.

## External Research

No external docs were needed. This is a repo-local command that uses the existing Bronze artifact contract and existing source adapter behavior; there are no Spark or third-party API surface claims to verify.

## Implementation Notes

- Add tests first for local landing and manifest behavior.
- Keep defaults bounded through `--max-artifacts`.
- Record source status, artifact paths, byte counts, HTTP statuses, failures, and run timestamp in `manifest.json`.
- Run the requested bounded command for `rss,ksh` only after tests pass.
