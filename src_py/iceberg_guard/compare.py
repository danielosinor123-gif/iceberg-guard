# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
"""Baseline-vs-candidate comparison — correctness gates performance, always."""
from __future__ import annotations
import hashlib

import pandas as pd


def canonical_md5(df: pd.DataFrame, order_sensitive: bool) -> str:
    if not order_sensitive:
        df = df.sort_values(list(df.columns)).reset_index(drop=True)
    payload = df.to_csv(index=False).encode("utf-8")
    return hashlib.md5(payload).hexdigest()


def compare_results(baseline: dict, candidate: dict) -> dict:
    """Both sides: {query_id: [md5 per repetition]}. A mismatch anywhere invalidates the layout pair."""
    out = {"query_id": [], "match": [], "detail": []}
    all_ok = True
    ids = sorted(set(baseline) | set(candidate))
    for qid in ids:
        b, c = baseline.get(qid, []), candidate.get(qid, [])
        ok = len(b) == len(c) and all(x == y for x, y in zip(b, c))
        out["query_id"].append(qid)
        out["match"].append(bool(ok))
        out["detail"].append({"baseline": b, "candidate": c})
        all_ok = all_ok and ok
    return {"rowset_match": all_ok, "queries": out}
