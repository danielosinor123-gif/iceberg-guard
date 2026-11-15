# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
"""DuckDB engine adapter: installs/loads the iceberg extension, runs manifest queries.

The iceberg extension needs `unsafe_enable_version_guessing=true` in this setup — recorded
here and in docs/limitations.md, never hidden. Query timeouts are enforced with a watchdog
thread calling `connection.interrupt()`; on interruption the query is marked `timed_out`,
not averaged into samples.
"""
from __future__ import annotations
import threading
import time

import duckdb
import pandas as pd

def df_md5(df: pd.DataFrame, order_sensitive: bool = False) -> str:  # noqa: F401  (re-exported for compatibility)
    from .fixture import df_md5 as _raw
    return _raw(df, order_sensitive=order_sensitive)

class EngineError(RuntimeError):
    """Engine-level failure (extension missing, table unreadable, etc.)."""


def connect():
    con = duckdb.connect()
    try:
        con.execute("INSTALL iceberg; LOAD iceberg;")
        con.execute("SET unsafe_enable_version_guessing=true;")
    except Exception as e:  # engine must fail loudly, never silently
        raise EngineError(f"DuckDB iceberg extension setup failed: {e}") from e
    return con


def run_query(con, sql: str, timeout_sec: int):
    """Execute one rendered query. Returns (df, elapsed_s, status) — status: ok|timed_out."""
    started = {"t": time.perf_counter()}
    result = {"df": None, "error": None, "status": "ok"}

    def work():
        try:
            result["df"] = con.execute(sql).fetchdf()
        except Exception as e:  # surfaced, never swallowed
            result["error"] = str(e)
            result["status"] = "error"

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(timeout_sec)
    elapsed = time.perf_counter() - started["t"]
    if t.is_alive():
        con.interrupt()
        t.join(5)
        return None, elapsed, "timed_out"
    if result["status"] == "error":
        raise EngineError(result["error"])
    return result["df"], elapsed, "ok"


def result_md5(df: pd.DataFrame, order_sensitive: bool) -> str:
    from .fixture import df_digest
    return df_digest(df, order_sensitive=order_sensitive)
