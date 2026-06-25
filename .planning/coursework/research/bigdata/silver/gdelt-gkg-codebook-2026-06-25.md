# GAP-031 GDELT GKG Codebook Research

Date: 2026-06-25

Workflow:
- Used `research-orchestrator`; local repo files were inspected before external docs.
- Local files checked: `src/railway_lakehouse/silver/schema.py`, `src/railway_lakehouse/silver/news/extract.py`, `src/railway_lakehouse/silver/news/cache.py`, `src/railway_lakehouse/pipeline.py`, `src/railway_lakehouse/bronze/sources/past_recordings.py`, `docs/DATA_CONTRACTS.md`, `docs/SILVER_DESIGN.md`, `docs/TASKS.md`, and `docs/index.html`.
- External routing used Tavily and Firecrawl MCP against official GDELT documentation and blog pages.

## Local Findings

- The GAP-031 draft is stale after GAP-039/GAP-050:
  - `NewsFeature` already has `gkg_themes`, `gkg_persons`, `gkg_organizations`, `gkg_locations`, `gkg_tone`, `gkg_emotions`, and `gkg_tone_source`.
  - `gdelt_passthrough_cached(gkg: dict, cache=...)` already avoids Ollama for GDELT article dicts carrying `gkg_*` fields.
  - `pipeline._normalize_article()` already preserves GDELT/GKG metadata fields from Bronze JSON into the article dict.
- Missing for GAP-031:
  - No `GKGRecord` transient schema exists.
  - No parser exists for raw `.gkg.csv.zip` Bronze files.
  - `gdelt_passthrough()` does not accept `GKGRecord`.
  - `article_records_to_news_features()` cannot receive an explicit GKG lookup for deterministic passthrough routing.
  - Existing GDELT passthrough does not map themes to event types or organizations to known operators.

## Official GDELT Findings

### GKG 2.1 Format

Source: `http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf`

Firecrawl extracted the V2.1 codebook as a 27-column, tab-delimited record. Relevant columns:

| Index | Name | Use in GAP-031 |
|---:|---|---|
| 0 | `GKGRECORDID` | Stable GKG ID. |
| 1 | `V2.1DATE` | GKG date, `YYYYMMDDHHMMSS`. |
| 3 | `V2SOURCECOMMONNAME` | Optional source host/name. |
| 4 | `V2DOCUMENTIDENTIFIER` | Source document identifier, usually URL for web content. |
| 7 | `V1THEMES` | Semicolon-delimited themes. |
| 8 | `V2ENHANCEDTHEMES` | Semicolon-delimited `theme,offset` entries. |
| 9 | `V1LOCATIONS` | Semicolon-delimited location blocks. |
| 10 | `V2ENHANCEDLOCATIONS` | Location blocks plus offsets. |
| 11 | `V1PERSONS` | Semicolon-delimited persons. |
| 12 | `V2ENHANCEDPERSONS` | `person,offset` entries. |
| 13 | `V1ORGANIZATIONS` | Semicolon-delimited organizations. |
| 14 | `V2ENHANCEDORGANIZATIONS` | `organization,offset` entries. |
| 15 | `V1.5TONE` | Comma-delimited tone/emotion values; first value is average tone. |
| 17 | `V2GCAM` | GCAM metrics; out of scope for GAP-031. |

The codebook says the file uses one record per line and tab-delimited fields despite a `.csv` suffix. It also says V1 fields are preserved for compatibility, and V2.1 enhanced fields append offsets.

Tone: `V1.5TONE`/`V2Tone` is comma-delimited. The first value is average tone, calculated as positive score minus negative score. The codebook describes the scale as `-100` to `+100`, with common values around `-10` to `+10`, and `0` neutral. GAP-031 should keep the current deterministic threshold mapping: `> 1` positive, `< -1` negative, otherwise neutral.

Locations: location fields are semicolon-delimited blocks whose subfields are `#`-delimited. The first subfields include location type, full display name, country code, admin code, latitude, longitude, and feature ID. GDELT country codes are FIPS-style in these fields; Hungary can appear as `HU`, while Austria can appear as a full name or FIPS `AU`, not just ISO `AT`.

### GKG 1.0 Daily Files

Sources:
- `http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook.pdf`
- `https://www.gdeltproject.org/data.html`

The original GKG codebook describes the alpha/1.0 GKG as tab-delimited with grouped daily files. Fields relevant to this parser include:

| Name | Use in GAP-031 |
|---|---|
| `DATE` | GKG date, `YYYYMMDD`. |
| `TONE` | Comma-delimited emotional dimensions; first value is average tone. |
| `THEMES` | Semicolon-delimited themes. |
| `LOCATIONS` | Semicolon-delimited `#`-delimited location blocks. |
| `PERSONS` | Semicolon-delimited person names. |
| `ORGANIZATIONS` | Semicolon-delimited organization names. |
| `SOURCEURLS` | Delimited source article URLs for grouped 1.0 rows. |

GKG 1.0 groups multiple articles with the same extracted metadata into a single nameset row. Therefore a 1.0 row is still useful for tone/theme/entity passthrough, but URL matching can be one-to-many and must remain best-effort.

### Themes

Sources:
- `http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_CategoryList.xlsx`
- `http://data.gdeltproject.org/documentation/GKG-MASTER-THEMELIST.TXT`
- `https://blog.gdeltproject.org/new-november-2021-gkg-2-0-themes-lookup/`

The current theme fields are GKG theme tokens, not CAMEO numeric event codes. The task draft examples like `036`, `180`, and `330` should not be implemented as numeric CAMEO mappings.

Official theme lookup snippets include transport-relevant tokens such as:
- `PUBLIC_TRANSPORT` - public transportation from buses to subways.
- `RAIL_INCIDENT` - train accidents and derailments.
- `TRANSPORT` / transport-related World Bank taxonomy tokens.

Implementation decision for GAP-031:
- Map only explicit, documented or self-evident rail/transport tokens to the existing `NEWS_EVENT_TYPES`.
- Use `RAIL_INCIDENT` -> `accident`, strike/protest tokens -> `strike`, infrastructure/investment tokens -> `investment`, transport/service tokens -> `service_change`; otherwise `other`.
- Do not infer event types from undocumented numeric CAMEO codes.

## Parser Edge Cases

- Decode GKG zip members as UTF-8 with replacement fallback rather than aborting the entire file.
- Skip empty rows.
- Skip rows whose column count does not match a known 1.0 or 2.x shape.
- Missing or malformed tone yields `gkg_tone=None`; do not invent sentiment.
- `V2ENHANCED*` fields include offsets; when normalizing persons/orgs/themes for `NewsFeature`, strip trailing offset components only when the field looks like `value,number`.
- URL matching is future/best-effort. GAP-031 may route explicit `GKGRecord` lookups passed by the caller, but it must not claim fully automated GKG-to-DOC cross-linking.

## Sources

- GDELT GKG 2.1 Codebook: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
- GDELT original GKG Codebook: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook.pdf
- GDELT data/download overview: https://www.gdeltproject.org/data.html
- GDELT GKG Category List: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_CategoryList.xlsx
- GDELT GKG Theme List: http://data.gdeltproject.org/documentation/GKG-MASTER-THEMELIST.TXT
- GDELT blog, GKG 2.0 themes lookup: https://blog.gdeltproject.org/new-november-2021-gkg-2-0-themes-lookup/
