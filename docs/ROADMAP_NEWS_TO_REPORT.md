# Roadmap — news unblock → all parsers wired → Spark EDA → hypotheses → analysis → report

> Destination (≈2-3 orchestration sessions): every source parsed Bronze→Silver→Gold, all preprocessing
> (incl. the LLM) runs end-to-end on a single box, then an **iterative Spark EDA** produces artifacts from
> which **hypotheses are formed (not before)**, analysed, and written into the final report.
> Authored 2026-06-25 from the `news-feature-integration-scan`, `news-model-spec-and-task-pack`, and
> `roadmap-research-and-eda-design` workflows (research-orchestrator-routed, adversarially reviewed).
> Companions: design contract `docs/SPEC_NEWS_PREPROCESSING.md`; per-gap specs `docs/GAP_TASKS.md`;
> status `docs/GAP_REGISTER.md`; board `docs/TASKS.md`; orchestration runbook the `scripts/orch/` harness.

## Guiding principles

1. **MVP-first, clean to extend.** Unblock real news into Gold on the *existing* code, then layer improvements — each a separate GAP runnable one-at-a-time by `scripts/orch/codex_impl.sh <GAP-ID>`.
2. **Feature width is the lever.** The richer the Gold feature matrix (every parser + macro indicators + news + any geo), the larger the hypothesis space the EDA can mine. That is *why* "wire everything" (Sessions A/B) precedes the analysis finale (Session C).
3. **Hypotheses are an OUTPUT of the EDA, never an input.** The EDA harness systematically scans **all feature pairs × {level, YoY-delta, lag}** and ranks candidate relationships; hypotheses are then formed from what the data actually shows. We do **not** pre-author a hypothesis list — the teammate's correlation list is one seed thrown into that pot, not the boundary.
4. **Single box, sequential model passes** (Ryzen 5 1600 / GTX 1060 6 GB). One model resident at a time; heavy torch models run as a GPU **sidecar** subprocess that exits to free VRAM/RAM. See "Compute plan" below.
5. **Hard Rules hold throughout:** raw Bronze immutable; numeric merges deterministic (no LLM on numbers); outputs under `output/`; tests use `tmp_path`; every GAP syncs `docs/TASKS.md` + `docs/index.html`.

## Compute plan (single box) — verified

