# GAP-041 Research - UIC PDF Widen And Stage

Date: 2026-06-25

Skill/workflow:
- `research-orchestrator` invoked as required by `AGENTS.md`.
- Local files researched first: `src/railway_lakehouse/silver/stats/load.py`, `src/railway_lakehouse/silver/persist.py`, `tests/test_silver_stats_uic_pdf.py`, `docs/DATA_CONTRACTS.md`, `docs/TASKS.md`, `docs/index.html`, `docs/GAP_REGISTER.md`, and `docs/GAP_TASKS.md`.
- External routed providers used: Context7, Ref, Firecrawl, Tavily.

Provider notes:
- Ref was attempted for pycountry and ISO-3166 documentation, but returned "Not enough credits"; Context7 and Firecrawl/Tavily were used as routed fallbacks.

Queries and sources:
- Context7 query: `pdfplumber` / "How to extract page text and tables from PDF bytes: pdfplumber.open, page.extract_text, page.extract_tables return values and examples."
  - Source URL: https://github.com/jsvine/pdfplumber/blob/stable/README.md
  - Finding: `Page.extract_tables()` returns a nested `table -> row -> cell` list; `Page.extract_text()` extracts page text. The current code's `pdfplumber.open(io.BytesIO(raw))`, per-page text extraction, and per-page table extraction match the documented API.
- Context7 query: `pycountry` / "How to iterate pycountry.countries and access ISO 3166 alpha_2 alpha_3 name attributes; lookup usage."
  - Source URL: https://github.com/pycountry/pycountry/blob/main/README.rst
  - Finding: `pycountry.countries` exposes ISO country attributes including `alpha_2`, `alpha_3`, and `name`; `countries.get(alpha_2='DE')` and `countries.lookup('de')` are documented. The local environment does not have `pycountry` installed, and adding a new dependency is not needed for this gap.
- Firecrawl query: "ISO 3166-1 alpha-2 alpha-3 official country codes list ISO Online Browsing Platform"
  - Source URL: https://www.iso.org/iso-3166-country-codes.html
  - Finding: ISO identifies ISO 3166 as the country-code standard and points users to the Online Browsing Platform for codes from ISO 3166 parts 1, 2, and 3.
- Tavily query: "ISO 3166-1 alpha-2 alpha-3 country codes official source"
  - Source URLs surfaced: https://www.iso.org/iso-3166-country-codes.html and https://www.iso.org/obp/ui
  - Finding: The official source is ISO/OBP; non-official mirrors were not used for implementation decisions.

Spec refinements after live-code sanity check:
- `tests/test_silver_stats_uic_pdf.py` currently has 6 UIC tests, not 12. GAP-041 will add 4 tests, so the targeted file should have 10 tests unless other tests land concurrently.
- The current repo already tracks GAP-041 in `docs/GAP_REGISTER.md`, `docs/GAP_TASKS.md`, and the dashboard Wave 6 line. This task still needs the explicit `docs/TASKS.md` row and a dashboard open-gap item/chip so the dashboard-sync rule is satisfied.
- `pycountry` is not installed in the current constrained stack. To avoid dependency churn, implementation will use a local deterministic ISO alpha-2/alpha-3 mapping covering EU countries plus known adjacent/UIC-publication countries named in the spec. The mapping can later be replaced by `pycountry` without changing parser behavior.
- `load_uic_frame()` is a stats-contract reader and should continue returning only golden `StatFact`-shape rows. Staging will be exposed via dedicated UIC staging functions and optional persistence helpers so current Gold/stats paths remain stable.
