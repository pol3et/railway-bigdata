"""
End-to-end driver: Bronze -> Silver -> Gold for a bounded demo run
(100 news articles + the Eurostat rail datasets) producing the ML-ready Parquet.

The live mode is intended to land fresh Bronze data through MinIO-compatible
storage, then read it back for Silver/Gold. For deterministic coursework
evidence, pass `--bronze-root` to read an existing local Bronze fixture tree and
skip live Bronze collection.

Run inside your Docker stack (needs network for Eurostat/GDELT and a running
Ollama for news extraction):

    python -m railway_lakehouse.pipeline --news 100 --out gold/railway_ml.parquet
"""
import argparse
import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

# Bronze (your existing package + the new fetchers)
from railway_lakehouse.bronze.config import BRONZE_BUCKET
from railway_lakehouse.bronze.lander import RawLander
from railway_lakehouse.bronze.sources import eurostat
from railway_lakehouse.bronze.sources import past_recordings


# Silver
from railway_lakehouse.silver.stats import load as stats_load
from railway_lakehouse.silver.stats import merge as stats_merge
from railway_lakehouse.silver.news import extract as news_extract
from railway_lakehouse.silver.news.rss import parse_rss_xml
from railway_lakehouse.silver.ollama_client import health_check

# Gold
from railway_lakehouse.gold.run import build_from_silver

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger("pipeline")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--news", type=int, default=100, help="target number of articles")
    ap.add_argument("--out", default="gold/railway_ml.parquet")
    ap.add_argument(
        "--bronze-root",
        default=None,
        help="local Bronze bucket root to read instead of running live Bronze ingestion",
    )
    ap.add_argument(
        "--skip-news-extraction",
        action="store_true",
        help="read Bronze news but skip Ollama-backed Silver news extraction",
    )
    ap.add_argument(
        "--crosswalk-path",
        default=None,
        help="write/read the Silver stats crosswalk cache at this path",
    )
    args = ap.parse_args(argv)

    return run_pipeline(
        news=args.news,
        out=args.out,
        bronze_root=args.bronze_root,
        skip_news_extraction=args.skip_news_extraction,
        crosswalk_path=args.crosswalk_path,
    )


def run_pipeline(
    *,
    news: int = 100,
    out: str = "gold/railway_ml.parquet",
    bronze_root: str | None = None,
    skip_news_extraction: bool = False,
    crosswalk_path: str | None = None,
) -> str:
    ollama_reachable = False if skip_news_extraction else health_check()

    # ---------------- BRONZE ----------------
    if bronze_root:
        log.info("BRONZE: reading existing local Bronze root %s", bronze_root)
        lander = SimpleNamespace(bronze_root=Path(bronze_root))
    else:
        log.info("BRONZE: landing Eurostat rail datasets + %d news articles", news)
        lander = RawLander()
        eurostat.ingest(lander)  # all rail TSVs, raw
        past_recordings.ingest(lander, target_articles=news)  # ~N articles, raw JSON

    # ---------------- SILVER (stats) ----------------
    # Local Bronze mode uses the shared stats loader, so Eurostat and World Bank
    # are both read from the canonical Bronze tree. Live MinIO mode keeps the
    # existing Eurostat-only fallback for now.
    frames = _read_bronze_stats_frames(lander)
    log.info("SILVER stats: %d source frames", len(frames))

    # crosswalk (Eurostat/World Bank maps by rule; LLM only if reachable)
    if crosswalk_path:
        stats_merge.CROSSWALK_PATH = crosswalk_path

    labels = sorted({l for fr in frames for l in fr["source_column"].astype(str)})
    sources = {}
    for fr in frames:
        if fr.empty or "source_system" not in fr:
            continue
        source_system = fr["source_system"].iloc[0]
        for label in fr["source_column"].astype(str).unique():
            sources[label] = source_system

    crosswalk = stats_merge.build_crosswalk(labels, sources=sources, use_llm=ollama_reachable)
    stats_long = stats_merge.merge_sources(frames, crosswalk)

    # ---------------- SILVER (news) ----------------
    # Read the raw article records you landed or supplied as fixtures.
    articles = _read_bronze_news(lander, limit=news)          # -> list[dict]
    if skip_news_extraction:
        log.info("Skipping news extraction by request.")
        news_rows = []
    elif ollama_reachable:
        news_rows = news_extract.extract_batch(articles)      # Ollama -> NewsFeature
    else:
        log.warning("Ollama unreachable; skipping news extraction.")
        news_rows = []

    # ---------------- GOLD ----------------
    out_path = build_from_silver(stats_long, news_rows, out)
    log.info("DONE -> %s", out_path)
    return out_path


def _read_bronze_eurostat(lander) -> dict:
    """Return {dataset_id: raw DataFrame} from Bronze Eurostat TSV artifacts."""
    tables = {}
    for path in _list_bronze_files(
        lander,
        domain="stats",
        source="eurostat",
        include=lambda name: name.endswith((".tsv", ".tsv.gz")),
    ):
        dataset_id = _dataset_id_from_path(path, "eurostat")
        tables[dataset_id] = _read_tsv(lander, path)
    return tables



