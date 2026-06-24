#!/usr/bin/env python3
"""Measure the volume of data that passed through the Bronze layer.

Reports, per source and in total: datasets, raw artifacts, on-disk bytes,
decompressed bytes, data rows, and observations. "Observations" is the number
of (key, period) value cells — i.e. how many records the data becomes once the
wide Eurostat tables are unpivoted in Silver — which is the honest big-data
metric for statistical data (bytes under-count it because gzipped TSV is dense).

Usage:
    python scripts/bronze_volume.py output/evidence/bigdata/bronze \
        [--out output/evidence/bigdata/bronze_volume.json]
"""
import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path


def _human(n: int) -> str:
    f = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if f < 1024 or unit == "TB":
            return f"{f:.1f} {unit}"
        f /= 1024


def _group(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def _open(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.suffix == ".gz" \
        else open(path, "rt", encoding="utf-8", errors="replace")


def _decompressed_size(path: Path) -> int:
    if path.suffix == ".gz":
        try:
            with gzip.open(path, "rb") as fh:
                total = 0
                while True:
                    chunk = fh.read(1 << 20)
                    if not chunk:
                        break
                    total += len(chunk)
                return total
        except Exception:
            return path.stat().st_size
    return path.stat().st_size


def _count_tsv(path: Path):
    """Return (data_rows, observations) for a Eurostat TSV.
    observations = data_rows * number of period (year/quarter/month) columns."""
    try:
        with _open(path) as fh:
            header = fh.readline()
            period_cols = max(len(header.split("\t")) - 1, 0)
            rows = sum(1 for line in fh if line.strip())
        return rows, rows * period_cols
    except Exception:
        return 0, 0


def _count_wb_json(path: Path):
    """World Bank series JSON is [pagination, [observation, ...]]."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[1], list):
            n = len(payload[1])
            return n, n
    except Exception:
        pass
    return 0, 0


def measure(root: Path) -> dict:
    stats_root = root / "stats"
    blank = lambda: {"datasets": set(), "artifacts": 0, "bytes_on_disk": 0,
                     "bytes_decompressed": 0, "data_rows": 0, "observations": 0}
    per_source = defaultdict(blank)
    for f in stats_root.rglob("*"):
        if not f.is_file() or f.name.endswith(".meta.json"):
            continue
        rel = f.relative_to(stats_root).parts
        if len(rel) < 2:
            continue
        source, dataset = rel[0], rel[1]
        rec = per_source[source]
        rec["datasets"].add(dataset)
        rec["artifacts"] += 1
        rec["bytes_on_disk"] += f.stat().st_size
        rec["bytes_decompressed"] += _decompressed_size(f)
        if f.name.endswith((".tsv", ".tsv.gz", ".gz")):
            r, o = _count_tsv(f)
        elif f.name.endswith(".json"):
            r, o = _count_wb_json(f)
        else:
            r, o = 0, 0
        rec["data_rows"] += r
        rec["observations"] += o

    sources, tot = {}, defaultdict(int)
    for src, rec in sorted(per_source.items()):
        d = {"datasets": len(rec["datasets"]), "artifacts": rec["artifacts"],
             "bytes_on_disk": rec["bytes_on_disk"], "bytes_decompressed": rec["bytes_decompressed"],
             "data_rows": rec["data_rows"], "observations": rec["observations"]}
        sources[src] = d
        for k, v in d.items():
            tot[k] += v
    return {"bronze_root": str(root), "sources": sources, "total": dict(tot)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("bronze_root")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    report = measure(Path(args.bronze_root))
    t = report["total"]
    print(f"Bronze root: {report['bronze_root']}")
    hdr = f"{'source':<14}{'datasets':>9}{'on-disk':>11}{'decompr.':>11}{'data_rows':>14}{'observations':>16}"
    print(hdr)
    for src, d in report["sources"].items():
        print(f"{src:<14}{d['datasets']:>9}{_human(d['bytes_on_disk']):>11}"
              f"{_human(d['bytes_decompressed']):>11}{_group(d['data_rows']):>14}{_group(d['observations']):>16}")
    print("-" * len(hdr))
    print(f"{'TOTAL':<14}{t['datasets']:>9}{_human(t['bytes_on_disk']):>11}"
          f"{_human(t['bytes_decompressed']):>11}{_group(t['data_rows']):>14}{_group(t['observations']):>16}")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nJSON manifest -> {args.out}")
    return report


if __name__ == "__main__":
    main()
