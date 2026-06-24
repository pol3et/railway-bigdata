"""
Deterministic guard for the optional Spark stack pins (GAP-017).

These tests do not import pyspark. They only verify that committed package,
configuration, and documentation files keep the Spark, Delta, Hadoop, and JDK
decisions aligned.
"""

from pathlib import Path
import importlib
import re
import runpy
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


def _package_name(requirement: str) -> str:
    return re.split(r"[<>=!~;\s]", requirement, maxsplit=1)[0].lower()


def _is_spark_41(version: str) -> bool:
    major, minor, *_ = version.split(".")
    return major == "4" and minor == "1"


def test_gap017_spark_stack_pins_and_docs_stay_coherent():
    spark_extra = _spark_extra()
    assert [_package_name(req) for req in spark_extra] == ["pyspark", "delta-spark"]

    pyspark_req = _requirement(spark_extra, "pyspark")
    delta_req = _requirement(spark_extra, "delta-spark")

    assert re.search(r"\bpyspark==4\.1\.\*$", pyspark_req)
    assert _is_spark_41("4.1.2")
    assert not _is_spark_41("3.5.8")
    assert not _is_spark_41("5.0.0")

    assert re.search(r"\bdelta-spark==4\.1\.\*$", delta_req)

    spark_extra_text = "\n".join(spark_extra).lower()
    for forbidden in (
        ";",
        "python_version < '0'",
        'python_version < "0"',
        "hadoop-aws",
        "software.amazon.awssdk",
        "aws-java-sdk",
        "3.3.4",
        "3.5.",
        "3.2.",
    ):
        assert forbidden not in spark_extra_text

    spark_config = runpy.run_path(str(ROOT / "src" / "railway_lakehouse" / "spark_config.py"))

    hadoop_aws = "org.apache.hadoop:hadoop-aws:3.4.1"
    aws_sdk_bundle = "software.amazon.awssdk:bundle:2.24.6"
    s3a_packages = f"{hadoop_aws},{aws_sdk_bundle}"
    delta_maven = "io.delta:delta-spark_4.1_2.13:4.1.0"

    assert spark_config["SPARK_S3A_HADOOP_AWS_PACKAGE"] == hadoop_aws
    assert spark_config["SPARK_S3A_AWS_SDK_BUNDLE_PACKAGE"] == aws_sdk_bundle
    assert spark_config["SPARK_S3A_PACKAGES"] == s3a_packages
    assert spark_config["DELTA_SPARK_MAVEN_PACKAGE"] == delta_maven

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "STATE_AND_ROADMAP.md").read_text(encoding="utf-8")
    dashboard = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    tasks = (ROOT / "docs" / "TASKS.md").read_text(encoding="utf-8")
    gap_tasks = (ROOT / "docs" / "GAP_TASKS.md").read_text(encoding="utf-8")

    assert "JAVA_HOME" in readme
    assert re.search(r"JDK\s+(?:17\s+or\s+21|17\s*/\s*21|17-21|17..21)", readme)
    assert "JAVA_HOME" in env_example
    assert re.search(r"JDK\s+(?:17\s+or\s+21|17\s*/\s*21|17-21|17..21)", env_example)
    assert "JDK 17 or 21" in roadmap
    assert "JDK <b>17 / 21</b>" in dashboard
    for text in (readme, env_example, roadmap, dashboard, tasks, gap_tasks):
        assert hadoop_aws in text
        assert aws_sdk_bundle in text

    stale_claims = (
        "pyspark 3.5",
        "pyspark==3.5",
        "hadoop-aws 3.3.4",
        "delta-spark 3.2",
        "pin 3.5.* + jdk 17",
        "spark 3.5 supports 8/11/17",
    )
    for text in (readme, roadmap, dashboard, gap_tasks):
        lowered = text.lower()
        for stale in stale_claims:
            assert stale not in lowered

    stale_gap_task_patterns = (
        r"pyspark\s*==\s*3\.5",
        r"delta-spark\s*(?:==)?\s*3\.2",
        r"hadoop-aws\s*(?:==)?\s*3\.3\.4",
    )
    gap_tasks_lower = gap_tasks.lower()
    for pattern in stale_gap_task_patterns:
        assert re.search(pattern, gap_tasks_lower) is None


def test_gap009_coverage_module_imports_without_pyspark():
    coverage = importlib.import_module("railway_lakehouse.spark_jobs.coverage")

    assert callable(coverage.build_session)
    assert callable(coverage.run_coverage)
    assert callable(coverage.main)
    assert (
        coverage.DEFAULT_INPUT
        == "output/evidence/inventory-live-2026-06-23/railway_ml.parquet"
    )
    assert coverage.DEFAULT_OUT == "output/evidence/spark/"
