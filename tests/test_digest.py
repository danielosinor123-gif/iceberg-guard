# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
import pandas as pd

from iceberg_guard.fixture import df_digest, df_md5


def _frame(values):
    return pd.DataFrame({"category": ["growth"], "measure": values})


def test_digest_rounds_float_noise():
    a = _frame([180226.12728600012])
    b = _frame([180226.12728599983])
    assert df_md5(a) != df_md5(b)          # raw md5 differs (bitwise) — by design, informational only
    assert df_digest(a) == df_digest(b)    # disclosed 1e-9 normalization makes layouts comparable


def test_digest_detects_real_difference():
    a = _frame([100.0])
    b = _frame([100.01])                   # beyond 1e-9 — must NOT match
    assert df_digest(a) != df_digest(b)


def test_digest_string_columns_exact():
    a = _frame([100.0]); a["category"] = "growth"
    b = _frame([100.0]); b["category"] = "growth "  # trailing space — must NOT match
    assert df_digest(a) != df_digest(b)
