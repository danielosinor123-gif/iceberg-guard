# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd

from iceberg_guard import signals


def _write_table(path, rows, seed):
    df = pd.DataFrame({
        "ts": list(range(rows[0], rows[0] + rows[1])),
        "category": ["growth"] * rows[1],
        "tenant": ["tenant-000"] * rows[1],
        "join_key": list(range(rows[1])),
        "measure": [1.0] * rows[1],
    })
    pq.write_table(pa.Table.from_pandas(df), path)


def _mk_layout(tmp_path, table, ranges, seed=0):
    d = tmp_path / "spike" / table
    d.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (lo, hi) in enumerate(ranges):
        p = d / f"part-{i}.parquet"
        _write_table(p, (lo, hi - lo), seed + i)
        paths.append(p)
    return list(d.rglob("*.parquet"))


def test_file_stats_ranges(tmp_path):
    _mk_layout(tmp_path, "t", [(100, 200)])
    s = signals.all_files(tmp_path, "t")[0]
    assert s.rows == 100
    assert s.ts_min == 100 and s.ts_max == 199
    assert s.cat_min == "growth"


def test_predicate_overlap_counts_literal_containment(tmp_path):
    files = _mk_layout(tmp_path, "t", [(1, 11), (20, 31), (5, 41)])
    stats = [signals.file_stats(f) for f in files]
    assert signals.predicate_overlap(stats, "category", "growth") == 1.0
    assert signals.predicate_overlap(stats, "category", "legacy") == 0.0
    assert abs(signals.predicate_overlap(stats, "ts", 25) - 2 / 3) < 1e-3


def test_overlap_not_measurable_returns_none(tmp_path):
    df = pd.DataFrame({"tenant": ["a"]})  # no ts/category columns
    p = tmp_path / "spike" / "bare" / "part-0.parquet"
    p.parent.mkdir(parents=True)
    pq.write_table(pa.Table.from_pandas(df), p)
    stats = [signals.file_stats(p)]
    assert signals.predicate_overlap(stats, "category", "growth") is None


def test_many_small_files_signal(tmp_path):
    witnesses = tmp_path / "layoutA"
    _mk_layout(witnesses, "many_small", [(0, 5)] * 10)
    sig = signals.layout_signals(witnesses, "many_small")
    assert sig["many_small_files"] is True
    assert sig["files"] == 10


def test_negative_control_not_flagged(tmp_path):
    big = tmp_path / "layoutB"
    _mk_layout(big, "few_big", [(0, 1000), (1000, 2000), (2000, 3000)])
    sig = signals.layout_signals(big, "few_big")
    assert sig["many_small_files"] is False   # control must NOT be labeled — the M2 exit condition


def test_missing_column_stats_are_null_not_guessed(tmp_path):
    p = tmp_path / "spike" / "s" / "part.parquet"
    p.parent.mkdir(parents=True)
    pq.write_table(pa.Table.from_pandas(pd.DataFrame({"ts": [1, 2]})), p)  # category absent
    all_s = signals.layout_signals(tmp_path, "s")
    assert all_s["table"] == "s"
    assert signals.all_files(tmp_path, "s")[0].cat_min is None
