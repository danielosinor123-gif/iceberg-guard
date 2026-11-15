# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
"""Filesystem-level Iceberg layout evidence — honest when APIs are silent.

PyIceberg 0.12 exposes no public per-file stats API, so we stat Parquet files directly
under the table's data/ tree. This measures layout, not query behaviour.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path


def layout_summary(warehouse: str | Path, table_name: str) -> dict:
    root = Path(warehouse) / "spike" / table_name
    files = sorted(root.rglob("*.parquet")) if root.exists() else []
    total = sum(f.stat().st_size for f in files)
    by_dir: dict[str, int] = defaultdict(int)
    for f in files:
        by_dir[str(f.parent.relative_to(root))] += 1
    return {
        "table": table_name,
        "data_files": len(files),
        "bytes_total": total,
        "bytes_per_file": (total // len(files)) if files else 0,
        "files_per_dir": dict(by_dir),
        "signal_type": "measured_filesystem",
    }
