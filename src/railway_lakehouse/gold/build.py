"""
Gold layer — build the ML-ready feature matrix.

Input  (from Silver):
  * stats_long : the unified StatFact long table
        (geo, year, feature, value, unit, source_system, source_dataset, source_column)
  * news_rows  : a list of NewsFeature (or their dicts)

Output:
  * one wide dataframe at the (geo, year) grain — the ML-ready table — written to
    Parquet. Columns = canonical statistical features + news-derived features.

Two deterministic stages, no LLM:
  1. stats: resolve conflicts (same geo-year-feature from multiple sources) by a
     source-priority policy, then PIVOT long -> wide.
  2. news:  AGGREGATE per (country, year) -> event-type counts, sentiment, money,
     operator mentions; then JOIN onto the stats matrix on (geo, year).
"""
import json
import logging
import math
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import re
from typing import Optional

import pandas as pd

from railway_lakehouse.silver.config import NEWS_EVENT_TYPES, KNOWN_OPERATORS
from railway_lakehouse.silver.schema import ISO_639_1_CODES, news_feature_from_row

logger = logging.getLogger("gold.build")

# When the same (geo, year, feature) appears from multiple sources, keep the
# value from the highest-priority source (most authoritative / rail-specific first).
SOURCE_PRIORITY = ["eurostat", "uic", "ksh", "statistik_austria", "worldbank"]
# GAP-034 rows carry a signed XLM-R `sentiment_score`; keep the label map for
# legacy rows and GDELT passthrough rows that only have a sentiment label.
_SENTIMENT_MAP = {"negative": -1.0, "neutral": 0.0, "positive": 1.0}
_NUTS_GEO_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{1,3}$")
CANONICAL_LANGUAGES = ["hu", "de", "en", "fr", "es", "it", "pl", "ro", "sk", "cs"]
_LANGUAGE_ALIASES = {"cz": "cs"}
_CONFIDENCE_BIN_LABELS = ["low", "medium", "high"]
_CONFIDENCE_BIN_COLUMNS = [f"news_confidence_bin_{name}" for name in _CONFIDENCE_BIN_LABELS]
_GKG_TOKEN_FIELDS = ("themes", "persons", "organizations", "locations", "emotions")
_NEWS_INPUT_COLUMNS = [
    "article_id", "country", "published_date", "is_rail_related", "event_type",
    "operators", "rail_lines", "sentiment", "sentiment_score",
    "monetary_amount_eur", "language", "confidence", "gkg_tone", "gkg_themes",
    "gkg_persons", "gkg_organizations", "gkg_locations", "gkg_emotions",
]
_NEWS_OPTIONAL_DEFAULTS = ("monetary_amount_eur", "operators", "confidence")
_NEWS_TEXT_COLUMNS = {
    "news_language_primary",
    "news_rail_lines_list",
    "news_gkg_themes_list",
    "news_gkg_persons_list",
    "news_gkg_organizations_list",
    "news_gkg_locations_list",
    "news_gkg_emotions_list",
}


# --------------------------------------------------------------------------
# 1) statistics: resolve conflicts + pivot to (geo, year) x feature
# --------------------------------------------------------------------------
def resolve_stat_conflicts(stats_long: pd.DataFrame,
                           priority: Optional[list] = None) -> pd.DataFrame:
    """For each (geo, year, feature) keep one value: the one from the highest
    priority source present. Deterministic and explainable (vs averaging)."""
    if stats_long.empty:
        return stats_long
    priority = priority or SOURCE_PRIORITY
    rank = {s: i for i, s in enumerate(priority)}
    df = stats_long.copy()
    df["_rank"] = df["source_system"].map(lambda s: rank.get(s, len(priority)))
    df = (df.sort_values(["geo", "year", "feature", "_rank"])
            .drop_duplicates(["geo", "year", "feature"], keep="first")
            .drop(columns="_rank"))
    return df


def pivot_stats(stats_long: pd.DataFrame) -> pd.DataFrame:
    """Long -> wide. Index (geo, year), one column per canonical feature."""
    if stats_long.empty:
        return pd.DataFrame(columns=["geo", "year"])
    resolved = resolve_stat_conflicts(stats_long)
    wide = (resolved.pivot_table(index=["geo", "year"], columns="feature",
                                 values="value", aggfunc="first")
                    .reset_index())
    wide.columns.name = None
    return wide


