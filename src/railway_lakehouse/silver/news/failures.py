"""Typed failure accounting for Silver news extraction."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class ExtractionFailure:
    article_id: str
    source: str
    url: str
    title: str
    published_date: Optional[str]
    reason: str
    timestamp_utc: str
    model_digest: str
    raw: Optional[str] = None

    def to_row(self) -> dict:
        return asdict(self)


def persist_news_failures(failures: list, root, ingest_date: str):
    """Write extraction failures as a JSON sidecar manifest.

    GAP-039 deliberately does not create a Parquet failure table; GAP-006/GAP-050
    can promote this sidecar to a table once the persisted schema is approved.
    """
    path = (
        Path(root)
        / "news"
        / "news_extraction_failures"
        / f"ingest_date={ingest_date}"
        / "failures.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [f.to_row() if hasattr(f, "to_row") else dict(f) for f in failures or []]
    path.write_text(
        json.dumps(
            {
                "ingest_date": ingest_date,
                "failure_count": len(rows),
                "failures": rows,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def persist_extraction_run_manifest(manifest: dict, root, ingest_date: str):
    """Write per-run extraction metrics alongside Silver news outputs."""
    path = (
        Path(root)
        / "news"
        / "news_extraction_runs"
        / f"ingest_date={ingest_date}"
        / "manifest.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
