# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
"""Append-only run records (JSONL). No record is ever deleted or overwritten."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path


def record(run_dir: Path, record: dict) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {"started": stamp, **record}
    path = run_dir / f"{stamp}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path
