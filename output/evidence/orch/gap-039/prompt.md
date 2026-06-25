You are implementing one task in the railway-lakehouse big-data course project.
The repo's `AGENTS.md` is authoritative and auto-loaded — follow its Hard Rules
(raw Bronze immutable; numeric stat merges deterministic, never LLM-rewritten;
outputs under `output/`; no fabricated data; tests must not depend on `coursework/`
data — use `tmp_path`/fixtures; keep the live dashboard in sync).

## Your task: GAP-039

The spec below was drafted by a Claude research subagent. **First review and improve it**:
sanity-check it against the live code, and refine it (via `$ship-it` + research MCPs) ONLY where
it is wrong, stale, or thin — **do not widen scope**. Then implement strictly against the
(possibly-refined) spec.

### GAP-039 — Wide article-grain NewsFeature contract + idempotent cached Silver extraction pass

`HIGH` . level **model-pipeline** . effort **L** . depends on: GAP-006 (Silver persistence contract); unblocks: GAP-031–038 (language, sentiment, NER, embeddings, monetary, summarization, per-field confidence), GAP-040 (news pivot determinism)

**Build:** Define the wide article-grain NewsFeature schema (extending the current 15-field baseline with gkg_* fields, embeddings, cluster/dedup IDs, extraction_model_digest, per-field confidences, and a content-hash contract), establish the idempotent, content-hash-cached, model-digest-pinned Silver extraction pass that never reruns the same content twice, and freeze the Parquet schema/paths in DATA_CONTRACTS.md. The expensive NLP runs ONCE and is cached; never inside Spark. Backward-compatible with the existing 15-field NewsFeature in production.

**Context.** GAP-039 is the unblocker for the news-feature-extraction wave (GAP-031–038, GAP-040). Currently: (1) NewsFeature schema (schema.py:39–54) has 15 fields, none carrying model digests, confidences per field, or embeddings; gdelt_passthrough() exists but has zero callers (extract.py:86–100); ArticleRecord landing (bronze/sources/) captures 6 fields only, dropping GDELT DOC 2.0's domain/language/sourcecountry/socialimage; the LLM prompt (extract.py:31–69) asks for sentiment+confidence+language+summary but returns a flat dict, never confidences-per-field; the Ollama client (ollama_client.py) returns a single dict, untraceable to the model digest (Qwen 3.5:9b-q8_0); no extraction ever runs live (every test mocks generate_json); extraction quality is unvalidated (round-trip tested only with empty arrays). (2) Gold aggregate_news() (gold/build.py:82–125) emits counts+sentiment per (geo,year) but NEVER aggregates rail_lines/language/confidence/embeddings. Real production Gold is stats-only (news_rows=[]); no news column lands in Gold. (3) DATA_CONTRACTS.md:47–66 lists the current 15 fields but omits monetary_raw (GAP-029). (4) Silver persist (persist.py) writes one replaceable snapshot per ingest_date partition with NO content-hash cache or model-digest tracking, so reruns extract the same content twice. (5) The registered verification command pipeline.py:45–78 has `--skip-news-extraction` defaulting True, so `--news 0` is untested in a real run (pipeline.py:342–357). This task freezes the wide contract before GAP-031–040 build extractors into it. The expensive NLP (embeddings, clustering, sentiment, operators, monetary, translation) runs ONCE and is cached via content-hash; never per-row UDFs in Spark. Multi-tool ROLE SPLIT per AGENTS.md:120–137: LLM (Ollama Qwen, schema-JSON, temp 0) for generative slice (is_rail_related, event_type, summary_en, monetary_raw); XLM-R for deterministic sentiment; fastText/lingua for language; LaBSE for embeddings/clustering; huBERT+BERT NER for operators/rail_lines; GDELT GKG passthrough for tone/themes/persons/orgs/locations. Extraction failures account visible in a sidecar manifest, not dropped silently.

