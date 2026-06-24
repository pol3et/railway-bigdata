You are implementing one task in the railway-lakehouse big-data course project.
The repo's `AGENTS.md` is authoritative and auto-loaded — follow its Hard Rules
(raw Bronze immutable; numeric stat merges deterministic, never LLM-rewritten;
outputs under `output/`; no fabricated data; tests must not depend on `coursework/`
data — use `tmp_path`/fixtures; keep the live dashboard in sync).

## Your task: GAP-013

Implement it EXACTLY as written below. Do not widen scope.

### GAP-013 — Live MinIO stats path must read World Bank, not only Eurostat

`MID` · level **pipeline** · effort **S** · depends on: none (reuses existing `silver.stats.load.load_worldbank_frame`; fsspec `memory://` injection proven by GAP-020; GAP-014 UTF-8 `_read_text` fix already merged).

**Build:** Wire World Bank into the live (s3/MinIO) branch of `pipeline._read_bronze_stats_frames` so a genuinely-live Gold stats matrix is no longer silently empty, and WARN when a live stats read produces zero World Bank frames.

**Context.** `src/railway_lakehouse/pipeline.py` drives Bronze→Silver→Gold. `_read_bronze_stats_frames(lander)` (pipeline.py:209-226) has two backends:
- **local** (`lander.bronze_root` set) → `stats_load.frames_from_bronze(root)`, which reads BOTH Eurostat **and** World Bank (`silver/stats/load.py:87-111`, `_SOURCES` includes `worldbank`).
- **live MinIO** (`lander.s3`, no `bronze_root`) → the `else` branch calls only `_read_bronze_eurostat(lander)` and tags every frame `source_system='eurostat'`. **World Bank is never read.**

World Bank is currently the only source that maps to a Gold feature on the live path (`rail_network_length_km`, `rail_freight_tonne_km`). So a live MinIO run produces an empty/feature-less Gold stats matrix; the committed headline WB Gold (2,968×4) was produced via the local `--bronze-root` path, not live MinIO.

**Problem (exact).** pipeline.py:220-225 — the live branch is Eurostat-only:
```python
raw_eurostat_tables = _read_bronze_eurostat(lander)
frames = []
for dataset_id, df in raw_eurostat_tables.items():
    long = stats_merge.read_eurostat_tsv(df, dataset_id)
    long["source_system"] = "eurostat"
    frames.append(long)
return frames
```
No World Bank reader on the live path; no warning when WB is absent.

**Steps.**
1. Read `_read_bronze_stats_frames` (pipeline.py:209-226), `_read_bronze_eurostat` (194-205) as the per-source template, `_list_bronze_files` (264-277), `_read_tsv`/`_read_text` (285-297), `_dataset_id_from_path` (300-301). Read `silver/stats/load.py:39-57` (`load_worldbank_frame(raw: bytes, dataset_id) -> DataFrame` — deterministic, tags `source_system='worldbank'`, returns EMPTY on error-envelope/no-data/non-JSON) and `frames_from_bronze` (87-111) which **skips `_`-prefixed dataset dirs** and reads only the latest partition.
2. Add `_read_bytes(lander, path) -> bytes` mirroring `_read_text` (Path → `path.read_bytes()`; else `with lander.s3.open(path, "rb") as f: return f.read()`).
3. Add `_read_bronze_worldbank(lander) -> list[pd.DataFrame]`: iterate `_list_bronze_files(lander, domain="stats", source="worldbank", include=lambda name: name.endswith(".json"))`; `dataset_id = _dataset_id_from_path(path, "worldbank")`; **skip `dataset_id.startswith("_")`**; `frame = stats_load.load_worldbank_frame(_read_bytes(lander, path), dataset_id)`; append iff `not frame.empty`.
4. Rewrite the live branch of `_read_bronze_stats_frames` to combine Eurostat frames (as today) with `wb_frames = _read_bronze_worldbank(lander)`. If `not wb_frames`, `log.warning("live stats read produced 0 World Bank frames; live Gold stats matrix may be feature-less. Check bronze/stats/worldbank/*/ingest_date=*/*.json landed via the lander.")`. Return `eurostat_frames + wb_frames`. Do NOT change the local branch.
5. `stats_load` is already imported (pipeline.py:31). No new Silver/Gold logic; no LLM; no numeric rewriting.
6. New test `tests/test_pipeline_live_stats_worldbank.py`, `pytestmark = pytest.mark.integration`, no Docker/MinIO/network — inject `lander = SimpleNamespace(s3=fsspec.filesystem("memory"))` (clear `fs.store` first per GAP-020). Seed under the `bronze/` root: a real WB `[meta, records]` JSON at `bronze/stats/worldbank/IS.RRS.TOTL.KM/ingest_date=2026-06-23/IS.RRS.TOTL.KM.json` (+ `.meta.json`) and a Eurostat `.tsv` at `bronze/stats/eurostat/<ds>/ingest_date=2026-06-23/<ds>.tsv` (+ `.meta.json`). Use a tiny valid WB body with HUN/AUT records and known values.
7. Assertions (closure criterion): `frames = pipeline._read_bronze_stats_frames(lander)` returns ≥1 frame with `source_system == "worldbank"` AND ≥1 with `source_system == "eurostat"`; WB `value`s equal the seeded JSON values byte-for-byte; geos include mapped `HU`/`AT`. Second test: WB-less live seed (eurostat only) logs the zero-WB WARNING (`caplog`).
8. Run `python -m pytest -q -m integration` then full `python -m pytest -q`; both green. `python -m compileall -q src tests` clean.
9. Append a Test Failure Mapping row to `docs/GAP_REGISTER.md` (exact command + result + `GAP-013`) and flip GAP-013 toward `closed` with evidence. If pipeline state advances, sync `docs/TASKS.md` + `docs/index.html`.

