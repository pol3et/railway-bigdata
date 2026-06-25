# Analysis artifacts — rail investment correlation study

Committed CSV and JSON copies from a Spark analysis run over a wider Gold feature
matrix. This folder holds the result tables and manifest snapshots used by the
summary below. The source Gold Parquet for this snapshot was not committed in
this PR, so reruns must pass `--input` to an existing Gold file with rail
investment and regional columns.

## What was analysed

**Question.** How does investment in rail infrastructure relate to railway,
economic, demographic and quality-of-life indicators — and to their year-over-year
changes — across European countries and regions?

**Data.** Snapshot Gold feature matrix built by the Bronze→Silver→Gold pipeline
from two open sources, **Eurostat** and **World Bank**:
- Bronze net: ~285 datasets, ~16 million observations.
- Gold matrix: ~28,000 rows × 71 columns (~64 features), grain `(geo, year)` with
  a `geo_level` of country / region / aggregate.

**Target variable.** Rail infrastructure investment, in four forms (all monetary
values handled in EUR and **PPS**, purchasing-power-adjusted):
`rail_investment_pps`, `rail_investment_per_capita`, `rail_investment_pct_gdp`,
`rail_investment_per_network_km`.

**Method.** For each target we computed correlations against every other feature
as **levels** and as **year-over-year deltas**: Pearson r, Spearman ρ (rank-based,
robust to outliers) and a two-sided p-value (Fisher z). Three designs:
1. **Pooled** — all country-years together (cross-sectional).
2. **Per-country** — within each country over time (levels and panel).
3. **Panel** — Δtarget vs Δfeature, which removes constant cross-country
   differences (closest to a within-country / causal reading).

A separate **regional** job analysed NUTS2 regions.

## Main results

### 1. Cross-country (pooled)
- **Rail investment per capita ↔ life satisfaction**: Pearson **+0.47**, Spearman
  **+0.43** — the single robust relationship. Countries that invest more per
  capita in rail report higher life satisfaction (reflects development level).
- Absolute investment tracks rail **scale** (wagons, locomotives, employees) — a
  size effect.
- Apparent links to `infant_mortality` / `inflation` are **outlier artifacts**:
  Pearson positive but Spearman ≈ 0.

### 2. Within-country over time (panel, Δ vs Δ)
- The only consistent, sensible signal: **investment → physical infrastructure** —
  e.g. **Portugal** Δinvestment ↔ Δtrack length **+0.90**, **Slovakia** ↔
  Δelectrification **+0.83**, **Sweden** ↔ Δhigh-speed pkm **+0.76**.
- The large pooled Δinvestment ↔ Δinflation correlation (+0.49…+0.65) is a
  **nominal / outlier artifact** (Spearman ≈ 0) — not a real relationship.
- Otherwise year-to-year investment changes are largely idiosyncratic.
- Caveats: small per-country samples (n≈9–24) and many tested pairs ⇒ multiple
  comparisons; discount pairs where Pearson ≫ Spearman.

### 3. Regional (NUTS2)
- 276 NUTS2 regions, 9,667 region-years.
- **Most uneven within-country rail distribution** (CV of network across regions):
  **Spain (1.02), Greece (1.01), Austria (1.01)**, then Germany, Finland.
- **National investment vs regional disparity**: r = **−0.09**, p = 0.10 (n=329) —
  **not significant**. Rail investment does not measurably even out regional gaps.

## Overall reading
Rail investment turns into infrastructure (within-country), is associated with a
country's development / life satisfaction (cross-country), but is **not**
redistributed toward lagging regions, and shows **no robust short-run driver**
among the measured indicators. Spearman + the panel design were essential to
separate genuine signal from trend- and outlier-driven artifacts.

## Files
| File | Analysis |
|------|----------|
| `correlations_pooled_levels.csv` | Pooled, levels + deltas |
| `correlations_pooled_panel.csv` | Pooled, Δ vs Δ |
| `correlations_by_country_levels.csv` | Per-country, levels + deltas |
| `correlations_by_country_panel.csv` | Per-country, Δ vs Δ |
| `regional_descriptives.csv` | Per region-year: network, electrification share, NUTS level |
| `regional_inequality.csv` | Per country-year: CV of network/electrification across NUTS2 |
| `manifest_*.json` | Run metadata snapshots (Spark version, targets, mode, top results) |

Notes: correlation tables carry `pearson_r`, `p_pearson`, `spearman_r`,
`p_spearman`, `n` (and `geo` for per-country, `target` for the intensity variant).
All monetary comparisons use PPS. No terrain-complexity feature is included in
Gold unless a future source lands a real measured value.
