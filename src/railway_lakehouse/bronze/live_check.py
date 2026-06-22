"""Bounded local Bronze live checks for parser owners.

This module writes raw artifacts to a local directory using the Bronze layout.
It intentionally avoids the scheduler, MinIO, Spark, Ollama, and historical
backfills.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping

import requests

from .lander import RawArtifact
from .sources import ksh, rss_media

logger = logging.getLogger("bronze.live_check")

DEFAULT_SOURCES = ("rss", "ksh")
DEFAULT_MAX_ARTIFACTS = 2
DEFAULT_TIMEOUT_SECONDS = 45
USER_AGENT = "railway-lakehouse-live-check/1.0"

Clock = Callable[[], datetime]
Collector = Callable[..., "SourceResult"]


@dataclass
class SourceResult:
    source: str
    status: str
    artifact_count: int
    byte_count: int
    http_statuses: list[int] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)


class LocalBronzeLander:
    """Local writer with the same path semantics as the Bronze lander."""

    def __init__(self, root: str | Path, run_id: str, clock: Clock | None = None):
        self.root = Path(root)
        self.run_id = run_id
        self.clock = clock or _utc_now
        self.artifacts: list[dict] = []

    def land(self, artifact: RawArtifact) -> dict:
        now = self.clock()
        ingest_date = now.strftime("%Y-%m-%d")
        obj_path = (
            self.root
            / "bronze"
            / artifact.domain
            / artifact.source
            / artifact.dataset_id
            / f"ingest_date={ingest_date}"
            / artifact.filename
        )
        meta_path = obj_path.with_name(f"{obj_path.name}.meta.json")

        obj_path.parent.mkdir(parents=True, exist_ok=True)
        obj_path.write_bytes(artifact.content)

        sha256 = hashlib.sha256(artifact.content).hexdigest()
        meta = {
            "source_system": artifact.source,
            "domain": artifact.domain,
            "dataset_id": artifact.dataset_id,
            "source_url": artifact.source_url,
            "original_filename": artifact.filename,
            "content_type": artifact.content_type,
            "http_status": artifact.http_status,
            "byte_size": len(artifact.content),
            "sha256": sha256,
            "fetch_timestamp_utc": now.isoformat(),
            "ingest_run_id": self.run_id,
            "extra": artifact.extra,
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        record = {
            "source": artifact.source,
            "domain": artifact.domain,
            "dataset_id": artifact.dataset_id,
            "path": obj_path.as_posix(),
            "meta_path": meta_path.as_posix(),
            "bytes": len(artifact.content),
            "sha256": sha256,
            "http_status": artifact.http_status,
        }
        self.artifacts.append(record)
        return record


def run_live_check(
    *,
    sources: Iterable[str],
    out: str | Path,
    max_artifacts: int = DEFAULT_MAX_ARTIFACTS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    collectors: Mapping[str, Collector] | None = None,
    clock: Clock | None = None,
) -> Path:
    if max_artifacts < 1:
        raise ValueError("--max-artifacts must be at least 1")
    if timeout_seconds < 1:
        raise ValueError("--timeout-seconds must be at least 1")

    now = (clock or _utc_now)()
    run_id = f"live-check-{now.strftime('%Y%m%d-%H%M%S')}"
    collector_map = collectors or _default_collectors()
    selected_sources = _normalize_sources(sources)
    _validate_sources(selected_sources, collector_map)
    run_out = _resolve_run_output_dir(Path(out), run_id)
    lander = LocalBronzeLander(run_out, run_id=run_id, clock=clock)
    source_results: list[SourceResult] = []

    for source in selected_sources:
        collector = collector_map[source]
        try:
            source_results.append(
                collector(
                    lander=lander,
                    max_artifacts=max_artifacts,
                    timeout_seconds=timeout_seconds,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Live check collector failed for %s", source)
            source_results.append(
                SourceResult(
                    source=source,
                    status="failed",
                    artifact_count=0,
                    byte_count=0,
                    failures=[{"error": str(exc)}],
                )
            )

    return write_manifest(
        run_out,
        run_id=run_id,
        run_timestamp=now,
        source_results=source_results,
        artifacts=lander.artifacts,
    )


def write_manifest(
    out: str | Path,
    *,
    run_id: str,
    run_timestamp: datetime,
    source_results: Iterable[SourceResult],
    artifacts: Iterable[dict],
) -> Path:
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    source_dicts = [asdict(result) for result in source_results]
    artifact_dicts = list(artifacts)
    manifest = {
        "run_id": run_id,
        "timestamp_utc": run_timestamp.isoformat(),
        "scope": (
            "bounded local Bronze live check; no scheduler, MinIO, Ollama, Spark, "
            "or long historical GDELT backfill"
        ),
        "sources": source_dicts,
        "artifacts": artifact_dicts,
        "artifact_count": len(artifact_dicts),
        "byte_count": sum(int(artifact.get("bytes", 0)) for artifact in artifact_dicts),
    }
    manifest_path = out_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def collect_rss(
    *,
    lander: LocalBronzeLander,
    max_artifacts: int,
    timeout_seconds: int,
) -> SourceResult:
    session = requests.Session()
    failures: list[dict] = []
    statuses: list[int] = []
    start_count = len(lander.artifacts)

    for outlet_id, url, geo in rss_media._all_feeds()[:max_artifacts]:
        try:
            response = session.get(url, timeout=timeout_seconds, headers={"User-Agent": USER_AGENT})
        except requests.RequestException as exc:
            failures.append({"dataset_id": outlet_id, "url": url, "error": str(exc)})
            continue

        statuses.append(response.status_code)
        if response.status_code != 200 or not response.content:
            failures.append(
                {
                    "dataset_id": outlet_id,
                    "url": url,
                    "http_status": response.status_code,
                    "bytes": len(response.content or b""),
                    "error": "empty or non-200 response",
                }
            )
            continue

        lander.land(
            RawArtifact(
                domain="news",
                source="rss",
                dataset_id=outlet_id,
                filename=f"{outlet_id}.xml",
                content=response.content,
                source_url=url,
                content_type=response.headers.get("Content-Type", "application/rss+xml"),
                http_status=response.status_code,
                extra={"geo": geo},
            )
        )

    return _source_result("rss", lander.artifacts[start_count:], statuses, failures)


def collect_ksh(
    *,
    lander: LocalBronzeLander,
    max_artifacts: int,
    timeout_seconds: int,
) -> SourceResult:
    failures: list[dict] = []
    statuses: list[int] = []
    start_count = len(lander.artifacts)

    for dataset_id, path, expected_content_type, filename in ksh.KSH_RAIL_TABLES[:max_artifacts]:
        url = f"{ksh.KSH_API_BASE}/{path}"
        try:
            response = requests.get(url, timeout=timeout_seconds, headers={"User-Agent": USER_AGENT})
        except requests.RequestException as exc:
            failures.append({"dataset_id": dataset_id, "url": url, "error": str(exc)})
            continue

        statuses.append(response.status_code)
        if response.status_code != 200 or not response.content:
            failures.append(
                {
                    "dataset_id": dataset_id,
                    "url": url,
                    "http_status": response.status_code,
                    "bytes": len(response.content or b""),
                    "error": "empty or non-200 response",
                }
            )
            continue

        lander.land(
            RawArtifact(
                domain="stats",
                source="ksh",
                dataset_id=dataset_id,
                filename=filename,
                content=response.content,
                source_url=url,
                content_type=response.headers.get("Content-Type", expected_content_type),
                http_status=response.status_code,
                extra={
                    "agency": "KSH",
                    "country": "HU",
                    "discovery": "configured_rail_table",
                },
            )
        )

    return _source_result("ksh", lander.artifacts[start_count:], statuses, failures)


def parse_sources(raw_sources: str) -> list[str]:
    return _normalize_sources(raw_sources.split(","))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a bounded local Bronze live check.")
    parser.add_argument("--sources", default=",".join(DEFAULT_SOURCES), help="Comma-separated sources: rss,ksh")
    parser.add_argument("--out", default="output/evidence/live-bronze", help="Local evidence output directory")
    parser.add_argument(
        "--max-artifacts",
        type=int,
        default=DEFAULT_MAX_ARTIFACTS,
        help="Maximum URL attempts/artifacts per selected source",
    )
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)

    manifest_path = run_live_check(
        sources=parse_sources(args.sources),
        out=args.out,
        max_artifacts=args.max_artifacts,
        timeout_seconds=args.timeout_seconds,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failed_sources = [source for source in manifest["sources"] if source["status"] != "passed"]
    print(
        json.dumps(
            {
                "manifest": manifest_path.as_posix(),
                "artifact_count": manifest["artifact_count"],
                "byte_count": manifest["byte_count"],
                "sources": [
                    {
                        "source": source["source"],
                        "status": source["status"],
                        "artifact_count": source["artifact_count"],
                        "failures": len(source["failures"]),
                    }
                    for source in manifest["sources"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if failed_sources else 0


def _source_result(source: str, artifacts: list[dict], http_statuses: list[int], failures: list[dict]) -> SourceResult:
    if artifacts and failures:
        status = "partial"
    elif artifacts:
        status = "passed"
    else:
        status = "failed"
    return SourceResult(
        source=source,
        status=status,
        artifact_count=len(artifacts),
        byte_count=sum(int(artifact["bytes"]) for artifact in artifacts),
        http_statuses=http_statuses,
        failures=failures,
    )


def _normalize_sources(sources: Iterable[str]) -> list[str]:
    normalized = []
    for source in sources:
        name = source.strip().lower()
        if name:
            normalized.append(name)
    if not normalized:
        raise ValueError("at least one source is required")
    return normalized


def _validate_sources(sources: Iterable[str], collector_map: Mapping[str, Collector]) -> None:
    unsupported = [source for source in sources if source not in collector_map]
    if unsupported:
        supported = ", ".join(sorted(collector_map))
        requested = ", ".join(unsupported)
        raise ValueError(f"unsupported source(s): {requested}. Supported sources: {supported}")


def _resolve_run_output_dir(out_path: Path, run_id: str) -> Path:
    if not ((out_path / "manifest.json").exists() or (out_path / "bronze").exists()):
        return out_path

    candidate = out_path / run_id
    suffix = 2
    while candidate.exists():
        candidate = out_path / f"{run_id}-{suffix}"
        suffix += 1
    return candidate


def _default_collectors() -> dict[str, Collector]:
    return {
        "rss": collect_rss,
        "ksh": collect_ksh,
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


if __name__ == "__main__":
    raise SystemExit(main())