**Problem.** (1) Schema gap: NewsFeature lacks per-field confidences, model digests, GKG fields, embeddings, cluster/dedup IDs. (2) No idempotent caching: Silver rewrites the same article 15 times via pipeline reruns, missing 15-way extraction cost savings. (3) No content-hash contract: DATA_CONTRACTS.md:47–66 lists only 15 fields; monetary_raw is missing (GAP-029 confirms); no Parquet schema update. (4) No extraction failure accounting: extract_batch (extract.py:103–113) silently returns a subset; failed articles are lost. (5) Unverified GDELT: gdelt_passthrough() (extract.py:86–100) is unreferenced code; ArticleRecord landing drops sourcecountry/language fields GDELT provides; GKG passthrough path is unbuilt. (6) Test coverage: extract_batch is mocked everywhere (generate_json never runs live); roundtrip tested only with empty arrays (pipeline.py:342–357 `news_rows=[]` when extraction is skipped). Evidence: schema.py:39–54 (15 fields, no confidences/digest/embedding/gkg/cluster); persist.py:110–125 (one snapshot per ingest_date, no hash cache); gold/build.py:82–125 (no aggregation of language/confidence/rail_lines/embeddings); DATA_CONTRACTS.md:47–66 (15 fields listed, monetary_raw absent); extract.py:86–100 (gdelt_passthrough zero refs); pipeline.py:45–78 (--news 0 by default); tests/test_silver_news_parsers.py (mocked generate_json only).

**Steps.**
1. RESEARCH (mandatory per coursework workflow): invoke `research-orchestrator` skill; route through Context7/Ref/Tavily/Exa: (a) per-field confidence patterns in LLM outputs (transformers library, huggingface guidance docs, pydantic field validators); (b) content-hash + model-digest caching for NLP pipelines (sentence-transformers, spacy, huggingface caching); (c) GDELT GKG field semantics (themes, tone, persons, orgs, locations; current data.gdeltproject.org/gkg docs); (d) Parquet schema evolution (pyarrow schema contract for append-only growth); (e) LangChain embeddings and clustering patterns (embeddings dimension contracts, approximate matching, deduplication). Write `.planning/coursework/research/bigdata/newsfeature-wide-contract.md` naming research-orchestrator, the routed provider(s), and source URLs.

