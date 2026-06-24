# GAP-013 — Live MinIO stats path must read World Bank, not only Eurostat (spec research)

Date: 2026-06-24
Skill: research-orchestrator (local-materials-first lens).
MCP providers routed: Tavily (one confirmatory pass; see below). The fix is
fully grounded in in-repo source — no external API was load-bearing.

## Task
Write an implementation-ready spec for GAP-013: the live MinIO branch of
`pipeline._read_bronze_stats_frames` reads only Eurostat, silently dropping World
Bank — the only source that currently maps to a Gold feature
(`rail_network_length_km` / `rail_freight_tonne_km`). A genuinely-live Gold stats
matrix is therefore silently empty; the headline WB Gold was produced via the
local `--bronze-root` path, not the live MinIO path.

## Local files read (with the load-bearing lines)
- `docs/GAP_REGISTER.md` — GAP-013 row (line 45). Closure criterion: a test drives
  `_read_bronze_stats_frames` via a fake lander exposing `.s3` (no `bronze_root`)
  seeded with both `stats/worldbank/*.json` and `stats/eurostat/*.tsv` and asserts
  a `source_system='worldbank'` frame is returned; live branch WARNs on zero WB
  frames; `pytest -q -m integration`.
- `src/railway_lakehouse/pipeline.py:209-226` — `_read_bronze_stats_frames`. The
  local branch (`bronze_root` set) delegates to `stats_load.frames_from_bronze`,
  which reads BOTH Eurostat and World Bank. The live `else` branch only calls
  `_read_bronze_eurostat(lander)` and tags `source_system='eurostat'` — WB is
  never read. **This is the exact bug.**
- `src/railway_lakehouse/pipeline.py:194-205` — `_read_bronze_eurostat`: the
  template for a per-source live reader (`_list_bronze_files` →
  `_dataset_id_from_path` → `_read_tsv`).
- `src/railway_lakehouse/pipeline.py:264-297` — `_list_bronze_files` (s3 glob
  `{BRONZE_BUCKET}/{domain}/{source}/*/ingest_date=*/*` + `_is_data_file`
  sidecar filter), `_read_tsv`, `_read_text` (now reads bytes and decodes UTF-8 —
  GAP-014 fixed). There is **no bytes reader**; `load_worldbank_frame` wants
  `bytes`, so add a tiny `_read_bytes(lander, path)` mirroring `_read_text`, or
  reuse `_read_text(...).encode("utf-8")` (JSON is UTF-8-safe).
- `src/railway_lakehouse/silver/stats/load.py:39-57` — `load_worldbank_frame(raw:
  bytes, dataset_id) -> DataFrame`. Already exists, already deterministic: parses
  the WB `[meta, records]` JSON, melts to the long contract, tags
  `source_system='worldbank'`, returns an EMPTY frame (never a fabricated row) on
  an error envelope / no-data body / non-JSON. **Reuse this — do not reimplement.**
- `src/railway_lakehouse/silver/stats/load.py:87-111` — `frames_from_bronze`: the
  local-branch reference. Note it **skips `_`-prefixed dataset dirs**
  (`_catalogue_*`) and reads only the latest `ingest_date=` partition. The live
  reader should likewise skip `_`-prefixed datasets (the WB catalogue file would
  otherwise be read; `load_worldbank_frame` returns empty for it, so it is
  defensive-only, but skipping keeps parity and avoids a spurious dataset id).
- `src/railway_lakehouse/silver/stats/merge.py:195-207` — `read_worldbank_json`
  (the inner melt), and `_worldbank_geo` ISO3→geo (HUN→HU, AUT→AT, CZE→CZ).
- `tests/test_pipeline_s3_readback.py` — the deterministic fsspec `memory://`
  injection style (`SimpleNamespace(s3=fsspec.filesystem('memory'))`, `fs.pipe`,
  store-clearing) the new test must follow. GAP-020 proved every s3 branch is
  reachable offline this way.
- `tests/fixtures/bronze/**` — committed raw Bronze for byte-for-byte parity;
  immutable.

## Key findings
1. **Root cause is one missing reader.** The local path already reads WB
   (`frames_from_bronze`); only the live MinIO path is Eurostat-only. The fix is
   to add a WB live reader and wire it into the `else` branch — no Silver/Gold,
   no LLM, no numeric semantics change.
2. **The deterministic WB parser already exists** (`load_worldbank_frame`); the
   live reader just needs to: glob `stats/worldbank/*/ingest_date=*/*.json` (skip
   `_`-prefixed datasets and `.meta.json` sidecars), read bytes, call
   `load_worldbank_frame`, keep non-empty frames.
3. **WARN on zero WB frames** in the live branch (closure criterion): if the live
   stats read yields no WB frame, log a warning so a silently-empty live Gold
   matrix is visible, mirroring `frames_from_bronze`'s logging discipline.
4. **Fully offline-testable** via fsspec `memory://` (GAP-020). No MinIO, no
   network, no Ollama. Mark the new test `integration` per the closure criterion
   (it exercises the Bronze→Silver read seam end to end on the live branch).

## Recommended shape
- Add `_read_bronze_worldbank(lander) -> list[pd.DataFrame]`: iterate
  `_list_bronze_files(lander, domain="stats", source="worldbank",
  include=lambda n: n.endswith(".json"))`, skip `_`-prefixed dataset ids, read
  bytes, `frame = stats_load.load_worldbank_frame(raw, dataset_id)`, append if
  non-empty.
- Add `_read_bytes(lander, path)` mirroring `_read_text` (Path → `read_bytes`;
  else `lander.s3.open(path, "rb").read()`).
- In `_read_bronze_stats_frames` live branch: build the Eurostat frames (as now)
  AND `wb_frames = _read_bronze_worldbank(lander)`; if not `wb_frames`,
  `log.warning("live stats read produced 0 World Bank frames ...")`; return
  eurostat + WB frames combined.
- Test (`tests/test_pipeline_live_stats_worldbank.py`, `pytest.mark.integration`):
  seed an fsspec `memory://` fs with a real WB `[meta, records]` JSON under
  `bronze/stats/worldbank/IS.RRS.TOTL.KM/ingest_date=.../...json` AND a Eurostat
  `.tsv` under `bronze/stats/eurostat/...`; `lander = SimpleNamespace(s3=fs)`
  (no `bronze_root`); assert `_read_bronze_stats_frames(lander)` returns at least
  one frame with `source_system == 'worldbank'` (and the eurostat frame too), and
  that the WB values match the source JSON byte-for-byte (no rewriting). Add a
  second assertion / caplog check that a WB-less live seed logs the zero-WB WARN.

## External confirmation (Tavily, 2026-06-24)
- Not strictly required for GAP-013 (in-repo fix). Confirmed only that fsspec
  `MemoryFileSystem` glob/leading-slash behavior matches GAP-020's empirical
  finding; no new API surface. Source: prior GAP-020 evidence + fsspec docs.

## Evidence
Planning/spec pass only; no code, MinIO, Spark, or live collectors run here.
