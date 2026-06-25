"""Spark correlation job (project spec).

Correlates rail investment with every other feature. Computes, per (target,
feature):
  * Pearson r and Spearman rho (rank-based; robust to outliers),
  * pairwise sample size n,
  * two-sided p-values via the Fisher z-transformation.

Targets (investment intensities, derived in-Spark so Gold stays raw):
  rail_investment_pps, _per_capita, _pct_gdp, _per_network_km.

Two analysis modes:
  * levels  (default): target level vs feature levels AND year-over-year deltas;
  * panel   (--panel): Δtarget vs Δfeature only, which removes constant
    cross-country differences (closer to a within-country / causal reading).

    python -m railway_lakehouse.spark_jobs.correlations \
        --input output/evidence/inventory-live-2026-06-23/railway_ml.parquet \
        --out output/evidence/spark-correlations/
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_NAME = "railway-correlations"
DEFAULT_INPUT = "output/evidence/inventory-live-2026-06-23/railway_ml.parquet"
DEFAULT_OUT = "output/evidence/spark-correlations/"
OUTPUT_DIR_NAME = "correlations"
MANIFEST_NAME = "manifest.json"
DEFAULT_TARGET = "rail_investment_pps"
INVESTMENT_FAMILY = {"rail_investment", "rail_investment_pps"}
NON_FEATURE = {"geo", "year", "geo_level"}
NUMERIC_TYPES = {"double", "float", "int", "bigint", "long", "smallint", "tinyint", "decimal"}
MISSING_INPUT_HINT = (
    "run the Gold pipeline first or pass --input to an existing Gold parquet"
)
MISSING_TARGET_HINT = (
    "pass a Gold parquet that contains rail_investment or rail_investment_pps"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _spark_local_path(p: Path) -> str:
    return p.resolve().as_uri()


def _fisher_p(r, n) -> float | None:
    """Two-sided p-value for a correlation via Fisher z (normal approx)."""
    if r is None or n is None or n < 4 or abs(r) >= 1.0:
        return None
    z = math.atanh(r) * math.sqrt(n - 3)
    return math.erfc(abs(z) / math.sqrt(2.0))


def build_session(master: str):
    from pyspark.sql import SparkSession

    # Spark 4.x ANSI mode makes corr() raise DIVIDE_BY_ZERO on zero-variance
    # columns; disable so corr() returns NULL instead (those pairs are dropped).
    return (
        SparkSession.builder.appName(APP_NAME)
        .master(master)
        .config("spark.sql.ansi.enabled", "false")
        .getOrCreate()
    )


def _mode_suffix(*, by_country: bool, panel: bool) -> str:
    scope = "by_country" if by_country else "pooled"
    design = "panel" if panel else "levels"
    return f"_{scope}_{design}"


def _output_name(*, by_country: bool, panel: bool) -> str:
    return f"{OUTPUT_DIR_NAME}{_mode_suffix(by_country=by_country, panel=panel)}"


def _manifest_name(*, by_country: bool, panel: bool) -> str:
    return f"manifest{_mode_suffix(by_country=by_country, panel=panel)}.json"


def _rank_partition_cols(label_col: str, *, by_country: bool) -> list[str]:
    return (["geo"] if by_country else []) + [label_col]


def _validate_input_exists(input_file: Path) -> None:
    if not input_file.exists():
        raise FileNotFoundError(
            f"Gold parquet not found: {input_file.as_posix()}. "
            f"{MISSING_INPUT_HINT}."
        )


def _raise_if_empty(label: str, count: int, input_file: Path) -> None:
    if count == 0:
        raise ValueError(
            f"{label} has 0 rows for {input_file.as_posix()}; no correlation "
            "evidence can be written."
        )


def run_correlations(
    spark: Any,
    input_path,
    out_dir,
    *,
    target: str = DEFAULT_TARGET,
    min_obs: int = 30,
    country_only: bool = True,
    panel: bool = False,
    by_country: bool = False,
    command: str | None = None,
) -> dict[str, Any]:
    from pyspark.sql import functions as F, Window

    started_at = _utc_now()
    started = time.perf_counter()
    input_file = Path(input_path)
    out_root = Path(out_dir)
    _validate_input_exists(input_file)
    out_root.mkdir(parents=True, exist_ok=True)

    df = spark.read.parquet(_spark_local_path(input_file))
    _raise_if_empty("Input Gold parquet", int(df.count()), input_file)
    if country_only and "geo_level" in df.columns:
        df = df.filter(F.col("geo_level") == "country")
        _raise_if_empty("Country-only Gold selection", int(df.count()), input_file)

    cols = set(df.columns)
    numeric = [c for c, t in df.dtypes
               if c not in NON_FEATURE and t.split("(")[0] in NUMERIC_TYPES]

    # investment-intensity targets (derived in-Spark; ANSI off -> /0 = NULL)
    if {"rail_investment_pps", "population_total"} <= cols:
        df = df.withColumn("rail_investment_per_capita",
                           F.col("rail_investment_pps") / F.col("population_total") * F.lit(1_000_000.0))
    if {"rail_investment", "gdp_current_meur"} <= cols:
        df = df.withColumn("rail_investment_pct_gdp",
                           F.col("rail_investment") / F.col("gdp_current_meur") * F.lit(100.0))
    if {"rail_investment_pps", "rail_network_length_km"} <= cols:
        df = df.withColumn("rail_investment_per_network_km",
                           F.col("rail_investment_pps") / F.col("rail_network_length_km"))
    target_candidates = [target, "rail_investment_pps", "rail_investment",
                         "rail_investment_per_capita", "rail_investment_pct_gdp",
                         "rail_investment_per_network_km"]
    targets = [t for t in dict.fromkeys(target_candidates) if t in set(df.columns)]
    if not targets:
        raise ValueError(
            f"No investment target columns found in {input_file.as_posix()}. "
            f"{MISSING_TARGET_HINT}."
        )

    # year-over-year deltas (consecutive years only)
    w = Window.partitionBy("geo").orderBy("year")
    prev_year = F.lag("year").over(w)
    feature_levels = [c for c in numeric if c not in INVESTMENT_FAMILY]
    delta_of = {}
    for c in feature_levels:
        d = f"{c}__delta"
        df = df.withColumn(d, F.when(F.col("year") - prev_year == 1,
                                     F.col(c) - F.lag(c).over(w)))
        delta_of[c] = d
    # target deltas (for panel mode)
    target_delta = {}
    for t in targets:
        d = f"{t}__delta"
        df = df.withColumn(d, F.when(F.col("year") - prev_year == 1,
                                     F.col(t) - F.lag(t).over(w)))
        target_delta[t] = d

    if panel:
        feature_cols = list(delta_of.values())
        target_cols = list(target_delta.values())
    else:
        feature_cols = feature_levels + list(delta_of.values())
        target_cols = targets
    if not feature_cols:
        raise ValueError(
            f"No numeric non-investment feature columns found in "
            f"{input_file.as_posix()}."
        )
    if not target_cols:
        raise ValueError(
            f"No target columns available for correlation in "
            f"{input_file.as_posix()}."
        )

    def _melt(frame, columns, name_col, val_col):
        pairs = ", ".join(f"'{c}', CAST(`{c}` AS DOUBLE)" for c in columns)
        long = frame.select("geo", "year",
                            F.expr(f"stack({len(columns)}, {pairs}) as ({name_col}, {val_col})"))
        return long.where(F.col(val_col).isNotNull())

    feat_long = _melt(df, feature_cols, "feat", "fval")
    feat_long = feat_long.withColumn(
        "frank",
        F.percent_rank().over(
            Window.partitionBy(*_rank_partition_cols("feat", by_country=by_country))
            .orderBy("fval")
        ),
    )
    tgt_long = _melt(df, target_cols, "tgt", "tval")
    tgt_long = tgt_long.withColumn(
        "trank",
        F.percent_rank().over(
            Window.partitionBy(*_rank_partition_cols("tgt", by_country=by_country))
            .orderBy("tval")
        ),
    )

    joined = tgt_long.join(feat_long, ["geo", "year"])
    _raise_if_empty("Joined target-feature pairs", int(joined.count()), input_file)
    group_cols = (["geo"] if by_country else []) + ["tgt", "feat"]
    stats = (joined.groupBy(*group_cols)
             .agg(F.corr("tval", "fval").alias("pearson_r"),
                  F.corr("trank", "frank").alias("spearman_r"),
                  F.count(F.lit(1)).alias("n")))

    pdf = stats.toPandas()
    if not pdf.empty:
        pdf["target"] = pdf["tgt"].str.replace("__delta", "", regex=False)
        pdf["kind"] = pdf["feat"].apply(lambda c: "delta" if c.endswith("__delta") else "level")
        pdf["feature"] = pdf["feat"].apply(lambda c: c[:-7] if c.endswith("__delta") else c)
        pdf["p_pearson"] = [_fisher_p(r, n) for r, n in zip(pdf["pearson_r"], pdf["n"])]
        pdf["p_spearman"] = [_fisher_p(r, n) for r, n in zip(pdf["spearman_r"], pdf["n"])]
        pdf = pdf[(pdf["n"] >= min_obs) & pdf["pearson_r"].notna()].copy()
        pdf["abs_r"] = pdf["pearson_r"].abs()
        pdf = pdf.sort_values(["target", "abs_r"], ascending=[True, False])
    if pdf.empty:
        raise ValueError(
            f"No correlation pairs met min_obs={min_obs} for "
            f"{input_file.as_posix()}."
        )
    keep = (["geo"] if by_country else []) + ["target", "feature", "kind",
            "pearson_r", "p_pearson", "spearman_r", "p_spearman", "n"]
    pdf = pdf[keep]

    suffix = _mode_suffix(by_country=by_country, panel=panel)
    output_path = out_root / _output_name(by_country=by_country, panel=panel)
    manifest_path = out_root / _manifest_name(by_country=by_country, panel=panel)
    csv_path = out_root / f"correlations{suffix}.csv"
    pdf.to_csv(csv_path, index=False)
    spark.createDataFrame(pdf).write.mode("overwrite").parquet(_spark_local_path(output_path))

    # for by-country, surface the strongest *significant* pairs across countries
    view = pdf
    if by_country and not pdf.empty:
        view = pdf[pdf["p_pearson"].notna() & (pdf["p_pearson"] < 0.05)]
    top_by_target = {}
    for tgt in view["target"].unique() if not view.empty else []:
        sub = view[view["target"] == tgt].head(15)
        top_by_target[tgt] = [
            {**({"geo": r.geo} if by_country else {}),
             "feature": r.feature, "kind": r.kind,
             "pearson_r": round(r.pearson_r, 4),
             "p_pearson": None if r.p_pearson is None else round(r.p_pearson, 4),
             "spearman_r": None if r.spearman_r is None else round(r.spearman_r, 4),
             "n": int(r.n)}
            for r in sub.itertuples()
        ]

    manifest = {
        "command": command or "run_correlations",
        "spark_version": str(spark.version),
        "ansi_enabled": False,
        "mode": ("panel (delta vs delta)" if panel else "levels + deltas")
                + (" | per-country" if by_country else " | pooled"),
        "by_country": by_country,
        "targets": targets,
        "country_only": country_only,
        "min_obs": min_obs,
        "input_path": input_file.as_posix(),
        "n_features": len(feature_cols),
        "n_rows_reported": int(len(pdf)),
        "output_path": output_path.as_posix(),
        "csv_path": csv_path.as_posix(),
        "top_by_target": top_by_target,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "status": "passed",
        "started_at_utc": started_at,
        "finished_at_utc": _utc_now(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return manifest


def _parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=DEFAULT_INPUT)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--target", default=DEFAULT_TARGET)
    p.add_argument("--min-obs", type=int, default=30)
    p.add_argument("--all-levels", action="store_true",
                   help="include regions/aggregates, not only country rows")
    p.add_argument("--panel", action="store_true",
                   help="correlate delta-target vs delta-features (within-country)")
    p.add_argument("--by-country", dest="by_country", action="store_true",
                   help="compute correlations separately per country (geo)")
    p.add_argument("--master", default="local[*]")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    spark = None
    try:
        spark = build_session(args.master)
        manifest = run_correlations(
            spark, args.input, args.out,
            target=args.target, min_obs=args.min_obs,
            country_only=not args.all_levels, panel=args.panel,
            by_country=args.by_country,
            command="python -m railway_lakehouse.spark_jobs.correlations",
        )
        print(f"Mode: {manifest['mode']}")
        for tgt, rows in manifest["top_by_target"].items():
            print(f"\n=== Top correlations with {tgt} ===")
            print(f"  {'pearson':>8} {'p':>8} {'spearman':>9}  feature")
            for t in rows[:12]:
                sp = "  n/a " if t["spearman_r"] is None else f"{t['spearman_r']:+.3f}"
                pp = " n/a " if t["p_pearson"] is None else f"{t['p_pearson']:.3f}"
                geo = (t["geo"] + " ") if "geo" in t else ""
                print(f"  {t['pearson_r']:+.3f} {pp:>8} {sp:>9}  {geo}[{t['kind']:5}] {t['feature']} (n={t['n']})")
        print(f"\nCSV: {manifest['csv_path']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