2. SCHEMA EVOLUTION — extend NewsFeature (schema.py:39–54) from 15 → 28+ fields, backward-compatible via defaults. New fields (all Optional, default None unless stated):
   - `language_detected_code: Optional[str]` — ISO 639-1 (fastText/lingua model output).
   - `language_confidence: Optional[float]` — [0,1] per-field confidence from fasttext/lingua.
   - `sentiment_label: Optional[str]` — negative|neutral|positive (XLM-R model output; rename current `sentiment` to avoid conflict, OR keep it and track model-source separately via digest).
   - `sentiment_score: Optional[float]` — continuous [-1,1] from XLM-R logits.
   - `sentiment_confidence: Optional[float]` — [0,1] per XLM-R model uncertainty.
   - `is_rail_related_confidence: Optional[float]` — [0,1] Ollama/LLM confidence on the gate.
   - `event_type_confidence: Optional[float]` — [0,1] Ollama confidence on the event classification.
   - `summary_en_source: Optional[str]` — "ollama" | "google_translate" | "gpt4" (traceability; set by the extractor, not the LLM).
   - `operators_ner_model: Optional[str]` — "hubert_nerkoc" | "german_bert" | "gazetteer" (which NER passed the match).
   - `operators_confidence: Optional[float]` — mean [0,1] across all matched operators.
   - `rail_lines_ner_model: Optional[str]` — same as operators_ner_model.
   - `rail_lines_confidence: Optional[float]` — mean [0,1] across all matched lines.
   - `monetary_raw_parsed_eur: Optional[float]` — numeric EUR extracted by a dedicated monetary parser (separate from LLM, e.g. regex + currency-db).
   - `monetary_confidence: Optional[float]` — [0,1] confidence in the extraction (whether amount came from LLM, regex, or None).
   - `gkg_themes: Optional[str]` — GDELT GKG semicolon-delimited theme tags (e.g. "ECON_TRADE_AGREEMENT;LABOR_STRIKE").
   - `gkg_persons: Optional[str]` — GDELT GKG persons (free-form concatenation or JSON list).
   - `gkg_organizations: Optional[str]` — GDELT GKG organizations.
   - `gkg_locations: Optional[str]` — GDELT GKG locations (comma-separated).
   - `gkg_tone: Optional[float]` — GDELT GKG tone [-100,100]; mapped to sentiment_label if sentiment is absent.
   - `gkg_emotions: Optional[str]` — GDELT GKG emotion codes (e.g. "DISGUST,FEAR").
   - `gkg_tone_source: Optional[str]` — "gdelt_gkg" | "xlm_r_model".
   - `text_embedding_model: Optional[str]` — "labse_v5_d768" | "sentence_bert_multilingual" (used by GAP-035 clustering).
   - `text_embedding: Optional[list[float]]` — 768-d float vector (or None to defer to GAP-035).
   - `cluster_id: Optional[str]` — dedup/cross-lingual cluster ID assigned by GAP-035 MLlib clustering (e.g. "cluster_001_seed_url_hash").
   - `cross_lingual_dedup_id: Optional[str]` — group ID for articles with near-identical embedding (LaBSE similarity > threshold; managed by GAP-035).
   - `extraction_timestamp_utc: Optional[str]` — ISO 8601 UTC timestamp when the extraction ran (for debugging/auditing).
   - `extraction_model_digest: Optional[str]` — sha256(Ollama Qwen:3.5:9b-q8_0 + config.json + prompt_hash) so reruns detect model changes. Set by `extract_article()` and `gdelt_passthrough()`.
   - `confidence_schema_version: str = "1.0"` — schema version for backward compat (new field, not optional, default "1.0" for existing rows).

   Preserve the current 15 fields with their defaults; add the new fields as Optional[T] = None. Update validate_news_feature() to accept and coerce the new fields (e.g. language_code range check, confidence clamp to [0,1], sentiment_score to [-1,1]).

3. CONTENT-HASH + MODEL-DIGEST CACHE CONTRACT: create `silver/news/cache.py` exporting:
   - `extract_cache_key(article: ArticleRecord | dict) -> str` — SHA256 of (article_id, title, body, url, published_date) to detect content changes.
   - `model_digest_key() -> str` — SHA256(OLLAMA_MODEL + config.OLLAMA_TIMEOUT + _JSON_SCHEMA + _SYSTEM + temperature) from config.py and extract.py:23–47. A changed model/prompt/schema invalidates all cached extractions.
   - `CacheBackend` protocol: `get(cache_key: str, model_digest: str) -> Optional[NewsFeature]`, `put(cache_key: str, model_digest: str, feature: NewsFeature) -> None`, `cache_stats() -> dict`.
   - `FileSystemCache` implementation: root `silver/.news_extraction_cache/`, subdirs per model_digest (e.g. `silver/.news_extraction_cache/{model_digest}/`), one JSON per article (key = hex_cache_key + ".json"). Idempotent writes, no multiprocessing lock needed (file-per-article). Include a `_manifest.json` per digest listing cached count, last_update, model_digest, and a truncated log of the last 100 hits/misses.

4. EXTRACTION PASS (rewrite extract.py): split `extract_article()` into two phases:
   - `extract_article_cached(article: ArticleRecord, cache: CacheBackend) -> Optional[NewsFeature]` — check cache first (cache_key + model_digest), return cached hit or None if uncached. On cache miss, run LLM, validate, store in cache, return.
   - `gdelt_passthrough_cached(gkg: dict, cache: CacheBackend) -> NewsFeature` — similar caching for GDELT GKG (cache_key = article_id+source="gdelt"). No LLM call, deterministic passthrough.
   - Keep the old `extract_article()` for backward compat (calls `extract_article_cached` with a no-op cache).
   - Populate `extraction_model_digest` in every returned NewsFeature so Gold/Spark know what model produced it.

