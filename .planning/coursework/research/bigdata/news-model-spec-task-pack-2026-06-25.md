# News multi-model preprocessing — spec + 14-task pack + adversarial review (2026-06-25)

> Skill: `research-orchestrator`. Routed MCP providers (via workflow sub-agents): Tavily, Exa, Context7, Ref, WebFetch/WebSearch + primary sources.
> Method: dynamic workflow `news-model-spec-and-task-pack` — 1 spec author + 14 task-spec authors (each read cited source files) + 5 independent reviewers + 1 synthesis (21 agents). Builds on `news-feature-integration-scan-2026-06-24.md`.

## Deliverables produced
- `docs/SPEC_NEWS_PREPROCESSING.md` — design contract (wide article-grain NewsFeature, role split, Silver-once cache, Spark-filter, eval strategy) + **single-box compute plan (Ryzen 5 1600 / GTX 1060 6 GB, sequential passes)** + 8 must-fix review blockers + MVP build order + open decisions.
- `docs/GAP_TASKS.md` — 14 appended pick-up-cold specs (GAP-031…044).
- `docs/GAP_REGISTER.md` — GAP-031…044 rows (status open, priorities P0→P3).
- `docs/TASKS.md` — Wave 6 board section. `docs/index.html` — WAVE 6 chips + footer.

## Owner decisions captured
- **UIC PDF**: capture everything (widen geo to all countries, stage unmapped tables/rows, mine traffic-trends text) but map deliberately into the numeric merge → GAP-041.
- **Compute**: single box, no hosted infra, sequential model passes due to 6 GB VRAM.

## Review blockers (code/source-grounded, must-fix before build)
1. **torch is CPU-only on Python 3.14 Windows** — no CUDA `cp314` wheels (PyTorch #169929). Encoders (XLM-R, embeddings, NER) can't use the 1060 without a separate Py3.12+CUDA env; Ollama (own llama.cpp CUDA build) CAN use the GPU. Run CPU-first, corpus is small.
2. **GDELT DOC body = snippet, many RSS = description-only** (gdelt.py / rss.py) — not full text; quality gates must stratify by `text_source`.
3. **GKG is absent for all live DOC rows** — DOC ArtList structurally lacks GKG; the csv.zip history parser is deferred. v1 must work GKG-absent.
4. **LaBSE is the wrong embedder** for dedup+clustering (~33 vs ~76 MMTEB clustering, arXiv 2502.13595) → pin **intfloat/multilingual-e5-large-instruct** or **bge-m3**; LaBSE only for strict-translation dedup.
5. **Spark MLlib KMeans is non-deterministic** (SPARK-21679) → clustering is a separate artifact, not a Gold column; reproducibility comes from the cache, not recomputation.
6. **Pinned NER ids were base LMs, not NER heads** → re-pin NYTK/novakat huBERT-NerKor (HU), flair/xlm-roberta-conll03 (DE).
7. **Identity/cache-key unsound** — `article_record_id` uses raw URL + per-batch index; decouple `article_id` (lineage) from `content_sha256` (cache/dedup key over normalized title+body).
8. **Golden-set statistics** — disjoint TUNE/TEST split (no tune-on-test), collapse 10-way event taxonomy to 3-4 gated super-classes, bootstrap CIs + min-support, replace N=3 flakiness gate with offline N≥20 stability.
- Plus: dedup must use date-window (not country) blocking, deterministic edge order, and field-union before canonical pick (don't drop the only money/operator on a collapsed sibling).

## Key sources (cited by reviewers)
- PyTorch Py3.14 CUDA wheels: https://github.com/pytorch/pytorch/issues/169929
- MMTEB (LaBSE clustering weakness): https://arxiv.org/abs/2502.13595 ; https://sbert.net/docs/sentence_transformer/pretrained_models.html
- Spark KMeans non-determinism: https://issues.apache.org/jira/browse/SPARK-21679
- HU NER: https://huggingface.co/NYTK/named-entity-recognition-nerkor-hubert-hungarian ; https://huggingface.co/novakat/nerkor-cars-onpp-hubert
- XLM-R sentiment: https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment
- fastText lid.176: https://fasttext.cc/docs/en/language-identification.html
- GDELT GKG 2.1 codebook: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
- Spark batch inference: https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.ml.functions.predict_batch_udf.html

## Next
- Owner to resolve open decisions (embedder e5-vs-bge, HU sentiment, clustering-in-Gold, GKG-history scope, monetary FX, golden-set body storage, gated taxonomy).
- Then build MVP-first: GAP-039 (wide contract + sound cache key) → GAP-033 (first live LLM run) → P1 encoders/Gold/eval.
