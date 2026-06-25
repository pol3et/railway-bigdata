# GAP-044 Parser Correctness Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:test-driven-development` for behavior changes and `superpowers:verification-before-completion` before any completion claim.

**Goal:** Add deterministic parser golden fixtures, field-coverage assertions, and robustness fixes for GAP-022, GAP-025, and GAP-026 without changing Bronze immutability or numeric merge semantics.

**Architecture:** Keep parsers deterministic and local. News parsers return `ArticleRecord` dataclasses; stats loaders return the existing long stats frame. Gold date handling and dict-default normalization are the only production behavior changes outside parser modules.

**Tech Stack:** Python stdlib XML/JSON/email date parsing, pandas, openpyxl, pdfplumber, pytest.

## Scope

In:
- RSS/GDELT parser error handling and field-drop logging.
- Gold news date parsing and optional dict-field defaults.
- Golden fixture tests for RSS, GDELT, World Bank, Eurostat, KSH, and UIC.
- Coverage matrix docs and JSON mirror.
- Dashboard/task/progress docs needed by `AGENTS.md`.

Out:
- Live downloads or network tests.
- Statistik Austria ODS parser implementation.
- GDELT GKG history parser.
- Eurostat GAP-023 policy changes beyond documenting current coverage behavior.
- LLM extraction or Ollama runs.

## Work Units

### Task 1: Fixture Set And RED Golden Tests

Files:
- Create `tests/fixtures/silver/news/rss_real_example.xml`
- Create `tests/fixtures/silver/news/gdelt_real_example.json`
- Create `tests/fixtures/silver/stats/worldbank_real_example.json`
- Create `tests/fixtures/silver/stats/eurostat_real_example.tsv`
- Create `tests/fixtures/silver/stats/eurostat_real_example.tsv.gz`
- Create `tests/fixtures/silver/stats/ksh_real_example.xlsx`
- Create `tests/fixtures/silver/stats/uic_real_synopsis.pdf`
- Create `tests/test_silver_parser_golden_fixtures.py`

Steps:
- Add deterministic self-contained fixtures under `tests/fixtures/silver/**`.
- Write tests that load fixture bytes and call only parser/loader functions.
- Assert row/article counts, expected columns, content-vs-description preference, GDELT dropped-row logging, gzip/uncompressed Eurostat parity, KSH long frame shape, and UIC AT/HU rows.
- Run the new test file and confirm RED failures on current RSS/GDELT behavior before production edits.

### Task 2: Robustness Tests For GAP-022/025/026

Files:
- Create `tests/test_parser_robustness.py`
- Modify `src/railway_lakehouse/silver/news/rss.py`
- Modify `src/railway_lakehouse/silver/news/gdelt.py`
- Modify `src/railway_lakehouse/gold/build.py`

Steps:
- Write tests for mixed ISO/GDELT/RFC dates, malformed RSS skipping/logging, malformed GDELT JSON skipping/logging, and dict news rows missing optional fields.
- Run the robustness tests and confirm RED failures.
- Implement RSS `ParseError` handling with module logger.
- Implement GDELT malformed JSON/schema-drop logging.
- Implement explicit Gold date parsing and optional-field defaulting.
- Rerun the focused tests to GREEN.

### Task 3: Field Coverage And Schema Guards

Files:
- Create `tests/test_parser_field_coverage.py`
- Create `tests/test_parser_imports_and_schemas.py`
- Create `docs/PARSER_FIELD_COVERAGE.md`
- Create `docs/PARSER_FIELD_COVERAGE.json`

Steps:
- Encode source-field availability/capture/drop decisions in a single matrix shared by docs and tests.
- Assert parser functions import and return current contracts.
- Assert `ArticleRecord` has 6 dataclass fields and `NewsFeature` has 43 dataclass fields.
- Assert helper behavior for GDELT passthrough, World Bank long schema, KSH year/label detection, and UIC table hints.

### Task 4: Documentation And Dashboard Sync

Files:
- Modify `docs/DATA_CONTRACTS.md`
- Modify `docs/GAP_REGISTER.md`
- Modify `docs/TASKS.md`
- Modify `docs/index.html`
- Modify `README.md`
- Modify `docs/PROGRESS_LOG.md`
- Modify `.planning/COURSEWORK_PROGRESS.md`

Steps:
- Link the parser coverage matrix from contract docs and README.
- Mark GAP-044 closed only after verification passes.
- Update task board and dashboard wave/status text for GAP-044.
- Append progress entries with evidence commands and results.

### Task 5: Verification, Commit, Push, PR

Commands:
- `python -m pytest -q tests/test_silver_parser_golden_fixtures.py tests/test_parser_robustness.py tests/test_parser_field_coverage.py tests/test_parser_imports_and_schemas.py`
- `python -m pytest -q`
- `python -m compileall -q src tests`
- `python -c "import json; m=json.load(open('docs/PARSER_FIELD_COVERAGE.json', encoding='utf-8')); assert len(m['sources']) >= 6; print('Parser coverage matrix OK')"`
- `git diff --check`

Steps:
- Run all verification fresh.
- Commit with an intentional GAP-044 message.
- Push `impl/gap-044` to origin.
- Open a PR against `main`.
- Query PR mergeability and report final schema JSON.

## Self Review

Spec coverage:
- Golden fixtures and tests are covered by Task 1.
- GAP-022/025/026 are covered by Task 2.
- Field matrix and schema guard are covered by Task 3.
- Dashboard/progress/doc sync is covered by Task 4.
- Verification/PR requirement is covered by Task 5.

Refinements approved:
- The stale Pydantic/15-field NewsFeature claim is corrected to dataclass/43 fields.
- Live fixture fetching is removed because tests must be deterministic and current raw evidence bytes are not committed for every source.
- GDELT malformed JSON handling is added because current code does not already guard it.
- Statistik Austria remains matrix-only because GAP-042 owns the parser.

Status: approved for implementation by this agent on 2026-06-25.