5. FAILURE ACCOUNTING: create `silver/news/failures.py` exporting:
   - `ExtractionFailure` dataclass: `article_id, source, url, title, published_date, reason (str), timestamp_utc, model_digest`.
   - `persist_news_failures(failures: list, root, ingest_date)` — write to `silver/news/news_extraction_failures/ingest_date=YYYY-MM-DD/failures.parquet` (same partition scheme as successes).
   - Update `extract_batch()` to collect failures (missing required fields, LLM timeout, validation error) and return `(successes, failures)` tuple. Caller decides whether to persist both or warn on failures; logging is required.

6. UPDATE persist.py: add `persist_news_failures()` signature (defer implementation to GAP-006 follow-up if not in scope); log failure counts in the manifest. Parquet schema for failures includes the `ExtractionFailure` fields.

7. UPDATE DATA_CONTRACTS.md Silver News section (lines 47–66): rewrite to list all 28 fields in order, group into "Provided by Bronze", "LLM generative", "Model-extracted", "GKG passthrough", "Per-field confidence", "Caching/audit", with citations to the new schema.py field order. Explicitly list monetary_raw (close GAP-029). Add a "Content-hash cache contract" subsection explaining the cache key, model_digest, and the FileSystemCache location/layout.

8. TESTS (tests/test_silver_news_wide_contract.py, new, marked `unit`):
   - Test 1: `NewsFeature` dataclass: 15 old fields + 13 new fields = 28 total; instantiate with all old fields (backward compat) and assert new fields default to None. Instantiate a new-field row and assert `confidence_schema_version="1.0"`.
   - Test 2: `validate_news_feature()` coerces new fields: sentiment_score clamped [-1,1], language_code checked against ISO 639-1 set, confidences clamped [0,1], gkg_* strings empty-string→None.
   - Test 3: `extract_cache_key()` deterministic: same content → same key; minor title change → different key.
   - Test 4: `model_digest_key()` includes OLLAMA_MODEL + config values; a changed OLLAMA_MODEL env var produces a different digest.
   - Test 5: `FileSystemCache` get/put round-trip: put a NewsFeature, get it back byte-exact (JSON serialization idempotent). Verify `_manifest.json` is created and hit/miss counts increment.
   - Test 6: `extract_article_cached()` with cache: (a) cache miss on first call, LLM called (mocked), result stored in cache; (b) cache hit on second call, LLM NOT called, cached result returned; (c) model_digest mismatch invalidates cache (same article, different model → re-extract).
   - Test 7: `gdelt_passthrough_cached()` deterministic (no LLM): populates gkg_* and tone-derived sentiment, sets `extraction_model_digest` to a canonical "gdelt_gkg_passthrough" marker.
   - Test 8: `extract_batch()` returns tuple `(successes, failures)`. Feed mixed valid+invalid articles (one with missing title, one malformed URL), assert successes non-empty and failures non-empty with reason logged.
   - Test 9: Parquet round-trip: serialize a wide NewsFeature to Parquet (28 fields, with floats, lists, strings, None), reload, assert byte-exact equality. Verify new fields are present in the schema.
   - All tests mock Ollama; no live model needed. Use tmp_path for cache files.

9. INTEGRATION TEST (tests/test_silver_news_extraction_e2e.py, marked `integration`): feed fixture Bronze news (RSS XML + GDELT JSON from tests/fixtures/bronze/news/) through the full pipeline: ArticleRecord → cached extraction → NewsFeature → persist → reload. Verify: (a) first run extracts and caches; (b) second run with same ingest_date reloads from cache (zero LLM calls); (c) a new ingest_date with new articles extracts new articles, reuses cache for unchanged articles; (d) failure accounting sidecar written if any articles fail; (e) Parquet schema includes all 28 fields.

10. GDELT PASSTHROUGH WIRING: update pipeline.py and silver/run.py to call `gdelt_passthrough_cached()` on incoming GDELT articles (not just RSS). Check if GDELT DOC ArtList response includes gkg_* fields; if not, the article is still processed as a normal `extract_article_cached()` call. If GKG is available (future integration with GDELT history backfill), use passthrough. For now, document as "reserved for future integration with GDELT GKG history".

