# GAP-045 macro indicators research

Date: 2026-06-25

Skill: `research-orchestrator`

Providers and routes:

- Local repository research first: `rg` and file reads of `AGENTS.md`, `docs/GAP_TASKS.md`, `docs/GAP_REGISTER.md`, `src/railway_lakehouse/bronze/sources/worldbank.py`, `src/railway_lakehouse/silver/config.py`, `src/railway_lakehouse/silver/stats/merge.py`, and stats tests.
- Tavily search/extract for World Bank API/DataBank documentation and current indicator pages.
- Ref documentation search was attempted for World Bank Indicators API docs, but returned "Not enough credits"; Tavily + direct World Bank API probes were used instead.
- Direct World Bank API probes through `Invoke-RestMethod` against `api.worldbank.org` for metadata and AT/HU observations.

Queries and URLs:

- Tavily query: `World Bank API IS.VEH.PCAR.P3 passenger cars per 1000 PA.NUS.PPP IS.VEH.NVEH.P3 retired indicator`
  - `https://databank.worldbank.org/metadataglossary/africa-development-indicators/series/IS.VEH.PCAR.P3`
  - `https://databank.worldbank.org/metadataglossary/world-development-indicators/series/IS.VEH.NVEH.P3`
  - `https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation`
- Tavily query: `World Bank API indicator source parameter source=2 series endpoint indicator IS.VEH.PCAR.P3`
  - `https://datahelpdesk.worldbank.org/knowledgebase/articles/898599-indicator-api-queries`
  - `https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures`
  - `https://databank.worldbank.org/metadataglossary/world-development-indicators/series/IS.VEH.PCAR.P3`
- Tavily extract:
  - `https://datahelpdesk.worldbank.org/knowledgebase/articles/898599-indicator-api-queries`
  - `https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures`
  - `https://databank.worldbank.org/metadataglossary/world-development-indicators/series/IS.VEH.PCAR.P3`
  - `https://databank.worldbank.org/metadataglossary/world-development-indicators/series/PA.NUS.PPP`

Direct API probes:

```text
https://api.worldbank.org/v2/indicator/IS.VEH.PCAR.P3?format=json
https://api.worldbank.org/v2/indicator/IS.VEH.PCAR.P3?format=json&source=2
https://api.worldbank.org/v2/country/AUT;HUN/indicator/IS.VEH.PCAR.P3?format=json&per_page=20000
https://api.worldbank.org/v2/country/all/indicator/IS.VEH.PCAR.P3?format=json&per_page=20000

https://api.worldbank.org/v2/indicator/PA.NUS.PPP?format=json
https://api.worldbank.org/v2/country/AUT;HUN/indicator/PA.NUS.PPP?format=json&per_page=20000

https://api.worldbank.org/v2/indicator/IS.VEH.NVEH.P3?format=json
https://api.worldbank.org/v2/indicator/IS.VEH.NVEH.P3?format=json&source=2
https://api.worldbank.org/v2/country/AUT;HUN/indicator/IS.VEH.NVEH.P3?format=json&per_page=20000
```

Findings:

- `PA.NUS.PPP` is active in the World Bank V2 Indicators API as World Development Indicators source id `2`, named `PPP conversion factor, GDP (LCU per international $)`. Direct AT/HU probe returned 72 non-null rows across `AUT,HUN`, years `1990-2025`.
- `IS.VEH.PCAR.P3` has DataBank metadata named `Passenger cars (per 1,000 people)`, but the V2 indicator metadata response currently resolves to source id `11` (`Africa Development Indicators`), last updated `2013-02-22`, not WDI source id `2`. Direct `source=2` metadata returned zero series. Direct AT/HU probe returned `0` non-null rows. Direct all-country probe returned 177 non-null rows, but they are ADI rows with blank `countryiso3code` and no AT/HU coverage.
- DataBank's WDI metadata page for `IS.VEH.PCAR.P3` states a licensing caveat: data have been removed from external publication pending review of the IRF licensing agreement. This explains why the page/metadata exists while the current API path does not provide AT/HU observations.
- `IS.VEH.NVEH.P3` behaves like the retired/unusable vehicle indicator in this repository context: source id `11` only, no `source=2` metadata, and zero AT/HU non-null rows. It must not be added.
- Local code review found `CANONICAL_FEATURES` already contains semantically related Eurostat keys `cars_per_1000_inhabitants` and `ppp_factor`, but not the task's requested World-Bank-specific keys `cars_per_1000` and `ppp_conversion_factor`.

Spec refinement:

- Keep the requested additive implementation: add `IS.VEH.PCAR.P3` and `PA.NUS.PPP` to World Bank collection, add `cars_per_1000` and `ppp_conversion_factor`, and map both deterministically.
- Refine the live-evidence expectation: the bounded live run can prove `PA.NUS.PPP` reaches Gold for AT/HU, and can prove `IS.VEH.PCAR.P3` lands/mapping is wired but has zero AT/HU non-null rows from the current World Bank API. Do not claim AT/HU car-ownership coverage from World Bank until a live API response actually contains it.
