# Roadmap research — compute/embedder, feature availability, EDA→report design (2026-06-25)

> Skill: `research-orchestrator`. Routed providers (workflow sub-agents): Tavily, Exa, Context7, WebFetch + primary sources.
> Method: dynamic workflow `roadmap-research-and-eda-design` (3 research agents + 1 design agent). The HU-sentiment agent failed the structured-output cap — answered from the small-corpus reasoning instead. Builds the roadmap `docs/ROADMAP_NEWS_TO_REPORT.md`.

## Compute / embedder (verified)
- **No stack migration.** torch is CPU-only on Python 3.14 Windows (no cp314 CUDA wheels, PyTorch #169929). Run torch models in a **separate Python 3.12 venv as a subprocess sidecar** (text parquet → embedding parquet); the Py3.14 pipeline never imports torch. Process exit guarantees VRAM/RAM release.
- **Pascal sm_61 (GTX 1060) works on the `cu126` torch wheel** (confirmed sm_61, uv #14742) but was **dropped in cu128+** (min sm_75). Pin a torch build shipping cu126/cu118. No source compile.
- **Footprints (all fit 6 GB):** bge-m3 ≈ 1.06 GB fp16 (568M, 1024-dim, 8192 tok); multilingual-e5-large-instruct ≈ 1.1 GB (560M, 512 tok); **multilingual-e5-base ≈ 0.55 GB (278M, 768-dim, 512 tok)**; MiniLM-L12 ≈ 0.24 GB (118M, 128 tok).
- **Owner decision: default embedder = multilingual-e5-base.** Our news texts are short snippets (GDELT snippet / RSS description), so bge-m3's long-context edge is moot; **dedup quality is dominated by the algorithm** (blocking/threshold/edge-order/field-union), not the model; e5-base is faster/lighter on the box. `embedding_model` is a config knob (bge-m3 swappable for sharper clustering). e5 needs `query:`/`passage:` prefixes.
- **Sequential-pass hygiene:** Ollama LLM (GPU, Qwen-4B-q4) → `ollama stop`/`OLLAMA_KEEP_ALIVE=0` → confirm `ollama ps` empty → embed sidecar (exit frees VRAM) → gate next stage on `nvidia-smi` idle. Kill idle Serena/MCP servers during heavy passes (scarce ~6 GB RAM). Corpus is tiny → CPU embedding viable in minutes; GPU is a 5-20× speedup.
- **HU sentiment:** one multilingual XLM-R pass for HU+DE+EN (no separate HU model = no second load/pass) + golden offset; gkg_tone free fallback for GKG-history. At a hundreds-article HU corpus, HU sentiment accuracy barely moves (geo,year) Gold aggregates.

## Feature availability for the analysis (verified)
- **Rail investment has a dense deterministic source already wired:** Eurostat `rail_ec_expend` → `rail_investment` (INF_INV+RSTK_INV, MIO_EUR, mapped in `silver/stats/merge.py`). **Use it as the primary investment X; news `monetary_amount_eur` is a sparse secondary cross-check.**
- 9 of 12 teammate correlates already collected (GDP growth NY.GDP.MKTP.KD.ZG, pop density EN.POP.DNST, Gini SI.POV.GINI + Eurostat ilc_di12, CO2 AR5 family, track/locomotives/wagons/passengers via Eurostat rail_* + UIC + WB, life satisfaction Eurostat ilc_pw01).
- **Only 2 new WB codes needed (GAP-045):** `IS.VEH.PCAR.P3` (cars/1000 — requested `IS.VEH.NVEH.P3` is RETIRED) + `PA.NUS.PPP` (PPP). Feature-deltas are free derived Gold columns.
- **Hard / deferred (new source):** terrain complexity (Copernicus/SRTM DEM), line coordinates+speeds (OSM railway=rail + maxspeed). "Investment vs coordinates/speeds" deferred to a geospatial source ticket.
- **Statistical-power caveat:** AT+HU only = tiny n; widening UIC to all countries (GAP-041) materially helps every correlation. Gini + cars/1000 are sparse recent years.

## Design decisions
- EDA is **hypothesis-generator, not checklist** — all-pairs corr × {level, delta, lag}, ranked. **Hypotheses are formed in GAP-048 FROM the EDA artifacts (owner decision), not pre-authored.** No hypothesis list created now.
- New tickets: GAP-045 (macro indicators), GAP-046 (Spark EDA harness → artifacts only), GAP-047 (analysis_artifacts/ + Spark verify of teammate claims; empty HYPOTHESES.md), GAP-048 (form-from-EDA + analyses), GAP-049 (report). Plus GAP-050 (LLM prompt-engineering design via prompt-master, precedes GAP-033).
- **All data is local:** MinIO Docker volume (lakehouse buckets) + `output/` (committed small evidence; gitignored large raw Bronze). Golden bodies gitignored / fetched-by-hash. Nothing hosted.

## Sources
- PyTorch Py3.14 CUDA: https://github.com/pytorch/pytorch/issues/169929 · sm_61 on cu126: https://github.com/astral-sh/uv/issues/14742
- World Bank: https://data.worldbank.org/indicator/IS.VEH.NVEH.P3 (retired) · IS.VEH.PCAR.P3 · PA.NUS.PPP · EN.GHG.CO2.PC.CE.AR5
- Eurostat: rail_ec_expend, ILC_PW01 (life satisfaction); merge.py `_EUROSTAT_DATASET_RULES`
- Embedders: https://sbert.net/docs/sentence_transformer/pretrained_models.html · MMTEB https://arxiv.org/abs/2502.13595