11. DOCS: update README.md with a "News Feature Extraction" section explaining the wide schema, per-field confidences, model digest pinning, and the content-hash cache (location, how to clear). Add a "Known Limitations" subsection listing: (a) language detection not yet wired (GAP-031), (b) sentiment from XLM-R not yet wired (GAP-032), (c) operators/rail-lines NER not yet wired (GAP-034), (d) embeddings/clustering not yet wired (GAP-035), (e) monetary parsing not yet wired (GAP-036), (f) translation/summarization not yet wired (GAP-037), (g) extraction_model_digest currently a placeholder (no Qwen digest calculated live yet), (h) extraction failures not persisted (awaiting GAP-006 follow-up).

12. DASHBOARD SYNC (Hard Rule, AGENTS.md:81): flip `docs/TASKS.md` `silver/wide-newsfeature-contract` from `todo` to `in_progress`/`done`; update the related chip in `docs/index.html` (e.g. "28-field NewsFeature contract + cache"). Append a row to `docs/GAP_REGISTER.md` status = in_progress, evidence = schema.py + persist.py + cache.py + tests, closure criterion = all 28 fields persisted/reloaded + cache hit measured. Append handoff entry to `docs/PROGRESS_LOG.md` naming the unblocked tasks (GAP-031–038, GAP-040).

**Files to touch:** `src/railway_lakehouse/silver/schema.py (extend NewsFeature 15→28 fields, update validate_news_feature)` `src/railway_lakehouse/silver/news/cache.py (new, extract_cache_key, model_digest_key, CacheBackend protocol, FileSystemCache impl)` `src/railway_lakehouse/silver/news/extract.py (split extract_article → extract_article_cached, gdelt_passthrough → gdelt_passthrough_cached, extract_batch → (successes, failures) tuple, set extraction_model_digest)` `src/railway_lakehouse/silver/news/failures.py (new, ExtractionFailure, persist_news_failures)` `src/railway_lakehouse/silver/persist.py (add persist_news_failures signature, log failure counts)` `tests/test_silver_news_wide_contract.py (new, unit tests for schema, cache, validation)` `tests/test_silver_news_extraction_e2e.py (new, integration test with fixture Bronze, cache round-trip, failure accounting)` `docs/DATA_CONTRACTS.md (rewrite Silver News section:47–66, list all 28 fields, add cache contract subsection, close GAP-029)` `README.md (add News Feature Extraction section + known limitations)` `docs/TASKS.md (silver/wide-newsfeature-contract todo→in_progress)` `docs/GAP_REGISTER.md (GAP-039 status + evidence + closure + Test Failure Mapping row)` `docs/index.html (update related chip/metric)` `docs/PROGRESS_LOG.md (handoff entry)` `.planning/coursework/research/bigdata/newsfeature-wide-contract.md (research record, new)`