def _read_bronze_stats_frames(lander) -> list[pd.DataFrame]:
    """Return Silver stats frames from Bronze stats artifacts.

    Local Bronze mode reads all supported stats sources through
    silver.stats.load. At the moment this includes Eurostat and World Bank.
    Live MinIO mode keeps the existing Eurostat-only fallback.
    """
    local_root = getattr(lander, "bronze_root", None)
    if local_root is not None:
        return stats_load.frames_from_bronze(local_root)

    raw_eurostat_tables = _read_bronze_eurostat(lander)
    frames = []
    for dataset_id, df in raw_eurostat_tables.items():
        long = stats_merge.read_eurostat_tsv(df, dataset_id)
        long["source_system"] = "eurostat"
        frames.append(long)
    return frames


def _read_bronze_news(lander, limit: int) -> list:
    """Return normalized article dicts from Bronze JSON and RSS XML artifacts."""
    if limit <= 0:
        return []
    articles = []
    for path in _list_bronze_files(
        lander,
        domain="news",
        source=None,
        include=lambda name: name.endswith((".json", ".xml")),
    ):
        source = _source_from_news_path(path)
        text = _read_text(lander, path)
        if _is_xml_path(path):
            raw_records = _rss_article_records(text, source)
        else:
            raw_records = _article_records(json.loads(text))
        for index, raw in enumerate(raw_records):
            article = _normalize_article(raw, source=source, path=path, index=index)
            if article is None:
                continue
            articles.append(article)
            if len(articles) >= limit:
                return articles
    return articles


def _is_xml_path(path) -> bool:
    return str(path).lower().endswith(".xml")


def _rss_article_records(xml_text: str, source: str) -> list[dict]:
    return [record.to_row() for record in parse_rss_xml(xml_text, source=source)]


def _list_bronze_files(lander, *, domain: str, source: str | None, include) -> list:
    local_root = getattr(lander, "bronze_root", None)
    if local_root is not None:
        root = Path(local_root)
        pattern = f"{domain}/{source or '*'}/*/ingest_date=*/*"
        paths = sorted(p for p in root.glob(pattern) if p.is_file())
        return [p for p in paths if _is_data_file(str(p), include)]

    if not hasattr(lander, "s3"):
        raise ValueError("lander must expose either bronze_root or s3")

    pattern = f"{BRONZE_BUCKET}/{domain}/{source or '*'}/*/ingest_date=*/*"
    paths = sorted(lander.s3.glob(pattern))
    return [p for p in paths if _is_data_file(str(p), include)]


def _is_data_file(path: str, include) -> bool:
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return not name.endswith(".meta.json") and include(name)


def _read_tsv(lander, path) -> pd.DataFrame:
    compression = "gzip" if str(path).endswith(".gz") else None
    if isinstance(path, Path):
        return pd.read_csv(path, sep="\t", compression=compression)
    with lander.s3.open(path, "rb") as f:
        return pd.read_csv(f, sep="\t", compression=compression)


def _read_text(lander, path) -> str:
    if isinstance(path, Path):
        return path.read_text(encoding="utf-8")
    with lander.s3.open(path, "r") as f:
        return f.read()


def _dataset_id_from_path(path, source: str) -> str:
    return _path_part_after(path, source, purpose="stats dataset id")


def _source_from_news_path(path) -> str:
    return _path_part_after(path, "news", purpose="news source")


def _path_part_after(path, token: str, *, purpose: str) -> str:
    parts = _path_parts(path)
    try:
        value = parts[parts.index(token) + 1]
    except (ValueError, IndexError) as exc:
        raise ValueError(
            f"Cannot derive {purpose} from Bronze path {path!r}; "
            f"expected a path segment after {token!r}."
        ) from exc
    if not value:
        raise ValueError(
            f"Cannot derive {purpose} from Bronze path {path!r}; "
            f"path segment after {token!r} is empty."
        )
    return value


def _path_parts(path) -> list[str]:
    return str(path).replace("\\", "/").split("/")


def _article_records(payload) -> list:
    if isinstance(payload, dict) and isinstance(payload.get("articles"), list):
        return payload["articles"]
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    return []


def _normalize_article(raw: dict, *, source: str, path, index: int) -> dict | None:
    if not isinstance(raw, dict):
        return None
    url = str(raw.get("url") or raw.get("URL") or "")
    title = str(raw.get("title") or raw.get("headline") or "")
    body = str(raw.get("body") or raw.get("description") or raw.get("content") or "")
    article_id = str(raw.get("article_id") or url or f"{_stable_path_key(path)}#{index}")
    return {
        "article_id": article_id,
        "source": source,
        "url": url,
        "title": title,
        "body": body,
        "published_date": _normalize_article_date(
            raw.get("published_date") or raw.get("seendate") or raw.get("date")
        ),
    }


def _normalize_article_date(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 14:
        parsed = pd.to_datetime(digits[:14], format="%Y%m%d%H%M%S", errors="coerce")
    elif len(digits) >= 8:
        parsed = pd.to_datetime(digits[:8], format="%Y%m%d", errors="coerce")
    else:
        parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def _stable_path_key(path) -> str:
    return str(path).replace("\\", "/")


if __name__ == "__main__":
    main()
