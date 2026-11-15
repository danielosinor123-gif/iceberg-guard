# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0
"""Python ↔ C++ interface: pipe normalized file statistics into iceberg-guard-agg.

The binary prints a single JSON line; we embed it verbatim in the layout signals
under the key `layout.cpp`. If the binary is absent, the key is simply absent —
no silent fallback to a Python-computed proxy labeled as C++.
"""
from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BIN_CANDIDATES = [
    os.environ.get("ICEBERG_GUARD_AGG"),
    REPO_ROOT / "src_cpp" / "build" / "iceberg-guard-agg",          # debug+sanitizers
    REPO_ROOT / "src_cpp" / "build-release" / "iceberg-guard-agg",  # release
]


def cpp_binary() -> Path | None:
    import platform
    if platform.system() != "Linux":      # the committed build is Linux-only (see docs/m4-cpp.md)
        return None
    for cand in BIN_CANDIDATES:
        if cand and Path(cand).exists():
            return Path(cand)
    return None


def run_aggregate(files_stats) -> dict | None:
    binary = cpp_binary()
    if binary is None:
        return None
    lines = []
    for s in files_stats:
        stats = 1 if (s.ts_min is not None and s.ts_max is not None) else 0
        rows = getattr(s, "rows", 0)
        lines.append(f"{rows}\t{s.bytes}\t{s.ts_min or 0.0}\t{s.ts_max or 0.0}\t{stats}")
    payload = "\n".join(lines) + ("\n" if lines else "")
    cp = subprocess.run([str(binary)], input=payload, capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"iceberg-guard-agg failed (rc={cp.returncode}): {cp.stderr.strip()}")
    out = json.loads(cp.stdout.strip())
    out["provenance"] = "measured_cpp"
    return out