**Definition of Done (contract).**
- [ ] `NewsFeature` dataclass in schema.py now has 28 fields: 15 original (backward-compatible defaults) + 13 new (all Optional, default None). `confidence_schema_version="1.0"` is the only new non-optional field. Instantiation and `to_row()` serialization work for both old (15-field) and new (28-field) rows.
- [ ] `validate_news_feature()` accepts and coerces the 13 new fields: sentiment_score → [-1,1], language_code → ISO 639-1 set, all confidences → [0,1], gkg_* strings → coerce empty string to None.
- [ ] `silver/news/cache.py` exists and exports: `extract_cache_key(article) → str`, `model_digest_key() → str` (deterministic, includes OLLAMA_MODEL + config), `CacheBackend` protocol with `get/put/cache_stats()`, `FileSystemCache` implementation with per-model-digest subdirs, `_manifest.json` per digest tracking hits/misses/count.
- [ ] `extract_article_cached(article, cache)` and `gdelt_passthrough_cached(gkg, cache)` replace the old functions; `extract_article()` backward-compat wrapper calls cached version with optional cache. Both set `extraction_model_digest` on return.
- [ ] `extract_batch()` returns `(successes: list, failures: list)` tuple. Failures are `ExtractionFailure` objects with article_id, reason, timestamp. Logging on failure is required.
- [ ] `silver/news/failures.py` exists with `ExtractionFailure` dataclass and stub `persist_news_failures()` signature (implementation may defer to GAP-006 follow-up).
- [ ] Cache round-trip test passes: write a NewsFeature, get it back, byte-exact JSON equality. Cache hit on second call measured (LLM call count = 0 on cache hit).
- [ ] Parquet round-trip test passes: serialize 28-field NewsFeature, reload, schema includes all 28 fields by name, no field loss.
- [ ] Integration test with fixture Bronze (RSS XML + GDELT JSON) passes: first extraction → cached, second run → all cache hits, failure account sidecar written if needed.
- [ ] `python -m pytest -q tests/test_silver_news_wide_contract.py tests/test_silver_news_extraction_e2e.py` passes with 0 mock warnings, all new fields exercised.
- [ ] DATA_CONTRACTS.md Silver News section (lines 47–66) rewritten: all 28 fields listed in order, grouped by source (Bronze, LLM, model, GKG, confidence, cache/audit), monetary_raw explicitly listed (close GAP-029), cache contract subsection describes key/digest/layout.
- [ ] README.md has a "News Feature Extraction" section with schema overview, per-field confidence rationale, model digest pinning, cache location, and known limitations (GAP-031–037 unlinked).
- [ ] Dashboard + docs synced in the same change (Hard Rule): `docs/TASKS.md` silver/wide-newsfeature-contract status updated, `docs/index.html` chip updated, `docs/GAP_REGISTER.md` GAP-039 status + evidence + Test Failure Mapping row added, `docs/PROGRESS_LOG.md` handoff entry to GAP-031–038 + GAP-040.
- [ ] Research record written at `.planning/coursework/research/bigdata/newsfeature-wide-contract.md` naming research-orchestrator + routed MCP provider(s) + source URLs.
- [ ] Raw Bronze untouched; no numeric values changed; all extractions cached and deterministic (no rerun penalty). All outputs under output/ or the committed .news_extraction_cache/ root.

**Verify:** `python -m pytest -q -m unit tests/test_silver_news_wide_contract.py` (all schema/cache/validation tests pass) AND `python -m pytest -q -m integration tests/test_silver_news_extraction_e2e.py` (fixture extraction + cache round-trip + failure account pass) AND `python -m pytest -q` (no new failures, was 108 passed) AND `python -c "import railway_lakehouse.silver.news.cache; import railway_lakehouse.silver.news.failures; from railway_lakehouse.silver.schema import NewsFeature; print(len(NewsFeature.__dataclass_fields__)); assert 28 <= len(NewsFeature.__dataclass_fields__)"` (28+ fields) AND manual inspection of docs/DATA_CONTRACTS.md Silver News section (28 fields, monetary_raw listed, cache contract subsection present).