# --------------------------------------------------------------------------
# 2) news: aggregate to (country, year) feature block
# --------------------------------------------------------------------------
def _timestamp_from_datetime(value: datetime) -> pd.Timestamp:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return pd.Timestamp(value)


def _parse_news_datetime(value) -> pd.Timestamp:
    if value is None:
        return pd.NaT
    try:
        if pd.isna(value):
            return pd.NaT
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is not None:
            value = value.tz_convert("UTC").tz_localize(None)
        return value
    if isinstance(value, datetime):
        return _timestamp_from_datetime(value)

    text = str(value).strip()
    if not text:
        return pd.NaT

    compact_formats = (
        (r"^\d{8}T\d{6}Z$", "%Y%m%dT%H%M%SZ"),
        (r"^\d{14}$", "%Y%m%d%H%M%S"),
        (r"^\d{8}$", "%Y%m%d"),
    )
    for pattern, fmt in compact_formats:
        if re.fullmatch(pattern, text):
            try:
                return _timestamp_from_datetime(datetime.strptime(text, fmt))
            except ValueError:
                return pd.NaT

    iso_text = text.replace("Z", "+00:00")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}([T ].*)?", text):
        try:
            return _timestamp_from_datetime(datetime.fromisoformat(iso_text))
        except ValueError:
            pass

    try:
        return _timestamp_from_datetime(parsedate_to_datetime(text))
    except (TypeError, ValueError, IndexError, AttributeError):
        return pd.NaT


def _parse_news_datetimes(published_date: pd.Series) -> pd.Series:
    parsed = published_date.map(_parse_news_datetime)
    parsed = pd.to_datetime(parsed, errors="coerce")
    present = published_date.notna() & published_date.astype(str).str.strip().ne("")
    failed = present & parsed.isna()
    if failed.any():
        sample = published_date[failed].astype(str).head(3).tolist()
        logger.warning(
            "failed to parse %d published_date values; sample=%s",
            int(failed.sum()),
            sample,
        )
    return parsed


def _news_to_df(news_rows: list) -> pd.DataFrame:
    if not news_rows:
        return pd.DataFrame()
    missing_counts: Counter[str] = Counter()
    rows = []
    for raw in news_rows:
        row = raw if isinstance(raw, dict) else raw.to_row()
        row = dict(row)
        for field in _NEWS_OPTIONAL_DEFAULTS:
            if field not in row:
                missing_counts[field] += 1
        rows.append(news_feature_from_row(row).to_row())
    if missing_counts:
        details = ", ".join(
            f"{field}={count}" for field, count in sorted(missing_counts.items())
        )
        logger.info("defaulted missing optional news fields: %s", details)
    df = pd.DataFrame(rows).reindex(columns=_NEWS_INPUT_COLUMNS)
    dates = _parse_news_datetimes(df["published_date"])
    df["year"] = dates.dt.year.astype("Int64")
    df["month"] = dates.dt.month.astype("Int64")
    return df


def _sentiment_scores(df: pd.DataFrame) -> pd.Series:
    fallback = (
        df["sentiment"].map(_SENTIMENT_MAP)
        if "sentiment" in df
        else pd.Series([pd.NA] * len(df), index=df.index, dtype="Float64")
    )
    if "sentiment_score" not in df:
        return fallback
    scores = pd.to_numeric(df["sentiment_score"], errors="coerce")
    return scores.where(scores.notna(), fallback)


def _group_keys_for_granularity(granularity: str) -> list[str]:
    if granularity not in {"year", "year-month"}:
        raise ValueError("granularity must be 'year' or 'year-month'")
    return ["country", "year"] + (["month"] if granularity == "year-month" else [])


def _empty_news_frame(granularity: str) -> pd.DataFrame:
    columns = ["geo", "year"] + (["month"] if granularity == "year-month" else [])
    return pd.DataFrame(columns=columns)


def _clean_token(value) -> Optional[str]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or None


def _as_string_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, set):
        raw_items = sorted(value, key=lambda item: str(item))
    elif isinstance(value, (list, tuple)):
        raw_items = value
    elif not isinstance(value, (str, bytes)) and hasattr(value, "__iter__"):
        raw_items = list(value)
    else:
        try:
            if pd.isna(value):
                return []
        except (TypeError, ValueError):
            pass
        raw_items = [value]
    out = []
    for item in raw_items:
        token = _clean_token(item)
        if token is not None:
            out.append(token)
    return out


