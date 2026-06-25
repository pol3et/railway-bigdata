"""Canonical Silver schemas + validators (no heavy deps; pure dataclasses)."""
from dataclasses import MISSING, asdict, dataclass, field
from typing import Optional


# ---------- merged statistics: one unified long-format row ----------
@dataclass
class StatFact:
    geo: str                 # country code (HU, AT, EU27, ...)
    year: Optional[int]      # observation year
    feature: str             # canonical English feature key (config.CANONICAL_FEATURES)
    value: Optional[float]   # numeric value (None if missing/flagged)
    unit: str                # source unit string (normalized later in Gold)
    source_system: str       # eurostat | worldbank | ksh | statistik_austria | uic
    source_dataset: str      # original dataset id
    source_column: str       # original column/dimension label (provenance)

    def to_row(self) -> dict:
        return asdict(self)



@dataclass
class ArticleRecord:
    article_id: str
    source: str
    title: str
    url: str
    published_date: Optional[str]
    body: Optional[str] = None

    def to_row(self) -> dict:
        return asdict(self)



# ---------- per-article news features ----------
@dataclass
class NewsFeature:
    article_id: str
    source: str
    url: str
    published_date: Optional[str]
    language: Optional[str]            # ISO 639-1 guess (hu/de/en/...)
    is_rail_related: bool              # LLM gate: drop false positives in Gold
    country: Optional[str]             # HU | AT | other
    event_type: str                    # one of config.NEWS_EVENT_TYPES
    operators: list = field(default_factory=list)   # subset of KNOWN_OPERATORS
    rail_lines: list = field(default_factory=list)  # free-text line/route mentions
    monetary_amount_eur: Optional[float] = None      # normalized if derivable
    monetary_raw: Optional[str] = None                # original money string
    summary_en: Optional[str] = None                  # 1-2 sentence English summary
    sentiment: Optional[str] = None                   # XLM-R label: negative | neutral | positive
    confidence: Optional[float] = None                # XLM-R max softmax [0,1] for GAP-034 rows
    language_detected_code: Optional[str] = None      # deterministic language-id output
    language_confidence: Optional[float] = None
    sentiment_label: Optional[str] = None             # deterministic sentiment model label
    sentiment_score: Optional[float] = None           # signed XLM-R score in [-1,1]
    sentiment_confidence: Optional[float] = None      # XLM-R max softmax [0,1]
    is_rail_related_confidence: Optional[float] = None
    event_type_confidence: Optional[float] = None
    summary_en_source: Optional[str] = None
    operators_ner_model: Optional[str] = None
    operators_confidence: Optional[float] = None
    rail_lines_ner_model: Optional[str] = None
    rail_lines_confidence: Optional[float] = None
    monetary_raw_parsed_eur: Optional[float] = None
    monetary_confidence: Optional[float] = None
    gkg_themes: Optional[str] = None
    gkg_persons: Optional[str] = None
    gkg_organizations: Optional[str] = None
    gkg_locations: Optional[str] = None
    gkg_tone: Optional[float] = None
    gkg_emotions: Optional[str] = None
    gkg_tone_source: Optional[str] = None
    text_embedding_model: Optional[str] = None
    text_embedding: Optional[list[float]] = None
    cluster_id: Optional[str] = None
    cross_lingual_dedup_id: Optional[str] = None
    extraction_timestamp_utc: Optional[str] = None
    extraction_model_digest: Optional[str] = None
    confidence_schema_version: str = "1.0"
    is_duplicate: Optional[bool] = None

    def to_row(self) -> dict:
        return asdict(self)


@dataclass
class GKGRecord:
    gkg_id: str
    gkg_date: Optional[str] = None
    document_identifier: Optional[str] = None
    source_common_name: Optional[str] = None
    gkg_themes: Optional[str] = None
    gkg_tone: Optional[float] = None
    gkg_persons: Optional[str] = None
    gkg_organizations: Optional[str] = None
    gkg_locations: Optional[str] = None
    gkg_emotions: Optional[str] = None

    def to_row(self) -> dict:
        return asdict(self)


