import json
from pathlib import Path

import pandas as pd
import pytest

from railway_lakehouse.eval.harness import main, run_evaluation
from railway_lakehouse.eval.news import cohens_kappa, compute_all_metrics


pytestmark = pytest.mark.unit


EVENT_ROWS = [
    ("accident", "HU", "hu", "negative"),
    ("strike", "AT", "de", "negative"),
    ("service_change", "other", "en", "neutral"),
    ("delay", "HU", "hu", "negative"),
    ("investment", "AT", "de", "positive"),
    ("line_opening", "other", "en", "positive"),
    ("financial", "HU", "hu", "positive"),
    ("investment", "AT", "de", "positive"),
    ("policy", "other", "en", "neutral"),
    ("policy", "HU", "hu", "neutral"),
    ("policy", "AT", "de", "neutral"),
    ("policy", "other", "en", "neutral"),
    ("other", "HU", "hu", "neutral"),
    ("other", "AT", "de", "neutral"),
    ("other", "other", "en", "neutral"),
    ("other", "HU", "hu", "neutral"),
]


def _golden_rows(*, include_tune: bool = False) -> list[dict]:
    rows = []
    for idx, (event_type, country, language, sentiment) in enumerate(EVENT_ROWS):
        year = 2026 if idx < 8 else 2025
        rows.append({
            "article_id": f"article-{idx:02d}",
            "partition": "TEST",
            "source": "synthetic",
            "url": f"https://example.test/news/{idx}",
            "published_date": f"{year}-06-{(idx % 20) + 1:02d}",
            "title": "Synthetic railway evaluation seed",
            "body_sha256": f"sha256-{idx:02d}",
            "excerpt": "Synthetic excerpt for evaluator tests.",
            "language_gold": language,
            "is_rail_related_gold": True,
            "country_gold": country,
            "event_type_gold": event_type,
            "sentiment_gold": sentiment,
            "operators_gold": ["MAV"] if country == "HU" else ["OBB"] if country == "AT" else [],
            "rail_lines_gold": [f"Line {idx % 3}"],
            "monetary_amount_eur_gold": 1000.0 + idx if event_type in {"investment", "financial"} else None,
            "monetary_currency_gold": "EUR" if event_type in {"investment", "financial"} else None,
            "dup_group_id_gold": f"dup-{idx // 2:02d}",
        })
    if include_tune:
        for idx in range(4):
            rows.append({
                **rows[idx],
                "article_id": f"tune-{idx:02d}",
                "partition": "TUNE",
                "event_type_gold": "investment",
                "sentiment_gold": "positive",
                "dup_group_id_gold": f"tune-dup-{idx}",
            })
    return rows


def _prediction_from_gold(row: dict) -> dict:
    return {
        "article_id": row["article_id"],
        "source": row["source"],
        "url": row["url"],
        "published_date": row["published_date"],
        "language": row["language_gold"],
        "is_rail_related": row["is_rail_related_gold"],
        "country": row["country_gold"],
        "event_type": row["event_type_gold"],
        "operators": row["operators_gold"],
        "rail_lines": row["rail_lines_gold"],
        "monetary_amount_eur": row["monetary_amount_eur_gold"],
        "sentiment": row["sentiment_gold"],
        "confidence": 0.9,
        "cross_lingual_dedup_id": row["dup_group_id_gold"],
        "extraction_model_digest": "mock-row-digest",
    }


def _write_json(path: Path, data) -> Path:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _run(tmp_path: Path, rows: list[dict], preds: list[dict], **kwargs) -> dict:
    golden_path = _write_json(tmp_path / "golden.json", rows)
    pred_path = _write_json(tmp_path / "predictions.json", preds)
    return run_evaluation(
        str(golden_path),
        str(pred_path),
        out_dir=str(tmp_path / "eval"),
        min_support=kwargs.pop("min_support", 3),
        **kwargs,
    )


def test_perfect_match_writes_manifest_and_article_scores(tmp_path):
    rows = _golden_rows()
    preds = [_prediction_from_gold(row) for row in rows]
    pred_parquet = tmp_path / "predictions.parquet"
    pd.DataFrame(preds).to_parquet(pred_parquet)
    golden_path = _write_json(tmp_path / "golden.json", rows)

    manifest = run_evaluation(
        str(golden_path),
        str(pred_parquet),
        model_digest="mock-perfect",
        out_dir=str(tmp_path / "eval"),
        min_support=3,
    )

    assert manifest["status"] == "passed"
    assert manifest["model_digest"] == "mock-perfect"
    assert manifest["alignment"] == {"matched": 16, "gold_only": 0, "pred_only": 0}
    assert manifest["metrics"]["is_rail_related_recall"]["value"] == pytest.approx(1.0)
    assert manifest["metrics"]["event_superclass_macro_f1"]["value"] == pytest.approx(1.0)
    assert manifest["metrics"]["country_macro_f1"]["value"] == pytest.approx(1.0)
    assert manifest["metrics"]["language_accuracy"]["value"] == pytest.approx(1.0)
    assert manifest["metrics"]["dedup_geoyear_count_error"]["value"] == pytest.approx(0.0)
    assert (tmp_path / "eval" / "manifest.json").exists()
    assert (tmp_path / "eval" / "metric_summary.json").exists()

    scores = pd.read_csv(tmp_path / "eval" / "per_article_scores.csv")
    assert set(scores["article_id"]) == {row["article_id"] for row in rows}
    assert scores["overall_score"].min() == pytest.approx(1.0)