def _normalize_language(value) -> Optional[str]:
    token = _clean_token(value)
    if token is None:
        return None
    code = _LANGUAGE_ALIASES.get(token.lower(), token.lower())
    return code if code in ISO_639_1_CODES else None


def _canonical_count_pivot(groups: pd.DataFrame, rows: pd.DataFrame, *,
                           group_keys: list[str], value_col: str,
                           categories: list[str], prefix: str) -> pd.DataFrame:
    expected = [f"{prefix}{category}" for category in categories]
    if rows.empty:
        out = groups.copy()
        for column in expected:
            out[column] = 0
        return out

    counts = (rows[rows[value_col].isin(categories)]
              .groupby(group_keys + [value_col])
              .size()
              .reset_index(name="count"))
    if counts.empty:
        out = groups.copy()
        for column in expected:
            out[column] = 0
        return out

    pivot = (counts.pivot_table(index=group_keys, columns=value_col,
                                values="count", aggfunc="sum", fill_value=0)
                   .reindex(columns=categories, fill_value=0)
                   .reset_index())
    pivot.columns.name = None
    pivot = pivot.rename(columns={category: f"{prefix}{category}" for category in categories})
    out = groups.merge(pivot, on=group_keys, how="left")
    for column in expected:
        out[column] = out[column].fillna(0).astype(int)
    return out


def _mode_or_none(values: pd.Series):
    tokens = [_clean_token(value) for value in values.dropna()]
    tokens = [token for token in tokens if token is not None]
    if not tokens:
        return None
    counts = pd.Series(tokens).value_counts()
    winners = sorted(str(value) for value in counts[counts == counts.max()].index)
    return winners[0]


def _entropy(values: pd.Series):
    tokens = [_clean_token(value) for value in values.dropna()]
    tokens = [token for token in tokens if token is not None]
    if not tokens:
        return pd.NA
    counts = pd.Series(tokens).value_counts()
    total = counts.sum()
    return float(-sum((count / total) * math.log(count / total) for count in counts))


def _language_block(df: pd.DataFrame, groups: pd.DataFrame,
                    group_keys: list[str]) -> pd.DataFrame:
    lang_rows = df[group_keys + ["language"]].dropna(subset=["language"])
    out = _canonical_count_pivot(
        groups, lang_rows, group_keys=group_keys, value_col="language",
        categories=CANONICAL_LANGUAGES, prefix="news_language_",
    )
    if lang_rows.empty:
        out["news_language_primary"] = None
        out["news_language_entropy"] = pd.NA
        return out
    primary = (lang_rows.groupby(group_keys)["language"]
               .apply(_mode_or_none)
               .reset_index(name="news_language_primary"))
    entropy = (lang_rows.groupby(group_keys)["language"]
               .apply(_entropy)
               .reset_index(name="news_language_entropy"))
    out = out.merge(primary, on=group_keys, how="left")
    out = out.merge(entropy, on=group_keys, how="left")
    return out


def _confidence_block(df: pd.DataFrame, groups: pd.DataFrame,
                      group_keys: list[str]) -> pd.DataFrame:
    conf = df[group_keys + ["confidence"]].dropna(subset=["confidence"]).copy()
    if conf.empty:
        out = groups.copy()
        for column in (
            "news_confidence_mean", "news_confidence_std",
            "news_confidence_min", "news_confidence_max",
        ):
            out[column] = pd.NA
        for column in _CONFIDENCE_BIN_COLUMNS:
            out[column] = 0
        return out

    stats = (conf.groupby(group_keys)["confidence"]
             .agg(["mean", "std", "min", "max"])
             .reset_index()
             .rename(columns={
                 "mean": "news_confidence_mean",
                 "std": "news_confidence_std",
                 "min": "news_confidence_min",
                 "max": "news_confidence_max",
             }))
    binned = conf.copy()
    binned["_bin"] = pd.cut(
        binned["confidence"],
        bins=[0.0, 0.33, 0.67, 1.0],
        labels=_CONFIDENCE_BIN_LABELS,
        include_lowest=True,
    )
    bin_counts = (binned.dropna(subset=["_bin"])
                  .groupby(group_keys + ["_bin"], observed=False)
                  .size()
                  .reset_index(name="count"))
    bin_pivot = (bin_counts.pivot_table(index=group_keys, columns="_bin",
                                        values="count", aggfunc="sum", fill_value=0)
                          .reindex(columns=_CONFIDENCE_BIN_LABELS, fill_value=0)
                          .reset_index())
    bin_pivot.columns.name = None
    bin_pivot = bin_pivot.rename(
        columns={label: f"news_confidence_bin_{label}" for label in _CONFIDENCE_BIN_LABELS}
    )
    out = groups.merge(stats, on=group_keys, how="left").merge(
        bin_pivot, on=group_keys, how="left")
    for column in _CONFIDENCE_BIN_COLUMNS:
        out[column] = out[column].fillna(0).astype(int)
    return out


