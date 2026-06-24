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
from pathlib import Path
from typing import Optional

import pandas as pd

from railway_lakehouse.silver.config import NEWS_EVENT_TYPES, KNOWN_OPERATORS

logger = logging.getLogger("gold.build")

# When the same (geo, year, feature) appears from multiple sources, keep the
# value from the highest-priority source (most authoritative / rail-specific first).
SOURCE_PRIORITY = ["eurostat", "uic", "ksh", "statistik_austria", "worldbank"]
_SENTIMENT_MAP = {"negative": -1.0, "neutral": 0.0, "positive": 1.0}


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
def _news_to_df(news_rows: list) -> pd.DataFrame:
    if not news_rows:
        return pd.DataFrame()
    rows = [r if isinstance(r, dict) else r.to_row() for r in news_rows]
    df = pd.DataFrame(rows)
    # derive year from published_date (YYYY-...); drop rows with no usable date/country
    df["year"] = pd.to_datetime(df.get("published_date"), errors="coerce").dt.year.astype("Int64")
    return df


def aggregate_news(news_rows: list) -> pd.DataFrame:
    """NewsFeature rows -> per-(country, year) aggregate features.
    Only rail-related rows with a known country (HU/AT) and a year are counted."""
    df = _news_to_df(news_rows)
    if df.empty:
        return pd.DataFrame(columns=["geo", "year"])
    df = df[(df.get("is_rail_related") == True)
            & df["country"].isin(["HU", "AT"])
            & df["year"].notna()].copy()
    if df.empty:
        return pd.DataFrame(columns=["geo", "year"])
    df["sent_score"] = df["sentiment"].map(_SENTIMENT_MAP)

    grp = df.groupby(["country", "year"])
    agg = grp.agg(
        news_article_count=("article_id", "count"),
        news_sentiment_mean=("sent_score", "mean"),
        news_share_negative=("sentiment", lambda s: (s == "negative").mean()),
        news_total_investment_eur=("monetary_amount_eur", "sum"),
    ).reset_index()

    # event-type counts (one column per canonical event type)
    ev = (df.assign(_one=1)
            .pivot_table(index=["country", "year"], columns="event_type",
                         values="_one", aggfunc="sum", fill_value=0)
            .reset_index())
    ev.columns.name = None
    ev = ev.rename(columns={e: f"news_n_{e}" for e in NEWS_EVENT_TYPES})

    # operator mention counts (explode the operators list)
    ops = df[["country", "year", "operators"]].explode("operators")
    ops = ops[ops["operators"].isin(KNOWN_OPERATORS)]
    if not ops.empty:
        opc = (ops.assign(_one=1)
                  .pivot_table(index=["country", "year"], columns="operators",
                               values="_one", aggfunc="sum", fill_value=0)
                  .reset_index())
        opc.columns.name = None
        opc = opc.rename(columns={o: f"news_op_{o}" for o in KNOWN_OPERATORS})
        agg = agg.merge(opc, on=["country", "year"], how="left")

    out = agg.merge(ev, on=["country", "year"], how="left")
    out = out.rename(columns={"country": "geo"})
    return out


# --------------------------------------------------------------------------
# 3) join stats + news -> ML-ready matrix
# --------------------------------------------------------------------------
def _geo_level(geo) -> str:
    """Classify a geo code: country (2-letter), aggregate (EU*/EA* totals),
    or region (NUTS code). Lets the country+region matrix be filtered by level."""
    g = str(geo).strip().upper()
    if g.startswith(("EU", "EA")) and any(c.isdigit() for c in g):
        return "aggregate"
    if len(g) == 2 and g.isalpha():
        return "country"
    return "region"


def build_gold(stats_long: pd.DataFrame, news_rows: list, *,
               year_min: Optional[int] = None,
               year_max: Optional[int] = None) -> pd.DataFrame:
    """Produce the wide ML-ready table at the (geo, year) grain."""
    stats_wide = pivot_stats(stats_long)
    news_agg = aggregate_news(news_rows)

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
        if c not in ("news_sentiment_mean", "news_share_negative"):
            gold[c] = gold[c].fillna(0)

    gold = gold.sort_values(["geo", "year"]).reset_index(drop=True)
    # tag the geo grain so country/region/aggregate rows can be filtered
    if "geo" in gold.columns:
        gold.insert(1, "geo_level", gold["geo"].map(_geo_level))
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
