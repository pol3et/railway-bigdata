# GAP-044 Parser Correctness Audit Research

Date: 2026-06-25

Workflow:
- Used `research-orchestrator`.
- Local files were reviewed first, then routed MCP providers were used for external claims.

Local files reviewed:
- `AGENTS.md`
- `docs/GAP_TASKS.md`
- `docs/GAP_REGISTER.md`
- `docs/DATA_CONTRACTS.md`
- `docs/TASKS.md`
- `docs/index.html`
- `src/railway_lakehouse/silver/news/rss.py`
- `src/railway_lakehouse/silver/news/gdelt.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/schema.py`
- `src/railway_lakehouse/silver/stats/load.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `src/railway_lakehouse/gold/build.py`
- Existing parser tests under `tests/test_silver_news_parsers.py`, `tests/test_silver_stats_ksh.py`, `tests/test_silver_stats_uic_pdf.py`, and `tests/test_eurostat_hardening.py`
- Existing committed fixtures under `tests/fixtures/bronze/**`
- Evidence manifests under `output/evidence/*/manifest.json`

External research:

| Provider | Query | Source URLs / notes |
|---|---|---|
| Context7 | `xml.etree.ElementTree.fromstring raises ParseError on malformed XML; ParseError exception docs` | Python CPython docs: `https://github.com/python/cpython/blob/main/Doc/library/xml.etree.elementtree.rst` |
| Context7 | `email.utils.parsedate_to_datetime parse RFC 2822 RFC 822 Date header returns datetime raises ValueError` | Python CPython docs: `https://github.com/python/cpython/blob/main/Doc/library/email.utils.rst` |
| Context7 | `pandas.to_datetime format='mixed' errors='coerce' parses arrays with mixed date formats` | pandas docs: `https://pandas.pydata.org/docs/reference/api/pandas.to_datetime.html`, `https://pandas.pydata.org/docs/whatsnew/v2.0.0.html` |
| Context7 | `pdfplumber extract_tables extract_text methods return tables list of rows cells` | pdfplumber README: `https://github.com/jsvine/pdfplumber/blob/stable/README.md` |
| Tavily | `RSS content:encoded namespace CDATA RSS 2.0 documentation content module` | RSS Content module: `https://web.resource.org/rss/1.0/modules/content`; RSS Best Practices Profile: `https://www.rssboard.org/rss-profile` |
| Tavily | `RFC 822 date time format day month year time zone specification date-time` | RFC Editor: `https://www.rfc-editor.org/info/rfc822` |
| Tavily | `GDELT DOC 2.0 API Article List fields title url seendate snippet sourcecountry tone themes GKG` | GDELT DOC API client docs: `https://github.com/alex9smith/gdelt-doc-api`; GDELT DOC 2.0 announcement: `https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts` |
| Tavily | `World Bank API indicator response JSON date value country indicator fields format=json documentation` | World Bank Data Help Desk: `https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures`, `https://datahelpdesk.worldbank.org/knowledgebase/articles/1886674-new-features-and-enhancements-in-the-v2-api` |
| Tavily | `Eurostat TSV SDMX TSV flags unit geo TIME_PERIOD documentation tsv.gz values flags` | Eurostat TSV FAQ: `https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-faq/tsv-format`; Eurostat SDMX data query docs: `https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-detailed-guidelines/sdmx3-0/data-query` |

Findings:
- `ET.fromstring()` is the correct low-level parser for a whole XML document, but malformed XML raises `xml.etree.ElementTree.ParseError`. With ElementTree there is no safe partial item recovery after a malformed document-level parse; the parser should log and skip that feed.
- RSS `content:encoded` is a namespaced full-content element and may coexist with `description`; the parser's current preference for `content:encoded` over `description` is correct for article body coverage.
- RSS dates commonly use RFC 822 / RFC 2822 style values. Python `email.utils.parsedate_to_datetime()` is the appropriate standard-library parser for those strings and raises `ValueError` for invalid values.
- pandas 2.x parses arrays with a consistent inferred format by default; mixed formats should either use `format="mixed"` or explicit format routing. GAP-044 should use explicit routing for ISO, GDELT compact, and RFC/RSS dates, and log unparseable-but-present dates.
- GDELT DOC 2.0 `ArtList` returns article-list fields such as `url`, `url_mobile`, `title`, `seendate`, `socialimage`, `domain`, `language`, and `sourcecountry`. It can search on GKG themes/tone, but the ArtList payload is not the GKG record schema with themes/persons/orgs/locations/tone columns. Full GKG passthrough remains a separate GKG source/parser concern.
- Eurostat TSV stores dimensions in the first series-key column and observations in year columns; missing values use `:`, and flags are appended to values separated by spaces. Current numeric parsing strips flags into numeric values but does not preserve the flag as a separate Silver field.
- World Bank indicator JSON responses use a two-element `[metadata, rows]` shape for time series and can return error envelopes with HTTP 200. Current Bronze validates those before landing; Silver still needs malformed JSON tests.
- pdfplumber `Page.extract_tables()` returns nested `table -> row -> cell` lists. The UIC parser's table-shape detection is consistent with that API.

Spec refinements applied before implementation:
- No live fixture fetching: the task text mentions fetching RSS and copying raw bytes from `output/evidence/*/bronze`, but this worktree currently commits only manifests for KSH/UIC evidence, not the raw XLSX/PDF bytes. Tests must remain self-contained. The new fixtures will live under `tests/fixtures/silver/**`; where source bytes are already committed under `tests/fixtures/bronze/**`, they are copied/adapted from there. KSH/UIC golden files are deterministic parser-shape fixtures modeled on the real live table shapes already encoded in existing tests and evidence manifests, not new live downloads.
- `NewsFeature` is now a 43-field dataclass after GAP-039, not a 15-field Pydantic model. Import/schema guard tests must assert dataclass field counts: `ArticleRecord=6`, `NewsFeature=43`.
- `parse_gdelt_artlist_json()` does not currently handle malformed JSON gracefully. The drafted spec said it already did; implementation must add this guard.
- GAP-023 geo filtering is not widened into this change. Eurostat parser tests for this task assert explicit behavior and coverage documentation; they do not silently add a separate geo-filtering policy.
- Statistik Austria remains documented as available raw ODS with no Silver parser; GAP-042 owns implementation. GAP-044 documents it in the matrix but does not add an ODS reader.