def _unique_token_rollup(groups: pd.DataFrame, token_rows: pd.DataFrame, *,
                         group_keys: list[str], token_col: str,
                         count_col: str, list_col: str) -> pd.DataFrame:
    if token_rows.empty:
        out = groups.copy()
        out[count_col] = 0
        out[list_col] = ""
        return out

    tokens = (token_rows.groupby(group_keys)[token_col]
              .apply(lambda s: sorted({str(value) for value in s if _clean_token(value)}))
              .reset_index(name="_tokens"))
    tokens[count_col] = tokens["_tokens"].map(len)
    tokens[list_col] = tokens["_tokens"].map(lambda values: ",".join(values))
    out = groups.merge(tokens[group_keys + [count_col, list_col]], on=group_keys, how="left")
    out[count_col] = out[count_col].fillna(0).astype(int)
    out[list_col] = out[list_col].fillna("")
    return out


def _rail_lines_block(df: pd.DataFrame, groups: pd.DataFrame,
                      group_keys: list[str]) -> pd.DataFrame:
    rail = df[group_keys + ["rail_lines"]].explode("rail_lines")
    rail["rail_lines"] = rail["rail_lines"].map(_clean_token)
    rail = rail.dropna(subset=["rail_lines"])
    return _unique_token_rollup(
        groups, rail, group_keys=group_keys, token_col="rail_lines",
        count_col="news_n_rail_lines_unique", list_col="news_rail_lines_list",
    )


def _split_semicolon_tokens(value) -> list[str]:
    if isinstance(value, (list, tuple, set)) or (
        not isinstance(value, (str, bytes)) and hasattr(value, "__iter__")
    ):
        raw_parts = []
        for item in value:
            raw_parts.extend(_split_semicolon_tokens(item))
        return raw_parts
    token = _clean_token(value)
    if token is None:
        return []
    return [part.strip() for part in str(token).split(";") if part.strip()]


def _gkg_token_block(df: pd.DataFrame, groups: pd.DataFrame,
                     group_keys: list[str]) -> pd.DataFrame:
    out = groups.copy()
    for field in _GKG_TOKEN_FIELDS:
        source_col = f"gkg_{field}"
        rows = []
        for _, row in df[group_keys + [source_col]].iterrows():
            for token in _split_semicolon_tokens(row[source_col]):
                rows.append({**{key: row[key] for key in group_keys}, "_token": token})
        token_rows = pd.DataFrame(rows, columns=group_keys + ["_token"])
        block = _unique_token_rollup(
            groups, token_rows, group_keys=group_keys, token_col="_token",
            count_col=f"news_n_gkg_{field}_unique",
            list_col=f"news_gkg_{field}_list",
        )
        out = out.merge(block, on=group_keys, how="left")
    return out


def _gkg_tone_block(df: pd.DataFrame, groups: pd.DataFrame,
                    group_keys: list[str]) -> pd.DataFrame:
    tone = df[group_keys + ["gkg_tone"]].dropna(subset=["gkg_tone"]).copy()
    if tone.empty:
        out = groups.copy()
        for column in (
            "news_gkg_tone_mean", "news_gkg_tone_std",
            "news_gkg_tone_min", "news_gkg_tone_max",
        ):
            out[column] = pd.NA
        return out
    stats = (tone.groupby(group_keys)["gkg_tone"]
             .agg(["mean", "std", "min", "max"])
             .reset_index()
             .rename(columns={
                 "mean": "news_gkg_tone_mean",
                 "std": "news_gkg_tone_std",
                 "min": "news_gkg_tone_min",
                 "max": "news_gkg_tone_max",
             }))
    return groups.merge(stats, on=group_keys, how="left")


