# News → Gold feature integration: state scan + options research — 2026-06-24

> Skill: `research-orchestrator` (forced search before answering).
> Routed MCP providers used by the sub-agents: **Tavily** (search), **Exa** (web_search_exa),
> **Context7** (Ollama/Spark docs), **WebFetch/WebSearch** fallback, plus primary-source pages
> (GDELT GKG codebook, HuggingFace model cards, spaCy/Spark NLP/sbert docs, pdfplumber/Camelot/Docling, Databricks).
> Method: dynamic multi-agent workflow `news-feature-integration-scan` — 4 read-only codebase
> explorers + 5 routed research agents + 1 synthesis pass (1 explorer + 0 research agents failed;
> the failed explorer was `contracts-and-planned-schema`, covered by the gold/non-text explorers).

## Sub-notes (written by the research agents this session)
- `local-llm-feature-extraction-role-2026-06-24.md` — LLM role/model/throughput.
- `nonllm-nlp-news-features-2026-06-24.md` — encoders / spaCy / Spark NLP / sentence-transformers.
- `images-nontext-pdf-mining-2026-06-24.md` — images vs PDF-table extraction decision.

## Codebase reality (verified against source this session)
- **Parsers work, narrowest source.** RSS (`silver/news/rss.py`) + GDELT DOC (`silver/news/gdelt.py`)
  emit a 6-field `ArticleRecord`; 429 retry/backoff tested (`tests/test_gdelt_rate_limit.py`).
  GDELT is queried via **DOC 2.0 ArtList** (`gdelt.py:43-56`) which **structurally cannot** return
  GKG themes/tone/persons/orgs/locations.
- **Dead free signal (verified):** `gdelt_passthrough()` (`silver/news/extract.py:86`) has **zero callers**
  in `src/` or `tests/`; `past_recordings` master_v1 downloads GKG zips but lands them verbatim, unparsed.
- **`NewsFeature` = 15 fields (verified `schema.py:39-54`):** article_id, source, url, published_date,
  language, is_rail_related, country, event_type, operators[], rail_lines[], monetary_amount_eur,
  monetary_raw, summary_en, sentiment, confidence. The LLM prompt (`extract.py:31-69`) currently asks the
  model for **all** semantic fields incl. sentiment + confidence (i.e. broader than the recommended scope).
- **LLM news path has NEVER run live** — every test monkeypatches `generate_json`; no real `NewsFeature`
  row has been persisted. Extraction *quality* is unvalidated.
- **Gold (`gold/build.py`, verified):** `aggregate_news()` (l.82) emits `news_article_count`,
  `news_sentiment_mean`, `news_share_negative`, `news_total_investment_eur`, `news_n_<event>`,
  `news_op_<operator>` on `(geo, year)`. It **never** aggregates `rail_lines`, `language`, `confidence`.
  Real production Gold is **stats-only** (news_rows=[] because Ollama unavailable / `--skip-news-extraction`).
- **Non-text today:** numeric stats only (World Bank JSON, Eurostat TSV, KSH XLSX → StatFact; 93 canonical
  features). Statistik Austria ODS + UIC PDFs landed raw, **not parsed**. No image/OCR/PDF code in `/src`.

## Recommendation (integrated)
- **Keep the medallion "extract-wide in Silver, filter in Spark" pattern**, two grains: article-level wide
  `NewsFeature` store + `(geo,year)` Gold rollup.
- **Multi-tool role split** (not one model):
  - LLM (Ollama Qwen 7-9B, schema-JSON, temp 0): `is_rail_related`, `event_type`, `summary_en`,
    `monetary_raw/amount` — the generative slice only.
  - **XLM-R** (`cardiffnlp/twitter-xlm-roberta-base-sentiment`) for deterministic sentiment; mDeBERTa/bge-m3
    zero-shot as event/gate cross-check. (Reject FinBERT — EN-only, equities domain.)
  - **huBERT NerKor + German BERT NER + gazetteer** for operators/rail_lines *iff* hard Gold requirements.
  - **spaCy/HuSpaCy** as cheap substrate; **fastText/lingua** for `language`.
  - **LaBSE sentence-embeddings** → cross-lingual dedup + MLlib clustering (new Spark job, biggest depth lever).
  - **Wire `gdelt_passthrough` + parse GKG** → free tone/themes/persons/orgs/locations.
- **Never** call the LLM/encoders row-at-a-time inside Spark — one-time cached Silver pass; if distributed,
  `predict_batch_udf`/`mapInArrow` with broadcast model.
- **Images: do NOT build an image pipeline.** Only worthwhile non-text add = deterministic **pdfplumber**
  table extraction of the born-digital UIC PDFs into numeric StatFacts. Vision-LLM only as a labelled fallback.

## Priority (score-per-effort)
1. Parse GDELT GKG + wire `gdelt_passthrough` (free, already downloaded, zero inference).
2. Run the LLM news pass **for real once** and persist real `NewsFeature` rows (closes the credibility gap).
3. Add LaBSE embedding column + MLlib clustering/dedup Spark job.
4. Swap sentiment to XLM-R.
5. Widen `aggregate_news` to also roll up rail_lines/language/confidence/GKG-theme columns.

## Key sources (full lists in the sub-notes)
- GDELT GKG 2.1 codebook: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
- XLM-R sentiment: https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment
- huBERT: https://hlt.bme.hu/en/resources/hubert | https://huggingface.co/SZTAKI-HLT/hubert-base-cc
- Ollama structured outputs: https://docs.ollama.com/capabilities/structured-outputs
- PDF tables: https://camelot-py.readthedocs.io | https://heidloff.net/article/docling | https://developer.nvidia.com/blog/approaches-to-pdf-data-extraction-for-information-retrieval
- Spark NLP / Arrow UDFs: https://sparknlp.org/docs/en/concepts | https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.ml.functions.predict_batch_udf.html
