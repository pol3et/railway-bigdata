### GAP-013 — Live MinIO stats path must read World Bank, not only Eurostat

`MID` · level **pipeline** · effort **S** · depends on: none (reuses existing `silver.stats.load.load_worldbank_frame`; fsspec `memory://` injection proven by GAP-020; GAP-014 UTF-8 `_read_text` fix already merged).

**Build:** Wire World Bank into the live (s3/MinIO) branch of `pipeline._read_bronze_stats_frames` so a genuinely-live Gold stats matrix is no longer silently empty, and WARN when a live stats read produces zero World Bank frames.

**Context.** `src/railway_lakehouse/pipeline.py` drives Bronze→Silver→Gold. `_read_bronze_stats_frames(lander)` (pipeline.py:209-226) has two backends:
- **local** (`lander.bronze_root` set) → `stats_load.frames_from_bronze(root)`, which reads BOTH Eurostat **and** World Bank (`silver/stats/load.py:87-111`, `_SOURCES` includes `worldbank`).
- **live MinIO** (`lander.s3`, no `bronze_root`) → the `else` branch calls only `_read_bronze_eurostat(lander)` and tags every frame `source_system='eurostat'`. **World Bank is never read.**

World Bank is currently the only source that maps to a Gold feature on the live path (`rail_network_length_km`, `rail_freight_tonne_km`). So a live MinIO run produces an empty/feature-less Gold stats matrix; the committed headline WB Gold (2,968×4) was produced via the local `--bronze-root` path, not live MinIO. This is the live-path correctness gap.

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
There is no World Bank reader on the live path and no warning when WB is absent.

**Steps.**
1. Read `_read_bronze_stats_frames` (pipeline.py:209-226), `_read_bronze_eurostat` (194-205) as the per-source template, `_list_bronze_files` (264-277), `_read_tsv`/`_read_text` (285-297), `_dataset_id_from_path` (300-301). Read `silver/stats/load.py:39-57` (`load_worldbank_frame(raw: bytes, dataset_id) -> DataFrame` — deterministic, tags `source_system='worldbank'`, returns EMPTY on error-envelope/no-data/non-JSON) and `frames_from_bronze` (87-111) which **skips `_`-prefixed dataset dirs** (e.g. `_catalogue_*`) and reads only the latest partition.
2. Add `_read_bytes(lander, path) -> bytes` mirroring `_read_text` (Path → `path.read_bytes()`; else `with lander.s3.open(path, "rb") as f: return f.read()`).
3. Add `_read_bronze_worldbank(lander) -> list[pd.DataFrame]`: iterate `_list_bronze_files(lander, domain="stats", source="worldbank", include=lambda name: name.endswith(".json"))`; for each path derive `dataset_id = _dataset_id_from_path(path, "worldbank")`; **skip `dataset_id.startswith("_")`** (catalogue); `frame = stats_load.load_worldbank_frame(_read_bytes(lander, path), dataset_id)`; append iff `not frame.empty`.
4. Rewrite the live branch of `_read_bronze_stats_frames` to combine Eurostat frames (as today) with `wb_frames = _read_bronze_worldbank(lander)`. If `not wb_frames`, `log.warning("live stats read produced 0 World Bank frames; live Gold stats matrix may be feature-less. Check bronze/stats/worldbank/*/ingest_date=*/*.json landed via the lander.")`. Return `eurostat_frames + wb_frames`. Do not change the local branch.
5. Import `load` as `stats_load` is already imported (pipeline.py:31). No new Silver/Gold logic; no LLM; no numeric rewriting.
6. New test `tests/test_pipeline_live_stats_worldbank.py`, `pytestmark = pytest.mark.integration`, no Docker/MinIO/network — inject `lander = SimpleNamespace(s3=fsspec.filesystem("memory"))` (clear `fs.store` first per GAP-020). Seed under the `bronze/` BRONZE_BUCKET root: a real WB `[meta, records]` JSON at `bronze/stats/worldbank/IS.RRS.TOTL.KM/ingest_date=2026-06-23/IS.RRS.TOTL.KM.json` (+ `.meta.json` sidecar) and a Eurostat `.tsv` at `bronze/stats/eurostat/<ds>/ingest_date=2026-06-23/<ds>.tsv` (+ sidecar). Use a tiny but valid WB body with HUN/AUT records and known values.
7. Test assertions (closure criterion): `frames = pipeline._read_bronze_stats_frames(lander)` returns ≥1 frame with `source_system == "worldbank"` AND ≥1 with `source_system == "eurostat"`; the WB frame's `value`s equal the seeded JSON values byte-for-byte (no rewriting); geos include the mapped `HU`/`AT`. Second assertion: with a WB-less live seed (only eurostat), `_read_bronze_stats_frames` logs the zero-WB WARNING (use `caplog`).
8. Run `python -m pytest -q -m integration` then full `python -m pytest -q`; both green. `python -m compileall -q src tests` clean.
9. Append a Test Failure Mapping row to `docs/GAP_REGISTER.md` (exact command + result + `GAP-013`) and flip the GAP-013 entry toward `closed` with evidence. If pipeline state advances, sync `docs/TASKS.md` + `docs/index.html` (dashboard-sync Hard Rule).

