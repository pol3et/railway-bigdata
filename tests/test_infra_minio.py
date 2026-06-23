"""
Deterministic guard for the MinIO lakehouse infra (GAP-010).

These tests do not require Docker or network. They only verify that committed
MinIO infra files stay aligned with the S3 config defaults used by the code.
"""

from pathlib import Path
from runpy import run_path
import sys

import pytest

from railway_lakehouse.bronze import config as bronze_config
from railway_lakehouse.silver import config as silver_config

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]


def _parse_env(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
    return out


def test_env_example_matches_code_config_defaults():
    env = _parse_env((ROOT / ".env.example").read_text(encoding="utf-8"))

    assert env["S3_ENDPOINT"] == bronze_config.S3_ENDPOINT
    assert env["S3_KEY"] == bronze_config.S3_KEY
    assert env["S3_SECRET"] == bronze_config.S3_SECRET
    assert env["BRONZE_BUCKET"] == bronze_config.BRONZE_BUCKET
    assert env["SILVER_BUCKET"] == silver_config.SILVER_BUCKET
    assert env["GOLD_BUCKET"] == "gold"

    assert bronze_config.S3_ENDPOINT == silver_config.S3_ENDPOINT
    assert bronze_config.S3_KEY == silver_config.S3_KEY
    assert bronze_config.S3_SECRET == silver_config.S3_SECRET
    assert bronze_config.BRONZE_BUCKET == silver_config.BRONZE_BUCKET


def test_compose_defines_minio_and_bootstraps_lakehouse_buckets():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "minio/minio" in compose
    assert "minio/mc" in compose
    assert "9000:9000" in compose
    assert "9001:9001" in compose

    for bucket_var in ("BRONZE_BUCKET", "SILVER_BUCKET", "GOLD_BUCKET"):
        assert bucket_var in compose

    assert "mc mb --ignore-existing" in compose


def test_minio_smoke_records_evidence_manifest():
    smoke = (ROOT / "scripts" / "minio_smoke.py").read_text(encoding="utf-8")

    assert "output/evidence/minio-smoke" in smoke
    assert "manifest.json" in smoke
    assert "roundtrip_ok" in smoke
    assert "s3fs.S3FileSystem" in smoke


def test_minio_smoke_loads_dotenv_before_config_imports(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for key in ("S3_ENDPOINT", "S3_KEY", "S3_SECRET", "BRONZE_BUCKET", "SILVER_BUCKET", "GOLD_BUCKET"):
        monkeypatch.delenv(key, raising=False)
    for module in ("railway_lakehouse.bronze.config", "railway_lakehouse.silver.config"):
        monkeypatch.delitem(sys.modules, module, raising=False)

    (tmp_path / ".env").write_text(
        "\n".join([
            "S3_ENDPOINT=http://127.0.0.1:19000",
            "S3_KEY=from_env_file",
            "S3_SECRET=from_env_secret",
            "BRONZE_BUCKET=bronze_env",
            "SILVER_BUCKET=silver_env",
            "GOLD_BUCKET=gold_env",
        ]),
        encoding="utf-8",
    )

    globals_after_load = run_path(str(ROOT / "scripts" / "minio_smoke.py"))

    assert globals_after_load["S3_ENDPOINT"] == "http://127.0.0.1:19000"
    assert globals_after_load["S3_KEY"] == "from_env_file"
    assert globals_after_load["S3_SECRET"] == "from_env_secret"
    assert globals_after_load["BRONZE_BUCKET"] == "bronze_env"
    assert globals_after_load["SILVER_BUCKET"] == "silver_env"
    assert globals_after_load["GOLD_BUCKET"] == "gold_env"
