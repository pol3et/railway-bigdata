"""
Deterministic guard for the optional Spark stack pins (GAP-017).

These tests do not import pyspark. They only verify that committed package and
documentation files keep the Spark, Delta, Hadoop, and JDK decisions aligned.
"""

from pathlib import Path
import re
import tomllib

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]


def _spark_extra() -> list[str]:
    with (ROOT / "pyproject.toml").open("rb") as fh:
        pyproject = tomllib.load(fh)
    return pyproject["project"]["optional-dependencies"]["spark"]


def _requirement(extra: list[str], name: str) -> str:
    pattern = re.compile(rf"^{re.escape(name)}\b", re.IGNORECASE)
    matches = [req for req in extra if pattern.search(req)]
    assert len(matches) == 1, f"expected exactly one {name!r} requirement, got {matches!r}"
    return matches[0]


def _is_spark_41(version: str) -> bool:
    major, minor, *_ = version.split(".")
    return major == "4" and minor == "1"


def test_gap017_spark_stack_pins_and_docs_stay_coherent():
    spark_extra = _spark_extra()
    pyspark_req = _requirement(spark_extra, "pyspark")
    delta_req = _requirement(spark_extra, "delta-spark")
    hadoop_req = _requirement(spark_extra, "hadoop-aws")

    assert re.search(r"\bpyspark==4\.1\.\*(?:\s*;.*)?$", pyspark_req)
    assert _is_spark_41("4.1.2")
    assert not _is_spark_41("3.5.8")
    assert not _is_spark_41("5.0.0")

    assert re.search(r"\bdelta-spark==4\.1\.\*(?:\s*;.*)?$", delta_req)
    assert re.search(r"\bhadoop-aws==3\.4\.1(?:\s*;.*)?$", hadoop_req)

    spark_extra_text = "\n".join(spark_extra).lower()
    for forbidden in ("3.3.4", "3.5.", "3.2."):
        assert forbidden not in spark_extra_text

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "STATE_AND_ROADMAP.md").read_text(encoding="utf-8")
    dashboard = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")

    assert "JAVA_HOME" in readme
    assert re.search(r"JDK\s+(?:17\s+or\s+21|17\s*/\s*21|17-21|17..21)", readme)
    assert "JAVA_HOME" in env_example
    assert re.search(r"JDK\s+(?:17\s+or\s+21|17\s*/\s*21|17-21|17..21)", env_example)
    assert "JDK 17 or 21" in roadmap
    assert "JDK <b>17 / 21</b>" in dashboard

    stale_claims = (
        "pyspark 3.5",
        "pyspark==3.5",
        "hadoop-aws 3.3.4",
        "delta-spark 3.2",
        "pin 3.5.* + jdk 17",
        "spark 3.5 supports 8/11/17",
    )
    for text in (readme, roadmap, dashboard):
        lowered = text.lower()
        for stale in stale_claims:
            assert stale not in lowered
