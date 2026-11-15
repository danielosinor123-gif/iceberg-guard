# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
import pytest

from iceberg_guard.workload import ManifestError, load_manifest

BASE = """name: broken
queries:
  - id: q
    template: "SELECT count(*) FROM t WHERE x = {y}"
    param_sets:
      - {}
limits:
  repetitions: 3
  timeout_sec: 10
"""

def test_manifest_rejects_missing_params(tmp_path):
    p = tmp_path / "m.yaml"
    p.write_text(BASE)
    with pytest.raises(ManifestError, match="missing"):
        load_manifest(p)


def test_manifest_rejects_unknown_top_key(tmp_path):
    p = tmp_path / "m.yaml"
    p.write_text("name: x\nextra: 1\nqueries: []\nlimits: {repetitions: 1, timeout_sec: 5}\n")
    with pytest.raises(ManifestError, match="unknown keys"):
        load_manifest(p)


def test_manifest_rejects_empty_param_sets(tmp_path):
    p = tmp_path / "m.yaml"
    p.write_text("name: x\nqueries:\n  - {id: q, template: 'SELECT 1'}\nlimits: {repetitions: 1, timeout_sec: 5}\n")
    with pytest.raises(ManifestError, match="param_sets"):
        load_manifest(p)