# ---------- validators (coerce + bound LLM output) ----------
ISO_639_1_CODES = {
    "aa", "ab", "ae", "af", "ak", "am", "an", "ar", "as", "av", "ay", "az",
    "ba", "be", "bg", "bh", "bi", "bm", "bn", "bo", "br", "bs",
    "ca", "ce", "ch", "co", "cr", "cs", "cu", "cv", "cy",
    "da", "de", "dv", "dz", "ee", "el", "en", "eo", "es", "et", "eu",
    "fa", "ff", "fi", "fj", "fo", "fr", "fy", "ga", "gd", "gl", "gn",
    "gu", "gv", "ha", "he", "hi", "ho", "hr", "ht", "hu", "hy", "hz",
    "ia", "id", "ie", "ig", "ii", "ik", "io", "is", "it", "iu", "ja",
    "jv", "ka", "kg", "ki", "kj", "kk", "kl", "km", "kn", "ko", "kr",
    "ks", "ku", "kv", "kw", "ky", "la", "lb", "lg", "li", "ln", "lo",
    "lt", "lu", "lv", "mg", "mh", "mi", "mk", "ml", "mn", "mr", "ms",
    "mt", "my", "na", "nb", "nd", "ne", "ng", "nl", "nn", "no", "nr",
    "nv", "ny", "oc", "oj", "om", "or", "os", "pa", "pi", "pl", "ps",
    "pt", "qu", "rm", "rn", "ro", "ru", "rw", "sa", "sc", "sd", "se",
    "sg", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "ss", "st",
    "su", "sv", "sw", "ta", "te", "tg", "th", "ti", "tk", "tl", "tn",
    "to", "tr", "ts", "tt", "tw", "ty", "ug", "uk", "ur", "uz", "ve",
    "vi", "vo", "wa", "wo", "xh", "yi", "yo", "za", "zh", "zu",
}


CONFIDENCE_FIELDS = (
    "confidence",
    "language_confidence",
    "sentiment_confidence",
    "is_rail_related_confidence",
    "event_type_confidence",
    "operators_confidence",
    "rail_lines_confidence",
    "monetary_confidence",
)

GKG_STRING_FIELDS = (
    "gkg_themes",
    "gkg_persons",
    "gkg_organizations",
    "gkg_locations",
    "gkg_emotions",
)


def _str_or_none(x):
    return x if isinstance(x, str) and x.strip() else None


