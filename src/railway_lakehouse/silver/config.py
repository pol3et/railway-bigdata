"""Silver-layer configuration: Ollama, paths, and the canonical rail vocabulary."""
import os

# --- Ollama ---
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
# Single-box default: Qwen3-4B (q4_K_M, ~2.6-3 GB) fits the GTX 1060 6 GB per the
# roadmap/SPEC owner decision (2026-06-25). The 9B-q8 tag (~11 GB) spills to CPU on
# this box and crawls — never use it as the default; override via OLLAMA_MODEL only on
# a larger box.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))
OLLAMA_NUM_RETRIES = int(os.environ.get("OLLAMA_NUM_RETRIES", "3"))
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))
OLLAMA_NUM_PREDICT = int(os.environ.get("OLLAMA_NUM_PREDICT", "1024"))
OLLAMA_THINK = os.environ.get("OLLAMA_THINK", "false").strip().lower() in {"1", "true", "yes", "on"}
# Number of model layers to offload to the GPU. Empty = let Ollama decide (GPU placement — the
# normal case). Set OLLAMA_NUM_GPU=0 only to force CPU as a fallback. NOTE on Pascal (GTX 1060,
# sm_61): the format=json GPU path crashes WITH flash attention but works with it OFF — the fix is
# OLLAMA_FLASH_ATTENTION=0 (server-side), NOT num_gpu=0. See
# .planning/coursework/research/bigdata/gpu-hosting-ollama-pascal-flashattn-2026-06-25.md.
_OLLAMA_NUM_GPU = os.environ.get("OLLAMA_NUM_GPU", "").strip()
OLLAMA_NUM_GPU = int(_OLLAMA_NUM_GPU) if _OLLAMA_NUM_GPU != "" else None

# --- Lakehouse (MinIO), mirrors Bronze ---
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://localhost:9000")
S3_KEY = os.environ.get("S3_KEY", "admin")
S3_SECRET = os.environ.get("S3_SECRET", "password123")
BRONZE_BUCKET = os.environ.get("BRONZE_BUCKET", "bronze")
SILVER_BUCKET = os.environ.get("SILVER_BUCKET", "silver")

# Where the cached column crosswalk lives (review-and-commit artifact).
CROSSWALK_PATH = os.environ.get("CROSSWALK_PATH", "silver/crosswalk_cache.json")