**Pitfalls.** ["Do NOT persist extraction failures as a separate table until GAP-006 follow-up confirms the schema. For now, collect them in memory, log loudly, and optionally write a sidecar JSON manifest (not Parquet). The integration test must verify they are logged.", "The content-hash cache MUST NOT invalidate based on article changes (immutable content contract): if an article URL changes but the article_id is the same, it is a NEW article (different extracted content), not a cache miss. Use (article_id + title + body + url) as the cache key to detect actual content changes; a new URL with the same body is a cache miss.", "model_digest_key() MUST include the OLLAMA_MODEL value so changing from Qwen:3.5:9b to Qwen:7b invalidates the cache. If OLLAMA_MODEL is an env var, read it in the function; if it is a config constant, include it in the hash. Document this in the function docstring.", "Extraction failures must NOT abort extract_batch(). If one article fails LLM extraction, log it, append to failures, and continue with the next article. Only raise if the cache itself is corrupted (e.g., OSError on write).", "The 13 new fields are backward-compatible (all Optional=None); existing code reading 15-field NewsFeature rows from persisted Parquet MUST still work. Test this explicitly: reload an old 15-field Parquet, assert missing new-field columns are None/empty after coercion.", "Do NOT calculate Qwen model digest live (SHA256 of binary weights) — that is infeasible. Instead, use a canonical string (model name + version + quantization + prompt hash). The digest is for cache invalidation only, not cryptographic authenticity.", "The FileSystemCache location (silver/.news_extraction_cache/) is git-ignored (add to .gitignore). Cache is a local optimization; it is not committed or synced to MinIO. Per-machine cache semantics OK.", "Per-field confidence fields (language_confidence, sentiment_confidence, etc.) are placeholders in this task. GAP-031–038 will populate them. For now, populate with None or a stubbed 0.5 if the extractor produces a generic confidence; the schema contract just reserves the fields.", "Backward compat with the current 15-field NewsFeature is critical: the schema change MUST NOT break existing production Gold/Spark jobs. Test explicitly that a pickle/Parquet round-trip of a 15-field row survives a reload with the new schema.", "Do NOT add the new fields to the LLM prompt (extract.py:50–69) unless they are implemented. The prompt asks for 11 fields today; adding 'give me per-field confidences' to Qwen without implementation is scope creep. The prompt stays the same; GAP-031–038 each updates their own extractor to populate new fields.", "Extraction model digest is currently a placeholder string (e.g., 'ollama_qwen_3.5_9b_q8_0_placeholder'). Calculating a real Qwen weight digest is out of scope; GAP-037–038 may refine this."]

## How to work
- Drive this with your **`$ship-it`** workflow, with **NO Linear** — all context lives in
  this repo's code and docs (`AGENTS.md`, `docs/GAP_TASKS.md`, `docs/GAP_REGISTER.md`,
  `docs/DATA_CONTRACTS.md`, `docs/TASKS.md`, `docs/STATE_AND_ROADMAP.md`). Do not look for or
  expect a ticket.
- First write **one** implementation plan, **review and approve it yourself**, then implement
  strictly against that approved plan. Keep the plan scoped to this gap only.
- If you need ANY external research (library/framework APIs, exact config keys, a method or
  algorithm, version compatibility, course-domain background), use the **`/research-orchestrator`**
  skill and route through its MCP providers (Context7, Ref, Tavily, Exa, Firecrawl, LangChain
  Docs) — do not rely on memory or ad-hoc browsing. Cite source URLs for any external claim, and
  record the research in `.planning/coursework/research/bigdata/<gap-slug>.md`.
- Write **unit tests** and **integration tests**; MinIO is already running on
  localhost:9000 (compose `railway-minio`), so integration paths that need object
  storage can use it. Add a **short live test** only if the Definition-of-Done
  requires live evidence; keep it bounded.
- Run the task's **Verify** command and the full suite (`python -m pytest -q`) and
  make them green before you open the PR.
- If this changes pipeline state (advances/closes a gap, wires a parser, persists a
  layer, changes a source's status), update `docs/TASKS.md` + `docs/index.html` in
  the SAME change (AGENTS dashboard-sync Hard Rule) or CI will flag it.
- Branch `impl/gap-039` is already checked out in this worktree. Commit, push
  to origin, and open a PR against `main` with `gh` (you have write access).

## Definition of done (do not stop until ALL are true)
- The task's Definition-of-Done checklist items are met.
- `python -m pytest -q` is green; `python -m compileall -q src tests` clean.
- A PR against `main` exists and is **mergeable** (no conflicts, CI reminder satisfied).

## Final output
When done, your final message MUST be a single JSON object matching the provided
output schema: the branch, PR url+number, which test tiers you ran and their result,
whether it is mergeable, which Definition-of-Done items are met, and (if you had to
stop early) blocked=true with the blocker. No prose outside the JSON.