**Files to touch:** `src/railway_lakehouse/pipeline.py` · `tests/test_pipeline_live_stats_worldbank.py` (new) · `docs/GAP_REGISTER.md` · `docs/TASKS.md` + `docs/index.html` (only if state changes). Do NOT modify `tests/fixtures/bronze/**`.

**Definition of Done (contract).**
- [ ] Live (s3) `_read_bronze_stats_frames` returns World Bank frames tagged `source_system='worldbank'` in addition to Eurostat, reusing `stats_load.load_worldbank_frame` (no reimplementation, no LLM, no numeric rewriting).
- [ ] `_`-prefixed WB datasets skipped; `.meta.json` sidecars excluded.
- [ ] Live branch logs a WARNING when zero World Bank frames are read.
- [ ] New `tests/test_pipeline_live_stats_worldbank.py` (`pytest.mark.integration`, fsspec `memory://`) asserts a `source_system='worldbank'` frame is returned alongside Eurostat, WB values byte-identical to the seed, and the zero-WB WARN fires.
- [ ] `python -m pytest -q -m integration` green; full `python -m pytest -q` green; `python -m compileall -q src tests` clean.
- [ ] `docs/GAP_REGISTER.md` mapping row + GAP-013 status/evidence; dashboard synced if state changed.

**Verify:** `python -m pytest -q -m integration tests/test_pipeline_live_stats_worldbank.py  (then full gate: python -m pytest -q)`

**Pitfalls.** Raw Bronze immutability — seed in-memory via `fs.pipe('bronze/...', bytes)`, never modify `tests/fixtures/bronze/`. fsspec MemoryFileSystem store is process-global — clear it; glob returns leading-slash `str` (don't coerce to Path). s3 glob rooted at `BRONZE_BUCKET` — seed under `bronze/`. Determinism — WB numbers come straight from JSON; no Ollama, no network. Scope — only the live `else` branch changes; leave local branch, Eurostat reader, news path untouched. Test artifacts under `tmp_path`/in-memory only.

## How to work
- Drive this with your **`$ship-it`** workflow, with **NO Linear** — all context lives in
  this repo's code and docs (`AGENTS.md`, `docs/GAP_TASKS.md`, `docs/GAP_REGISTER.md`,
  `docs/DATA_CONTRACTS.md`, `docs/TASKS.md`, `docs/STATE_AND_ROADMAP.md`). Do not look for or
  expect a ticket.
- First write **one** implementation plan, **review and approve it yourself**, then implement
  strictly against that approved plan. Keep the plan scoped to this gap only.
- If you need ANY external research, use the **`/research-orchestrator`** skill and route through
  its MCP providers (Context7, Ref, Tavily, Exa, Firecrawl). Cite source URLs for any external
  claim; record research in `.planning/coursework/research/bigdata/gap013-*.md` (a research
  record already exists there — extend it rather than duplicate).
- Write the **integration test** above; MinIO is available on localhost:9000 if you want a
  live cross-check, but the closure test must be deterministic fsspec `memory://` (no Docker).
- Run the task's **Verify** command and the full suite (`python -m pytest -q`) and make them
  green before you open the PR.
- This advances/closes a gap → update `docs/GAP_REGISTER.md`, and `docs/TASKS.md` + `docs/index.html`
  in the SAME change if state changes (AGENTS dashboard-sync Hard Rule) or CI will flag it.
- Branch `impl/gap-013` is already checked out in this worktree. Commit, push to origin, and
  open a PR against `main` with `gh` (you have write access).

## Definition of done (do not stop until ALL are true)
- The task's Definition-of-Done checklist items are met.
- `python -m pytest -q` is green; `python -m compileall -q src tests` clean.
- A PR against `main` exists and is **mergeable** (no conflicts, CI reminder satisfied).

## Final output
When done, your final message MUST be a single JSON object: the branch, PR url+number,
which test tiers you ran and their result, whether it is mergeable, which Definition-of-Done
items are met, and (if you had to stop early) blocked=true with the blocker. No prose outside the JSON.