# --- Canonical English feature vocabulary for the merged stats table ---
# Small and bounded on purpose: every source column maps to one of these (or
# stays unmapped). Units are the canonical unit each feature is normalized to in
# Gold; Silver keeps the source unit in a column and records it.
CANONICAL_FEATURES = {
    "rail_freight_tonnes":        "Goods transported by rail (tonnes)",
    "rail_freight_tonne_km":      "Goods transport performance (tonne-kilometres)",
    "rail_passengers":            "Rail passengers carried (count)",
    "rail_passenger_km":          "Passenger transport performance (passenger-kilometres)",
    "rail_network_length_km":     "Length of railway lines in operation (km)",
    "rail_electrified_km":        "Length of electrified railway lines (km)",
    "rail_accidents":             "Number of railway accidents",
    "rail_fatalities":            "Railway accident fatalities (count)",
    "rail_investment":            "Investment in rail infrastructure (monetary)",
    "rail_rolling_stock":         "Rolling stock (locomotives/wagons, count)",
    "rail_employees":             "Persons employed by rail undertakings (count)",
    "rail_track_length_km":        "Length of railway tracks (km)",
    "rail_locomotives":           "Number of locomotives (count)",
    "rail_wagons":                 "Number of goods wagons (count)",
    "rail_train_km":               "Train movements (thousand train-km)",
    "rail_vehicle_km":             "Vehicle movements (thousand vehicle-km)",
    "rail_gross_tonne_km":         "Gross tonne-kilometres hauled (million)",
    "rail_seat_km":                "Seat-kilometres offered (million)",
    # economy
    "gdp_current_meur":            "GDP at current prices (million EUR)",
    "gdp_current_usd":             "GDP at current prices (current USD)",
    "gdp_growth_pct":              "GDP volume growth rate (%)",
    "gdp_per_capita_eur":          "GDP per capita (current EUR)",
    "gdp_pps":                     "GDP in purchasing power standards (million PPS)",
    "gdp_per_capita_pps":          "GDP per capita (PPS)",
    "gdp_per_capita_usd":          "GDP per capita (current USD)",
    "gni_per_capita_usd":          "GNI per capita (current USD)",
    "gva_total_meur":              "Gross value added, total (million EUR)",
    "compensation_employees_meur": "Compensation of employees (million EUR)",
    "gov_debt_pct_gdp":            "General government gross debt (% of GDP)",
    "gov_deficit_pct_gdp":         "Government net lending/borrowing (% of GDP)",
    "gov_revenue_pct_gdp":         "General government total revenue (% of GDP)",
    "gov_expenditure_pct_gdp":     "General government total expenditure (% of GDP)",
    "inflation_pct":               "Inflation, annual average rate of change (%)",
    "unemployment_rate_pct":       "Unemployment rate (% of active population)",
    "net_earnings_eur":            "Annual net earnings, single person no children (EUR)",
    "exports_pct_gdp":             "Exports of goods and services (% of GDP)",
    "imports_pct_gdp":             "Imports of goods and services (% of GDP)",
    "fdi_pct_gdp":                 "Foreign direct investment, net inflows (% of GDP)",
    # population
    "population_total":            "Total population on 1 January (count)",
    "population_density":          "Population density (people per sq km)",
    "urban_population_pct":        "Urban population (% of total population)",
    "pop_growth_rate":             "Population growth rate",
    "birth_rate":                  "Crude birth rate (per 1000)",
    "death_rate":                  "Crude death rate (per 1000)",
    "net_migration_rate":          "Crude rate of net migration (per 1000)",
    "life_expectancy_years":       "Life expectancy at birth (years)",
    "fertility_rate":              "Total fertility rate (births per woman)",
    "infant_mortality_rate":       "Infant mortality rate (per 1000 live births)",
    # quality of life / social
    "life_satisfaction":           "Overall life satisfaction, average rating (0-10)",
    "life_satisfaction_high_pct":  "Share reporting high life satisfaction (%)",
    "gini_coefficient":            "Gini coefficient of equivalised disposable income",
    "poverty_risk_rate_pct":       "At-risk-of-poverty rate (%)",
    "arope_rate_pct":              "At risk of poverty or social exclusion (%)",
    "material_deprivation_pct":    "Severe material deprivation rate (%)",
    "education_spend_pct_gdp":     "Government expenditure on education (% of GDP)",
    "health_spend_pct_gdp":        "Current health expenditure (% of GDP)",
    "electricity_access_pct":      "Access to electricity (% of population)",
    "internet_users_pct":          "Individuals using the internet (% of population)",
    "suicide_rate":                "Suicide mortality rate (per 100k)",
    "homicide_rate":               "Intentional homicides (per 100k)",
    "co2_per_capita":              "CO2 emissions per capita",
    # transport modal split
    "freight_modal_split_rail_pct": "Rail share of inland freight transport (%)",
    "cars_per_1000_inhabitants":   "Passenger cars per 1000 inhabitants",
    "price_level_index":           "Comparative price level index (EU27=100)",
    "ppp_factor":                  "Purchasing power parity conversion factor (GDP)",
    "rail_high_speed_pkm":         "High-speed rail passenger-km (million)",
    "passenger_modal_split_rail_pct": "Rail share of inland passenger transport (%)",
}

# Canonical news event taxonomy (the enum the extractor must choose from).
NEWS_EVENT_TYPES = [
    "investment", "accident", "strike", "service_change", "policy",
    "line_opening", "line_closure", "delay", "financial", "other",
]
KNOWN_OPERATORS = ["MÁV", "GYSEV", "ÖBB", "Westbahn", "RailCargo", "other"]
