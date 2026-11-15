# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
"""Workload-manifest loading & validation. Fail closed on anything unknown."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
REQUIRED_TOP = {"name", "queries", "limits"}


class ManifestError(ValueError):
    """Raised for any invalid manifest. Always specific: which field, which query."""


@dataclass
class Query:
    id: str
    template: str
    order_sensitive: bool = True
    weight: float = 1.0
    param_sets: list[dict] = field(default_factory=list)

    def render(self, params: dict) -> str:
        return self.template.format(**params)


@dataclass
class Manifest:
    name: str
    repetitions: int
    timeout_sec: int
    queries: list[Query]


def load_manifest(path: str | Path) -> Manifest:
    p = Path(path)
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ManifestError(f"{p}: invalid YAML: {e}") from e
    if not isinstance(raw, dict):
        raise ManifestError(f"{p}: top-level mapping expected")
    missing = REQUIRED_TOP - set(raw)
    if missing:
        raise ManifestError(f"{p}: missing required keys: {sorted(missing)}")
    unknown = set(raw) - REQUIRED_TOP
    if unknown:
        raise ManifestError(f"{p}: unknown keys: {sorted(unknown)}")
    limits = raw["limits"]
    if not isinstance(limits, dict):
        raise ManifestError(f"{p}: limits must be a mapping")
    repetitions = int(limits.get("repetitions", 3))
    timeout_sec = int(limits.get("timeout_sec", 30))
    if repetitions < 1:
        raise ManifestError(f"{p}: limits.repetitions must be >= 1")
    if timeout_sec < 1:
        raise ManifestError(f"{p}: limits.timeout_sec must be >= 1")
    queries = []
    for i, q in enumerate(raw["queries"]):
        if not isinstance(q, dict):
            raise ManifestError(f"{p}: queries[{i}] must be a mapping")
        qid = q.get("id")
        template = q.get("template")
        if not qid or not isinstance(qid, str):
            raise ManifestError(f"{p}: queries[{i}].id missing or not a string")
        if not template or not isinstance(template, str):
            raise ManifestError(f"{p}: queries[{i}].template missing or not a string")
        placeholders = set(PLACEHOLDER.findall(template))
        param_sets = q.get("param_sets", [])
        if not param_sets:
            raise ManifestError(f"{p}: query {qid!r} has no param_sets")
        for j, ps in enumerate(param_sets):
            if not isinstance(ps, dict):
                raise ManifestError(f"{p}: query {qid!r}.param_sets[{j}] must be a mapping")
            missing_params = placeholders - set(ps)
            extra_params = set(ps) - placeholders
            if missing_params:
                raise ManifestError(f"{p}: query {qid!r}.param_sets[{j}] missing {sorted(missing_params)}")
            if extra_params:
                raise ManifestError(f"{p}: query {qid!r}.param_sets[{j}] unused params {sorted(extra_params)}")
        weight = float(q.get("weight", 1.0))
        if weight <= 0:
            raise ManifestError(f"{p}: query {qid!r} weight must be > 0")
        queries.append(Query(id=qid, template=template,
                             order_sensitive=bool(q.get("order_sensitive", True)),
                             weight=weight, param_sets=list(param_sets)))
    return Manifest(name=str(raw["name"]), repetitions=repetitions,
                    timeout_sec=timeout_sec, queries=queries)