def _float_or_none(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _clamp_float(x, low: float, high: float):
    value = _float_or_none(x)
    if value is None:
        return None
    return max(low, min(high, value))


def _language_code(x):
    text = _str_or_none(x)
    if text is None:
        return None
    text = text.strip().lower()
    return text if text in ISO_639_1_CODES else None


def _sentiment(x):
    return x if x in ("negative", "neutral", "positive") else None


def _string_enum(x, allowed):
    text = _str_or_none(x)
    return text if text in allowed else None


def _float_list(x):
    if x is None:
        return None
    if not isinstance(x, (list, tuple)):
        return None
    out = []
    for item in x:
        value = _float_or_none(item)
        if value is None:
            return None
        out.append(value)
    return out


def _bool_or_none(x):
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        text = x.strip().lower()
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n"}:
            return False
    return None


def news_feature_from_row(row: dict) -> NewsFeature:
    """Build a NewsFeature from a row dict, filling new fields for legacy rows."""
    values = {}
    for name, dataclass_field in NewsFeature.__dataclass_fields__.items():
        if name in row:
            values[name] = row[name]
        elif dataclass_field.default is not MISSING:
            values[name] = dataclass_field.default
        elif dataclass_field.default_factory is not MISSING:  # type: ignore[comparison-overlap]
            values[name] = dataclass_field.default_factory()
        else:
            values[name] = None
    return NewsFeature(**values)


def validate_news_feature(raw: dict, *, article_id: str, source: str, url: str,
                          published_date: Optional[str], language: Optional[str] = None,
                          event_types: list, operators_allowed: list) -> "NewsFeature":
    """Coerce raw semantic extraction into a NewsFeature.

    Language is identified deterministically before validation and takes
    priority over any legacy/raw model field. LLM-owned fields are still
    bounded here: enums and types are enforced, unknown event types collapse
    to 'other', unknown operators collapse to 'other', and
    out-of-range/missing fields become safe defaults. Never raises on bad LLM data.
    """
    detected_language = _language_code(language)
    ev = raw.get("event_type")
    ev = ev if ev in event_types else "other"
    ops_in = raw.get("operators") or []
    if isinstance(ops_in, str): ops_in = [ops_in]
    ops = [o for o in ops_in if o in operators_allowed]
    if ops_in and not ops: ops = ["other"]
    lines = raw.get("rail_lines") or []
    if isinstance(lines, str): lines = [lines]
    sent = _sentiment(raw.get("sentiment"))
    country = raw.get("country")
    country = country if country in ("HU", "AT", "other") else None
    wide = {
        name: raw.get(name)
        for name in NewsFeature.__dataclass_fields__
        if name not in {
            "article_id", "source", "url", "published_date", "language",
            "is_rail_related", "country", "event_type", "operators", "rail_lines",
            "monetary_amount_eur", "monetary_raw", "summary_en", "sentiment",
            "confidence",
        }
    }
    for name in CONFIDENCE_FIELDS:
        if name == "confidence":
            continue
        if name in raw:
            wide[name] = _clamp_float(raw.get(name), 0.0, 1.0)
    for name in GKG_STRING_FIELDS:
        wide[name] = _str_or_none(raw.get(name))
    raw_language = _language_code(raw.get("language"))
    if detected_language:
        wide["language_detected_code"] = detected_language
    elif "language_detected_code" in raw:
        wide["language_detected_code"] = _language_code(raw.get("language_detected_code"))
    else:
        wide["language_detected_code"] = raw_language
    wide["sentiment_label"] = _sentiment(raw.get("sentiment_label"))
    wide["sentiment_score"] = _clamp_float(raw.get("sentiment_score"), -1.0, 1.0)
    wide["summary_en_source"] = _str_or_none(raw.get("summary_en_source"))
    wide["operators_ner_model"] = _str_or_none(raw.get("operators_ner_model"))
    wide["rail_lines_ner_model"] = _str_or_none(raw.get("rail_lines_ner_model"))
    wide["monetary_raw_parsed_eur"] = _float_or_none(raw.get("monetary_raw_parsed_eur"))
    wide["gkg_tone"] = _clamp_float(raw.get("gkg_tone"), -100.0, 100.0)
    wide["gkg_tone_source"] = _string_enum(
        raw.get("gkg_tone_source"), {"gdelt_gkg", "xlm_r_model"}
    )
    wide["text_embedding_model"] = _str_or_none(raw.get("text_embedding_model"))
    wide["text_embedding"] = _float_list(raw.get("text_embedding"))
    wide["cluster_id"] = _str_or_none(raw.get("cluster_id"))
    wide["cross_lingual_dedup_id"] = _str_or_none(raw.get("cross_lingual_dedup_id"))
    wide["extraction_timestamp_utc"] = _str_or_none(raw.get("extraction_timestamp_utc"))
    wide["extraction_model_digest"] = _str_or_none(raw.get("extraction_model_digest"))
    wide["confidence_schema_version"] = (
        _str_or_none(raw.get("confidence_schema_version")) or "1.0"
    )
    wide["is_duplicate"] = _bool_or_none(raw.get("is_duplicate"))
    return NewsFeature(
        article_id=article_id, source=source, url=url, published_date=published_date,
        language=detected_language or raw_language,
        is_rail_related=bool(raw.get("is_rail_related", False)),
        country=country, event_type=ev, operators=ops, rail_lines=[str(x) for x in lines],
        monetary_amount_eur=_float_or_none(raw.get("monetary_amount_eur")),
        monetary_raw=_str_or_none(raw.get("monetary_raw")),
        summary_en=_str_or_none(raw.get("summary_en")), sentiment=sent,
        confidence=_clamp_float(raw.get("confidence"), 0.0, 1.0),
        **wide,
    )
