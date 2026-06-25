# GAP-035 Silver Language ID Research And Approved Plan

Date: 2026-06-25

Workflow:
- Skill: `research-orchestrator`
- Local-first review: `src/railway_lakehouse/silver/news/extract.py`, `src/railway_lakehouse/silver/schema.py`, `tests/test_silver_news_parsers.py`, `tests/test_silver_news_extract_prompt.py`, `tests/test_silver_news_wide_contract.py`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`
- Routed MCP providers: Context7, Tavily, Firecrawl

## Spec Review

The drafted spec is directionally correct but stale against the current branch:

- `extract.py` already removed `language` from `_JSON_SCHEMA` and the system prompt during GAP-050.
- `_build_prompt()` still embeds `language` keys in the few-shot example metadata, so the prompt can still show language even though the schema does not request it.
- `validate_news_feature()` still derives `language` and `language_detected_code` from raw model output, and no explicit deterministic language parameter exists.
- `gdelt_passthrough_cached()` still passes through `gkg.get("language")`, which may be absent or not ISO 639-1.
- Existing tests still include `"language": "en"` in fake LLM responses and do not assert deterministic HU/DE/EN detection.

Refined scope: use Lingua, not fastText. This keeps GAP-035 small, avoids a runtime model download/cache path, works offline after package installation, supports the project languages HU/DE/EN, and is enough for routing downstream model passes.

## External Research

Queries:
- Context7: `lingua-language-detector Python usage for deterministic language detection, LanguageDetectorBuilder, ISO 639-1 output, supported versions`
- Tavily: `lingua-language-detector PyPI latest version LanguageDetectorBuilder detect_language_of iso_code_639_1`
- Firecrawl: `fastText language identification lid.176.ftz model 176 languages official documentation`
- Firecrawl: `lingua-py lingua-language-detector Python README 75 languages LanguageDetectorBuilder from_languages ISO 639-1`

Sources:
- https://github.com/pemistahl/lingua-py
- https://pypi.org/project/lingua-language-detector
- https://fasttext.cc/docs/en/language-identification.html

Findings:
- Lingua Python package name is `lingua-language-detector`; imports are from `lingua`.
- Current Lingua release found by Tavily/PyPI and the GitHub README badge is `2.2.0`.
- Lingua 2.x uses Rust-backed Python bindings, supports Python >=3.12, and supports 75 languages including English, German, and Hungarian.
- Lingua exposes `LanguageDetectorBuilder.from_languages(...)`, `detector.detect_language_of(text)`, and `language.iso_code_639_1.name`.
- fastText official docs distribute `lid.176.bin` and `lid.176.ftz` for 176 languages, but choosing fastText would require model download/digest/cache handling that is outside the smallest implementation path for this gap.

Pinned dependency:
- `lingua-language-detector==2.2.0`

## Approved Implementation Plan

Self-review result: approved. The plan closes only GAP-035 and does not widen into sentiment, NER, GKG recovery, or Gold aggregation.

1. Tests first:
   - Add `tests/test_silver_language_id.py` with `pytest.mark.unit`.
   - Assert `identify_language()` returns `hu`, `de`, `en`, and `None` for empty/None text.
   - Assert `extract_article()` populates `NewsFeature.language` and `language_detected_code` from deterministic detection while fake LLM output omits language.
   - Assert `gdelt_passthrough_cached()` detects language without calling Ollama.
   - Assert validation accepts an explicit language and prioritizes it over any raw LLM language.
   - Assert package metadata matches the pinned `pyproject.toml` dependency.
   - Update existing news parser/extraction tests to remove fake LLM `language` fields and assert deterministic language where appropriate.

2. Implementation:
   - Add `src/railway_lakehouse/silver/language_id.py`.
   - Build one cached Lingua detector restricted to `Language.ENGLISH`, `Language.GERMAN`, and `Language.HUNGARIAN`.
   - Expose `identify_language(text: str | None) -> Optional[str]`.
   - Normalize whitespace and return lowercase ISO 639-1 codes, else `None`.
   - Add `lingua-language-detector==2.2.0` to `[project.dependencies]`.

3. Silver integration:
   - Import `identify_language` in `silver/news/extract.py`.
   - Add a small `_article_language()` helper and call it after article validation, before cache lookup/LLM calls.
   - Pass `language=...` into `_call_llm_once()` and `validate_news_feature()`.
   - Remove stale `language` keys from `_FEW_SHOT_EXAMPLES`.
   - Set GDELT passthrough `language` and `language_detected_code` from deterministic detection, falling back only to validated raw language if detection returns `None`.

4. Schema validation:
   - Add `language: Optional[str] = None` to `validate_news_feature()`.
   - Prioritize explicit deterministic language over raw output for both `language` and `language_detected_code`.
   - Update docstring to state that language is supplied before validation and is not LLM-owned.

5. Docs/dashboard:
   - Mark GAP-035 closed in `docs/GAP_REGISTER.md`.
   - Update `docs/TASKS.md` Wave 6 status.
   - Update `docs/index.html` model-preprocessing/dashboard text to mention deterministic Lingua language ID.
   - Append handoff entries to `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md`.

6. Verification:
   - `python -c "from railway_lakehouse.silver.language_id import identify_language; print(identify_language('Vasúti bővítés'))"`
   - `python -m pytest -q tests/test_silver_language_id.py`
   - `python -m pytest -q tests/test_silver_news_parsers.py`
   - `python -m pytest -q`
   - `python -m compileall -q src tests`
   - `git diff --check`
