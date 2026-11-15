# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0
import statistics
import platform

import pytest
import pyarrow as pa
import pyarrow.parquet as pq

from iceberg_guard import signals
from iceberg_guard.cpp_adapter import cpp_binary, run_aggregate

pytestmark = pytest.mark.skipif(platform.system() != "Linux" or cpp_binary() is None,
                                reason="cpp core is Linux-only; build first (see docs/m4-cpp.md)")


def _write(path, ts):
    import pandas as pd
    df = pd.DataFrame({
        "ts": ts,
        "category": ["growth"] * len(ts),
        "tenant": ["tenant-000"] * len(ts),
        "join_key": list(range(len(ts))),
        "measure": [1.0 + i * 0.01 for i in range(len(ts))],
    })
    pq.write_table(pa.Table.from_pandas(df), path)


def test_cpp_agg_matches_python_reference(tmp_path):
    d = tmp_path / "spike" / "t1"
    d.mkdir(parents=True)
    ranges = [(0, 50), (50, 120), (120, 300), (300, 310)]
    sizes = []
    for i, (lo, hi) in enumerate(ranges):
        _write(d / f"part-{i}.parquet", list(range(lo, hi)))

    files_stats = signals.all_files(tmp_path, "t1")
    cpp = run_aggregate(files_stats)
    assert cpp is not None

    ref_rows = sum(s.rows for s in files_stats)
    ref_bytes = sum(s.bytes for s in files_stats)
    assert cpp["files"] == len(files_stats)
    assert cpp["rows"] == ref_rows
    assert cpp["bytes"] == ref_bytes
    assert cpp["with_stats"] == len(files_stats)

    ref_sizes = [s.bytes for s in files_stats]
    ref_mean = statistics.fmean(ref_sizes)
    ref_pvar = statistics.pvariance(ref_sizes)     # population variance — matches Welford n-denominator
    ref_mean_extent = (min(s.ts_min for s in files_stats), max(s.ts_max for s in files_stats))

    assert cpp["mean_file_bytes"] == pytest.approx(ref_mean, rel=1e-9)
    assert cpp["variance_bytes"] == pytest.approx(ref_pvar, rel=1e-9)
    assert cpp["stdev_bytes"] == pytest.approx(ref_pvar ** 0.5, rel=1e-9)
    assert cpp["size_cv"] == pytest.approx((ref_pvar ** 0.5) / ref_mean, rel=1e-9)
    assert cpp["bytes_min"] == float(min(ref_sizes))
    assert cpp["bytes_max"] == float(max(ref_sizes))
    assert cpp["ts_min"] == float(ref_mean_extent[0])
    assert cpp["ts_max"] == float(ref_mean_extent[1])


def test_cpp_agg_empty_input(tmp_path):
    assert run_aggregate([]) == {
        "files": 0, "rows": 0, "bytes": 0,
        "mean_file_bytes": 0.0, "variance_bytes": 0.0, "stdev_bytes": 0.0,
        "size_cv": 0.0, "bytes_min": 0.0, "bytes_max": 0.0,
        "ts_min": 0.0, "ts_max": 0.0, "with_stats": 0,
        "provenance": "measured_cpp",
    }
