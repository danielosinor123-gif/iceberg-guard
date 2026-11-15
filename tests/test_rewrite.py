# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
import json

from iceberg_guard.cli import main


def _rewrite_records(runs_dir):
    records = [json.loads(l) for p in runs_dir.rglob("*.jsonl") for l in p.open()]
    return [r for r in records if r.get("type") == "rewrite"]


def test_sort_rewrite_is_row_equivalent(tmp_path):
    wh = tmp_path / "warehouse"
    assert main(["generate", "--rows", "400", "--seed", "7", "--warehouse", str(wh)]) == 0
    assert main(["rewrite", "--warehouse", str(wh), "--target", "t_sorted",
                 "--mode", "sort", "--sort-key", "category,ts", "--batches", "2",
                 "--run-dir", str(tmp_path / "runs")]) == 0
    rw = _rewrite_records(tmp_path / "runs")
    assert rw, "rewrite record not written"
    assert rw[0]["digest_match"] is True
    assert rw[0]["output_files"] == 2


def test_compact_rewrite_keeps_order(tmp_path):
    wh = tmp_path / "warehouse"
    assert main(["generate", "--rows", "200", "--seed", "3", "--warehouse", str(wh)]) == 0
    assert main(["rewrite", "--warehouse", str(wh), "--target", "t_compact",
                 "--mode", "compact", "--batches", "1",
                 "--run-dir", str(tmp_path / "runs")]) == 0
    rw = _rewrite_records(tmp_path / "runs")
    assert rw[0]["digest_match"] is True
    assert rw[0]["output_files"] == 1
    assert rw[0]["sort_key"] is None


def test_rewrite_fails_closed_on_digest_mismatch(tmp_path, monkeypatch):
    wh = tmp_path / "warehouse"
    assert main(["generate", "--rows", "200", "--seed", "9", "--warehouse", str(wh)]) == 0
    calls = {"n": 0}
    def fake_md5(*a, **k):
        calls["n"] += 1
        return "AAA" if calls["n"] == 1 else "BBB"
    monkeypatch.setattr("iceberg_guard.cli.df_md5", fake_md5)
    rc = main(["rewrite", "--warehouse", str(wh), "--target", "t_sabotaged",
               "--mode", "sort", "--sort-key", "category", "--batches", "2",
               "--run-dir", str(tmp_path / "runs")])
    assert rc == 2   # fail closed — the digest check must stop the pipeline
    rw = _rewrite_records(tmp_path / "runs")
    assert rw[0]["digest_match"] is False