- **Don't migrate the stack.** Py3.14 is required (Spark 4.1). The embedder/encoders run in a **separate Python 3.12 venv** invoked as a subprocess CLI (text parquet → embedding parquet). The main pipeline never imports torch.
- **Pascal sm_61 still works on the `cu126` torch wheel** (confirmed on sm_61 hardware, uv #14742) — but was **dropped in cu128+**. So the sidecar pins a torch build that ships a `cu126` (or `cu118`) variant; `cu128+` drops the 1060. No source compile needed.
- **Everything fits 6 GB with headroom:** `bge-m3` ≈ **1.06 GB fp16** (568M, 1024-dim, **8192 max seq** — only candidate that embeds full bodies); Ollama Qwen-4B-q4 ≈ 3 GB. Run them **sequentially** anyway on a shared box.
- **`multilingual-e5-base` is the DEFAULT embedder** (278M, ~0.55 GB, 512 tok). Rationale: our news texts are short **snippets** (GDELT snippet / RSS description), so bge-m3's 8192-token edge is moot; **dedup quality is dominated by the algorithm** (blocking, threshold, edge order, field-union), not the embedder; and e5-base is ~2× faster/lighter on the 6 GB box for repeated re-embeds. Keep `embedding_model` a **config knob** — swap to `bge-m3` in one line only if the clustering deliverable needs sharper clusters. LaBSE rejected (weak clustering). (e5 needs `query:`/`passage:` prefixes — bake into the sidecar.) **The model is swappable config; we invest in the dedup/cluster algorithm.**
- **Sequential-pass hygiene:** LLM pass → `ollama stop` / `OLLAMA_KEEP_ALIVE=0` → confirm `ollama ps` empty → embed sidecar (loads → batches → **process exit frees VRAM**) → gate next stage on `nvidia-smi` VRAM back to idle. **Kill idle Serena/MCP servers during heavy passes** to reclaim the scarce ~6 GB RAM.
- **Corpus is tiny** (hundreds of rail articles) → even CPU embedding finishes in minutes; GPU-sidecar is a 5-20× speedup, nice-to-have not required. The sidecar takes `--device cuda|cpu` and auto-falls-back to CPU.
- **HU sentiment:** one multilingual XLM-R pass for HU+DE+EN (no separate HU model — saves a load/pass), recalibrate HU via the golden offset; `gkg_tone` as a free fallback for GKG-history rows. (Revisit only if the live corpus is much larger.)

## Where the data lives — all local, nothing hosted

Everything is on your machine; there is no cloud:
- **Lakehouse object store = local MinIO** (the `railway-minio` Docker container, buckets `bronze`/`silver`/`gold`, data in a Docker volume on your disk). This holds raw Bronze bytes + Silver/Gold parquet.
- **`output/` on disk** holds runtime + committed evidence. Small artifacts (manifests, `counts.json`, the Gold parquet, EDA/analysis CSVs+JSON under `output/evidence/eda|analysis/`) are git-committed; **large raw Bronze is gitignored** (`output/evidence/**/bronze/`) and stays local.
- **Golden news bodies**: gitignored `output/golden/news/bodies/` (or fetched from MinIO Bronze by `content_sha256` at eval time). Only `labels.jsonl` (hash + label + excerpt) is committed.
- **Embeddings**: parquet in the Silver layer — 384/768-dim × hundreds of rows is ~MB, trivial on disk.
- **Disk vs RAM:** the 6 GB constraint is *model memory* (RAM/VRAM), not storage. Total data is modest because the corpus is small; the only thing that could grow large is the **deferred** GDELT-history backfill — keep it bounded. Point MinIO's volume at a drive with a few GB free and you're fine.

## The investment finding (reshapes the analysis)

**Rail investment already has a dense, deterministic source in the pipeline:** Eurostat `rail_ec_expend` ("Expenditure on rolling stock and railway infrastructure", INF_INV+RSTK_INV, MIO_EUR) → mapped to the `rail_investment` Gold feature in `silver/stats/merge.py`. So the analysis uses **`rail_investment` as the primary X-variable** — the sparse news `monetary_amount_eur` becomes a *secondary cross-check* (hypothesis: do news-derived investment signals track the official figure?). 9 of the teammate's 12 correlates are already collected; only 2 new World-Bank codes are needed (GAP-045). Feature-deltas are free derived Gold columns. Only **terrain complexity (DEM)** and **line coordinates/speeds (OSM)** truly need new sources — deferred to a geospatial source ticket; **life satisfaction is available today** via Eurostat `ilc_pw01`.

---

## Session A — MVP: unblock news into Gold (WAVE 6a/6b)

Goal: the first **real** `news_*` columns in a real Gold file, on a clean base that improvements extend smoothly.

- **WAVE 6a (P0, sequential):** `GAP-039` wide NewsFeature contract + sound content-hash cache (the unblocker; fix identity/cache-key) → `GAP-050` **LLM pipeline engineering** (the whole pipeline, not just prompts: prompt + structured output, batching/concurrency, content-hash cache-skip, retries/JSON-repair + a failure-accounting sidecar, model load/unload lifecycle on the 6 GB box, throughput budget + run metrics; `prompt_version`→model digest; best practices via `prompt-master`/`senior-prompt-engineer` + research-orchestrator) → `GAP-033` run the LLM news pass **live once** via that pipeline, persist real NewsFeature rows + evidence.
- **WAVE 6b (P1, parallelizable):** `GAP-035` language-id (fastText, CPU) · `GAP-034` XLM-R sentiment (sidecar) · `GAP-031` GKG/DOC-field recovery + wire passthrough · `GAP-040` widen Gold news aggregation (+ GAP-016/022/026 fixes) · `GAP-043` eval harness · `GAP-044` parser-correctness audit.
- **⛔ Contract D:** real `news_*` rows reach Gold from a live Ollama run; the eval harness reports per-feature metrics on a held-out golden TEST set; dedup deflates inflated `(geo,year)` counts.

## Session B — complete parsers + preprocessing + full wiring (WAVE 6c + 7-prep)

Goal: every source parsed → Silver → Gold; all preprocessing (incl. embeddings) runs on the box.

- `GAP-041` UIC PDF widen-to-all-countries + stage unmapped rows + traffic-trends text · `GAP-042` Statistik Austria ODS reader · `GAP-032` news-capture widening · `GAP-036` embeddings + cross-lingual dedup (bge-m3 sidecar) · `GAP-037` Spark clustering (separate artifact, not a Gold column) · `GAP-038` NER (conditional) · **`GAP-045` add the 2 macro indicators** (`IS.VEH.PCAR.P3`, `PA.NUS.PPP`).
- **Widen geo** (GAP-041 UIC to all countries; WB/Eurostat are already multi-country) — this materially raises statistical power for Session C, since AT+HU alone is a tiny n.
- **⛔ Contract E:** every source parser → Silver → Gold verified; the full feature matrix (rail + macro + news + UIC) builds end-to-end; all model passes run sequentially on the box within memory budget.

## Session C — Spark EDA → hypotheses → analysis → report (WAVE 7) — the finale

**Strictly EDA-first; hypotheses are formed from the artifacts, then analysed, then reported.**

```
GAP-046  Iterative Spark EDA harness → ARTIFACTS ONLY (no hypotheses)
         all-pairs Pearson/Spearman over features + YoY deltas, lag cross-corr,
         per-(geo,year) panels, coverage/missingness, distributions, top-correlations
         → output/evidence/eda/   (re-run every time data grows)
            │  iterate until artifacts are rich + stable
            ▼
GAP-047  analysis_artifacts/ integration + Spark RE-VERIFICATION infra
         (teammate uploads recompute against CURRENT Gold → confirmed/drifted/broken;
          hypothesis registry docs/HYPOTHESES.md created as an EMPTY structure)
            ▼
GAP-048  HYPOTHESIS FORMATION (read the EDA artifacts) → curate interesting/robust/
         surprising relationships → register in HYPOTHESES.md → Spark-backed analyses
         (correlation / lag / panel / clustering; investment-centred + AT-vs-HU + news-signal)
            ▼
GAP-049  Final REPORT grounded in EDA + analysis evidence (deterministic link/number checker)
```

- **⛔ Contract F:** the report's every quantitative claim cites a committed `output/evidence/eda/` or `output/evidence/analysis/` artifact; teammate analyses in `analysis_artifacts/` are re-verified against current Gold (confirmed/drifted/broken); hypotheses trace to EDA artifacts, not to anyone's prior guesses; limitations (short ≤27-yr AT/HU series, sparse Gini/life-satisfaction, deferred terrain/speed) stated honestly.

### `analysis_artifacts/` integration (GAP-047)
- `analysis_artifacts/<author>/<slug>/` = upload inbox: `analysis.md` (narrative) + `analysis.py` (`recompute(gold_df)`, reads `--gold`, **no hardcoded data**) + `claims.json` (`{claim_id, statement, metric, expected_value, tolerance, gold_columns, geo_filter, hypothesis_id}`).
- `railway_lakehouse.spark_jobs.verify_analyses` re-runs every `claims.json` against the **current** Gold → `output/evidence/analysis/<author>__<slug>/verification.json` with status ∈ {confirmed, drifted, broken, low_support} + a top-level `verification_summary.json/.md`. A claim referencing a now-absent column is `broken`, not silently passed; a number that no longer matches is `drifted` (data grew since they ran it) — surfaced, never "fixed".
- New hypotheses are appended to `docs/HYPOTHESES.md` (status `candidate` → `active` once an analysis or EDA artifact backs them). Teammate uploads need no code change — the verifier globs the inbox.

## Hypothesis space (illustrative — the EDA decides, GAP-048 forms them)

Not a plan to confirm; just the *kinds* of questions the all-pairs EDA + GAP-048 will surface and formalise: rail_investment vs every feature and every YoY-delta; investment lead/lag on capacity (network/rolling-stock) via lag cross-correlation; AT-vs-HU divergence; freight↔CO2 decoupling and modal shift; news-sentiment / news-event-volume vs official investment (the news↔stats validation); cars-per-capita vs rail passenger-km; clustering of country-year regimes. Teammate seeds (investment ↔ {track, locomotives, wagons, passengers, GDP, CO2, density, Gini, life-satisfaction, cars-pp}) fold in here. Deferred (needs a new source): investment vs terrain (DEM) and vs line coordinates/speeds (OSM).

## Ticket index (this roadmap)

| GAP | Slug | Session | Sev | Notes |
|---|---|---|---|---|
| 039 | `silver/wide-newsfeature-contract` | A · 6a | HIGH (P0) | unblocker; sound cache key |
| 050 | `silver/llm-pipeline-engineering` | A · 6a | HIGH (P0) | full LLM PIPELINE (prompt + batching + cache-skip + retries + failure-accounting + model lifecycle + metrics); prompt-master + research-orchestrator; precedes the live run |
| 033 | `silver/news-llm-extraction-live` | A · 6a | HIGH (P0) | first live LLM run, uses the GAP-050 prompt |
| 035 / 034 / 031 | language-id / sentiment-encoder / gdelt-gkg-parser | A · 6b | LOW/MID/HIGH | cheap encoders + free GKG/DOC signal |
| 040 / 043 / 044 | widen-news-aggregation / eval-harness / parser-audit | A · 6b | MID/HIGH/MID | Gold columns + measurable quality + parser audit |
| 041 / 042 / 032 / 036 / 037 / 038 | UIC-widen / StatAustria-ODS / capture-widen / embeddings-dedup / clustering / NER | B | MID…LOW | complete parsers + preprocessing; widen geo |
| 045 | `add-macro-indicators` | B | MID | `IS.VEH.PCAR.P3` + `PA.NUS.PPP` (2 new WB codes) |
| 046 | `spark-eda-harness` | C | HIGH | iterative EDA → artifacts only |
| 047 | `analysis-integration` | C | HIGH | analysis_artifacts/ + verifier + empty registry |
| 048 | `hypothesis-analyses-spark` | C | HIGH | **form hypotheses FROM EDA**, then analyse |
| 049 | `final-eda-analysis-report` | C | HIGH | report grounded in EDA + analysis evidence |

Detailed pick-up-cold specs for every GAP are in `docs/GAP_TASKS.md`; the 8 must-fix review blockers (cache-key, snippet-not-fulltext, GKG-absent-live, embedder, KMeans determinism, NER heads, golden-set stats, dedup) are in `docs/SPEC_NEWS_PREPROCESSING.md`.
