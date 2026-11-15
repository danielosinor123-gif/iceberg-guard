# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0
"""Baseline-vs-candidate comparison — correctness gates performance, always.

Fail-closed semantics (docs/benchmark-method.md):
- a pair with zero records on either side is a failure, never a pass;
- every (query_id, param_set) unit present in either layout's records must pass on both sides:
  status=ok, samples_recorded == repetitions (when known), identical md5 sets;
- missing, failed, timed-out, or partially-sampled units fail the gate and name the gaps.
"""
from __future__ import annotations
import hashlib

import pandas as pd


def canonical_md5(df: pd.DataFrame, order_sensitive: bool) -> str:
    if not order_sensitive:
        df = df.sort_values(list(df.columns)).reset_index(drop=True)
    payload = df.to_csv(index=False).encode("utf-8")
    return hashlib.md5(payload).hexdigest()


def _by_unit(records):
    out = {}
    for r in records:
        out[(r.get("query_id"), r.get("param_set"))] = r
    return out


def compare_records(baseline_records: list[dict], candidate_records: list[dict],
                    repetitions: int | None = None) -> dict:
    b_units, c_units = _by_unit(baseline_records), _by_unit(candidate_records)
    units = sorted(set(b_units) | set(c_units))

    if not units:
        return {"rowset_match": False, "status": "no_data",
                "problems": ["no benchmark records on either side — gate cannot be satisfied"],
                "repetitions": repetitions,
                "queries": {"query_id": [], "match": [], "units": []}}

    problems: list[str] = []
    units_out = []
    per_query: dict[str, list[bool]] = {}

    for (qid, ps) in units:
        b, c = b_units.get((qid, ps)), c_units.get((qid, ps))
        label = f"{qid} param_set={ps}"
        reasons = []
        for side, rec in (("baseline", b), ("candidate", c)):
            if rec is None:
                reasons.append(f"{side}: missing")
                continue
            if rec.get("status") != "ok":
                reasons.append(f"{side}: status={rec.get('status')}")
                continue
            samples = int(rec.get("samples_recorded", -1))
            if repetitions is not None and samples != repetitions:
                reasons.append(f"{side}: samples_recorded={samples}/{repetitions}")
        if b and c and b.get("status") == "ok" and c.get("status") == "ok":
            if sorted(b.get("unique_md5s", [])) != sorted(c.get("unique_md5s", [])):
                reasons.append("digest mismatch")
        ok = not reasons
        if not ok:
            problems.append(f"{label}: {'; '.join(reasons)}")
        per_query.setdefault(qid, []).append(ok)
        units_out.append({"query_id": qid, "param_set": ps, "match": bool(ok),
                          "baseline_md5s": b.get("unique_md5s") if b else None,
                          "candidate_md5s": c.get("unique_md5s") if c else None,
                          "reasons": reasons})

    q_ids = sorted(per_query)
    return {"rowset_match": all(u["match"] for u in units_out),
            "status": "ok" if all(u["match"] for u in units_out) else "insufficient_coverage",
            "problems": problems,
            "repetitions": repetitions,
            "queries": {"query_id": q_ids,
                        "match": [all(per_query[q]) for q in q_ids],
                        "units": units_out}}
