# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
"""Layout signals from measured evidence only.

Everything here is **signal**, never cause. Overlap counts, file-size stats and
collapse-shape heuristics are inputs to a human review, never verdicts.
Missing data is reported as `null`/`not_measurable`, never as a guessed number
(PyIceberg 0.12 exposes no public per-file stats API — we stat Parquet footers).
"""
from __future__ import annotations
import statistics
from dataclasses import dataclass, asdict
from pathlib import Path

import pyarrow.parquet as pq
import pyarrow as pa

NOT_MEASURABLE = None


def _decode(v):
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", "ignore")
    return v


@dataclass
class FileStat:
    path: str
    rows: int
    bytes: int
    ts_min: float | None
    ts_max: float | None
    cat_min: str | None
    cat_max: str | None


def _row_group_range(col_stats, kind):
    if col_stats is None:
        return None, None
    try:
        lo, hi = col_stats.min, col_stats.max
        return lo, hi
    except Exception:
        return None, None


def file_stats(parquet_path: Path) -> FileStat | None:
    try:
        md = pq.read_metadata(parquet_path)
    except Exception:
        return None
    rows = md.num_rows
    size = parquet_path.stat().st_size
    names = [md.schema.column(i).name for i in range(md.num_columns)]
    col_by_name = {md.schema.column(i).name: i for i in range(md.num_columns)}
    ts_min = ts_max = cat_min = cat_max = None
    try:
        mins, maxs = [], []
        if "ts" in col_by_name:
            for i in range(md.num_row_groups):
                st = md.row_group(i).column(col_by_name["ts"]).statistics
                lo, hi = _row_group_range(st, "int")
                if lo is not None:
                    mins.append(lo); maxs.append(hi)
            ts_min, ts_max = (min(mins), max(maxs)) if mins else (None, None)
        mins, maxs = [], []
        if "category" in col_by_name:
            for i in range(md.num_row_groups):
                st = md.row_group(i).column(col_by_name["category"]).statistics
                lo, hi = _row_group_range(st, "str")
                if lo is not None:
                    mins.append(str(_decode(lo))); maxs.append(str(_decode(hi)))
            cat_min, cat_max = (min(mins), max(maxs)) if mins else (None, None)
    except Exception:
        pass  # missing stats are reported as-is, not fabricated
    return FileStat(path=str(parquet_path), rows=rows, bytes=size,
                    ts_min=ts_min, ts_max=ts_max, cat_min=cat_min, cat_max=cat_max)


def layout_signals(warehouse: str | Path, table_name: str) -> dict:
    root = Path(warehouse) / "spike" / table_name
    files = sorted(root.rglob("*.parquet")) if root.exists() else []
    stats = [s for s in (file_stats(f) for f in files) if s is not None]
    n = len(stats)
    bytes_total = sum(s.bytes for s in stats)
    sizes = [s.bytes for s in stats]
    cv = (statistics.stdev(sizes) / statistics.mean(sizes)) if n > 1 and statistics.mean(sizes) else 0.0
    rows_total = sum(s.rows for s in stats)
    ts_lo = min((s.ts_min for s in stats if s.ts_min is not None), default=None)
    ts_hi = max((s.ts_max for s in stats if s.ts_max is not None), default=None)
    signals = {
        "table": table_name,
        "signal_type": "measured_filesystem",   # honest provenance
        "files": n,
        "rows": rows_total,
        "bytes_total": bytes_total,
        "size_cv": round(cv, 3),
        "size_min_bytes": min(sizes) if sizes else 0,
        "size_max_bytes": max(sizes) if sizes else 0,
        "mean_file_bytes": (bytes_total // n) if n else 0,
        "many_small_files": bool(n >= 8 and cv < 0.5 and (bytes_total / n) < 4_000_000),
        "ts_min": ts_lo,
        "ts_max": ts_hi,
        "note": "'many_small_files' is a heuristic over file count/size only; it proves no performance claim.",
    }
    return signals


def predicate_overlap(files: list[FileStat], column: str, literal) -> float | None:
    """Fraction of files whose [min,max] range contains the literal.

    Returns None (not_measurable) if stats for the column are missing — never a guessed number.
    Low ratio = good pruning signal for equality predicates; 1.0 = no pruning at all.
    """
    if not files:
        return None
    ratios = []
    for s in files:
        lo, hi = (s.cat_min, s.cat_max) if column == "category" else ((s.ts_min, s.ts_max) if column == "ts" else (None, None))
        if lo is None or hi is None:
            return None
        try:
            if column == "category":
                contains = str(lo) <= str(literal) <= str(hi)
            else:
                contains = float(lo) <= float(literal) <= float(hi)
        except (TypeError, ValueError):
            contains = False
        ratios.append(contains)
    return round(sum(ratios) / len(ratios), 3) if ratios else None


def all_files(warehouse: str | Path, table_name: str) -> list[FileStat]:
    root = Path(warehouse) / "spike" / table_name
    if not root.exists():
        return []
    out = []
    for f in sorted(root.rglob("*.parquet")):
        s = file_stats(f)
        if s is not None:
            out.append(s)
    return out
