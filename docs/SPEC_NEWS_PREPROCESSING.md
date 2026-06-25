# Multi-Model News-Preprocessing Pipeline — Wide Silver Extraction, Spark Aggregation, and Evaluation Strategy (Railway Lakehouse)

> **Status: DRAFT v0.1 — reviewed, REWORK REQUIRED before build.** Authored + adversarially reviewed 2026-06-25 by a 10+5 agent panel (1 spec author, 14 task-spec authors, 5 independent reviewers, 1 synthesis). Reviewer verdicts: adversarial = needs-rework, eval-rigor = needs-rework, gap-finder / approach-analyst / researcher = approve-with-changes. This document is the design contract; the per-task pick-up-cold specs live in `docs/GAP_TASKS.md` (GAP-031…044) and status in `docs/GAP_REGISTER.md`.

> Generated via the `research-orchestrator` workflow (routed MCP providers: Tavily, Exa, Context7, Ref, WebFetch). Source URLs are cited inline and in `.planning/coursework/research/bigdata/`.

## ⚠️ Must-fix before build (review blockers)

These eight items were raised as blockers by the review panel and **must be resolved in the spec/first task before any extraction code is written**:

- Define content-only identity BEFORE any cached extraction is coded: normalize URL, decouple article_id (lineage) from content_sha256 (cache/dedup key over normalized title+body only), drop per-batch index from the sha1 fallback. The entire idempotent-cache cost-control mechanism is unsound until this exists (gap-finder blocker).
- Resolve compute feasibility on the real box: torch on Python 3.14 Windows is CPU-only. Decide (a) separate Py3.12+CUDA encoder env, (b) measured CPU latency budget, or (c) ONNX/CPU-optimized or tone-only sentiment for v1 -- and state where model weights are cached offline (HF unreachable in build sandbox). Do not build the encoder pass on an unverified GPU-throughput assumption (adversarial blocker).
- State per-source text reality (GDELT DOC = snippet, many RSS = description-only) and add a text_source provenance column; do not set NER/dedup/embedding quality gates against text the pipeline does not have (adversarial + gap-finder blocker).
- Pin the v1 embedder away from LaBSE (use multilingual-e5-large-instruct or bge-m3 as default; LaBSE optional translation-only signal). Building dedup+clustering on LaBSE means weak dedup recall and a near-bottom clustering deliverable (researcher blocker). **Owner decision 2026-06-25: DEFAULT = `multilingual-e5-base` (our texts are short snippets so bge-m3's 8192-ctx edge is moot; dedup quality is algorithm-dominated; e5-base is faster/lighter on the 6 GB box). `embedding_model` is a config knob — swap to bge-m3 only if the clustering deliverable needs sharper clusters. All torch models (sentiment/embeddings/NER) run via a Python 3.12 + `cu126`-torch GPU SIDECAR (Pascal sm_61 supported by cu126, dropped in cu128+) that exits to free VRAM/RAM, or CPU fallback; see `docs/ROADMAP_NEWS_TO_REPORT.md` Compute plan.**
- Make 'clustering is a separate artifact, not a Gold column' binding for v1 and remove the byte-identical-Gold claim for any KMeans-derived column (SPARK-21679). Reproducibility is guaranteed by the cache, not by recomputation (researcher + adversarial blocker).
- Re-pin the NER model ids to actual NER heads (NYTK/novakat HU; flair/xlm-r-conll03 German) -- the currently pinned ids are base LMs and would fail at implementation (researcher major).
- Specify v1 behavior with GKG entirely ABSENT (it is absent for all live DOC rows): re-derive country precedence, canonical-row selection, and sentiment cross-check for the no-GKG case; mark all gkg_*-dependent mechanisms conditional/v2 (adversarial + gap-finder blocker).
- Rework the golden-set statistics before it becomes a gate: TUNE/TEST split (no tune-on-test), collapsed gated taxonomy, bootstrap CIs / minimum-support rule, and replace the N=3 epsilon flakiness gate with an offline N>=20 stability measurement. As written the gates fire on sampling noise and report in-sample-optimistic numbers (eval-rigor blocker x3).
- Add the dedup determinism + field-union + no-country-blocking + date-window fixes; otherwise dedup is non-deterministic, double-counts across year boundaries, misses the cross-border duplicates it exists to catch, and silently drops the only money/operator on a collapsed sibling (adversarial + gap-finder major).

## 🖥️ Compute target — single box, sequential passes (Ryzen 5 1600 + GTX 1060 6 GB)

**Hard constraint (owner, 2026-06-25):** the entire pipeline runs on ONE machine — AMD Ryzen 5 1600 (6c/12t), GTX 1060 6 GB, Windows, **no hosted/cluster processing**, no time to stand up remote infra. This makes the review panel's #1 blocker binding and forces the model stages to run **sequentially**, never concurrently. This section is the authoritative compute plan; tasks GAP-033/034/036/037/038 must conform to it.

### What can and cannot use the GPU
- **Ollama (the LLM) CAN use the 1060.** Ollama ships its own llama.cpp CUDA build (independent of PyTorch), so it uses the GPU even on Python 3.14. Pin a **~4B-class model at q4** (`qwen3:4b` q4_K_M ≈ 3–4 GB, the dashboard's existing "Qwen3-4B q4_K_M (6 GB fit)" choice) — **not** `qwen3.5:9b-q8` (~11 GB; it spills to CPU and crawls, and the 9B tag is multimodal, irrelevant here).
- **torch / transformers models are CPU-only on Python 3.14 Windows** (no CUDA `cp314` wheels — PyTorch #169929). This is the panel blocker. Two sanctioned options for XLM-R sentiment, e5/bge-m3 embeddings, and BERT NER: **(a)** stand up a **separate Python 3.12 + CUDA-torch env** (Pascal `sm_61` is still supported) and run the encoder passes there, handing Parquet back to the 3.14 pipeline; **(b)** run them **CPU-only** — the corpus is small (low thousands of articles), so a one-time *cached* pass is minutes-to-low-hours on the Ryzen, not days. **Recommend (b) first, measure, escalate to (a) only if CPU latency hurts.**
- **fastText lid.176 and Spark (`local[*]`) are CPU** and trivially fine on the Ryzen.

### Sequential pass schedule — one model resident at a time (6 GB cannot hold them all)
Each model is a **separate cached pass** over the article set; results merge by `content_sha256`. Run in this order, unloading each model before the next:
1. **Ollama LLM pass (GPU):** `is_rail_related`, `event_type`, `summary_en`, `monetary_raw`. `ollama stop` after → frees VRAM.
2. **Embedding pass (GPU-via-Py3.12 or CPU):** e5/bge-m3 vectors → dedup + clustering input.
3. **Sentiment (XLM-R) + language (fastText, CPU):** cheap, can share CPU.
4. **(deferred) NER pass:** only if operators/rail_lines become hard Gold requirements.
5. **Persist Silver → Spark `local[*]` reads Parquet:** dedup, aggregate, KMeans. **Never run Spark + a model concurrently** — they contend for RAM.

The content-hash cache makes every pass idempotent: an interrupted run resumes for free and re-runs do zero model work — essential on a single box you also use for other things.

### Implications baked into the plan
- **Open Decision #1 is resolved:** Ollama-on-GPU + encoders CPU-first (measure), Py3.12-CUDA env only if needed. Corpus size makes CPU viable.
- The deferred **GKG-history backfill (P3)** is the only piece with real volume/compute risk on this box — keep it deferred and bounded; the rest operates on a small corpus.
- **Spark stays `local[*]`; no cluster.** The rubric's "horizontal scaling" point is demonstrated by the local Spark job + a documented path to a standalone cluster, not by actually renting one.
- Memory-pressure ordering is natural: Bronze → Silver-LLM → Silver-encoders → persist → Spark are already discrete phases; schedule them as separate steps, each owning the machine.

## MVP-first build order (priority-ranked tasks)

The panel was unanimous that the news path has **never run live** — so the MVP is "make the existing pipeline produce real news Gold columns," and everything model-heavy is fast-follow gated on the MVP being green. Authoritative priority (correct GAP IDs):

| Priority | GAP | Slug | Rationale |
|---|---|---|---|
| P0 | GAP-039 | `silver/wide-newsfeature-contract` | The unblocker: every model-pipeline gap (031,032,034,035,036,038,040,043) depends on the wide article-grain contract + idempotent content-hash cache. Must ship FIRST but scoped to MVP (identity contract, cache key, persist contracts, legacy projection) -- not the full 40-column schema. Fix the identity/cache-key soundness here. |
| P0 | GAP-033 | `silver/news-llm-extraction-live` | Closes the single biggest reality gap -- the LLM news path has NEVER run live, zero real NewsFeature rows exist. Highest-value lowest-effort win; produces the first real evidence and is the precondition for any golden set / eval. Run existing extract.py live once on a real batch. |
| P1 | GAP-035 | `silver/language-id` | Cheapest deterministic encoder (single fastText lid.176 file, no torch), removes LLM language-guessing, and is the routing input NER needs. Verified current by researcher. Big defensibility payoff for tiny effort -- do early. |
| P1 | GAP-034 | `silver/sentiment-encoder` | Swapping LLM-sentiment for deterministic XLM-R is the headline defensibility upgrade and directly enables a real sentiment eval. Verified model facts (DE in-domain, HU caveat). Gated on the compute-feasibility decision (torch CPU-only). |
| P1 | GAP-040 | `gold/widen-news-aggregation` | Turns real Silver rows into the (geo,year) matrix columns the coursework is graded on, and folds in the cheap correctness fixes GAP-016 (reindex pivots), GAP-022 (parse year in Silver), GAP-026 (dict-row KeyError). Depends on the wide contract + first real rows. |
| P1 | GAP-031 | `silver/gdelt-gkg-parser` | Wiring the already-collected gdelt_passthrough + recovering dropped DOC domain/language/sourcecountry is near-zero-cost free signal. BUT scope v1 to DOC-metadata recovery + passthrough only; the GKG csv.zip history parser is the heavy, deferrable part (Open Decision #4) -- carry it as a separate P3 follow-up. |
| P1 | GAP-043 | `eval/news-model-quality-harness` | The owner's explicit ask -- measurable pipeline quality. Must ship alongside the encoders so quality is gated, but only AFTER real rows exist (GAP-033) to build a golden set on. Ship with the reworked statistics (TUNE/TEST split, CIs, collapsed taxonomy) -- not the statistically-broken v1 design. |
| P1 | GAP-044 | `tests/parser-correctness-audit` | Per-source field-coverage golden fixtures with NO new model dependency; protects the capture-everything principle and underpins GAP-032's widening. Cheap, independent, high-trust. Can run in parallel from day one. |
| P2 | GAP-032 | `silver/news-capture-widening` | Widening ArticleRecord to carry the dropped RSS/GDELT metadata is valuable capture-everything work but depends on the wide contract and overlaps GAP-031's DOC-field recovery; sequence after the contract lands to avoid double-touching the schema. |
| P2 | GAP-036 | `silver/news-embeddings-dedup` | Cross-lingual dedup matters only once real counts exist and are shown inflated by real duplicates. Re-scoped: pin e5/bge-m3 (not LaBSE), date-window (not country) blocking, deterministic edge order + field-union. Heavy torch dependency -- gated on compute decision and on MVP being green. |
| P2 | GAP-041 | `silver/uic-pdf-widen-and-stage` | Stats-side parser-correctness/capture work, fully independent of the news path. Owner-accepted (capture all geos, stage unmapped rows). Moderate value, no dependencies -- schedule when news P0/P1 work is not blocking. |
| P2 | GAP-042 | `silver/stataustria-ods-reader` | StatAustria ODS is landed-but-unparsed; building the reader adds a real second-country stats source. Independent, moderate effort, directly widens the deterministic numeric matrix that dominates the feature set. |
| P3 | GAP-037 | `spark/news-clustering` | MLlib clustering deliverable. Depends on embeddings (036) and is non-deterministic (SPARK-21679) -- keep as a SEPARATE analytical artifact, not a Gold column, for v1. Promote to Gold only if the coursework analysis uses clusters as features. Lowest urgency. |
| P3 | GAP-038 | `silver/news-ner` | Full huBERT+German-NER entity extraction is the heaviest model add for the lowest gated payoff (operators/rail_lines are LOW severity). Spec's own recommendation: gazetteer + GKG-orgs first; add NER models only if the operator-F1 gate shows gazetteer recall is insufficient. Re-pin to real NER heads when built. |

## Open decisions for the owner

Each carries a recommendation; these gate parts of the build:

1. COMPUTE TARGET for torch encoders (NEW, hard blocker): Python 3.14 is CPU-only for torch on this box. Options: (a) stand up a separate Python 3.12 + CUDA env for the encoder pass with a documented cross-interpreter handoff; (b) accept CPU-only and budget measured latency; (c) ONNXRuntime/CPU-optimized encoders or GDELT-tone-only sentiment for v1. RECOMMEND (a) for the GTX-1060 if CUDA cp312 wheels work, else (b) given the corpus is small (~thousands of rows), CPU latency is likely tolerable for a one-time cached pass -- measure first.
2. EMBEDDER (NEW, researcher blocker): default embedder for dedup+clustering. RECOMMEND intfloat/multilingual-e5-large-instruct as default (MMTEB-leading clustering, HU/DE/EN, MIT) with LaBSE retained only as an optional strict-translation dedup signal; let the golden duplicate-families slice A/B them and pick empirically.
3. Hungarian sentiment: XLM-R is not HU-fine-tuned (tweet domain); the proposed multilingual sibling is ALSO tweet-domain and lacks HU, so it will NOT close the gap. RECOMMEND golden-set offset recalibration + gkg_tone cross-check for v1, and evaluate a HU-native sentiment model (NYTK/huBERT fine-tune) as the real fix rather than the sibling.
4. Clustering in Gold: RECOMMEND binding Open Decision #6 to 'separate analytical artifact, not a Gold column' for v1 (KMeans non-determinism, SPARK-21679) and promote to Gold columns only if the coursework analysis actually uses clusters as features.
5. GKG history parser scope: RECOMMEND v1 = DOC-era + DOC-metadata recovery + gdelt_passthrough wiring only; defer the master_v1 GKG csv.zip parser (with its date-only unfiltered Bronze boundary) to a tracked P3 follow-up, since it carries the biggest unbudgeted compute/volume risk.
6. Monetary EUR normalization: RECOMMEND for v1 store monetary_raw + monetary_currency only and DEFER FX-to-EUR conversion until a citable ECB rate table is committed with a research record -- money-bearing rail articles are sparse and the deterministic stats sources already dominate investment, so this is low-yield and should not block MVP.
7. Golden-set body storage / copyright (NEW): committing 150-250 full third-party article bodies into a public GitHub-Pages repo is a copyright/PII exposure. RECOMMEND storing content hashes + minimal quoted excerpts + a fetch fixture (article IDs), or a private LFS/CI store, rather than full bodies.
8. Gated event taxonomy: the 10-way NEWS_EVENT_TYPES at n<=250 cannot support per-class F1 gates. RECOMMEND collapsing to 3-4 high-frequency super-classes for the GATE and reporting the full 10-way confusion matrix un-gated.
9. Gap decomposition / board slugs: confirm GAP-031..044 as scoped here (with GAP-031 split into a v1 DOC-metadata part and a deferred GKG-history part), and confirm each gap carries the docs/TASKS.md + docs/index.html sync obligation. RECOMMEND accept the MVP-first build order as the canonical sequence.

---

# Design spec (draft body — apply the revisions in the appendix before building)
This spec is the authoritative design for the news side of the railway lakehouse: how unstructured rail news (RSS full-text + GDELT) becomes a wide, article-grain feature table in Silver, and how Spark/Gold then filter, deduplicate, aggregate, and cluster it into the `(geo, year)` ML matrix. It supersedes the single-LLM-does-everything sketch in `docs/SILVER_DESIGN.md` for the news path while preserving its core principle ("LLM only where it adds information"). It is grounded in the current code: `silver/news/extract.py`, `silver/schema.py` (`NewsFeature`, 15 fields), `silver/config.py` (`NEWS_EVENT_TYPES`, `KNOWN_OPERATORS`), `silver/ollama_client.py`, `silver/persist.py`, `gold/build.py`.

> Status of reality this design must change (verified 2026-06-25): the LLM news path has **never run live** — every test mocks `generate_json`; no real `NewsFeature` row was ever persisted; real Gold is stats-only (`news_rows=[]`). GDELT is pulled via DOC 2.0 ArtList, which **structurally cannot** return GKG (themes/CAMEO/tone/persons/orgs/locations); the DOC fields `domain/language/socialimage/sourcecountry` are parsed then dropped (`silver/news/gdelt.py`). `gdelt_passthrough()` exists with zero callers. `past_recordings.master_v1` lands GKG `csv.zip` verbatim and unparsed. The richest free structured-NLP signal is collected then discarded. This spec turns that around.

---

## 1. Goals & non-goals

### Goals
- **G1 — Extract many features WIDE, once.** Produce an article-grain wide table (`NewsFeatureWide`) where every article gets the full feature set computed exactly once, cached by content hash, and pinned to the model digests that produced it. Re-running the pipeline over unchanged input does zero model work.
- **G2 — Right tool per feature (role split).** Use the generative LLM (Ollama Qwen) only for the genuinely generative slice (rail-relatedness, event type, English summary, monetary parsing). Use deterministic, pinned encoders for everything a classifier/encoder does better and reproducibly: sentiment (XLM-R), language ID (fastText lid.176), cross-lingual embeddings for dedup + clustering (LaBSE), and NER for operators/lines (conditional). Lift GDELT GKG fields for free where the source provides them.
- **G3 — The expensive non-deterministic step is never in a Spark job and never a per-row UDF.** Spark reads the already-materialized wide table and does only deterministic relational work: filter → dedup → aggregate → cluster.
- **G4 — Dedup before aggregation.** Cross-source/cross-lingual near-duplicates (same story via RSS + GDELT, HU + DE coverage of one event) must be collapsed to one canonical article before any `(geo, year)` count so article counts and investment sums are not inflated.
- **G5 — Provenance & reproducibility.** Every feature value records which model/tool produced it and at which digest; the same input + same digests + temp 0 ⇒ byte-identical Silver output.
- **G6 — Defensible evaluation.** A golden set, per-feature metrics with thresholds, CI regression gates that work for a non-deterministic LLM, model-digest tracking, and production drift monitoring (Section 6).

### Non-goals
- **N1 — No LLM over numbers.** The numeric stat merge stays deterministic (HARD RULE, AGENTS.md:74-81). News never rewrites a `StatFact`.
- **N2 — No image / OCR / vision / PDF-figure** work (none exists today; out of scope).
- **N3 — No new external news collection.** Bronze collection boundary (rail terms + `sourcecountry` AT/HU) is unchanged. This is a *preprocessing* redesign, not an ingestion one.
- **N4 — No distributed model serving as the default.** Single-box Ollama + local HF encoders. `predict_batch_udf`/`mapInArrow` with a broadcast model is documented as the *only* sanctioned distribution path if extraction ever needs to scale (Section 4.6), but it is not the default and is still a one-time cached pass, never per-row in an aggregation job.
- **N5 — Not changing the Gold grain.** Output stays `(geo, year)`. We widen its *columns*, not its key.

---

## 2. The WIDE article-grain `NewsFeatureWide` schema

This is the new Silver news contract: one row per article, persisted to Parquet, the single input both to dedup/aggregation and to clustering. It is a **strict superset** of today's 15-field `NewsFeature` so the existing Gold path keeps working during migration. Types are the persisted Arrow/Parquet types.

Legend for **Source-of-truth (SoT)**: `LLM` = Ollama Qwen JSON; `XLM-R` = cardiffnlp sentiment; `lid` = fastText lid.176; `LaBSE` = sentence embedding; `NER` = huBERT/German-BERT NER + gazetteer; `GKG` = GDELT GKG passthrough; `DOC` = GDELT DOC ArtList metadata (currently dropped); `det` = deterministic Python (regex/lookup/hash); `bronze` = carried from `ArticleRecord`.

### 2.1 Identity & provenance
| Column | Type | SoT | Nullable | Notes |
|---|---|---|---|---|
| `article_id` | string | bronze | no | From `records.article_record_id`. Primary key of the wide table. |
| `source` | string | bronze | no | `rss` / `gdelt` / `gdelt_history`. |
| `url` | string | bronze | no | |
| `published_date` | string | bronze | yes | Raw source string. Date parsing is deferred and hardened (GAP-022). |
| `published_year` | int32 | det | yes | Parsed once in Silver from `published_date` (RFC-822 for RSS, GDELT `seendate`); resolves GAP-022 *before* Spark so a bad date never silently drops a row at Gold. Null only if unparseable. |
| `ingest_date` | string | det | no | Partition key, mirrors persist layout. |
| `content_sha256` | string | det | no | SHA-256 over the normalized `(title + "\n" + body)`. The cache key (Section 4.2). |
| `body_len` | int32 | det | no | Char length of body after normalization; guardrail input (empty-body articles get reduced trust). |

### 2.2 Generative slice (LLM)
| Column | Type | SoT | Nullable | Notes |
|---|---|---|---|---|
| `is_rail_related` | bool | LLM | no | The Gold gate. Default `false` on extraction failure (fail-closed). |
| `event_type` | string (enum) | LLM | no | One of `config.NEWS_EVENT_TYPES`; unknown ⇒ `other` via `validate_news_feature`. |
| `event_type_secondary` | string (enum) | LLM | yes | NEW. Optional second label; many rail stories are multi-event (strike + service_change). Same enum + `null`. |
| `summary_en` | string | LLM | yes | 1–2 sentence English summary. Null on failure. |
| `monetary_amount_eur` | float64 | LLM→det | yes | LLM proposes the figure+currency; a **deterministic** converter normalizes to EUR using a pinned per-year FX table (no LLM arithmetic). See §3.1. |
| `monetary_raw` | string | LLM | yes | Original money string (e.g. `"12 milliárd forint"`). Restores GAP-029 (currently omitted from `DATA_CONTRACTS`). |
| `monetary_currency` | string | LLM | yes | NEW. ISO-4217 the LLM read (`HUF`/`EUR`/…); drives the deterministic FX conversion and makes it auditable. |
| `llm_confidence` | float64 | LLM | yes | Self-reported [0,1], clamped. Used only as a *weak* guardrail feature, never as ground truth (Section 6.4). Renamed from `confidence` for clarity. |

### 2.3 Deterministic-classifier slice
| Column | Type | SoT | Nullable | Notes |
|---|---|---|---|---|
| `language` | string | lid | yes | ISO-639-1 from fastText lid.176 (replaces LLM-guessed language). |
| `language_conf` | float64 | lid | yes | lid.176 top-1 probability. |
| `sentiment` | string (enum) | XLM-R | yes | `negative`/`neutral`/`positive` — argmax of XLM-R. **Not the LLM.** |
| `sentiment_score` | float64 | XLM-R | yes | Signed expected polarity `P(pos) − P(neg)` in [−1,1] for averaging in Gold (replaces the lossy 3-bucket map currently in `gold/build.py`). |
| `sentiment_probs` | list&lt;float64&gt; | XLM-R | yes | `[p_neg, p_neu, p_pos]`, sums to 1. Audit + recalibration. |

### 2.4 Entity slice (NER + gazetteer, conditional)
| Column | Type | SoT | Nullable | Notes |
|---|---|---|---|---|
| `operators` | list&lt;string&gt; | NER+gaz→det | no (empty list) | Canonicalized to `config.KNOWN_OPERATORS` via gazetteer; unknown collapses to `other`. NER proposes candidate ORGs; gazetteer is the canonical mapper. |
| `operators_raw` | list&lt;string&gt; | NER | no (empty list) | NEW. Raw ORG surface forms before canonicalization (provenance for GAP-016-style vocab audits). |
| `rail_lines` | list&lt;string&gt; | NER+gaz | no (empty list) | Line/route/station mentions; gazetteer-matched where possible, else raw LOC/FAC spans. |
| `entity_method` | string (enum) | det | no | `gkg` / `ner` / `llm_fallback` / `none` — records which path populated entities (the role split is conditional, §3.5). |

### 2.5 Clustering / dedup slice (LaBSE)
| Column | Type | SoT | Nullable | Notes |
|---|---|---|---|---|
| `embedding` | list&lt;float32&gt;[768] | LaBSE | yes | L2-normalized LaBSE sentence embedding of `summary_en` (preferred) or title+lead. Drives cross-lingual dedup and MLlib clustering. |
| `embedding_model` | string | det | yes | Digest/tag of the LaBSE checkpoint that produced it. |
| `dup_group_id` | string | det (Spark) | yes | NEW, populated in the Spark dedup stage (§4.4), not in the per-article pass. Canonical-story id; all near-duplicates share it. |
| `is_canonical` | bool | det (Spark) | yes | True for the one representative row of each `dup_group_id` (the row counted in Gold). |

### 2.6 GDELT-native slice (GKG passthrough — free signal)
Populated only for GDELT-sourced rows where GKG is available (history `gkg_v1_daily`, or a future GKG-mode live pull). DOC-only rows leave these null but still set `gdelt_*` DOC metadata.
| Column | Type | SoT | Nullable | Notes |
|---|---|---|---|---|
| `gkg_tone` | float64 | GKG | yes | GKG average tone. A *second* sentiment signal, reconciled with XLM-R (§3.3), never silently overwriting it. |
| `gkg_themes` | list&lt;string&gt; | GKG | yes | GKG theme tags. |
| `gkg_persons` | list&lt;string&gt; | GKG | yes | |
| `gkg_orgs` | list&lt;string&gt; | GKG | yes | Feeds the operator gazetteer as candidate ORGs (free NER). |
| `gkg_locations` | list&lt;string&gt; | GKG | yes | Drives `country` for GDELT rows without an LLM call (existing `gdelt_passthrough` logic, retained). |
| `gdelt_domain` | string | DOC | yes | NEW — currently parsed-then-dropped. Source domain (e.g. `orf.at`). |
| `gdelt_sourcecountry` | string | DOC | yes | NEW — DOC `sourcecountry`; corroborates `country`. |
| `gdelt_socialimage` | string | DOC | yes | NEW — captured, not used downstream yet (capture-everything principle). |

### 2.7 Geography & gating
| Column | Type | SoT | Nullable | Notes |
|---|---|---|---|---|
| `country` | string (enum) | reconcile | yes | `HU`/`AT`/`other`. Reconciled from GKG locations + DOC sourcecountry + LLM `country` by a deterministic precedence rule (§3.6). |
| `country_method` | string | det | no | Which signal won (`gkg`/`doc`/`llm`/`none`). |

### 2.8 Run metadata (the reproducibility spine — Section 7)
| Column | Type | SoT | Nullable | Notes |
|---|---|---|---|---|
| `llm_model_digest` | string | det | no | Ollama model + quant + digest (e.g. `qwen3.5:9b-q8_0@sha256:…`). |
| `sentiment_model_digest` | string | det | yes | HF revision of `cardiffnlp/twitter-xlm-roberta-base-sentiment`. |
| `lid_model_digest` | string | det | yes | fastText lid.176 file hash. |
| `embedding_model_digest` | string | det | yes | `sentence-transformers/LaBSE` revision. |
| `ner_model_digest` | string | det | yes | huBERT/German-BERT NER revisions if NER ran. |
| `prompt_version` | string | det | no | Hash/semver of the LLM prompt template — a prompt edit invalidates the cache. |
| `extractor_version` | string | det | no | Semver of the wide-extraction code. |

**Backward compatibility:** the legacy 15-column `NewsFeature`/`news_feature.parquet` becomes a deterministic *projection* of `NewsFeatureWide` (select + rename `llm_confidence→confidence`, drop new columns). `persist_news` continues to emit it from the canonical wide table so Gold and any consumer of the old contract are unaffected until they migrate.

---

## 3. The multi-tool role split

Each tool owns a slice. The contract states what it **owns**, what it **must NOT** do, why it was chosen, and its failure mode. Pinned choices below.

### 3.1 Ollama Qwen (LLM) — the generative slice ONLY
- **Owns:** `is_rail_related`, `event_type`(+secondary), `summary_en`, `monetary_raw` + `monetary_currency` + the *proposed* `monetary_amount` figure.
- **Must NOT:** assign `sentiment` (XLM-R owns it), guess `language` (lid owns it), do FX/currency arithmetic (deterministic converter owns it — LLM must never compute the EUR number), or be invoked inside a Spark UDF or per Spark partition. Its self-reported confidence is **not** treated as a calibrated probability.
- **Pinned:** `qwen3.5:9b-q8_0` (`OLLAMA_MODEL` default), `/api/chat`, `format=`JSON-schema, `temperature=0`, `think=false`, bounded `num_ctx`/`num_predict`, retries → `None` on failure (never a guess). Q4_K_M is the documented memory fallback. Multilingual HU/DE/EN extraction is the reason for Qwen over a generic 8B (per `SILVER_DESIGN.md`, sources checked 2026-06-22).
- **FX rule:** `monetary_amount_eur = round(amount × FX[currency, published_year], 0)` from a pinned, committed yearly FX table. If currency or year is missing, `monetary_amount_eur = null` (never approximated). This keeps "LLM never rewrites numbers" intact — the LLM only *reads* the figure; deterministic code converts.
- **Failure mode:** transport/parse failure ⇒ row kept with `is_rail_related=false` (fail-closed gate) and an entry in the extraction-failure sidecar (Section 6 / GAP-006 follow-up).

### 3.2 cardiffnlp/twitter-xlm-roberta-base-sentiment (XLM-R) — sentiment
- **Owns:** `sentiment`, `sentiment_score`, `sentiment_probs`.
- **Must NOT:** classify rail-relatedness or events; be the only sentiment signal without a documented HU caveat.
- **Pinned & verified (HF model card, 2026-06-25):** XLM-RoBERTa-base, ~198M tweets, sentiment fine-tuned on **8 languages: Ar, En, Fr, De, Hi, It, Sp, Pt**; labels Negative/Neutral/Positive. **Defensibility caveat (must be in the eval report):** German is in-domain but **Hungarian is not** in the fine-tune set, and the training domain is *tweets*, not news prose. Mitigations: (a) evaluate the `…-sentiment-multilingual` sibling on the HU golden slice and pick whichever wins per-language; (b) `sentiment_score` is used as a continuous, recalibratable signal, not a hard label, so a systematic HU bias can be corrected by an offset learned on the golden set; (c) `gkg_tone` provides an independent cross-check (§3.3). Deterministic: temp-free forward pass, argmax + softmax — same input ⇒ same output.
- **Failure mode:** model load failure ⇒ sentiment columns null; Gold treats null sentiment as excluded from the mean (not as neutral).

### 3.3 GKG tone vs XLM-R reconciliation
- GKG `gkg_tone` and XLM-R `sentiment_score` are **both stored**. The Gold sentiment aggregate uses `sentiment_score` (XLM-R) as primary because it is consistent across RSS and GDELT; `gkg_tone` is a monitoring cross-check. A large persistent disagreement between the two is a **drift alarm** (Section 6.5), never a silent overwrite.

### 3.4 fastText lid.176 — language identification
- **Owns:** `language`, `language_conf`. **Must NOT:** be replaced by the LLM's language guess (removed from the prompt's authority).
- **Pinned:** Facebook `lid.176.bin` (176 languages, single deterministic file). `lingua-py` is the documented fallback if a pure-Python dependency is preferred over the fastText binary. Deterministic.
- **Why:** language must be reproducible and is needed to *route* NER (HU vs DE model) before any heavy model runs.

### 3.5 NER — operators & rail lines (CONDITIONAL, cost-gated)
- **Owns:** `operators_raw`, `rail_lines`, and the NER candidates feeding the operator gazetteer.
- **Pinned:** huBERT NerKor (`SZTAKI-HLT/hubert-base-cc` NerKor fine-tune) for Hungarian; a German BERT NER (`mschiesser/ner-bert-german` class / German-domain bert-base NER) for German; English spaCy/HF NER for English. A **gazetteer** (built from `KNOWN_OPERATORS` + GKG orgs + known line names) is the canonical mapper to `operators`.
- **Conditional routing (`entity_method`):** for GDELT-GKG rows, prefer free `gkg_orgs`/`gkg_locations` (`entity_method=gkg`) and skip NER. For RSS/full-text, route by `language` to the matching NER model (`entity_method=ner`). If NER is unavailable, the LLM may emit a *candidate* operator list as a last resort (`entity_method=llm_fallback`), still canonicalized through the gazetteer. This is the only place the LLM may touch entities, and it is explicitly the fallback.
- **Must NOT:** invent canonical operator names — the gazetteer, not the model, decides the canonical vocabulary (prevents GAP-016 non-determinism).

### 3.6 LaBSE — cross-lingual embeddings (dedup + clustering)
- **Owns:** `embedding` (768-dim). **Must NOT:** be used as a classifier or for sentiment.
- **Pinned & verified (HF model card, 2026-06-25):** `sentence-transformers/LaBSE`, 109 languages **including hu and de**, 768-dim, cls-pooling + dense + L2-normalize, Apache-2.0. Chosen specifically because HU/DE/EN coverage in one shared space is what enables cross-lingual dedup (the same event reported in Hungarian and German lands near each other) and MLlib clustering downstream.
- **Failure mode:** embedding null ⇒ that row cannot be cross-lingually deduped; it falls back to exact-content-hash dedup only and is flagged.

### 3.7 GDELT GKG passthrough — free structured NLP
- **Owns:** `gkg_*` columns, and is the *preferred* source for `country` and operator/theme candidates when present. Wires up `gdelt_passthrough()` (currently zero callers) and a **new GKG `csv.zip` parser** for the `master_v1` history files (currently landed-then-discarded). Also recovers the dropped DOC `domain/language/sourcecountry/socialimage`.
- **Must NOT:** be assumed present for DOC-API rows (structural limit: DOC ArtList cannot return GKG). The pipeline must degrade cleanly when GKG is absent.

---

## 4. Silver-once: idempotent, content-hash-cached, model-digest-pinned extraction, and how it feeds Spark/Gold

### 4.1 Layering (the one-time pass)
```
Bronze raw (immutable)
   │  parse_rss_xml / parse_gdelt_artlist_json / NEW gkg_csv parser  → ArticleRecord(+DOC/GKG extras)
   ▼
[Silver wide-extraction pass]  — runs ONCE per (content_sha256, model-digest bundle, prompt_version)
   1. normalize text → content_sha256, published_year, body_len
   2. CACHE LOOKUP by (content_sha256, digest-bundle)   ── hit ⇒ copy cached row, ZERO model work
   3. on miss, run the role-split tools (order matters):
        lid.176 (language)                      ──┐ cheap, gates NER routing
        LLM gen slice (rail/event/summary/$)      │ the only non-deterministic, expensive call
        XLM-R sentiment                           │ deterministic encoders
        NER (conditional on language & source)    │
        LaBSE embedding                           │
        GKG/DOC passthrough merge                 ──┘
   4. deterministic reconcilers: monetary→EUR (FX table), country precedence, operator gazetteer
   5. validate (extend validate_news_feature) → NewsFeatureWide row
   6. WRITE row + write/refresh cache entry keyed by (content_sha256, digest-bundle)
   ▼
Silver Parquet:  silver/news/news_feature_wide/ingest_date=YYYY-MM-DD/...   (NEW canonical)
                 silver/news/news_feature/...  (legacy projection, for compat)
                 silver/news/extract_failures/...  (sidecar: failed article_ids + reason)
```

### 4.2 Idempotency & the cache
- **Cache key = `(content_sha256, llm_model_digest, prompt_version, sentiment_model_digest, lid_model_digest, embedding_model_digest, ner_model_digest, extractor_version)`.** Any change to input text *or* any model digest *or* the prompt invalidates only the affected rows.
- Cache store: a Parquet/SQLite keyed table under `silver/news/_cache/` (local), mirrors the reviewable-cache pattern already used for the stats crosswalk (`CROSSWALK_PATH`, `crosswalk_cache.json`). On MinIO it is an object under the silver bucket.
- **Idempotent guarantee:** re-running on the same Bronze with the same digests is a pure cache replay — no Ollama, no GPU, byte-identical output. This is what makes the non-deterministic LLM safe to put in a reproducible pipeline.
- This is **never** done as a Spark UDF. The pass is a single-box Python job (Section 7). Spark only reads the materialized Parquet.

### 4.3 Feeding Spark: two consumers, one wide table
The wide Parquet is the single source. Spark/Gold build **two** things from it, with strict ordering:
1. **Dedup + `(geo, year)` rollup** (feeds Gold).
2. **Embedding clustering** (MLlib KMeans/BisectingKMeans over `embedding`) for the analytical/clustering deliverable — read-only over the same table, never re-extracting.

### 4.4 Dedup BEFORE aggregation (the ordering that protects the counts)
Order is mandatory:
```
filter(is_rail_related = true AND country IN ('HU','AT') AND published_year IS NOT NULL)
  ▼
DEDUP:
   stage A — exact: collapse identical content_sha256
   stage B — cross-lingual near-dup: within a blocking window (same country, |Δpublished_year|≤ small, 
             cosine(embedding) ≥ τ), union-find into dup_group_id; pick is_canonical
             = the row with the richest provenance (GKG > NER > LLM-only), tie-break by earliest published_date
  ▼
AGGREGATE per (country, year) over is_canonical = true ONLY
  ▼
JOIN onto stats matrix on (geo, year)
```
Rationale: the same strike reported by ÖBB's press RSS, an Austrian news domain via GDELT DOC, and a Hungarian outlet would otherwise be counted 3× and its investment summed 3×. Dedup on LaBSE cosine collapses them cross-lingually first; only the canonical row contributes to counts/sums. `τ` is a tuned threshold (golden-set calibrated, Section 6).

### 4.5 Determinism of the Spark stage
All Spark work is relational + a fixed-seed clustering: filter, union-find dedup (deterministic given a fixed cosine threshold and a deterministic tie-break), groupBy aggregation, KMeans with a fixed seed. No randomness, no model calls. Same wide table ⇒ same Gold.

### 4.6 If extraction ever must distribute (documented, not default)
Only if the single-box pass is too slow: wrap the encoder forward-passes (XLM-R, LaBSE) in `predict_batch_udf` / `mapInArrow` with the model **broadcast once per executor** and loaded lazily per-partition — still a one-time pass writing the cached wide table, still never inside an aggregation job, still digest-pinned. The LLM is *not* distributed this way (Ollama is a single local server); for LLM scale-out the documented path is a vLLM batch server (per `SILVER_DESIGN.md`, a later option). This subsection exists so the design is honest about scale, but N4 stands: it is not the default.

---

## 5. Gold widening

Gold stays at `(geo, year)`; we add columns and fix two existing correctness gaps. New/changed aggregates in `gold/build.py::aggregate_news`, all computed over `is_canonical = true` rows:

**Retained (today):** `news_article_count`, `news_total_investment_eur`, `news_n_<event>` (per `NEWS_EVENT_TYPES`, **reindexed to the canonical enum** to fix GAP-016 non-determinism), `news_op_<operator>` (per `KNOWN_OPERATORS`, reindexed).

**Changed:**
- `news_sentiment_mean` now averages **`sentiment_score`** (continuous XLM-R polarity), not the lossy `{neg:-1,neu:0,pos:1}` map. Rows with null sentiment are excluded from the mean (not coerced to neutral).
- `news_share_negative` = share of canonical rows with XLM-R argmax = negative.

**New columns (the widening):**
- `news_n_secondary_<event>` — counts from `event_type_secondary`.
- `news_gkg_tone_mean` — mean `gkg_tone` over rows that have it (sentiment cross-check column).
- `news_lang_share_hu`, `news_lang_share_de`, `news_lang_share_en` — language mix of coverage (uses `language`, previously never aggregated).
- `news_line_mentions` — count of distinct `rail_lines` mentions (uses `rail_lines`, previously never aggregated).
- `news_mean_llm_confidence` — mean `llm_confidence` (a *quality* column for monitoring, explicitly not a feature to model on).
- `news_dedup_ratio` — `canonical_count / raw_count` per cell; a data-quality signal surfaced to the dashboard.
- `news_cluster_<k>` (optional) — share of canonical articles in MLlib cluster k, if the clustering deliverable is wired into Gold.

**Fill semantics (unchanged rule, AGENTS.md):** count/share-like news columns fill `0` on absence; mean/score columns (`news_sentiment_mean`, `news_share_negative`, `news_gkg_tone_mean`) stay `NaN` when no canonical article exists. Stat columns stay `NaN`. Also resolves GAP-026 (KeyError on dict rows missing optional fields) by building from the explicit wide schema, and GAP-022 because `published_year` is parsed in Silver.

**Dashboard sync (HARD RULE):** any change here updates `docs/TASKS.md` + `docs/index.html` in the same change.

---

## 6. Evaluation strategy

The central challenge: a non-deterministic, never-validated LLM is now load-bearing, and four other models join it. The strategy must (a) measure each feature against ground truth, (b) gate regressions in CI without a live Ollama, and (c) catch production drift.

### 6.1 Golden set design
- **Size & sampling:** 150–250 articles, **stratified** by `language`(hu/de/en) × `source`(rss/gdelt) × `event_type` × `country`, plus deliberate inclusion of: hard negatives (non-rail articles matching rail terms, e.g. "Bahnhofstraße" real-estate), multilingual duplicate *families* (the same event in HU+DE+EN, to test dedup), monetary articles in HUF and EUR, and empty/short-body articles.
- **Labeling:** two annotators independently label the gold fields (`is_rail_related`, `event_type`, `country`, `operators`, `rail_lines`, gold `sentiment`, gold `summary` adequacy, and `dup_group_id` for the duplicate families); disagreements adjudicated; inter-annotator agreement (Cohen's κ) reported per field. Gold money is the human-read figure + currency.
- **Storage:** committed under `tests/golden/news/` as fixtures (HARD RULE: tests must not depend on `coursework/` data — golden articles are checked-in fixtures, body text included, with `__init__.py` in the tests dir).
- **Frozen:** golden set is versioned; changes are reviewed PRs.

### 6.2 Per-feature metrics & thresholds
| Feature | Metric | Threshold (gate) |
|---|---|---|
| `is_rail_related` | Precision / Recall / F1 (positive=rail) | **Recall ≥ 0.95** (don't lose rail news), Precision ≥ 0.85 |
| `event_type` | Macro-F1 (+ confusion matrix) | Macro-F1 ≥ 0.60; no single class < 0.40 |
| `country` | Accuracy | ≥ 0.95 (mostly deterministic via GKG/DOC) |
| `sentiment` (XLM-R) | Macro-F1 **reported per language** | DE ≥ 0.60; HU reported, no hard gate v1 (known caveat §3.2) — gate on *non-regression* instead |
| `operators` | Set-level micro-F1 vs gold set | F1 ≥ 0.70 |
| `rail_lines` | Recall (set) | Recall ≥ 0.60 (recall-oriented; raw spans acceptable) |
| `language` (lid) | Accuracy | ≥ 0.97 |
| `monetary_amount_eur` | % within ±1% of gold EUR (given currency+year) | ≥ 0.90 of money-bearing articles |
| `summary_en` | ROUGE-L vs reference **and** an LLM-judge faithfulness pass (no hallucinated facts) | ROUGE-L ≥ 0.25; faithfulness ≥ 0.90 |
| **dedup** | duplicate-family clustering: pairwise precision/recall of `dup_group_id` | Recall ≥ 0.80, Precision ≥ 0.90 (don't merge distinct stories) |
| Gold rollup | `(geo,year)` count error vs gold-deduped count on the golden window | within ±5% |

### 6.3 Testing a non-deterministic LLM in CI
Three tiers, because Ollama cannot run in the build sandbox (documented limitation):
- **Tier 1 — deterministic CI (always runs, no Ollama):** the encoders (XLM-R, lid, LaBSE) are deterministic → assert exact/within-tol outputs on fixtures. The LLM is **mocked** (as today). Validation hardening (`validate_news_feature` on adversarial/malformed JSON), schema/round-trip, dedup ordering, FX conversion, gazetteer canonicalization, cache hit/miss & idempotency (run twice ⇒ identical bytes), and Gold reindex determinism (GAP-016) are all tested here. **This tier gates every PR.**
- **Tier 2 — LLM contract tests (mocked transport, real schema):** record/replay golden Ollama responses (a VCR-style cassette of real responses captured once). Assert the *pipeline* maps a known LLM JSON to the right `NewsFeatureWide` row. Catches prompt/parse/validation regressions without a live model.
- **Tier 3 — live golden-set eval (nightly / pre-release, requires Ollama):** run the full pipeline over the golden set, compute Section 6.2 metrics, **fail the release gate** if any hard threshold is breached. Because temp=0, the LLM is *near*-deterministic; to bound residual non-determinism, run the golden set **N=3** times and require metric variance below a small ε (flakiness gate). Report mean ± std per metric.

### 6.4 Regression gates
- A committed `golden_baseline.json` stores last-accepted per-feature metrics + the digest bundle that produced them.
- Tier-3 run **fails** if any metric drops more than a tolerance (e.g. F1 down > 0.03) below baseline — even if still above the absolute threshold. This catches silent degradation from a model/prompt change.
- Baseline updates are explicit reviewed commits (no auto-bumping).
- `llm_confidence` is evaluated for *calibration* (reliability curve vs actual correctness) but is **never** itself a gate or a model feature — it is known to be poorly calibrated self-report.

### 6.5 Model-digest tracking
- Every Silver run stamps the digest bundle (Section 2.8) into each row and into a run manifest.
- A **digest-change is a first-class event:** changing any digest (model upgrade, re-quant, prompt edit) (a) invalidates the relevant cache keys, (b) requires a Tier-3 re-eval before the new digests are allowed into a baseline, (c) is recorded in the research log and `docs/GAP_REGISTER.md`. Reproducibility of a past Gold file is recoverable because its inputs' digests are recorded.

### 6.6 Production monitoring (no ground truth at scale)
Per ingest batch, emit and dashboard:
- **Distribution drift:** PSI/KL of `event_type`, `sentiment`, `language` mix vs trailing baseline.
- **Sentiment cross-check:** correlation between XLM-R `sentiment_score` and `gkg_tone` on GKG rows; alarm on collapse (§3.3).
- **Extraction health:** LLM failure rate, JSON-parse failure rate, `is_rail_related` positive rate, mean `body_len`, share of empty embeddings.
- **Dedup health:** `news_dedup_ratio` per `(geo,year)`; a sudden ratio swing flags a source/duplicate-flood anomaly.
- **Coverage:** rows with null `country`/`published_year` (should be near zero after GAP-022 fix).
All thresholds breach → dashboard chip + log; none silently passes (no-silent-failure rule).

---

## 7. Reproducibility & throughput on local compute

- **Determinism contract:** identical Bronze + identical digest bundle + temp 0 + fixed clustering seed ⇒ byte-identical Silver wide table and Gold Parquet. The cache makes re-runs free; digest pinning makes them reproducible across machines.
- **Throughput budget (single box):** the LLM (Qwen 9B Q8_0, ~11 GB) is the bottleneck at order ~1–5 s/article on CPU/modest GPU. The encoders are cheap and batched (XLM-R/LaBSE process hundreds/sec in batches of 32–64). Strategy: (1) GKG passthrough + lid run first and **short-circuit** non-rail/non-HU-AT candidates *before* the LLM where the gate is already deterministically clear, cutting LLM volume; (2) the LLM call is the only thing the cache protects most aggressively — a 50k-article backfill is a one-time cost, thereafter weekly increments are small; (3) encoders run in batched vectorized passes, not per-row.
- **Memory fallback:** `qwen3.5:9b-q4_K_M` (6.6 GB) documented fallback for constrained boxes.
- **Where it runs:** the wide pass is a standalone `silver/news` job (Python 3.14, pandas/pyarrow + HF transformers + fastText). Spark (4.1, JDK 17/21) only reads the resulting Parquet. MinIO I/O mirrors `RawLander` (the s3fs wiring is the existing GAP-010 storage task; local FS tree per `persist.py` is the fixture/evidence path).
- **Research provenance (coursework HARD RULE):** introducing XLM-R, fastText lid.176, LaBSE, huBERT/German NER each requires a `research-orchestrator` record under `.planning/coursework/research/bigdata/<slug>.md` naming the routed MCP provider + source URLs. Model-card facts in §3 were verified 2026-06-25 (HF model cards for `cardiffnlp/twitter-xlm-roberta-base-sentiment` and `sentence-transformers/LaBSE`) and must be cited there.

---

## 8. Open decisions

These need an owner call before implementation; each has a recommended default.

1. **Hungarian sentiment.** XLM-R sentiment is not fine-tuned on HU (tweet domain). Options: (a) ship XLM-R with a golden-set offset recalibration; (b) evaluate `…-sentiment-multilingual` sibling and pick per-language; (c) accept GKG tone as the HU sentiment source. *Recommended:* (b) then (a) — evaluate both on the HU golden slice, pick the winner, recalibrate.
2. **Dedup threshold τ and blocking window.** Cosine threshold and the `|Δyear|`/country blocking for cross-lingual dedup. *Recommended:* calibrate τ on the golden duplicate-families to hit Recall ≥ 0.80 / Precision ≥ 0.90, start window = same country ± 0 years (date-blocked), revisit.
3. **NER scope v1.** Full huBERT+German-NER+gazetteer, or gazetteer-only (regex/dictionary over `KNOWN_OPERATORS` + line names) for v1 with NER as a fast-follow? *Recommended:* gazetteer + GKG-orgs first (cheapest, deterministic), add NER models once the operator-F1 gate shows gazetteer recall is insufficient.
4. **GKG history parser priority.** Parsing `master_v1` GKG `csv.zip` (1979–2016) is a sizable new parser. Ship it now (deep history) or scope v1 to DOC-era (2017+) only? *Recommended:* v1 = DOC-era + live GKG mode if available; GKG-history parser as a tracked follow-up gap.
5. **Embedding input.** Embed `summary_en` (English-normalized, but LLM-dependent) vs raw title+lead (language-native, LLM-independent)? *Recommended:* embed `summary_en` when present (better cross-lingual alignment via normalization) with raw title+lead fallback when summary is null — store which was used.
6. **Clustering deliverable in Gold.** Whether `news_cluster_<k>` columns land in the Gold matrix or stay a separate analytical artifact. *Recommended:* separate artifact first; promote to Gold columns only if the coursework analysis uses them as features.
7. **Failure-table contract.** Formalize `silver/news/extract_failures/` schema now (closes the GAP-006 follow-up) or keep ad-hoc logging? *Recommended:* formalize now — it is needed for the §6.6 failure-rate monitor.
8. **New gap IDs.** This work spans several new gaps starting at GAP-031 (wide extraction, multi-model role split, dedup, Gold widening, eval harness, GKG passthrough wiring) and resolves/touches GAP-016/022/026/029. Owner to confirm gap decomposition + board slugs in `docs/TASKS.md`.
---

# Appendix A — Revisions to apply (review changelog)

The draft body above predates the review. Apply these concrete revisions (do not treat the body as final):

- SCOPE / MVP CUT-LINE (new top-level section, from approach-analyst blocker + gap-finder): split the spec into an explicit MVP-for-grade and a full-vision backlog. MVP = run the EXISTING single-LLM extract.py live once -> first real NewsFeature rows + Gold news columns; swap LLM-sentiment->XLM-R and LLM-language->fastText lid; wire gdelt_passthrough + recover dropped DOC domain/language/sourcecountry; fix GAP-016/022/026. Everything else (LaBSE dedup, NER models, GKG history parser, clustering, drift monitoring) is fast-follow gated on MVP being green. Promote the Section 8 'recommended defaults' into the canonical body so a builder does not build the maximal version.
- CORPUS VOLUME (approach-analyst, gap-finder missing-item): replace the unsubstantiated '50k-article backfill' framing in Section 7 with a measured count of the actual bounded 2-country RSS+GDELT corpus (largest real artifact is ~2,968 Gold rows). The dedup/distribution/clustering justification must be re-grounded on real volume; if volume is small, commit harder to single-box batched extraction and explicitly REJECT Spark-NLP and predict_batch_udf as non-goals (keep Section 4.6 to two sentences).
- PLATFORM/COMPUTE REALITY (adversarial blocker): add a compute-feasibility section. Torch on Python 3.14 Windows is CPU-only (no CUDA cp314 wheels, PyTorch #169929). The Section 7 'encoders are cheap, hundreds/sec on GPU' claim is invalid on the stated box. Either (a) pin a separate Python 3.12 + CUDA inference env for the encoder pass and document the cross-interpreter handoff, (b) measure and state real CPU-only encoder latency and re-justify, or (c) use ONNXRuntime/CPU-optimized or GDELT-tone-only sentiment for v1. State where model weights are cached on an offline/sandboxed box (HF unreachable in build sandbox, same limitation that blocks Ollama).
- TEXT-IS-SNIPPET (adversarial + gap-finder blocker/major): correct the false 'RSS full-text' premise. GDELT DOC body = snippet/summary/description/title; many RSS feeds ship description-only. Add a has_full_text / text_source provenance column; stratify the golden set and all Section 6.2 metrics by text_source (rss-fulltext vs gdelt-snippet); scope NER/dedup/embedding quality gates to the full-text subset; note gkg_tone may be the more reliable sentiment for snippet rows. Reconcile this with non-goal N3 (no new collection) explicitly.
- IDENTITY / CACHE-KEY CONTRACT (gap-finder blocker): add a section defining content-only identity. Today article_record_id() returns the RAW url (or sha1 over source|title|date|body|INDEX). Fix: (1) normalize URL (strip query/fragment/utm, lowercase host) before keying; (2) make content_sha256 over normalized (title+body) ONLY the cache+dedup key, decoupled from article_id; (3) drop per-batch 'index' from the sha1 fallback (it makes ids non-idempotent across re-ingests); (4) state article_id is a lineage/display id, content_sha256 is the cache/dedup key; (5) add a collision/idempotency Tier-1 test. Without this the whole cache-replay idempotency guarantee (G5/4.2) is false.
- GKG REALITY + N3 CORRECTION (adversarial + gap-finder blocker/major): mark every gkg_*-dependent mechanism (sentiment cross-check 3.3, entity short-circuit 3.5, canonical-pick 'GKG>NER>LLM' 4.4, drift alarm 6.6) as CONDITIONAL/v2 and fully specify v1 behavior WITHOUT GKG, because live DOC rows have zero GKG. Correct N3: the GKG-history Bronze boundary is date-only (whole-day, unfiltered, every outlet on Earth), NOT 'rail terms + sourcecountry AT/HU'. The new GKG csv.zip parser must reuse the SAME bronze RAIL_TERMS + NATIONAL_SCOPE filter as build_query so history==live; add a GKG V1-vs-V2 column-layout schema, per-day row-volume estimate, and a throughput budget line for the GKG scan.
- EMBEDDER CHANGE (researcher blocker): replace LaBSE as the DEFAULT embedder. LaBSE is a bitext-mining model that degrades on non-translation similarity and scores ~33 vs ~76 on MMTEB clustering (arxiv 2502.13595); it both under-merges genuinely-different same-event articles and is weak at the KMeans deliverable. Pin intfloat/multilingual-e5-large-instruct or BAAI/bge-m3 as default (HU/DE/EN coverage, MMTEB-leading clustering, MIT/Apache license); keep LaBSE only as an optional second signal for strict-translation dedup. Make embedding_model a config knob the golden set A/Bs on the duplicate-families slice. If e5 is chosen, bake the required 'query:'/'passage:' prefixes into extractor_version.
- KMEANS DETERMINISM (researcher blocker): drop the 'fixed seed -> byte-identical Gold' claim for clustering. Spark MLlib KMeans is not deterministic across partitionings (SPARK-21679; k-means|| init uses takeSample). Make Open Decision #6 ('clustering as a separate artifact, not Gold') binding for v1 and drop the determinism claim for cluster columns; OR if clustering must be reproducible, repartition/sort to a single partition before fit, pin initMode+seed, and commit the fitted centroids so only assignment runs in the reproducible path. State explicitly: filter/dedup/groupBy ARE deterministic; KMeans training is NOT without these mitigations.
- NER MODEL RE-PIN (researcher major): the pinned HU NER id is a base masked-LM, not a NER head. Re-pin HU NER to NYTK/named-entity-recognition-nerkor-hubert-hungarian (or novakat/nerkor-cars-onpp-hubert for richer ORG/LOC types feeding the gazetteer). For German, dbmdz/bert-base-german-cased is also a base LM -> pin a real German NER head (flair/ner-german or FacebookAI/xlm-roberta-large-finetuned-conll03-german). Fix ner_model_digest provenance accordingly.
- DETERMINISM CLAIM DOWNGRADE (adversarial + eval-rigor major): G5/Section 7 'byte-identical across machines' contradicts 6.3 'near-deterministic'. Downgrade to: reproducibility is guaranteed by the CACHE (re-run = cache replay = byte-identical), NOT by recomputation. temp=0 is greedy not deterministic; torch float kernels are not bit-identical across BLAS threads/hardware. Pin Ollama version + num_ctx + num_batch + BLAS thread count into the digest bundle; quantize cosine to fixed precision before thresholding so a borderline dedup edge cannot flip across machines and change Gold counts.
- DEDUP REDESIGN (adversarial + gap-finder major x2): (1) do NOT block on country for cross-lingual dedup -- that structurally excludes the HU-vs-AT cross-border duplicate G4 exists to collapse; block on a +/-N-day window only (or a coarse embedding LSH bucket), never same published_year (splits a Dec31/Jan1 event across years and re-inflates at the (geo,year) grain). (2) specify deterministic edge-set construction order (sort by content_sha256 pair) and a connected-component/chaining cap. (3) add a FIELD-UNION step: coalesce monetary/operators/rail_lines/gkg_* across each dup_group BEFORE picking is_canonical, recording which sibling supplied each field, so collapsing duplicates never drops the only investment figure or operator. (4) define how a merged cross-country story is attributed to (geo,year).
- MONETARY SEMANTICS (adversarial + researcher major): (a) define money aggregation precisely -- sum monetary_amount_eur over is_canonical rows only, and specify how the canonical figure is chosen when duplicates disagree (e.g. max-confidence or median, pinned). (b) clarify relationship between event_type in {investment,financial} and the monetary columns (an accident article can carry money; news_n_investment and news_total_investment_eur can legitimately diverge -- document it). (c) add gkg_amounts (GKG V2.1 V2.1AMOUNTS field) as the deterministic SoT for monetary on GKG rows; LLM monetary becomes the DOC/RSS fallback. Note GKG amounts are object-typed and need rail-relevance filtering.
- FX TABLE GOVERNANCE (approach-analyst + gap-finder missing): source the pinned per-year FX table from a citable provider (ECB reference rates) with a research-orchestrator record and a committed CSV covering the HUF/EUR year range; declare an FX-table change a cache/digest-invalidating event. For v1, optionally store monetary_raw + monetary_currency only and defer EUR normalization (do not block MVP on FX).
- OPERATIONS / MIGRATION SECTION (gap-finder blocker): add persist.py contracts (Arrow schema + partition layout + atomic write-to-temp-then-rename) for the THREE new artifacts (news_feature_wide, _cache, extract_failures); a resumable, cache-checkpointed first-run backfill plan against the single Ollama with rate limiting and interruption recovery; a rollback/quarantine path for a bad digest bundle; and an explicit legacy-projection contract test (wide -> legacy bytes, llm_confidence -> confidence rename). Define the _cache single-writer/concurrency story.
- DATE-PARSE CONTRACT (gap-finder minor, GAP-022): specify accepted formats (RFC-822 for RSS pubDate, GDELT compact YYYYMMDDTHHMMSSZ seendate, plus publishedDate/datetime fallbacks), TZ->UTC normalization, ambiguous-year policy; route unparseable-date rows to extract_failures (NOT a silent drop at the published_year IS NOT NULL filter, which would re-open the very gap GAP-022 closes) and wire the count into the 6.6 monitor.
- VALIDATION CONTRACT (gap-finder minor): add a per-column validation/coercion table extending validate_news_feature for every NEW field (event_type_secondary enum, monetary_currency ISO-4217, sentiment_probs length-3/sum-1, embedding length/L2 invariant, *_method enums, dup_group_id), and require Tier-1 to assert each on adversarial input -- otherwise the 'hardened validation' Tier-1 gate cannot be implemented from the spec.
- PROVENANCE COLUMN DIET (approach-analyst minor): replace the 8 per-row *_model_digest columns + dormant captured-not-used columns (gdelt_socialimage) with a single run_id on NewsFeatureWide referencing a one-row run manifest holding the digest bundle. Capture-everything can mean kept in cache/raw, not a materialized Silver column.
- GKG TONE NORMALIZATION (gap-finder minor): pin gkg_tone normalization to [-1,1] before correlating with XLM-R sentiment_score in the 6.6 drift cross-check (tone is ~[-100,100]); document whether GKG themes feed event_type as a prior/candidate or are store-only, and how V1-vs-V2 GKG theme taxonomies are handled.
- ARROW/SPARK TYPE + STORAGE (adversarial minor + gap-finder missing): specify the array->VectorUDT conversion (pyspark.ml.functions array_to_vector) for MLlib KMeans over the embedding column; confirm Spark 4.1 + pyarrow 24 read the list<float32>; add a Silver Parquet size estimate (768 x float32 x N rows) and decide whether embeddings live in the wide table or a side table so count-only Gold reads do not load 768-dim vectors.
- GOLDEN-SET STATISTICS REWORK (eval-rigor blocker x2): (1) the 180-cell stratification at n=150-250 gives ~1.4 articles/cell -- per-class F1 / per-language gates / 0.03 regression delta are inside binomial noise. Collapse the gated event taxonomy to 3-4 super-classes for v1 (report the 10-way confusion matrix un-gated), attach bootstrap 95% CIs and gate on CI-overlap not a fixed delta, set a minimum support per gated cell (n>=30, else report-only). (2) split the golden set into disjoint TUNE (tau, FX edges, HU offset, prompt iteration) and TEST (frozen, gate+baseline only) partitions; use k-fold for threshold selection and report held-out metric -- current single-set tune-on-test makes dedup/sentiment numbers in-sample-optimistic.
- LLM DETERMINISM / STABILITY SPEC (eval-rigor blocker): drop the byte-identical claim for LLM fields; measure stability by running the golden TEST set N>=20 times offline and reporting per-field agreement / Krippendorff alpha; gate live runs on mean metric minus 2*sigma_run; cache guarantee applies to cached bytes only. The N=3 'variance below epsilon' flakiness gate has no statistical basis -- remove it. Pin Ollama version + num_ctx + num_batch into the digest bundle.
- LLM-JUDGE FAITHFULNESS (eval-rigor major): do not gate releases on an unvalidated, unpinned LLM judge. Either replace the hard faithfulness gate with a human-labeled faithfulness subset (ROUGE-L stays a coarse non-regression signal only), or pin the judge digest, validate it once against >=50 human labels (report judge-vs-human kappa), and gate on the error-adjusted score.
- ANNOTATION RIGOR (eval-rigor major): require a committed tests/golden/news/GUIDELINES.md defining each field's decision rules -- critically the sentiment TARGET (document polarity matching XLM-R training vs rail-system stance; if the latter, XLM-R is the wrong tool and must be flagged). State annotator HU+DE+EN language coverage and the single-annotator fallback (kappa unobtainable with one annotator -- acknowledge it). Set a kappa acceptance floor below which a field is report-only not gated.
- METRIC CHOICE FIXES (eval-rigor major + minor): use macro-F1 / per-class recall (not raw accuracy) for the imbalanced country field; evaluate is_rail_related PRECISION on a separate realistic-prevalence term-matched sample (the balanced golden set hides the 'Bahnhofstrasse' production precision problem); split monetary error into LLM read-error vs FX-conversion error; add a concrete calibration metric (ECE/Brier, reported-not-gated) for llm_confidence; make the +/-5% (geo,year) canonical-count error the PRIMARY dedup gate (demote pairwise P/R to a diagnostic; report B-cubed / adjusted Rand instead of raw pairwise).
- ENCODER CI FIXTURE STABILITY (eval-rigor minor): Tier-1 must assert encoder outputs at the DECISION level (argmax label, language code, cosine-rank ordering) with documented float tolerance (atol~1e-3) on probabilities, not raw logits; pin torch/transformers versions in the CI image and capture fixtures on that same image to avoid cross-machine flakiness.
- COPYRIGHT / PII (adversarial + gap-finder minor): committing 150-250 full third-party news bodies into a public GitHub-Pages-linked repo is a copyright/PII exposure (also gkg_persons). Store hashes + offsets + minimal quoted excerpts, or article IDs + a fetch fixture, or keep bodies in a private LFS/CI store. Add as an explicit open decision.
- DASHBOARD-SYNC OBLIGATION (approach-analyst missing): carry the HARD-RULE docs/TASKS.md + docs/index.html sync obligation onto EVERY gap in the GAP-031..044 decomposition, not just the Gold-widening gap, or most of the work lands non-compliant.
- RESEARCH-ORCHESTRATOR RECORDS (approach-analyst missing): map each new model (XLM-R, fastText lid.176, the chosen e5/bge-m3 embedder, HU/German NER) to a required research-orchestrator record under .planning/coursework/research/bigdata/<slug>.md with routed MCP provider + source URLs, and treat each as a real schedule item.

# Appendix B — Evaluation plan verdict

NEEDS-REWORK before it can serve as a gate, though the structure (golden set, per-feature metrics, 3-tier CI, regression baseline, digest tracking, drift monitoring) is the right skeleton and worth keeping. Three statistical defects make the current numbers untrustworthy: (1) tune-on-test leakage -- tau, the HU offset, and prompt iteration are fit on the same set used to report the gate, so dedup/sentiment numbers are in-sample-optimistic; fix with a disjoint frozen TUNE/TEST split + k-fold for thresholds. (2) The 180-cell stratification at n=150-250 puts per-class F1 gates and the 0.03 regression delta inside binomial sampling noise; fix by collapsing the gated taxonomy to 3-4 super-classes, attaching bootstrap CIs, gating on CI-overlap, and enforcing a minimum support per gated cell (report-only below it). (3) The 'temp=0 -> near-deterministic, N=3 variance<epsilon' flakiness gate is statistically baseless; replace with an offline N>=20 stability measurement (Krippendorff alpha), gate on mean minus 2*sigma_run, and apply the byte-identical guarantee only to CACHED bytes. Also fix: validate the LLM-judge faithfulness metric against >=50 human labels and pin its digest (or drop the hard gate); commit an annotation GUIDELINES.md that pins the sentiment TARGET (document-polarity vs rail-stance -- a real XLM-R mismatch risk); use macro-F1 not accuracy for the imbalanced country field; measure is_rail_related precision on a realistic-prevalence sample not the balanced set; make the +/-5% (geo,year) count error the PRIMARY dedup gate. After these, it is a defensible, gradeable eval plan.

# Appendix C — Testing strategy summary

Three CI tiers, scoped to the documented constraint that Ollama + HF models cannot run in the build sandbox. Tier-1 (gates every PR, no models): deterministic-only assertions -- content-hash identity/idempotency (run-twice = byte-identical cache replay), URL-normalization + collision tests, validate_news_feature on adversarial/malformed JSON for EVERY new column (enum/range/list-length/L2 invariants), FX conversion, gazetteer canonicalization, Gold pivot reindex determinism (GAP-016), date-parse contract incl unparseable->extract_failures (GAP-022), dedup shuffle-invariance (identical dup_group_ids regardless of input order), legacy-projection byte contract (wide->15-col, llm_confidence->confidence), and encoder fixtures asserted at the DECISION level (argmax label / language code / cosine-rank order) with atol~1e-3 on probabilities, captured on the pinned CI image. Tier-2 (mocked transport, real schema): VCR-style cassettes of real Ollama responses captured once, asserting the pipeline maps known LLM JSON to the right NewsFeatureWide row -- catches prompt/parse/validation regressions without a live model. Tier-3 (nightly/pre-release, requires Ollama+encoders): full pipeline over the FROZEN golden TEST partition, per-feature metrics with bootstrap CIs, release gate fails on any hard-threshold breach or CI-overlap regression vs a committed golden_baseline.json (explicit reviewed baseline bumps only); LLM stability characterized offline at N>=20 not N=3. Reproducibility is guaranteed by the cache (replay), not by cross-machine recomputation; the digest bundle (incl Ollama version, num_ctx, num_batch, BLAS threads) is pinned and a digest change forces Tier-3 re-eval before a new baseline. Production drift monitoring (no ground truth): PSI/KL on event_type/sentiment/language mix, XLM-R-vs-normalized-gkg_tone correlation alarm, LLM/JSON failure rates, news_dedup_ratio swings, null country/published_year coverage -- every breach raises a dashboard chip + log, never a silent pass. Golden set: stratified primarily by text_source (rss-fulltext vs gdelt-snippet) and language/country, with a committed annotation guideline pinning the sentiment target, a kappa floor below which a field is report-only, and bodies stored as hashes/excerpts/fetch-fixtures to avoid copyright/PII exposure.

# Appendix D — Open decisions (raised by the spec author, pre-review)

- Hungarian sentiment: XLM-R is not HU-finetuned (tweet domain) -- evaluate the ...-sentiment-multilingual sibling and pick per-language, then golden-set recalibrate, vs falling back to GKG tone for HU. Recommended: evaluate both, pick winner, recalibrate.
- Cross-lingual dedup cosine threshold tau and blocking window (country / |delta-year|) -- calibrate on golden duplicate-families to hit recall>=0.80/precision>=0.90; start date-blocked, same country.
- NER scope for v1: full huBERT + German-BERT NER + gazetteer, vs gazetteer + GKG-orgs only with NER as a fast-follow. Recommended: gazetteer + GKG-orgs first (deterministic, cheapest), add NER once operator-F1 shows gazetteer recall is insufficient.
- GKG history parser (master_v1 csv.zip, 1979-2016) now vs DOC-era-only v1. Recommended: v1 = DOC-era + live GKG-mode if available; deep-history GKG parser as a tracked follow-up.
- Embedding input: summary_en (LLM-normalized, best cross-lingual alignment) vs raw title+lead (LLM-independent). Recommended: summary_en when present, raw title+lead fallback, record which was used.
- Whether MLlib clustering lands as news_cluster_<k> columns in Gold or stays a separate analytical artifact. Recommended: separate artifact first; promote only if used as model features.
- Formalize the silver/news/extract_failures sidecar schema now (closes GAP-006 follow-up, needed for the failure-rate monitor) vs ad-hoc logging. Recommended: formalize now.
- Gap decomposition: new IDs from GAP-031 (wide extraction, multi-model role split, dedup-before-aggregation, Gold widening, eval harness, GKG/DOC passthrough wiring) and explicit resolution of GAP-016/022/026/029 -- owner to confirm board slugs in docs/TASKS.md and the dashboard sync.