def aggregate_news(news_rows: list, *, granularity: str = "year") -> pd.DataFrame:
    """NewsFeature rows -> deterministic per-geo news aggregate features.

    Default output grain is `(geo, year)`. With `granularity="year-month"`,
    output grain is `(geo, year, month)`. Only rail-related HU/AT rows with a
    usable date are counted.

    Output includes article counts, sentiment/money summaries, canonical
    event/operator count columns, canonical ISO 639-1 language counts and modal
    language, confidence stats and bins, deterministic free-text rail-line
    unique-count/list columns, and bounded `gkg_*` rollups from already-persisted
    Silver fields. Full GKG theme pivots are deferred until a Gold-owned
    canonical GKG/CAMEO vocabulary exists.
    """
    group_keys = _group_keys_for_granularity(granularity)
    df = _news_to_df(news_rows)
    if df.empty:
        return _empty_news_frame(granularity)

    df["operators"] = df["operators"].map(_as_string_list)
    df["rail_lines"] = df["rail_lines"].map(_as_string_list)
    df["language"] = df["language"].map(_normalize_language)
    df["event_type"] = df["event_type"].map(_clean_token).fillna("other")
    df.loc[~df["event_type"].isin(NEWS_EVENT_TYPES), "event_type"] = "other"
    df["sentiment"] = df["sentiment"].map(_clean_token)
    df["monetary_amount_eur"] = pd.to_numeric(df["monetary_amount_eur"], errors="coerce")
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
    df.loc[~df["confidence"].between(0.0, 1.0), "confidence"] = pd.NA
    df["gkg_tone"] = pd.to_numeric(df["gkg_tone"], errors="coerce")

    df = df[(df.get("is_rail_related") == True)
            & df["country"].isin(["HU", "AT"])
            & df["year"].notna()].copy()
    if granularity == "year-month":
        df = df[df["month"].notna()].copy()
    if df.empty:
        return _empty_news_frame(granularity)
    df["sent_score"] = _sentiment_scores(df)

    groups = df[group_keys].drop_duplicates().sort_values(group_keys).reset_index(drop=True)
    grp = df.groupby(group_keys)
    agg = grp.agg(
        news_article_count=("article_id", "count"),
        news_sentiment_mean=("sent_score", "mean"),
        news_share_negative=("sentiment", lambda s: (s == "negative").mean()),
        news_total_investment_eur=("monetary_amount_eur", "sum"),
    ).reset_index()

    # GKG aggregation is limited to fields already persisted in Silver. Parsing
    # raw GKG csv.zip files and pivoting hundreds of themes belongs to GAP-031.
    blocks = [
        _language_block(df, groups, group_keys),
        _confidence_block(df, groups, group_keys),
        _rail_lines_block(df, groups, group_keys),
        _gkg_tone_block(df, groups, group_keys),
        _gkg_token_block(df, groups, group_keys),
        _canonical_count_pivot(
            groups, df[group_keys + ["event_type"]], group_keys=group_keys,
            value_col="event_type", categories=NEWS_EVENT_TYPES, prefix="news_n_",
        ),
        _canonical_count_pivot(
            groups, df[group_keys + ["operators"]].explode("operators"),
            group_keys=group_keys, value_col="operators",
            categories=KNOWN_OPERATORS, prefix="news_op_",
        ),
    ]
    out = agg
    for block in blocks:
        out = out.merge(block, on=group_keys, how="left")

    ordered = (
        group_keys
        + [
            "news_article_count", "news_sentiment_mean", "news_share_negative",
            "news_total_investment_eur",
        ]
        + [f"news_language_{code}" for code in CANONICAL_LANGUAGES]
        + ["news_language_primary", "news_language_entropy"]
        + [
            "news_confidence_mean", "news_confidence_std",
            "news_confidence_min", "news_confidence_max",
        ]
        + _CONFIDENCE_BIN_COLUMNS
        + ["news_n_rail_lines_unique", "news_rail_lines_list"]
        + [
            "news_gkg_tone_mean", "news_gkg_tone_std",
            "news_gkg_tone_min", "news_gkg_tone_max",
        ]
        + [
            column
            for field in _GKG_TOKEN_FIELDS
            for column in (f"news_n_gkg_{field}_unique", f"news_gkg_{field}_list")
        ]
        + [f"news_n_{event_type}" for event_type in NEWS_EVENT_TYPES]
        + [f"news_op_{operator}" for operator in KNOWN_OPERATORS]
    )
    out = out[[column for column in ordered if column in out.columns]]
    out = out.rename(columns={"country": "geo"})
    return out


def _geo_level(geo) -> str:
    """Classify a geo code: country (2-letter), aggregate (EU*/EA* totals),
    or region (NUTS code). Lets the country+region matrix be filtered by level."""
    g = str(geo).strip().upper()
    if g.startswith(("EU", "EA")):
        return "aggregate"
    if len(g) == 2 and g.isalpha():
        return "country"
    if _NUTS_GEO_RE.fullmatch(g):
        return "region"
    return "aggregate"


