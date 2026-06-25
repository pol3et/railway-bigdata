"""CLI harness for GAP-043 news/model evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .news import (
    DEFAULT_THRESHOLDS,
    EVENT_SUPERCLASS,
    THRESHOLD_DIRECTIONS,
    alignment_counts,
    ci_overlap,
    compute_all_metrics,
    per_article_scores,
)


SCHEMA_VERSION = "gap043-eval-v1"
DEFAULT_GOLDEN_SET = "tests/fixtures/news_golden_set.json"
DEFAULT_OUT_DIR = "output/evidence/news_eval/"
DEFAULT_N_BOOT = 2000
DETERMINISTIC_TIMESTAMP_UTC = "1970-01-01T00:00:00Z"
CAVEAT = (
    "Agent-labeled silver-standard reference (Sonnet labelers, not human gold). "
    "Gates fire on NON-REGRESSION; absolute numbers are indicative only."
)


def run_evaluation(
    golden_set_path: str,
    extraction_results_path: str,
    *,
    model_digest: str | None = None,
    metric_thresholds: dict | None = None,
    baseline_path: str | None = None,
    partition: str = "TEST",
    min_support: int = 30,
    boot_seed: int = 12345,
    out_dir: str = DEFAULT_OUT_DIR,
) -> dict:
    golden_rows = _load_rows(golden_set_path, kind="golden set")
    prediction_rows = _load_rows(extraction_results_path, kind="extraction results")
    partition = str(partition).upper()
    thresholds = {**DEFAULT_THRESHOLDS, **(metric_thresholds or {})}
    metrics = compute_all_metrics(
        golden_rows,
        prediction_rows,
        partition=partition,
        min_support=min_support,
        n_boot=DEFAULT_N_BOOT,
        boot_seed=boot_seed,
    )
    sidecar = _load_sidecar_manifest(extraction_results_path)
    digest_bundle = _digest_bundle(model_digest, prediction_rows, sidecar)
    baseline = _load_baseline(baseline_path) if baseline_path else None
    digest_changed = _digest_changed(digest_bundle, baseline)

    threshold_violations = []
    regression_violations = []
    for name in sorted(metrics):
        metric = metrics[name]
        if not isinstance(metric, dict) or "value" not in metric:
            continue
        threshold = thresholds.get(name, metric.get("gate_threshold"))
        metric["gate_threshold"] = threshold
        metric["absolute_pass"] = None
        metric["regression"] = False
        if metric.get("gated"):
            absolute_pass = _passes_threshold(name, metric.get("value"), threshold)
            metric["absolute_pass"] = absolute_pass
            if not absolute_pass:
                threshold_violations.append({
                    "metric": name,
                    "value": metric.get("value"),
                    "threshold": threshold,
                })
            if baseline:
                baseline_metric = _baseline_metric(baseline, name)
                if baseline_metric is not None and _is_regression(name, metric, baseline_metric):
                    metric["regression"] = True
                    regression_violations.append({
                        "metric": name,
                        "ci": [metric.get("ci_lo"), metric.get("ci_hi")],
                        "baseline_ci": [baseline_metric.get("ci_lo"), baseline_metric.get("ci_hi")],
                    })

    status = "failed" if threshold_violations or regression_violations else "passed"
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_started_utc": DETERMINISTIC_TIMESTAMP_UTC,
        "run_finished_utc": DETERMINISTIC_TIMESTAMP_UTC,
        "duration_seconds": 0.0,
        "command": _command_string(
            golden_set_path,
            extraction_results_path,
            out_dir,
            partition,
            min_support,
            boot_seed,
            model_digest=model_digest,
            baseline_path=baseline_path,
        ),
        "status": status,
        "caveat": CAVEAT,
        "partition": partition,
        "min_support": min_support,
        "boot_seed": boot_seed,
        "n_boot": DEFAULT_N_BOOT,
        "alignment": alignment_counts(golden_rows, prediction_rows, partition=partition),
        "model_digest": model_digest,
        "digest_bundle": digest_bundle,
        "digest_changed": digest_changed,
        "event_superclass_map": dict(sorted(EVENT_SUPERCLASS.items())),
        "metrics": metrics,
        "threshold_violations": threshold_violations,
        "regression_violations": regression_violations,
        "baseline_path": baseline_path,
        "regression_checked": baseline_path is not None,
        "data_availability_blocker": (
            "Current committed Silver GAP-033 rows do not contain original title/body text; "
            "real label construction remains gated on owner-approved bounded re-extraction."
        ),
    }

    _write_json(out_path / "manifest.json", manifest)
    _write_json(out_path / "metric_summary.json", _metric_summary(metrics))
    scores = per_article_scores(golden_rows, prediction_rows, partition=partition)
    pd.DataFrame(scores).to_csv(out_path / "per_article_scores.csv", index=False)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m railway_lakehouse.eval.harness",
        description="Evaluate NewsFeature predictions against a GAP-043 golden set.",
    )
    parser.add_argument("--golden-set", default=DEFAULT_GOLDEN_SET, help="Path to golden-set JSON.")
    parser.add_argument("--extraction-results", required=True, help="Path to prediction JSON or parquet.")
    parser.add_argument("--model-digest", default=None, help="Model digest string to record in the manifest.")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help="Output directory for evaluation artifacts.")
    parser.add_argument("--metric-thresholds", default=None, help="Optional JSON file with metric threshold overrides.")
    parser.add_argument("--baseline", default=None, help="Optional non-regression baseline JSON.")
    parser.add_argument("--partition", choices=["TUNE", "TEST", "ALL"], default="TEST")
    parser.add_argument("--min-support", type=int, default=30)
    parser.add_argument("--boot-seed", type=int, default=12345)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        thresholds = _load_thresholds(args.metric_thresholds)
        manifest = run_evaluation(
            args.golden_set,
            args.extraction_results,
            model_digest=args.model_digest,
            metric_thresholds=thresholds,
            baseline_path=args.baseline,
            partition=args.partition,
            min_support=args.min_support,
            boot_seed=args.boot_seed,
            out_dir=args.out,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0 if manifest["status"] == "passed" else 1


def _load_rows(path: str, *, kind: str) -> list[dict]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"{kind} file not found: {file_path}")
    if file_path.suffix.lower() in {".parquet", ".pq"}:
        return _records_from_frame(pd.read_parquet(file_path))
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        if "rows" in payload:
            payload = payload["rows"]
        elif "golden_rows" in payload:
            payload = payload["golden_rows"]
        elif "predictions" in payload:
            payload = payload["predictions"]
    if not isinstance(payload, list):
        raise ValueError(f"{kind} must be a JSON list or an object containing rows")
    return [_normalize_record(row) for row in payload]


def _records_from_frame(frame: pd.DataFrame) -> list[dict]:
    return [_normalize_record(row) for row in frame.to_dict(orient="records")]


def _normalize_record(row: dict) -> dict:
    out = {}
    for key, value in dict(row).items():
        out[key] = _normalize_value(value)
    return out


def _normalize_value(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if value is pd.NA:
        return None
    if isinstance(value, np.ndarray):
        return [_normalize_value(item) for item in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _load_thresholds(path: str | None) -> dict | None:
    if path is None:
        return None
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"metric thresholds file not found: {file_path}")
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("metric thresholds file must contain a JSON object")
    return payload


def _load_baseline(path: str | None) -> dict | None:
    if path is None:
        return None
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"baseline file not found: {file_path}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def _load_sidecar_manifest(extraction_results_path: str) -> dict:
    file_path = Path(extraction_results_path)
    candidates = [
        file_path.with_suffix(".manifest.json"),
        file_path.parent / "manifest.json",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate != file_path:
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
    return {}


def _digest_bundle(model_digest: str | None, rows: list[dict], sidecar: dict) -> dict:
    row_digests = sorted({
        str(row["extraction_model_digest"])
        for row in rows
        if "extraction_model_digest" in row and row["extraction_model_digest"] is not None
    })
    llm_digest = model_digest or sidecar.get("model_digest") or (row_digests[0] if len(row_digests) == 1 else None)
    return {
        "llm_model_digest": llm_digest,
        "prompt_version": sidecar.get("prompt_version"),
        "sentiment_model_digest": sidecar.get("sentiment_model_digest"),
        "lid_model_digest": sidecar.get("language_id_model_digest") or sidecar.get("lid_model_digest"),
        "embedding_model_digest": sidecar.get("embedding_model_digest"),
        "extractor_version": sidecar.get("extractor_version") or sidecar.get("prompt_version"),
    }


def _digest_changed(digest_bundle: dict, baseline: dict | None) -> bool:
    if not baseline or "digest_bundle" not in baseline:
        return False
    return digest_bundle != baseline["digest_bundle"]


def _baseline_metric(baseline: dict, name: str) -> dict | None:
    if "metrics" in baseline and name in baseline["metrics"]:
        return baseline["metrics"][name]
    if name in baseline:
        return baseline[name]
    return None


def _is_regression(name: str, metric: dict, baseline_metric: dict) -> bool:
    metric_ci = (metric.get("ci_lo"), metric.get("ci_hi"))
    baseline_ci = (baseline_metric.get("ci_lo"), baseline_metric.get("ci_hi"))
    if ci_overlap(metric_ci, baseline_ci):
        return False
    direction = THRESHOLD_DIRECTIONS.get(name, "min")
    if direction == "max":
        return metric.get("value") is not None and metric.get("value") > baseline_metric.get("value")
    return metric.get("value") is not None and metric.get("value") < baseline_metric.get("value")


def _passes_threshold(name: str, value, threshold) -> bool:
    if threshold is None or value is None:
        return True
    if THRESHOLD_DIRECTIONS.get(name, "min") == "max":
        return float(value) <= float(threshold)
    return float(value) >= float(threshold)


def _metric_summary(metrics: dict) -> dict:
    summary = {}
    for name in sorted(metrics):
        metric = metrics[name]
        if not isinstance(metric, dict) or "value" not in metric:
            continue
        if metric.get("gated"):
            status = "pass" if metric.get("absolute_pass") is not False and not metric.get("regression") else "fail"
        else:
            status = "report_only"
        summary[name] = {
            "value": metric.get("value"),
            "ci_lo": metric.get("ci_lo"),
            "ci_hi": metric.get("ci_hi"),
            "support": metric.get("support"),
            "threshold": metric.get("gate_threshold"),
            "gated": metric.get("gated"),
            "status": status,
        }
    return summary


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _command_string(
    golden_set_path: str,
    extraction_results_path: str,
    out_dir: str,
    partition: str,
    min_support: int,
    boot_seed: int,
    *,
    model_digest: str | None,
    baseline_path: str | None,
) -> str:
    parts = [
        "python -m railway_lakehouse.eval.harness",
        f"--golden-set {golden_set_path}",
        f"--extraction-results {extraction_results_path}",
    ]
    if model_digest is not None:
        parts.append(f"--model-digest {model_digest}")
    parts.extend([
        f"--out {out_dir}",
        f"--partition {partition}",
        f"--min-support {min_support}",
        f"--boot-seed {boot_seed}",
    ])
    if baseline_path is not None:
        parts.append(f"--baseline {baseline_path}")
    return " ".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
