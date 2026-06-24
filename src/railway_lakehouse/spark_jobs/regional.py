"""Spark regional rail analysis (NUTS regions).

Uses the region-level rows of the Gold matrix (rail_network_length_km,
rail_electrified_km from tran_r_net) to produce:

  1. Descriptives  -> per region-year: electrification share + NUTS level;
     plus a ranking of NUTS2 regions by mean network length / electrification.
  2. Inequality    -> per country-year across its NUTS2 regions: coefficient of
     variation (std/mean) of network length and electrified length — how
     unevenly rail is distributed inside each country — and a pooled correlation
     between national rail investment (PPS) and that within-country disparity.

    python -m railway_lakehouse.spark_jobs.regional \
        --input output/evidence/bigdata/railway_ml.parquet \
        --out output/evidence/spark-regional/
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

APP_NAME = "railway-regional"
DEFAULT_INPUT = "output/evidence/bigdata/railway_ml.parquet"
DEFAULT_OUT = "output/evidence/spark-regional/"
MANIFEST_NAME = "manifest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _spark_local_path(p: Path) -> str:
    return p.resolve().as_uri()


def _fisher_p(r, n):
    if r is None or n is None or n < 4 or abs(r) >= 1.0:
        return None
    z = math.atanh(r) * math.sqrt(n - 3)
    return math.erfc(abs(z) / math.sqrt(2.0))


def build_session(master: str):
    from pyspark.sql import SparkSession

    return (SparkSession.builder.appName(APP_NAME).master(master)
            .config("spark.sql.ansi.enabled", "false").getOrCreate())


def run_regional(spark, input_path, out_dir, *, min_regions=3, command=None):
    from pyspark.sql import functions as F

    started = time.perf_counter()
    input_file = Path(input_path)
    out_root = Path(out_dir)
    if not input_file.exists():
        raise FileNotFoundError(f"Gold parquet not found: {input_file.as_posix()}")
    out_root.mkdir(parents=True, exist_ok=True)

    full = spark.read.parquet(_spark_local_path(input_file))
    NET, ELC = "rail_network_length_km", "rail_electrified_km"

    # ---- 1) regional descriptives ----
    reg = full.filter(F.col("geo_level") == "region")
    reg = (reg.withColumn("country_code", F.substring("geo", 1, 2))
              .withColumn("nuts_level", F.length("geo") - 2)  # 1=NUTS1,2=NUTS2,3=NUTS3
              .withColumn("electrification_share",
                          F.when(F.col(NET) > 0, F.col(ELC) / F.col(NET))))
    desc = reg.select("geo", "country_code", "nuts_level", "year",
                      NET, ELC, "electrification_share")
    desc.write.mode("overwrite").parquet(_spark_local_path(out_root / "descriptives"))
    desc.toPandas().to_csv(out_root / "regional_descriptives.csv", index=False)

    # ranking of NUTS2 regions by mean network length & electrification share
    nuts2 = reg.filter(F.col("nuts_level") == 2)
    rank = (nuts2.groupBy("geo", "country_code")
                 .agg(F.avg(NET).alias("mean_network_km"),
                      F.avg("electrification_share").alias("mean_elec_share"),
                      F.count(F.lit(1)).alias("years")))
    rpd = rank.toPandas()
    top_net = (rpd.dropna(subset=["mean_network_km"])
                  .sort_values("mean_network_km", ascending=False).head(10))
    top_elec = (rpd.dropna(subset=["mean_elec_share"])
                   .sort_values("mean_elec_share", ascending=False).head(10))

    # ---- 2) within-country inequality (CV across NUTS2 regions per year) ----
    ineq = (nuts2.groupBy("country_code", "year")
                 .agg(F.count(F.lit(1)).alias("n_regions"),
                      F.avg(NET).alias("mean_network"),
                      F.stddev(NET).alias("std_network"),
                      F.avg(ELC).alias("mean_elec"),
                      F.stddev(ELC).alias("std_elec"))
                 .filter(F.col("n_regions") >= min_regions))
    ineq = (ineq.withColumn("cv_network",
                            F.when(F.col("mean_network") > 0,
                                   F.col("std_network") / F.col("mean_network")))
                .withColumn("cv_elec",
                            F.when(F.col("mean_elec") > 0,
                                   F.col("std_elec") / F.col("mean_elec"))))
    ineq.write.mode("overwrite").parquet(_spark_local_path(out_root / "inequality"))
    ineq.toPandas().to_csv(out_root / "regional_inequality.csv", index=False)

    # average disparity per country (which countries have the most uneven rail)
    cv_by_country = (ineq.groupBy("country_code")
                         .agg(F.avg("cv_network").alias("avg_cv_network"))
                         .toPandas().dropna()
                         .sort_values("avg_cv_network", ascending=False))

    # ---- correlation: national rail investment (PPS) vs within-country disparity ----
    invest_col = "rail_investment_pps" if "rail_investment_pps" in full.columns else "rail_investment"
    nat = (full.filter(F.col("geo_level") == "country")
               .select(F.col("geo").alias("country_code"), "year",
                       F.col(invest_col).alias("invest")))
    joined = ineq.join(nat, ["country_code", "year"]).select("cv_network", "invest")
    row = joined.agg(F.corr("cv_network", "invest").alias("r"),
                     F.count(F.when(F.col("cv_network").isNotNull()
                                    & F.col("invest").isNotNull(), 1)).alias("n")).collect()[0]
    inv_r = None if row["r"] is None else float(row["r"])
    inv_n = int(row["n"])

    manifest = {
        "command": command or "run_regional",
        "spark_version": str(spark.version),
        "ansi_enabled": False,
        "input_path": input_file.as_posix(),
        "region_rows": int(reg.count()),
        "nuts2_regions": int(rank.count()),
        "top_nuts2_by_network_km": [
            {"geo": r.geo, "country": r.country_code,
             "mean_network_km": round(r.mean_network_km, 1)} for r in top_net.itertuples()],
        "top_nuts2_by_electrification": [
            {"geo": r.geo, "country": r.country_code,
             "mean_elec_share": round(r.mean_elec_share, 3)} for r in top_elec.itertuples()],
        "most_unequal_countries": [
            {"country": r.country_code, "avg_cv_network": round(r.avg_cv_network, 3)}
            for r in cv_by_country.head(10).itertuples()],
        "least_unequal_countries": [
            {"country": r.country_code, "avg_cv_network": round(r.avg_cv_network, 3)}
            for r in cv_by_country.tail(5).itertuples()],
        "investment_vs_disparity": {
            "target": invest_col, "metric": "cv_network",
            "pearson_r": None if inv_r is None else round(inv_r, 4),
            "p_value": None if _fisher_p(inv_r, inv_n) is None else round(_fisher_p(inv_r, inv_n), 4),
            "n": inv_n,
        },
        "outputs": {
            "descriptives_csv": (out_root / "regional_descriptives.csv").as_posix(),
            "inequality_csv": (out_root / "regional_inequality.csv").as_posix(),
        },
        "duration_seconds": round(time.perf_counter() - started, 3),
        "status": "passed",
        "generated_at_utc": _utc_now(),
    }
    (out_root / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def _parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=DEFAULT_INPUT)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--min-regions", type=int, default=3)
    p.add_argument("--master", default="local[*]")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    spark = None
    try:
        spark = build_session(args.master)
        m = run_regional(spark, args.input, args.out,
                         min_regions=args.min_regions,
                         command="python -m railway_lakehouse.spark_jobs.regional")
        print(f"Region rows: {m['region_rows']} | NUTS2 regions: {m['nuts2_regions']}")
        print("\nTop NUTS2 by mean network length (km):")
        for r in m["top_nuts2_by_network_km"][:8]:
            print(f"  {r['geo']:6} {r['country']}  {r['mean_network_km']}")
        print("\nMost UNEVEN rail distribution (avg CV of network across regions):")
        for r in m["most_unequal_countries"][:8]:
            print(f"  {r['country']}  CV={r['avg_cv_network']}")
        iv = m["investment_vs_disparity"]
        print(f"\nNational investment ({iv['target']}) vs within-country disparity (cv_network):")
        print(f"  pearson r={iv['pearson_r']}  p={iv['p_value']}  n={iv['n']}")
        print(f"\nCSVs: {m['outputs']['descriptives_csv']}  |  {m['outputs']['inequality_csv']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
