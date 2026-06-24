"""Silver-layer configuration: Ollama, paths, and the canonical rail vocabulary."""
import os

# --- Ollama ---
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:9b-q8_0")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))
OLLAMA_NUM_RETRIES = int(os.environ.get("OLLAMA_NUM_RETRIES", "3"))
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))
OLLAMA_NUM_PREDICT = int(os.environ.get("OLLAMA_NUM_PREDICT", "1024"))
OLLAMA_THINK = os.environ.get("OLLAMA_THINK", "false").strip().lower() in {"1", "true", "yes", "on"}

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
}

# Canonical news event taxonomy (the enum the extractor must choose from).
NEWS_EVENT_TYPES = [
    "investment", "accident", "strike", "service_change", "policy",
    "line_opening", "line_closure", "delay", "financial", "other",
]
KNOWN_OPERATORS = ["MÁV", "GYSEV", "ÖBB", "Westbahn", "RailCargo", "other"]