def _is_news_count_column(column: str) -> bool:
    return (
        column == "news_article_count"
        or column == "news_total_investment_eur"
        or column.startswith("news_n_")
        or column.startswith("news_op_")
        or column.startswith("news_confidence_bin_")
        or (column.startswith("news_language_")
            and column not in {"news_language_primary", "news_language_entropy"})
    )


def build_gold(stats_long: pd.DataFrame, news_rows: list, *,
               year_min: Optional[int] = None,
               year_max: Optional[int] = None,
               granularity: str = "year") -> pd.DataFrame:
    """Produce the wide ML-ready table.

    Default grain is `(geo, year)`. With `granularity="year-month"`, the news
    block is aggregated to `(geo, year, month)`; yearly stats are merged on
    `(geo, year)` and therefore repeat across months that have news.
    """
    stats_wide = pivot_stats(stats_long)
    news_agg = aggregate_news(news_rows, granularity=granularity)

    if stats_wide.empty and news_agg.empty:
        return pd.DataFrame()
    if stats_wide.empty:
        gold = news_agg
    elif news_agg.empty:
        gold = stats_wide
    else:
        gold = stats_wide.merge(news_agg, on=["geo", "year"], how="outer")

    # fill news count/event columns with 0 (absence of news == 0 articles, not NaN);
    # leave statistical features as NaN (missing measurement != 0).
    news_cols = [c for c in gold.columns if c.startswith("news_")]
    for c in news_cols:
        if _is_news_count_column(c):
            gold[c] = gold[c].fillna(0)
        elif c in _NEWS_TEXT_COLUMNS:
            gold[c] = gold[c].fillna("")

    sort_cols = ["geo", "year"] + (["month"] if "month" in gold.columns else [])
    gold = gold.sort_values(sort_cols).reset_index(drop=True)
    # tag the geo grain so country/region/aggregate rows can be filtered
    if "geo" in gold.columns:
        gold.insert(1, "geo_level", gold["geo"].map(_geo_level))
    # convert rail investment (EUR) to PPS using the comparative price level
    # (PLI, EU27=100):  value_PPS = value_EUR * 100 / PLI
    if "rail_investment" in gold.columns and "price_level_index" in gold.columns:
        gold["rail_investment_pps"] = (
            gold["rail_investment"] * 100.0 / gold["price_level_index"])
    if year_min is not None:
        gold = gold[gold["year"] >= year_min]
    if year_max is not None:
        gold = gold[gold["year"] <= year_max]
    return gold.reset_index(drop=True)


def write_parquet(df: pd.DataFrame, path: str) -> str:
    """Write the Gold table to Parquet (pyarrow). Returns the path."""
    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_parquet(path, engine="pyarrow", index=False)
    logger.info("Gold written: %s (%d rows, %d cols)", path, len(df), df.shape[1])
    return path


def write_gold_counts(parquet_path: str, counts_out: str) -> str:
    """Write a small reproducibility summary for a generated Gold Parquet file."""
    path = Path(parquet_path)
    df = pd.read_parquet(path)
    counts: dict[str, object] = {
        "path": path.as_posix(),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": [str(column) for column in df.columns],
    }

    if "geo" in df.columns:
        geos = df["geo"].dropna().astype(str)
        counts["geos_count"] = int(geos.nunique())
        counts["contains_AT"] = bool((geos == "AT").any())
        counts["contains_HU"] = bool((geos == "HU").any())

    if "geo_level" in df.columns:
        counts["geo_level_counts"] = {
            str(level): int(count)
            for level, count in df["geo_level"].value_counts(dropna=False).sort_index().items()
        }

    if "year" in df.columns:
        years = pd.to_numeric(df["year"], errors="coerce").dropna()
        counts["year_min"] = int(years.min()) if not years.empty else None
        counts["year_max"] = int(years.max()) if not years.empty else None

    if {"geo", "year"}.issubset(df.columns):
        counts["at_rows"] = int((df["geo"].astype(str) == "AT").sum())
        counts["hu_rows"] = int((df["geo"].astype(str) == "HU").sum())

    counts_path = Path(counts_out)
    counts_path.parent.mkdir(parents=True, exist_ok=True)
    counts_path.write_text(
        json.dumps(counts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return counts_path.as_posix()
