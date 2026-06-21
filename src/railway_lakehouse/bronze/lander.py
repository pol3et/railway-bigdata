"""
RawLander: the only component allowed to write to the Bronze bucket.

Contract (this is what "save completely unchanged" means in practice):
  * the source bytes are written verbatim -- no decode, no parse, no cast;
  * a sidecar <name>.meta.json records provenance (where/when/how/checksum);
  * each pull lands under ingest_date=YYYY-MM-DD, so re-pulls ACCUMULATE
    as history instead of overwriting -- this is what makes the yearly
    (stats) and weekly (news) online-update requirements auditable.

Layout:
  bronze/<domain>/<source>/<dataset_id>/ingest_date=YYYY-MM-DD/<file>
  bronze/<domain>/<source>/<dataset_id>/ingest_date=YYYY-MM-DD/<file>.meta.json
"""
import json
import time
import uuid
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

import s3fs

from .config import S3_ENDPOINT, S3_KEY, S3_SECRET, BRONZE_BUCKET

logger = logging.getLogger("bronze.lander")


@dataclass
class RawArtifact:
    """A single thing fetched from a source, ready to be landed verbatim."""
    domain: str            # "stats" | "news"
    source: str            # "eurostat" | "worldbank" | "gdelt" | "rss" ...
    dataset_id: str        # stable id of the item, e.g. "rail_go_total" or "orf"
    filename: str          # original file name incl. extension
    content: bytes         # RAW bytes, exactly as received
    source_url: str
    content_type: str = "application/octet-stream"
    http_status: int = 200
    extra: dict = field(default_factory=dict)   # any source-specific notes


class RawLander:
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.s3 = s3fs.S3FileSystem(
            key=S3_KEY,
            secret=S3_SECRET,
            client_kwargs={"endpoint_url": S3_ENDPOINT},
        )
        if not self.s3.exists(BRONZE_BUCKET):
            logger.info("Bucket '%s' missing -- creating.", BRONZE_BUCKET)
            self.s3.mkdir(BRONZE_BUCKET)

    def _partition_prefix(self, a: RawArtifact, ingest_date: str) -> str:
        return (
            f"{BRONZE_BUCKET}/{a.domain}/{a.source}/{a.dataset_id}/"
            f"ingest_date={ingest_date}"
        )

    def land(self, a: RawArtifact) -> str:
        """Write raw bytes + sidecar metadata. Returns the object path."""
        ingest_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        prefix = self._partition_prefix(a, ingest_date)
        obj_path = f"{prefix}/{a.filename}"
        meta_path = f"{obj_path}.meta.json"

        sha256 = hashlib.sha256(a.content).hexdigest()
        meta = {
            "source_system": a.source,
            "domain": a.domain,
            "dataset_id": a.dataset_id,
            "source_url": a.source_url,
            "original_filename": a.filename,
            "content_type": a.content_type,
            "http_status": a.http_status,
            "byte_size": len(a.content),
            "sha256": sha256,
            "fetch_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "ingest_run_id": self.run_id,
            "extra": a.extra,
        }

        # bytes first, metadata second -- metadata existing implies a complete write
        with self.s3.open(obj_path, "wb") as f:
            f.write(a.content)
        with self.s3.open(meta_path, "w") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        logger.info("Landed %s (%d bytes, sha256=%s...)",
                    obj_path, len(a.content), sha256[:12])
        return obj_path


def build_meta_dict(a: RawArtifact, run_id: str) -> dict:
    """Pure helper exposed for unit testing without touching S3."""
    return {
        "source_system": a.source,
        "dataset_id": a.dataset_id,
        "byte_size": len(a.content),
        "sha256": hashlib.sha256(a.content).hexdigest(),
        "ingest_run_id": run_id,
    }