def test_degraded_predictions_fail_gated_thresholds(tmp_path):
    rows = _golden_rows()
    preds = []
    for row in rows:
        pred = _prediction_from_gold(row)
        pred["event_type"] = "other"
        pred["sentiment"] = "neutral"
        preds.append(pred)

    manifest = _run(tmp_path, rows, preds)

    assert manifest["status"] == "failed"
    names = {item["metric"] for item in manifest["threshold_violations"]}
    assert "event_superclass_macro_f1" in names
    assert "sentiment_macro_f1_de" in names


def test_non_regression_uses_ci_overlap_rule(tmp_path):
    rows = _golden_rows()
    preds = [_prediction_from_gold(row) | {"event_type": "other"} for row in rows]
    baseline_path = _write_json(tmp_path / "baseline.json", {
        "digest_bundle": {"llm_model_digest": "old"},
        "metrics": {
            "event_superclass_macro_f1": {"value": 0.95, "ci_lo": 0.90, "ci_hi": 1.0},
        },
    })
    loose_thresholds = {"event_superclass_macro_f1": 0.0}

    manifest = _run(
        tmp_path,
        rows,
        preds,
        baseline_path=str(baseline_path),
        metric_thresholds=loose_thresholds,
    )

    assert manifest["status"] == "failed"
    assert manifest["regression_violations"][0]["metric"] == "event_superclass_macro_f1"

    overlapping_baseline = _write_json(tmp_path / "baseline_overlap.json", {
        "metrics": {
            "event_superclass_macro_f1": {"value": 0.40, "ci_lo": 0.0, "ci_hi": 1.0},
        },
    })
    manifest_overlap = _run(
        tmp_path,
        rows,
        preds,
        baseline_path=str(overlapping_baseline),
        metric_thresholds=loose_thresholds,
    )
    assert manifest_overlap["regression_violations"] == []


def test_support_demotion_prevents_threshold_failure(tmp_path):
    rows = _golden_rows()[:4]
    preds = [_prediction_from_gold(row) | {"event_type": "other"} for row in rows]

    manifest = _run(tmp_path, rows, preds, min_support=30)

    metric = manifest["metrics"]["event_superclass_macro_f1"]
    assert manifest["status"] == "passed"
    assert metric["gated"] is False
    assert metric["demotion_reason"] == "support<30"


def test_test_partition_excludes_tune_rows(tmp_path):
    rows = _golden_rows(include_tune=True)
    preds = []
    for row in rows:
        pred = _prediction_from_gold(row)
        if row["partition"] == "TUNE":
            pred["event_type"] = "other"
            pred["sentiment"] = "negative"
        preds.append(pred)

    manifest = _run(tmp_path, rows, preds, partition="TEST")

    assert manifest["status"] == "passed"
    assert manifest["alignment"]["matched"] == 16
    assert manifest["partition"] == "TEST"


def test_missing_args_and_missing_files_return_exit_2(tmp_path, capsys):
    assert main(["--golden-set", str(tmp_path / "missing.json")]) == 2
    missing_args = capsys.readouterr()
    assert "--extraction-results" in missing_args.err

    assert main([
        "--golden-set", str(tmp_path / "missing-golden.json"),
        "--extraction-results", str(tmp_path / "missing-pred.json"),
    ]) == 2
    missing_files = capsys.readouterr()
    assert "not found" in missing_files.err.lower()


def test_model_digest_is_recorded(tmp_path):
    rows = _golden_rows()
    preds = [_prediction_from_gold(row) for row in rows]

    manifest = _run(tmp_path, rows, preds, model_digest="mock-x")

    assert manifest["model_digest"] == "mock-x"


def test_manifest_is_byte_deterministic_for_same_seed(tmp_path):
    rows = _golden_rows()
    preds = [_prediction_from_gold(row) for row in rows]

    _run(tmp_path, rows, preds, boot_seed=12345)
    first = (tmp_path / "eval" / "manifest.json").read_bytes()
    _run(tmp_path, rows, preds, boot_seed=12345)
    second = (tmp_path / "eval" / "manifest.json").read_bytes()

    assert first == second


def test_bootstrap_seed_changes_ci_not_point_value(tmp_path):
    rows = _golden_rows()[:8]
    preds = [_prediction_from_gold(row) for row in rows]
    preds[0]["is_rail_related"] = False
    preds[1]["is_rail_related"] = False
    preds[3]["is_rail_related"] = False

    metric_a = compute_all_metrics(
        rows,
        preds,
        partition="TEST",
        min_support=3,
        n_boot=101,
        boot_seed=12345,
    )["is_rail_related_recall"]
    metric_b = compute_all_metrics(
        rows,
        preds,
        partition="TEST",
        min_support=3,
        n_boot=101,
        boot_seed=999,
    )["is_rail_related_recall"]

    assert metric_a["value"] == pytest.approx(metric_b["value"], abs=1e-12)
    assert (metric_a["ci_lo"], metric_a["ci_hi"]) != (metric_b["ci_lo"], metric_b["ci_hi"])


def test_cohens_kappa_matches_hand_computed_value():
    assert cohens_kappa(["yes", "yes", "no", "no"], ["yes", "no", "no", "no"]) == pytest.approx(0.5, abs=1e-9)
