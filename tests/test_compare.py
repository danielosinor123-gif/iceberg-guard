# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
import pandas as pd

from iceberg_guard.compare import canonical_md5
from iceberg_guard.fixture import make_events, df_md5


def test_canonical_md5_ignores_shuffle_when_unordered():
    df = make_events(rows=500, seed=42)
    a = canonical_md5(df.sample(frac=1, random_state=1), order_sensitive=False)
    b = canonical_md5(df.sample(frac=1, random_state=2), order_sensitive=False)
    assert a == b


def test_canonical_md5_respects_order_sensitive():
    df = make_events(rows=500, seed=42)
    a = canonical_md5(df.sample(frac=1, random_state=1), order_sensitive=True)
    b = canonical_md5(df.sample(frac=1, random_state=2), order_sensitive=True)
    assert a != b


def test_fixture_determinism():
    df1 = make_events(rows=1000, seed=99)
    df2 = make_events(rows=1000, seed=99)
    assert df_md5(df1) == df_md5(df2)
