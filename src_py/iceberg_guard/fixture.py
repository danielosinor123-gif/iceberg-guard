# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
"""Deterministic synthetic fixture generator. Every artefact derived from a seed is reproducible."""
import hashlib

import numpy as np
import pandas as pd

CATEGORIES = np.array(["growth", "core", "legacy", "experiment"])
CATEGORY_WEIGHTS = (0.55, 0.25, 0.12, 0.08)


def make_events(rows: int = 60_000, seed: int = 20261115) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ts = np.arange(rows, dtype=np.int64) * 17 + 1_700_000_000
    cat = rng.choice(CATEGORIES, size=rows, p=CATEGORY_WEIGHTS)
    tenant = np.array([f"tenant-{i % 400:03d}" for i in range(rows)])
    join_key = rng.integers(1, 50_000, size=rows).astype(np.int64)
    measure = np.round(rng.lognormal(mean=2.0, sigma=1.1, size=rows), 6)
    df = pd.DataFrame({"ts": ts, "category": cat, "tenant": tenant,
                       "join_key": join_key, "measure": measure})
    return df


def df_md5(df: pd.DataFrame, order_sensitive: bool = False) -> str:
    """Raw md5 of CSV — informational only; NOT layout-comparable across file splits."""
    if not order_sensitive:
        df = df.sort_values(list(df.columns)).reset_index(drop=True)
    return hashlib.md5(df.to_csv(index=False).encode("utf-8")).hexdigest()


def df_digest(df: pd.DataFrame, order_sensitive: bool = False, decimals: int = 9) -> str:
    """Cross-layout comparable digest.

    DuckDB re-associates float aggregates across different file splits, so the same
    aggregation can differ in the 11th significant digit between layouts. We therefore
    round numeric columns to `decimals` (1e-9) before hashing — DISCLOSED in
    docs/limitations.md; raw (unrounded) values are preserved separately in run logs.
    A digest match does not override a row-level correctness failure elsewhere.
    """
    if not order_sensitive:
        df = df.sort_values(list(df.columns)).reset_index(drop=True)
    out = df.copy()
    for col in out.select_dtypes("number").columns:
        out[col] = out[col].round(decimals)
    return hashlib.md5(out.to_csv(index=False).encode("utf-8")).hexdigest()
