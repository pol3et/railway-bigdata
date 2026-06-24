"""Read Gold Parquet with Spark and write GAP-009 coverage evidence."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_NAME = "railway-coverage"
DEFAULT_INPUT = "output/evidence/inventory-live-2026-06-23/railway_ml.parquet"
DEFAULT_OUT = "output/evidence/spark/"
OUTPUT_DIR_NAME = "coverage_by_geo_year"
MANIFEST_NAME = "manifest.json"
MISSING_INPUT_HINT = (
    "run the Gold pipeline first or pass --input to an existing Gold parquet"
)
EMPTY_INPUT_HINT = "pass --input to a non-empty Gold parquet before running Spark evidence"


def build_session(master: str):
    """Build the minimal local SparkSession for reading plain Parquet."""

    from pyspark.sql import SparkSession

    return (
        SparkSession.builder.appName(APP_NAME)
        .master(master)
        .getOrCreate()
    )


def run_coverage(
    spark: Any,
    input_path: str | os.PathLike[str],
    out_dir: str | os.PathLike[str],
    *,
    command: str | None = None,
) -> dict[str, Any]:
    """Run deterministic Spark coverage aggregation and write the manifest."""

    started_at = _utc_now()
    started = time.perf_counter()
    input_file = Path(input_path)
    out_root = Path(out_dir)
    output_path = out_root / OUTPUT_DIR_NAME
    manifest_path = out_root / MANIFEST_NAME

    _validate_input_exists(input_file)

    out_root.mkdir(parents=True, exist_ok=True)

    df = spark.read.parquet(_spark_local_path(input_file))
    input_rows = int(df.count())
    input_columns = [str(column) for column in df.columns]

    if input_rows == 0:
        raise ValueError(
            f"Input Gold parquet has 0 rows: {input_file.as_posix()}. "
            f"{EMPTY_INPUT_HINT}."
        )

    missing_columns = sorted({"geo", "year"} - set(input_columns))
    if missing_columns:
        raise ValueError(
            f"Input Gold parquet is missing required columns {missing_columns}: "
            f"{input_file.as_posix()}."
        )

    from pyspark.sql import functions as F

    feature_columns = [
        column for column in input_columns if column not in {"geo", "year"}
    ]
    coverage_exprs = [
        F.count(F.col(column)).alias(f"{column}_non_null")
        for column in feature_columns
    ]
    out_df = (
        df.groupBy("geo", "year")
        .agg(F.count(F.lit(1)).alias("row_count"), *coverage_exprs)
        .orderBy("geo", "year")
    )

    output_rows = int(out_df.count())
    output_columns = [str(column) for column in out_df.columns]
    out_df.write.mode("overwrite").parquet(_spark_local_path(output_path))

    files_written = _scan_files(output_path)
    partitions_written = sum(
        1
        for file_name in files_written
        if Path(file_name).name.startswith("part-")
        and Path(file_name).suffix == ".parquet"
    )
    finished_at = _utc_now()

    manifest: dict[str, Any] = {
        "command": command or "run_coverage",
        "spark_version": str(spark.version),
        "java_version": _java_version(spark),
        "java_home": os.environ.get("JAVA_HOME"),
        "hadoop_home": _env_path("HADOOP_HOME"),
        "input_path": input_file.as_posix(),
        "input_rows": input_rows,
        "input_columns": len(input_columns),
        "input_column_names": input_columns,
        "output_path": output_path.as_posix(),
        "output_rows": output_rows,
        "output_columns": len(output_columns),
        "output_column_names": output_columns,
        "files_written": files_written,
        "partitions_written": partitions_written,
        "duration_seconds": round(time.perf_counter() - started, 6),
        "status": "passed",
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "evidence_path": manifest_path.as_posix(),
    }
    _write_json(manifest_path, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    command = _command(args)
    manifest_path = Path(args.out) / MANIFEST_NAME
    spark = None
    started_at = _utc_now()
    started = time.perf_counter()

    try:
        _validate_input_exists(Path(args.input))
        spark = build_session(args.master)
        manifest = run_coverage(
            spark,
            args.input,
            args.out,
            command=command,
        )
        print(f"Evidence: {manifest['evidence_path']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        manifest = {
            "command": command,
            "spark_version": str(spark.version) if spark is not None else None,
            "java_version": _java_version(spark) if spark is not None else None,
            "java_home": os.environ.get("JAVA_HOME"),
            "hadoop_home": _env_path("HADOOP_HOME"),
            "input_path": Path(args.input).as_posix(),
            "output_path": (Path(args.out) / OUTPUT_DIR_NAME).as_posix(),
            "duration_seconds": round(time.perf_counter() - started, 6),
            "status": "failed",
            "started_at_utc": started_at,
            "finished_at_utc": _utc_now(),
            "error": str(exc),
            "hint": _failure_hint(exc),
            "evidence_path": manifest_path.as_posix(),
        }
        _write_json(manifest_path, manifest)
        print(f"FAILED: {exc}", file=sys.stderr)
        print(manifest["hint"], file=sys.stderr)
        print(f"Evidence: {manifest_path.as_posix()}", file=sys.stderr)
        return 1
    finally:
        if spark is not None:
            spark.stop()


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help="Gold Parquet file or directory to read with Spark",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help="Evidence directory that will receive manifest.json and Spark output",
    )
    parser.add_argument(
        "--master",
        default="local[*]",
        help="Spark master URL",
    )
    return parser.parse_args(argv)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _spark_local_path(path: Path) -> str:
    return path.resolve().as_uri()


def _validate_input_exists(input_file: Path) -> None:
    if not input_file.exists():
        raise FileNotFoundError(
            f"Input Gold parquet does not exist: {input_file.as_posix()}. "
            f"{MISSING_INPUT_HINT}."
        )


def _scan_files(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )


def _java_version(spark: Any) -> str | None:
    try:
        return str(
            spark.sparkContext._jvm.java.lang.System.getProperty("java.version")
        )
    except Exception:  # noqa: BLE001
        return None


def _env_path(name: str) -> str | None:
    value = os.environ.get(name)
    if not value:
        return None
    path = Path(value)
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return value


def _command(args: argparse.Namespace) -> str:
    return shlex.join(
        [
            "python",
            "-m",
            "railway_lakehouse.spark_jobs.coverage",
            "--input",
            args.input,
            "--out",
            args.out,
            "--master",
            args.master,
        ]
    )


def _failure_hint(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return MISSING_INPUT_HINT
    if isinstance(exc, ValueError) and "0 rows" in str(exc):
        return EMPTY_INPUT_HINT
    return (
        "install the pinned Spark extra, then run with JDK 17 or 21 and JAVA_HOME set"
    )


if __name__ == "__main__":
    sys.exit(main())
