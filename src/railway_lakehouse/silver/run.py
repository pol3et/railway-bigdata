"""
Silver orchestrator.

Modes:
    python -m silver.run stats   # read Bronze stats -> crosswalk -> one merged table
    python -m silver.run news    # read Bronze news  -> per-article features (Ollama)
    python -m silver.run all

The LLM (Ollama) is used ONLY for (a) the cached HU/DE column crosswalk and
(b) RSS/article feature extraction. Numeric merging is deterministic pandas.
This module wires the steps; reading raw bytes from MinIO and writing the Silver
tables back is left as thin I/O you adapt to your s3fs setup (the Bronze
RawLander shows the same pattern).
"""
import sys
import json
import logging

from .ollama_client import health_check
from .stats import merge as stats_merge
from .news import extract as news_extract

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("silver.run")


def run_stats(frames_with_system: list) -> "object":
    """frames_with_system: list of long frames (from stats_merge readers), each
    carrying a `source_system` column. Builds the crosswalk and returns the
    unified StatFact dataframe."""
    import pandas as pd  # local import so the module loads without pandas for --help
    labels, sources = [], {}
    for fr in frames_with_system:
        for lbl in fr["source_column"].astype(str).unique():
            labels.append(lbl)
            sources[lbl] = fr["source_system"].iloc[0] if "source_system" in fr else None
    crosswalk = stats_merge.build_crosswalk(sorted(set(labels)), sources=sources,
                                            use_llm=health_check())
    unified = stats_merge.merge_sources(frames_with_system, crosswalk)
    logger.info("STATS: unified table has %d rows, %d features",
                len(unified), unified["feature"].nunique() if len(unified) else 0)
    return unified


def run_news(articles: list) -> list:
    """articles: list of dicts {article_id, source, url, title, body, published_date}.
    Returns NewsFeature rows. Requires a reachable Ollama for RSS extraction."""
    if not health_check():
        logger.error("Ollama not reachable (%s); cannot extract news features.",
                     "set OLLAMA_HOST / start the server")
        return []
    feats, failures = news_extract.extract_batch(articles)
    if failures:
        logger.warning("NEWS: %d extraction failures", len(failures))
    logger.info("NEWS: produced %d feature rows", len(feats))
    return feats


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode not in ("stats", "news", "all"):
        print(__doc__); sys.exit(1)
    logger.info("Silver run mode=%s; Ollama reachable=%s", mode, health_check())
    logger.info("This entrypoint expects Bronze readers to supply frames/articles; "
                "wire your MinIO reads here.")


if __name__ == "__main__":
    main()
