"""
Central configuration for the Bronze ingestion layer.

Nothing here transforms data. These are *collection boundaries* only:
which geographies we care about, which terms count as "rail" across the
languages of our sources, and which outlets we poll. All filtering that
actually touches values happens later, in Silver.
"""
import os

# --- Lakehouse (MinIO) ------------------------------------------------------
# Defaults match the project .env so this runs unchanged inside the Docker stack.
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://localhost:9000")
S3_KEY = os.environ.get("S3_KEY", "admin")
S3_SECRET = os.environ.get("S3_SECRET", "password123")
BRONZE_BUCKET = os.environ.get("BRONZE_BUCKET", "bronze")

# --- Scope ------------------------------------------------------------------
# Phase 1 focuses on Hungary + Austria. Czechia is added later by extrapolation.
# NOTE: this scope governs which *national* agencies we touch and which news
# source-countries we query. It is NOT used to drop rows from pan-EU/global
# datasets (Eurostat, World Bank) -- those are landed whole and unchanged.
NATIONAL_SCOPE = ["HU", "AT"]

# ISO-3 variants needed by some APIs (e.g. World Bank uses HUN/AUT).
ISO3 = {"HU": "HUN", "AT": "AUT", "CZ": "CZE"}

# --- "Rail" semantics, multilingual ----------------------------------------
# Used to maximise recall when querying news. Sparse topic => cast wide.
RAIL_TERMS = {
    "en": ["railway", "railroad", "rail", "train", "locomotive"],
    "hu": ["vasút", "vasut", "vonat", "mozdony", "MÁV", "MAV", "GYSEV"],
    "de": ["Bahn", "Eisenbahn", "Zug", "Schiene", "ÖBB", "OEBB", "Lokomotive"],
}

# --- Popular HU / AT media outlets (RSS) ------------------------------------
# Broad coverage on purpose: state + commercial + business + regional.
# Feed URLs drift over time -- verify and extend these at deploy time.
MEDIA_FEEDS = {
    "HU": {
        "telex": "https://telex.hu/rss",
        "index": "https://index.hu/24ora/rss/",
        "hvg": "https://hvg.hu/rss",
        "24hu": "https://24.hu/feed/",
        "portfolio": "https://www.portfolio.hu/rss/all.xml",   # business; strong on MÁV/infra
        "origo": "https://www.origo.hu/contentpartner/rss/hircentrum/origo.xml",
        "magyarnemzet": "https://magyarnemzet.hu/feed",
        "nepszava": "https://nepszava.hu/feed",
    },
    "AT": {
        "orf": "https://rss.orf.at/news.xml",                  # public broadcaster
        "derstandard": "https://www.derstandard.at/rss",
        "diepresse": "https://www.diepresse.com/rss/home",
        "kurier": "https://kurier.at/xml/rss",
        "kleinezeitung": "https://www.kleinezeitung.at/rss",
        "salzburg": "https://www.sn.at/rss",
        "wienerzeitung": "https://www.wienerzeitung.at/feeds/wz.xml",
    },
}

# Operator / ministry newsrooms worth polling directly (official press).
OFFICIAL_FEEDS = {
    "HU": {
        "mav_press": "https://www.mavcsoport.hu/mav/sajtoszoba/rss",
    },
    "AT": {
        "oebb_press": "https://presse.oebb.at/de/rss",
    },
}
