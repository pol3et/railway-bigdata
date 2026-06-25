"""Deterministic news-evaluation metrics for GAP-043.

This module intentionally avoids sklearn/scipy so the CI-safe harness can run
with only the project's core NumPy/pandas stack.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Callable, Iterable

import numpy as np
import pandas as pd


EVENT_LABELS_10WAY = [
    "investment",
    "accident",
    "strike",
    "service_change",
    "policy",
    "line_opening",
    "line_closure",
    "delay",
    "financial",
    "other",
]

EVENT_SUPERCLASS: dict[str, str] = {
    "accident": "disruption",
    "strike": "disruption",
    "service_change": "disruption",
    "delay": "disruption",
    "line_closure": "disruption",
    "investment": "development",
    "line_opening": "development",
    "financial": "development",
    "policy": "policy",
    "other": "other",
}

EVENT_SUPERCLASS_LABELS = ["development", "disruption", "other", "policy"]
COUNTRY_LABELS = ["AT", "HU", "other"]
SENTIMENT_LABELS = ["negative", "neutral", "positive"]

DEFAULT_THRESHOLDS = {
    "is_rail_related_recall": 0.90,
    "event_superclass_macro_f1": 0.50,
    "country_macro_f1": 0.80,
    "sentiment_macro_f1_de": 0.60,
    "language_accuracy": 0.95,
    "dedup_geoyear_count_error": 0.10,
}

THRESHOLD_DIRECTIONS = {
    "dedup_geoyear_count_error": "max",
}


def to_superclass(event_type: str) -> str:
    return EVENT_SUPERCLASS.get(str(event_type or ""), "other")


def accuracy(gold: list[str], pred: list[str]) -> float:
    if not gold:
        return 0.0
    return sum(1 for g, p in zip(gold, pred) if g == p) / len(gold)


def precision_recall_f1(gold: list, pred: list, *, positive) -> tuple[float, float, float]:
    tp = sum(1 for g, p in zip(gold, pred) if g == positive and p == positive)
    fp = sum(1 for g, p in zip(gold, pred) if g != positive and p == positive)
    fn = sum(1 for g, p in zip(gold, pred) if g == positive and p != positive)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def macro_f1(gold: list[str], pred: list[str], *, labels: list[str]) -> float:
    if not labels:
        return 0.0
    scores = []
    for label in labels:
        if not any(value == label for value in gold) and not any(value == label for value in pred):
            continue
        _, _, f1 = precision_recall_f1(gold, pred, positive=label)
        scores.append(f1)
    return float(np.mean(scores)) if scores else 0.0


def confusion_matrix(gold, pred, *, labels) -> list[list[int]]:
    label_to_idx = {label: idx for idx, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for g, p in zip(gold, pred):
        if g in label_to_idx and p in label_to_idx:
            matrix[label_to_idx[g]][label_to_idx[p]] += 1
    return matrix


def set_micro_prf(gold_sets: list[set], pred_sets: list[set]) -> tuple[float, float, float]:
    tp = fp = fn = 0
    for gold, pred in zip(gold_sets, pred_sets):
        gold = set(gold or set())
        pred = set(pred or set())
        tp += len(gold & pred)
        fp += len(pred - gold)
        fn += len(gold - pred)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def monetary_match_rate(gold_amts, pred_amts, *, rel_tol=0.01) -> float:
    pairs = [(g, p) for g, p in zip(gold_amts, pred_amts) if not _is_null(g)]
    if not pairs:
        return 0.0
    matches = sum(1 for g, p in pairs if _money_match(g, p, rel_tol=rel_tol))
    return matches / len(pairs)


def bcubed_prf(gold_groups: list[str], pred_groups: list[str]) -> tuple[float, float, float]:
    if not gold_groups:
        return 0.0, 0.0, 0.0
    gold_members = _group_members(gold_groups)
    pred_members = _group_members(pred_groups)
    precisions = []
    recalls = []
    for idx in range(len(gold_groups)):
        gold_cluster = gold_members[gold_groups[idx]]
        pred_cluster = pred_members[pred_groups[idx]]
        overlap = len(gold_cluster & pred_cluster)
        precisions.append(overlap / len(pred_cluster) if pred_cluster else 0.0)
        recalls.append(overlap / len(gold_cluster) if gold_cluster else 0.0)
    precision = float(np.mean(precisions)) if precisions else 0.0
    recall = float(np.mean(recalls)) if recalls else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def geoyear_count_error(gold_rows, pred_rows) -> float:
    gold_counts = _canonical_counts(gold_rows, gold=True)
    pred_counts = _canonical_counts(pred_rows, gold=False)
    keys = sorted(set(gold_counts) | set(pred_counts))
    denominator = sum(gold_counts.values())
    if denominator == 0:
        return 0.0 if sum(pred_counts.values()) == 0 else 1.0
    error = sum(abs(pred_counts.get(key, 0) - gold_counts.get(key, 0)) for key in keys)
    return error / denominator


def cohens_kappa(labeler_a: list[str], labeler_b: list[str]) -> float:
    if len(labeler_a) != len(labeler_b):
        raise ValueError("label lists must have equal length")
    n = len(labeler_a)
    if n == 0:
        return 0.0
    observed = sum(1 for a, b in zip(labeler_a, labeler_b) if a == b) / n
    counts_a = Counter(labeler_a)
    counts_b = Counter(labeler_b)
    labels = sorted(set(counts_a) | set(counts_b))
    expected = sum((counts_a[label] / n) * (counts_b[label] / n) for label in labels)
    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1.0 - expected)


def bootstrap_ci(
    values: list[float] | Callable,
    *,
    n_boot=2000,
    seed=12345,
    alpha=0.05,
) -> tuple[float | None, float | None]:
    rng = np.random.default_rng(seed)
    scores = []
    if callable(values):
        n_items = int(getattr(values, "n_items", 0))
        if n_items <= 0:
            return None, None
        for _ in range(n_boot):
            indices = rng.integers(0, n_items, size=n_items)
            scores.append(float(values(indices)))
    else:
        clean = [float(value) for value in values if not _is_null(value)]
        if not clean:
            return None, None
        data = np.array(clean, dtype=float)
        for _ in range(n_boot):
            indices = rng.integers(0, len(data), size=len(data))
            scores.append(float(np.mean(data[indices])))
    lo, hi = np.percentile(scores, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def ci_overlap(ci_a: tuple, ci_b: tuple) -> bool:
    if ci_a[0] is None or ci_a[1] is None or ci_b[0] is None or ci_b[1] is None:
        return False
    return max(float(ci_a[0]), float(ci_b[0])) <= min(float(ci_a[1]), float(ci_b[1]))


def compute_all_metrics(
    golden_rows: list[dict],
    prediction_rows: list[dict],
    *,
    partition: str | None = None,
    min_support: int = 30,
    n_boot: int = 2000,
    boot_seed: int = 12345,
) -> dict:
    gold = _filter_partition(golden_rows, partition)
    pairs = _aligned_pairs(gold, prediction_rows)
    metrics: dict[str, dict] = {}

    bool_rows = [
        pair for pair in pairs
        if not _is_null(_gold_value(pair[0], "is_rail_related"))
    ]
    gold_bool = [bool(_gold_value(row, "is_rail_related")) for row, _ in bool_rows]
    pred_bool = [bool(_pred_value(row, "is_rail_related")) for _, row in bool_rows]
    precision, recall, f1 = precision_recall_f1(gold_bool, pred_bool, positive=True)
    metrics["is_rail_related_recall"] = _metric(
        "is_rail_related_recall",
        recall,
        bool_rows,
        lambda sample: precision_recall_f1(
            [bool(_gold_value(g, "is_rail_related")) for g, _ in sample],
            [bool(_pred_value(p, "is_rail_related")) for _, p in sample],
            positive=True,
        )[1],
        min_support=min_support,
        n_boot=n_boot,
        boot_seed=boot_seed,
        default_gated=True,
        support=sum(1 for value in gold_bool if value is True),
    )
    metrics["is_rail_related_precision"] = _metric(
        "is_rail_related_precision",
        precision,
        bool_rows,
        lambda sample: precision_recall_f1(
            [bool(_gold_value(g, "is_rail_related")) for g, _ in sample],
            [bool(_pred_value(p, "is_rail_related")) for _, p in sample],
            positive=True,
        )[0],
        min_support=min_support,
        n_boot=n_boot,
        boot_seed=boot_seed,
        default_gated=False,
        demotion_reason="balanced_precision_report_only",
    )
    metrics["is_rail_related_f1"] = _metric(
        "is_rail_related_f1",
        f1,
        bool_rows,
        lambda sample: precision_recall_f1(
            [bool(_gold_value(g, "is_rail_related")) for g, _ in sample],
            [bool(_pred_value(p, "is_rail_related")) for _, p in sample],
            positive=True,
        )[2],
        min_support=min_support,
        n_boot=n_boot,
        boot_seed=boot_seed,
        default_gated=False,
        demotion_reason="report_only",
    )

    event_rows = [
        pair for pair in pairs
        if not _is_null(_gold_value(pair[0], "event_type"))
    ]
    gold_events = [str(_gold_value(row, "event_type") or "other") for row, _ in event_rows]
    pred_events = [str(_pred_value(row, "event_type") or "other") for _, row in event_rows]
    gold_super = [to_superclass(value) for value in gold_events]
    pred_super = [to_superclass(value) for value in pred_events]
    event_supports = Counter(gold_super)
    event_gate_supported = all(
        event_supports.get(label, 0) >= min_support for label in EVENT_SUPERCLASS_LABELS
    )
    event_value = macro_f1(gold_super, pred_super, labels=EVENT_SUPERCLASS_LABELS)
    metrics["event_superclass_macro_f1"] = _metric(
        "event_superclass_macro_f1",
        event_value,
        event_rows,
        lambda sample: macro_f1(
            [to_superclass(str(_gold_value(g, "event_type") or "other")) for g, _ in sample],
            [to_superclass(str(_pred_value(p, "event_type") or "other")) for _, p in sample],
            labels=EVENT_SUPERCLASS_LABELS,
        ),
        min_support=min_support,
        n_boot=n_boot,
        boot_seed=boot_seed,
        default_gated=event_gate_supported,
        support=len(event_rows),
        demotion_reason=None if event_gate_supported else "support<30",
    )
    metrics["event_10way_confusion"] = {
        "labels": EVENT_LABELS_10WAY,
        "matrix": confusion_matrix(gold_events, pred_events, labels=EVENT_LABELS_10WAY),
        "support": len(event_rows),
        "support_per_class": {label: gold_events.count(label) for label in EVENT_LABELS_10WAY},
        "gated": False,
        "gate_threshold": None,
        "demotion_reason": "diagnostic_report_only",
    }

    country_rows = [
        pair for pair in pairs
        if not _is_null(_gold_value(pair[0], "country"))
    ]
    country_supports = Counter(str(_gold_value(row, "country") or "other") for row, _ in country_rows)
    country_supported = all(country_supports.get(label, 0) >= min_support for label in COUNTRY_LABELS)
    metrics["country_macro_f1"] = _metric(
        "country_macro_f1",
        macro_f1(
            [str(_gold_value(g, "country") or "other") for g, _ in country_rows],
            [str(_pred_value(p, "country") or "other") for _, p in country_rows],
            labels=COUNTRY_LABELS,
        ),
        country_rows,
        lambda sample: macro_f1(
            [str(_gold_value(g, "country") or "other") for g, _ in sample],
            [str(_pred_value(p, "country") or "other") for _, p in sample],
            labels=COUNTRY_LABELS,
        ),
        min_support=min_support,
        n_boot=n_boot,
        boot_seed=boot_seed,
        default_gated=country_supported,
        demotion_reason=None if country_supported else "support<30",
    )

    for language, metric_name, default_gated, report_reason in (
        ("de", "sentiment_macro_f1_de", True, None),
        ("hu", "sentiment_macro_f1_hu", False, "hu_caveat_report_only"),
        ("en", "sentiment_macro_f1_en", False, "report_only"),
    ):
        sentiment_rows = [
            pair for pair in pairs
            if str(_gold_value(pair[0], "language") or "").lower() == language
            and not _is_null(_gold_value(pair[0], "sentiment"))
        ]
        value = macro_f1(
            [str(_gold_value(g, "sentiment") or "neutral") for g, _ in sentiment_rows],
            [str(_pred_value(p, "sentiment") or "neutral") for _, p in sentiment_rows],
            labels=SENTIMENT_LABELS,
        )
        metrics[metric_name] = _metric(
            metric_name,
            value,
            sentiment_rows,
            lambda sample: macro_f1(
                [str(_gold_value(g, "sentiment") or "neutral") for g, _ in sample],
                [str(_pred_value(p, "sentiment") or "neutral") for _, p in sample],
                labels=SENTIMENT_LABELS,
            ),
            min_support=min_support,
            n_boot=n_boot,
            boot_seed=boot_seed,
            default_gated=default_gated,
            demotion_reason=report_reason,
        )

    language_rows = [
        pair for pair in pairs
        if not _is_null(_gold_value(pair[0], "language"))
    ]
    metrics["language_accuracy"] = _metric(
        "language_accuracy",
        accuracy(
            [str(_gold_value(g, "language") or "") for g, _ in language_rows],
            [str(_pred_value(p, "language") or "") for _, p in language_rows],
        ),
        language_rows,
        lambda sample: accuracy(
            [str(_gold_value(g, "language") or "") for g, _ in sample],
            [str(_pred_value(p, "language") or "") for _, p in sample],
        ),
        min_support=min_support,
        n_boot=n_boot,
        boot_seed=boot_seed,
        default_gated=True,
    )

    operators_rows = pairs[:]
    op_p, op_r, op_f1 = set_micro_prf(
        [_as_set(_gold_value(g, "operators")) for g, _ in operators_rows],
        [_as_set(_pred_value(p, "operators")) for _, p in operators_rows],
    )
    metrics["operators_micro_f1"] = _metric(
        "operators_micro_f1",
        op_f1,
        operators_rows,
        lambda sample: set_micro_prf(
            [_as_set(_gold_value(g, "operators")) for g, _ in sample],
            [_as_set(_pred_value(p, "operators")) for _, p in sample],
        )[2],
        min_support=min_support,
        n_boot=n_boot,
        boot_seed=boot_seed,
        default_gated=False,
        demotion_reason="ner_deferred_gap038",
    )
    metrics["operators_micro_f1"]["precision"] = op_p
    metrics["operators_micro_f1"]["recall"] = op_r

    rail_p, rail_r, rail_f1 = set_micro_prf(
        [_as_set(_gold_value(g, "rail_lines")) for g, _ in pairs],
        [_as_set(_pred_value(p, "rail_lines")) for _, p in pairs],
    )
    metrics["rail_lines_recall"] = _metric(
        "rail_lines_recall",
        rail_r,
        pairs,
        lambda sample: set_micro_prf(
            [_as_set(_gold_value(g, "rail_lines")) for g, _ in sample],
            [_as_set(_pred_value(p, "rail_lines")) for _, p in sample],
        )[1],
        min_support=min_support,
        n_boot=n_boot,
        boot_seed=boot_seed,
        default_gated=False,
        demotion_reason="ner_deferred_gap038",
    )
    metrics["rail_lines_recall"]["precision"] = rail_p
    metrics["rail_lines_recall"]["f1"] = rail_f1

    money_rows = [
        pair for pair in pairs
        if not _is_null(_gold_value(pair[0], "monetary_amount_eur"))
    ]
    metrics["monetary_match_rate"] = _metric(
        "monetary_match_rate",
        monetary_match_rate(
            [_gold_value(g, "monetary_amount_eur") for g, _ in money_rows],
            [_pred_value(p, "monetary_amount_eur") for _, p in money_rows],
        ),
        money_rows,
        lambda sample: monetary_match_rate(
            [_gold_value(g, "monetary_amount_eur") for g, _ in sample],
            [_pred_value(p, "monetary_amount_eur") for _, p in sample],
        ),
        min_support=min_support,
        n_boot=n_boot,
        boot_seed=boot_seed,
        default_gated=False,
        demotion_reason="monetary_sparse_report_only",
    )

    dedup_rows = [
        pair for pair in pairs
        if _row_year(pair[0], gold=True) is not None and _row_geo(pair[0], gold=True) is not None
    ]
    count_error = geoyear_count_error(
        [g for g, _ in dedup_rows],
        [p for _, p in dedup_rows],
    )
    metrics["dedup_geoyear_count_error"] = _metric(
        "dedup_geoyear_count_error",
        count_error,
        dedup_rows,
        lambda sample: geoyear_count_error(
            [g for g, _ in sample],
            [p for _, p in sample],
        ),
        min_support=min_support,
        n_boot=n_boot,
        boot_seed=boot_seed,
        default_gated=True,
    )

    gold_groups = [_group_value(g, idx, gold=True) for idx, (g, _) in enumerate(pairs)]
    pred_groups = [_group_value(p, idx, gold=False) for idx, (_, p) in enumerate(pairs)]
    b_p, b_r, b_f1 = bcubed_prf(gold_groups, pred_groups)
    metrics["dedup_bcubed_f1"] = _metric(
        "dedup_bcubed_f1",
        b_f1,
        pairs,
        lambda sample: bcubed_prf(
            [_group_value(g, idx, gold=True) for idx, (g, _) in enumerate(sample)],
            [_group_value(p, idx, gold=False) for idx, (_, p) in enumerate(sample)],
        )[2],
        min_support=min_support,
        n_boot=n_boot,
        boot_seed=boot_seed,
        default_gated=False,
        demotion_reason="dedup_diagnostic_report_only",
    )
    metrics["dedup_bcubed_f1"]["precision"] = b_p
    metrics["dedup_bcubed_f1"]["recall"] = b_r

    metrics["summary_rouge_l"] = {
        "value": None,
        "ci_lo": None,
        "ci_hi": None,
        "support": 0,
        "gated": False,
        "gate_threshold": None,
        "demotion_reason": "summary_report_only",
        "reason": "rouge_score not installed",
    }
    metrics["llm_confidence_ece"] = _confidence_ece_metric(pairs)
    return metrics


def per_article_scores(golden_rows: list[dict], prediction_rows: list[dict], *, partition: str = "TEST") -> list[dict]:
    pairs = _aligned_pairs(_filter_partition(golden_rows, partition), prediction_rows)
    rows = []
    for gold, pred in pairs:
        operator_gold = _as_set(_gold_value(gold, "operators"))
        operator_pred = _as_set(_pred_value(pred, "operators"))
        if not operator_gold and not operator_pred:
            operators_f1 = 1.0
        else:
            _, _, operators_f1 = set_micro_prf([operator_gold], [operator_pred])
        rail_gold = _as_set(_gold_value(gold, "rail_lines"))
        rail_pred = _as_set(_pred_value(pred, "rail_lines"))
        rail_recall = len(rail_gold & rail_pred) / len(rail_gold) if rail_gold else 1.0
        matches = {
            "is_rail_related_match": _match(_gold_value(gold, "is_rail_related"), _pred_value(pred, "is_rail_related")),
            "event_superclass_match": float(to_superclass(_gold_value(gold, "event_type")) == to_superclass(_pred_value(pred, "event_type"))),
            "event_10way_match": _match(_gold_value(gold, "event_type"), _pred_value(pred, "event_type")),
            "sentiment_match": _match(_gold_value(gold, "sentiment"), _pred_value(pred, "sentiment")),
            "country_match": _match(_gold_value(gold, "country"), _pred_value(pred, "country")),
            "language_match": _match(_gold_value(gold, "language"), _pred_value(pred, "language")),
            "monetary_match": float(_row_money_match(gold, pred)),
            "operators_f1": operators_f1,
            "rail_lines_recall": rail_recall,
            "dup_group_match": _match(_group_value(gold, 0, gold=True), _group_value(pred, 0, gold=False)),
        }
        present = [
            value for key, value in matches.items()
            if key not in {"operators_f1", "rail_lines_recall"} or not _is_null(value)
        ]
        rows.append({
            "article_id": str(gold["article_id"]),
            "partition": str(gold.get("partition") or ""),
            "language_gold": _gold_value(gold, "language"),
            **matches,
            "overall_score": float(np.mean(present)) if present else 0.0,
        })
    return sorted(rows, key=lambda row: row["article_id"])


def alignment_counts(golden_rows: list[dict], prediction_rows: list[dict], *, partition: str = "TEST") -> dict:
    filtered = _filter_partition(golden_rows, partition)
    all_gold_ids = {str(row["article_id"]) for row in golden_rows if not _is_null(row.get("article_id"))}
    filtered_ids = {str(row["article_id"]) for row in filtered if not _is_null(row.get("article_id"))}
    pred_ids = {str(row["article_id"]) for row in prediction_rows if not _is_null(row.get("article_id"))}
    return {
        "matched": len(filtered_ids & pred_ids),
        "gold_only": len(filtered_ids - pred_ids),
        "pred_only": len(pred_ids - all_gold_ids),
    }


def _metric(
    name: str,
    value: float,
    rows: list[tuple[dict, dict]],
    scorer: Callable[[list[tuple[dict, dict]]], float],
    *,
    min_support: int,
    n_boot: int,
    boot_seed: int,
    default_gated: bool,
    support: int | None = None,
    demotion_reason: str | None = None,
) -> dict:
    support = len(rows) if support is None else support
    gated = bool(default_gated and support >= min_support)
    reason = demotion_reason
    if default_gated and support < min_support:
        gated = False
        reason = "support<30"
    elif not default_gated and reason is None:
        reason = "report_only"
    ci_lo, ci_hi = _bootstrap_rows(rows, scorer, n_boot=n_boot, seed=boot_seed)
    return {
        "value": _json_float(value),
        "ci_lo": _json_float(ci_lo),
        "ci_hi": _json_float(ci_hi),
        "support": support,
        "gated": gated,
        "gate_threshold": DEFAULT_THRESHOLDS.get(name),
        "demotion_reason": None if gated else reason,
        "absolute_pass": None,
        "regression": None,
    }


def _bootstrap_rows(
    rows: list[tuple[dict, dict]],
    scorer: Callable[[list[tuple[dict, dict]]], float],
    *,
    n_boot: int,
    seed: int,
) -> tuple[float | None, float | None]:
    if not rows:
        return None, None

    class RowMetric:
        n_items = len(rows)

        def __call__(self, indices: Iterable[int]) -> float:
            sample = [rows[int(idx)] for idx in indices]
            return scorer(sample)

    return bootstrap_ci(RowMetric(), n_boot=n_boot, seed=seed)


def _aligned_pairs(golden_rows: list[dict], prediction_rows: list[dict]) -> list[tuple[dict, dict]]:
    predictions = {
        str(row["article_id"]): row
        for row in prediction_rows
        if "article_id" in row and not _is_null(row["article_id"])
    }
    pairs = []
    for gold in sorted(golden_rows, key=lambda row: str(row["article_id"])):
        article_id = str(gold["article_id"])
        if article_id in predictions:
            pairs.append((gold, predictions[article_id]))
    return pairs


def _filter_partition(rows: list[dict], partition: str | None) -> list[dict]:
    if partition is None or str(partition).upper() == "ALL":
        return list(rows)
    target = str(partition).upper()
    return [row for row in rows if str(row.get("partition") or "").upper() == target]


def _gold_value(row: dict, field: str):
    if f"{field}_gold" in row:
        return _none_if_null(row[f"{field}_gold"])
    if field in row:
        return _none_if_null(row[field])
    if field == "language" and "language_gold" in row:
        return _none_if_null(row["language_gold"])
    return None


def _pred_value(row: dict, field: str):
    if field in row:
        return _none_if_null(row[field])
    if field == "language" and "language_detected_code" in row:
        return _none_if_null(row["language_detected_code"])
    return None


def _none_if_null(value):
    return None if _is_null(value) else value


def _is_null(value) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict, np.ndarray)):
        return False
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _json_float(value):
    if value is None:
        return None
    return float(value)


def _as_set(value) -> set[str]:
    if _is_null(value):
        return set()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return set()
        if text.startswith("[") and text.endswith("]"):
            text = text.strip("[]")
        parts = [part.strip().strip("'\"") for part in text.replace("|", ",").split(",")]
        return {part for part in parts if part}
    if isinstance(value, np.ndarray):
        return {str(item) for item in value.tolist() if not _is_null(item) and str(item)}
    if isinstance(value, (list, tuple, set)):
        return {str(item) for item in value if not _is_null(item) and str(item)}
    return {str(value)}


def _money_match(gold_amt, pred_amt, *, rel_tol=0.01) -> bool:
    if _is_null(gold_amt):
        return _is_null(pred_amt)
    if _is_null(pred_amt):
        return False
    gold_value = float(gold_amt)
    pred_value = float(pred_amt)
    tolerance = abs(gold_value) * rel_tol
    return abs(gold_value - pred_value) <= tolerance


def _row_money_match(gold: dict, pred: dict) -> bool:
    return _money_match(_gold_value(gold, "monetary_amount_eur"), _pred_value(pred, "monetary_amount_eur"))


def _match(gold_value, pred_value) -> float:
    if _is_null(gold_value) and _is_null(pred_value):
        return 1.0
    return float(gold_value == pred_value)


def _group_members(groups: list[str]) -> dict[str, set[int]]:
    members: dict[str, set[int]] = defaultdict(set)
    for idx, group in enumerate(groups):
        members[str(group)].add(idx)
    return members


def _group_value(row: dict, idx: int, *, gold: bool) -> str:
    if gold:
        for key in ("dup_group_id_gold", "dup_group_id", "cross_lingual_dedup_id_gold"):
            if key in row and not _is_null(row[key]):
                return str(row[key])
    else:
        for key in ("cross_lingual_dedup_id", "dup_group_id", "cluster_id"):
            if key in row and not _is_null(row[key]):
                return str(row[key])
    if "article_id" in row and not _is_null(row["article_id"]):
        return str(row["article_id"])
    return f"row-{idx}"


def _canonical_counts(rows: list[dict], *, gold: bool) -> Counter:
    groups_by_geoyear: dict[tuple[str, int], set[str]] = defaultdict(set)
    for idx, row in enumerate(rows):
        geo = _row_geo(row, gold=gold)
        year = _row_year(row, gold=gold)
        if geo is None or year is None:
            continue
        groups_by_geoyear[(geo, year)].add(_group_value(row, idx, gold=gold))
    return Counter({key: len(groups) for key, groups in groups_by_geoyear.items()})


def _row_geo(row: dict, *, gold: bool) -> str | None:
    keys = ("geo_gold", "country_gold", "geo", "country") if gold else ("geo", "country")
    for key in keys:
        if key in row and not _is_null(row[key]):
            return str(row[key])
    return None


def _row_year(row: dict, *, gold: bool) -> int | None:
    keys = (
        ("published_year_gold", "year_gold", "published_year", "year", "published_date")
        if gold else
        ("published_year", "year", "published_date")
    )
    for key in keys:
        if key in row and not _is_null(row[key]):
            value = row[key]
            if key == "published_date":
                return _year_from_date(value)
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def _year_from_date(value) -> int | None:
    text = str(value or "").strip()
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, fmt).year
        except ValueError:
            continue
    return None


def _confidence_ece_metric(pairs: list[tuple[dict, dict]]) -> dict:
    items = []
    for gold, pred in pairs:
        confidence = _pred_value(pred, "confidence")
        if _is_null(confidence):
            continue
        correct = _match(_gold_value(gold, "is_rail_related"), _pred_value(pred, "is_rail_related"))
        items.append((float(confidence), float(correct)))
    value = _expected_calibration_error(items) if items else None
    return {
        "value": _json_float(value),
        "ci_lo": None,
        "ci_hi": None,
        "support": len(items),
        "gated": False,
        "gate_threshold": None,
        "demotion_reason": "calibration_report_only",
    }


def _expected_calibration_error(items: list[tuple[float, float]], *, n_bins: int = 10) -> float:
    if not items:
        return 0.0
    total = len(items)
    error = 0.0
    for bin_idx in range(n_bins):
        lo = bin_idx / n_bins
        hi = (bin_idx + 1) / n_bins
        in_bin = [
            (confidence, correct) for confidence, correct in items
            if (lo <= confidence < hi) or (bin_idx == n_bins - 1 and confidence == hi)
        ]
        if not in_bin:
            continue
        mean_conf = float(np.mean([confidence for confidence, _ in in_bin]))
        mean_acc = float(np.mean([correct for _, correct in in_bin]))
        error += (len(in_bin) / total) * abs(mean_acc - mean_conf)
    return error
