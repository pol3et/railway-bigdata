"""Canonical Silver schemas + validators (no heavy deps; pure dataclasses)."""
from dataclasses import dataclass, field, asdict
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
    sentiment: Optional[str] = None                   # negative | neutral | positive
    confidence: Optional[float] = None                # model self-reported [0,1]

    def to_row(self) -> dict:
        return asdict(self)


# ---------- validators (coerce + bound LLM output) ----------
def validate_news_feature(raw: dict, *, article_id: str, source: str, url: str,
                          published_date: Optional[str],
                          event_types: list, operators_allowed: list) -> "NewsFeature":
    """Coerce a raw LLM dict into a NewsFeature, enforcing enums and types.
    Unknown event types collapse to 'other'; unknown operators collapse to 'other';
    out-of-range/missing fields become safe defaults. Never raises on bad LLM data."""
    def _str(x): return x if isinstance(x, str) and x.strip() else None
    def _float(x):
        try: return float(x)
        except (TypeError, ValueError): return None
    ev = raw.get("event_type")
    ev = ev if ev in event_types else "other"
    ops_in = raw.get("operators") or []
    if isinstance(ops_in, str): ops_in = [ops_in]
    ops = [o for o in ops_in if o in operators_allowed]
    if ops_in and not ops: ops = ["other"]
    lines = raw.get("rail_lines") or []
    if isinstance(lines, str): lines = [lines]
    sent = raw.get("sentiment")
    sent = sent if sent in ("negative", "neutral", "positive") else None
    conf = _float(raw.get("confidence"))
    if conf is not None: conf = max(0.0, min(1.0, conf))
    country = raw.get("country")
    country = country if country in ("HU", "AT", "other") else None
    return NewsFeature(
        article_id=article_id, source=source, url=url, published_date=published_date,
        language=_str(raw.get("language")),
        is_rail_related=bool(raw.get("is_rail_related", False)),
        country=country, event_type=ev, operators=ops, rail_lines=[str(x) for x in lines],
        monetary_amount_eur=_float(raw.get("monetary_amount_eur")),
        monetary_raw=_str(raw.get("monetary_raw")),
        summary_en=_str(raw.get("summary_en")), sentiment=sent, confidence=conf,
    )
