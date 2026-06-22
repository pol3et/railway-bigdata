"""
Load Bronze stats *bytes* into Silver long frames, then merge to StatFact.

This is the deterministic Bronze->Silver glue for the World Bank + Eurostat
slice (GAP-006). The numeric parsing is PURE pandas — an LLM never touches the
numbers (it is only ever used, elsewhere, for the cached HU/DE column
crosswalk). Each loader returns the long contract expected by
`stats.merge.merge_sources`, plus a `source_system` column:

    geo, year, value, unit, source_dataset, source_column, source_system

Bronze layout consumed (same as the RawLander wrote it):

    <root>/stats/worldbank/<indicator>/ingest_date=YYYY-MM-DD/<indicator>.json
    <root>/stats/eurostat/<dataset_id>/ingest_date=YYYY-MM-DD/<file>.tsv[.gz]
"""
import gzip
import io
import json
import logging
from pathlib import Path

import pandas as pd

from . import merge as stats_merge
from .merge import read_eurostat_tsv, read_worldbank_json

logger = logging.getLogger("silver.stats.load")

_GZIP_MAGIC = b"\x1f\x8b"
_LONG_COLS = ["geo", "year", "value", "unit",
              "source_dataset", "source_column", "source_system"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=_LONG_COLS)


def load_worldbank_frame(raw: bytes, dataset_id: str) -> pd.DataFrame:
    """World Bank Bronze file is JSON ``[meta, records]``. Melt the records to a
    long frame tagged ``source_system='worldbank'``. An error envelope
    (``[{"message": ...}]``) or a no-data body (``[meta, null]``) yields an empty
    frame — never a fabricated row."""
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("worldbank %s: non-JSON payload; skipping", dataset_id)
        return _empty()
    records = payload[1] if isinstance(payload, list) and len(payload) > 1 else None
    if not isinstance(records, list) or not records:
        logger.warning("worldbank %s: no time-series records; skipping", dataset_id)
        return _empty()
    frame = read_worldbank_json(records, dataset_id)
    if frame.empty:
        return _empty()
    frame["source_system"] = "worldbank"
    return frame


def load_eurostat_frame(raw: bytes, dataset_id: str) -> pd.DataFrame:
    """Eurostat Bronze file is a TSV, optionally gzipped (the SDMX API serves
    ``.tsv.gz``). Decompress if needed, melt wide years to long, tag
    ``source_system='eurostat'``."""
    if raw[:2] == _GZIP_MAGIC:
        raw = gzip.decompress(raw)
    df = pd.read_csv(io.BytesIO(raw), sep="\t", dtype=str)
    if df.empty:
        return _empty()
    frame = read_eurostat_tsv(df, dataset_id)
    frame["source_system"] = "eurostat"
    return frame


# source -> (loader, accepted data-file suffixes); "_"-prefixed datasets
# (e.g. _catalogue_*) are skipped.
_SOURCES = {
    "worldbank": (load_worldbank_frame, (".json",)),
    "eurostat": (load_eurostat_frame, (".tsv", ".tsv.gz", ".gz")),
}


def _latest_partition(dataset_dir: Path):
    parts = sorted(p for p in dataset_dir.glob("ingest_date=*") if p.is_dir())
    return parts[-1] if parts else None


def frames_from_bronze(root) -> list:
    """Walk a Bronze tree and return one long frame per (source, dataset),
    reading only the latest ``ingest_date=`` partition of each dataset."""
    root = Path(root)
    frames = []
    for source, (loader, suffixes) in _SOURCES.items():
        base = root / "stats" / source
        if not base.is_dir():
            continue
        for ds_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            if ds_dir.name.startswith("_"):       # skip _catalogue_* etc.
                continue
            latest = _latest_partition(ds_dir)
            if latest is None:
                continue
            for f in sorted(latest.iterdir()):
                if f.name.endswith(".meta.json"):
                    continue
                if not any(f.name.endswith(s) for s in suffixes):
                    continue
                frame = loader(f.read_bytes(), ds_dir.name)
                if not frame.empty:
                    frames.append(frame)
    logger.info("loaded %d non-empty stats frames from %s", len(frames), root)
    return frames


def build_silver_stats(root, *, use_llm: bool = False, out=None) -> pd.DataFrame:
    """End-to-end WB+Eurostat Bronze -> unified StatFact long table.

    Deterministic by default (``use_llm=False``): English Eurostat/WB labels map
    by rule, unmapped labels are recorded in the crosswalk cache and dropped
    (never guessed). If ``out`` is given, the table is persisted to Parquet."""
    frames = frames_from_bronze(root)
    labels, sources = [], {}
    for fr in frames:
        for lbl in fr["source_column"].astype(str).unique():
            labels.append(lbl)
            sources[lbl] = fr["source_system"].iloc[0] if "source_system" in fr else None
    crosswalk = stats_merge.build_crosswalk(sorted(set(labels)), sources=sources,
                                            use_llm=use_llm)
    unified = stats_merge.merge_sources(frames, crosswalk)
    if out is not None:
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        unified.to_parquet(out, index=False)
        logger.info("silver stats persisted: %s (%d rows)", out, len(unified))
    return unified