**Files to touch:** `src/railway_lakehouse/pipeline.py` (add `_read_bytes`, `_read_bronze_worldbank`, rewrite live branch of `_read_bronze_stats_frames` + WARN) · `tests/test_pipeline_live_stats_worldbank.py` (new) · `docs/GAP_REGISTER.md` (mapping row + GAP-013 status/evidence) · `docs/TASKS.md` + `docs/index.html` (only if state changes) · `tests/fixtures/bronze/**` (read-only reference; do NOT modify).

**Definition of Done (contract).**
- [ ] Live (s3) `_read_bronze_stats_frames` returns World Bank frames tagged `source_system='worldbank'` in addition to Eurostat, reusing `stats_load.load_worldbank_frame` (no reimplementation, no LLM, no numeric rewriting).
- [ ] `_`-prefixed WB datasets (catalogue) are skipped; `.meta.json` sidecars excluded.
- [ ] The live branch logs a WARNING when zero World Bank frames are read.
- [ ] New `tests/test_pipeline_live_stats_worldbank.py` (`pytest.mark.integration`, fsspec `memory://`, no Docker/MinIO/network) asserts a `source_system='worldbank'` frame is returned alongside Eurostat from a both-sources seed, WB values are byte-identical to the seed, and the zero-WB WARN fires.
- [ ] `python -m pytest -q -m integration` green; full `python -m pytest -q` green with no regressions; `python -m compileall -q src tests` clean.
- [ ] `docs/GAP_REGISTER.md` has the mapping row and the GAP-013 entry reflects new evidence; dashboard synced if state changed.

**Verify:** `python -m pytest -q -m integration tests/test_pipeline_live_stats_worldbank.py  (then full gate: python -m pytest -q)`

**Pitfalls.**
- Raw Bronze immutability: do NOT modify `tests/fixtures/bronze/`; seed the in-memory s3 side via `fs.pipe('bronze/...', bytes)`.
- fsspec MemoryFileSystem store is process-global — clear it at test start to avoid glob leakage. `glob` returns leading-slash `str` paths; do not coerce to `Path` (they must take the s3 branch).
- The s3 glob is rooted at `BRONZE_BUCKET` (pipeline.py:275); seed under `bronze/` or the pattern won't match.
- Determinism: WB numbers come straight from the JSON via `load_worldbank_frame`; never route stats through Ollama or mutate values. No network.
- Scope discipline: only the live `else` branch changes. Leave the local `bronze_root` branch, Eurostat reader, and news path untouched.
- Output discipline: test artifacts under `tmp_path`/in-memory only — never repo root.
