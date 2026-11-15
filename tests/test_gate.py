# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0
from iceberg_guard.compare import compare_records


def rec(qid, ps, ok=True, digests=("a",), samples=2, md5="a"):
    md5s = list(digests) if isinstance(digests, (list, tuple)) else [digests]
    return {"query_id": qid, "param_set": ps, "status": "ok" if ok else "timed_out",
            "unique_md5s": md5s, "samples_recorded": samples}


OK = [rec("q_a", 0), rec("q_a", 1), rec("q_b", 0)]


def test_pass_when_complete_and_identical():
    out = compare_records(OK, list(OK), repetitions=2)
    assert out["rowset_match"] is True
    assert out["status"] == "ok"
    assert out["problems"] == []


def test_empty_comparison_fails():
    out = compare_records([], [], repetitions=2)
    assert out["rowset_match"] is False
    assert out["status"] == "no_data"


def test_missing_side_fails():
    out = compare_records(OK, [rec("q_b", 0)], repetitions=2)   # candidate missing the q_a units
    assert out["rowset_match"] is False
    assert any("candidate: missing" in p for p in out["problems"])


def test_timeout_status_fails():
    side = [rec("q_a", 0, ok=False), rec("q_a", 1), rec("q_b", 0)]
    out = compare_records(side, OK, repetitions=2)
    assert out["rowset_match"] is False
    assert any("status=timed_out" in p for p in out["problems"])


def test_partial_samples_fail():
    side = [rec("q_a", 0, samples=1), rec("q_a", 1), rec("q_b", 0)]   # one rep short
    out = compare_records(side, OK, repetitions=2)
    assert out["rowset_match"] is False
    assert any("samples_recorded=1/2" in p for p in out["problems"])


def test_digest_mismatch_fails():
    side = [rec("q_a", 0, digests=["x"]), rec("q_a", 1), rec("q_b", 0)]
    out = compare_records(side, OK, repetitions=2)
    assert out["rowset_match"] is False
    assert any("digest mismatch" in p for p in out["problems"])


def test_mixed_outcomes_named():
    a = OK
    b = [rec("q_a", 0, ok=False), rec("q_a", 1), rec("q_b", 0)]
    out = compare_records(a, b, repetitions=2)
    sub = next(u for u in out["queries"]["units"] if u["param_set"] == 0 and u["query_id"] == "q_a")
    assert sub["match"] is False
    assert any("timed_out" in p for p in sub["reasons"])
