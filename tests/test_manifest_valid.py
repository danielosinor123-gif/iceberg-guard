# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
import pytest

from iceberg_guard.workload import load_manifest


def test_example_manifest_parses():
    m = load_manifest("config/example-workload.yaml")
    assert m.name == "spike-basic"
    assert m.repetitions == 3
    assert m.timeout_sec == 30
    assert [q.id for q in m.queries] == ["q_growth_agg", "q_all_scan"]
    assert len(m.queries[0].param_sets) == 2
    assert len(m.queries[1].param_sets) == 1


def test_placeholder_render(tmp_path):
    m = load_manifest("config/example-workload.yaml")
    sql = m.queries[0].render(m.queries[0].param_sets[0])
    assert "growth" in sql
    assert "{" not in sql
