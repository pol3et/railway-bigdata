# GAP-033 News LLM Extraction Live Implementation Plan

Date: 2026-06-25
Status: Approved for implementation by Codex after local-code and routed-doc review.

## Scope Corrections

- Use `qwen3:4b`, not the stale `qwen3.5:9b-q8_0` model named in the old spec.
- Use the GAP-050 production runner through `railway_lakehouse.silver.run.run_news(...)`; do not add a new direct `extract_batch()` evidence loop.
- Keep the live pass bounded to about 30-50 real articles, one Ollama model pass at a time, with `OLLAMA_NUM_PARALLEL=1`.
- Persist only evidence outputs under `output/evidence/news-extraction-sample/`. Do not commit raw Bronze.
- Report the fields the current runner actually owns. Do not claim LLM-produced sentiment/operators/rail-lines if those remain unset by design.

## Implementation Steps

1. Add a live-marked regression test in `tests/test_silver_news_extraction_live.py`.
   - The test uses a hardcoded rail article and does not depend on coursework data.
   - It skips gracefully when `health_check()` is false.
   - Assertions cover `NewsFeature` structure, rail relevance, allowed country/event enums, summary presence, confidence bounds, and list-typed collection fields without requiring fields outside the current LLM contract to be populated.

2. Land a bounded real Bronze sample without committing raw Bronze.
   - Prefer existing Bronze source code and local evidence root `output/evidence/news-extraction-sample-bronze/`.
   - Attempt a real RSS sample and a small GDELT sample if network permits.
   - If one source fails, continue with the real source that landed and document the limitation. If no real articles land, stop blocked rather than fabricating.

3. Run the live extraction path through production code.
   - Read the landed Bronze articles with the current pipeline Bronze reader.
   - Call `railway_lakehouse.silver.run.run_news(...)` with `warm_up=True` behavior from the production entrypoint, `artifact_root=output/evidence/news-extraction-sample/silver`, and `ingest_date=2026-06-25`.
   - Use a runtime cache under ignored `output/runtime/` so the committed evidence includes outputs, not cache internals.
   - Preserve the generated run manifest and failure sidecar.

4. Persist and inspect evidence artifacts.
   - Persist canonical Silver news features with `persist.persist_news(...)`.
   - Build `output/evidence/news-extraction-sample/railway_ml.parquet` with `gold.build.build_from_silver(...)`.
   - Write `output/evidence/news-extraction-sample/counts.json` with `gold.build.write_gold_counts(...)`.
   - Reload persisted Parquet and compute actual shape, value counts, confidence stats, and sample rows.

5. Write the evidence manifest.
   - Create `output/evidence/news-extraction-sample/MANIFEST.md`.
   - Include real model digest, Ollama version, processed/succeeded/failed counts, failure-sidecar contents, wall-clock timing, persisted-row metrics, a sample row, and quality observations on actual `qwen3:4b` output.
   - Explicitly record any network-source limitation or persistent extraction failure.

6. Sync coursework and dashboard state.
   - Update `docs/GAP_REGISTER.md` for GAP-033 closure and the live-test mapping.
   - Update `docs/TASKS.md` and `docs/index.html` because this closes a gap and changes live dashboard state.
   - Append `docs/PROGRESS_LOG.md`.
   - Update `.planning/COURSEWORK_PROGRESS.md`.

7. Verify.
   - Run `python -m pytest tests/test_silver_news_extraction_live.py -m live -v`.
   - Reload the persisted Parquet and print shape plus `is_rail_related` counts.
   - Run `python -m pytest -q`.
   - Run `python -m compileall -q src tests`.
   - Run `git diff --check`.

8. Ship.
   - Commit only scoped source/docs/evidence artifacts.
   - Push `impl/gap-033`.
   - Open a PR against `main` with `gh`.
   - Confirm the PR reports a clean/mergeable state or record the blocker.

## Self-Review

- The plan keeps raw Bronze immutable and uncommitted.
- Numeric stat merging is untouched.
- The live test is bounded and skips when Ollama is offline.
- The evidence run uses production extraction code and records real outputs.
- Dashboard and coursework logs are included in Definition of Done.
