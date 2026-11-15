# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
"""iceberg-guard CLI. Subcommands: generate | inspect | benchmark | compare."""
from __future__ import annotations
import argparse
import hashlib
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
from pyiceberg.catalog import load_catalog

from . import __version__, fixture
from .engine_adapter import EngineError, connect, run_query, result_md5
from .workload import ManifestError, load_manifest, Manifest
from .report import record as append_record

DEFAULT_WAREHOUSE = "warehouse"
CATALOG_DB = "warehouse/catalog.db"


def sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL).strip()[:12]
    except Exception:
        return "unknown"


def _schema():
    return pa.schema([("ts", pa.int64()), ("category", pa.string()), ("tenant", pa.string()),
                       ("join_key", pa.int64()), ("measure", pa.float64())])


def _split_df(frame: pd.DataFrame, parts: int):
    import numpy as np
    idx = np.array_split(np.arange(len(frame)), parts)
    return [frame.iloc[i] for i in idx if len(i)]


def cmd_generate(args) -> int:
    wh = Path(args.warehouse)
    wh.mkdir(parents=True, exist_ok=True)
    wh_str = str(wh.resolve()).replace("\\", "/")
    cat = load_catalog("guard", **{"type": "sql",
                                    "uri": f"sqlite:///{Path(wh_str + '/catalog.db')}",
                                    "warehouse": wh_str})
    try:
        cat.create_namespace("spike")
    except Exception:
        pass  # namespace already exists
    df = fixture.make_events(rows=args.rows, seed=args.seed)
    pschema = _schema()
    for name, batches in (("events_many_small", _split_df(df, 30)),
                          ("events_sorted_compact", _split_df(df.sort_values(["category", "ts"]).reset_index(drop=True), 4))):
        ident = ("spike", name)
        if cat.table_exists(ident):
            cat.drop_table(ident)
        t = cat.create_table(ident, schema=pschema)
        with t.transaction() as tx:
            for b in batches:
                tx.append(pa.Table.from_pandas(b, schema=pschema, preserve_index=False))
    print("fixture generated: 2 layouts, warehouse:", wh.resolve())
    return 0


def cmd_inspect(args) -> int:
    from . import signals
    for table in ("events_many_small", "events_sorted_compact"):
        sig = signals.layout_signals(args.warehouse, table)
        ovl = signals.predicate_overlap(signals.all_files(args.warehouse, table), "category", "growth")
        print({**sig, "category_eq_growth_overlap": ovl})
    return 0


def _benchmark_one(con, manifest: Manifest, table_meta: str, layout: str):
    out = []
    for q in manifest.queries:
        for j, params in enumerate(q.param_sets):
            rendered = q.render(params)
            sql = rendered.replace("FROM t", f"FROM iceberg_scan('{table_meta}')")
            samples = []
            md5s = []
            status = "ok"
            for _ in range(manifest.repetitions):
                try:
                    df, elapsed, st = run_query(con, sql, manifest.timeout_sec)
                except EngineError as e:
                    status, df, elapsed, st = "error", None, 0.0, "error"
                    out.append({"query_id": q.id, "param_set": j, "params": params,
                                "status": status, "error": str(e)[:300]})
                    break
                if st == "timed_out":
                    status = "timed_out"
                    continue
                samples.append(elapsed)
                md5s.append(result_md5(df, q.order_sensitive))
            if status == "ok":
                samples.sort()
                n = len(samples)
                out.append({"query_id": q.id, "param_set": j, "params": params,
                            "status": "ok",
                            "rowcount": int(df.shape[0]),
                            "md5": md5s[-1],
                            "unique_md5s": sorted(set(md5s)),
                            "samples_ms": [round(s * 1000, 3) for s in samples],
                            "p50_ms": round(samples[n // 2] * 1000, 3),
                            "p95_ms": round(samples[min(n - 1, int(n * 0.95))] * 1000, 3)})
            elif status == "timed_out":
                out.append({"query_id": q.id, "param_set": j, "params": params, "status": status})
    return out


def _meta_json(warehouse: Path, table_name: str) -> Path:
    metas = sorted((warehouse / "spike" / table_name / "metadata").glob("*.metadata.json"))
    if not metas:
        raise FileNotFoundError(f"no metadata found under {warehouse / 'spike' / table_name / 'metadata'} — run `generate` first")
    return metas[-1]


def cmd_benchmark(args) -> int:
    manifest = load_manifest(args.manifest)
    warehouse = Path(args.warehouse)
    run_dir = Path(args.run_dir) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    meta = {t: _meta_json(warehouse, t) for t in ("events_many_small", "events_sorted_compact")}
    con = connect()
    results = []
    env = {"host": platform.platform(), "python": platform.python_version(),
           "iceberg_guard": __version__, "git": sha(), "manifest": str(args.manifest),
           "unsafe_enable_version_guessing": True}
    layouts = ["events_many_small", "events_sorted_compact"] if args.layout == "both" else [
        {"baseline": "events_many_small", "candidate": "events_sorted_compact"}[args.layout]]
    for table in layouts:
        t0 = time.perf_counter()
        rows = _benchmark_one(con, manifest, str(meta[table]), table)
        results.append({"layout": table, "results": rows, "elapsed_sec": round(time.perf_counter() - t0, 3)})
    record = append_record(run_dir, {"env": env, "workload": manifest.name, "results": results})
    print("records written:", record)
    return 0


def _latest_records(run_dir: Path):
    import json
    runs = sorted(run_dir.rglob("*.jsonl"))
    if not runs:
        return None, {}
    latest = runs[-1]
    data = {"events_many_small": [], "events_sorted_compact": []}
    env = {}
    with latest.open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            env = rec.get("env", env)
            for layout in rec.get("results", []):
                data.setdefault(layout["layout"], []).extend(layout.get("results", []))
    return (latest, env, data)


def cmd_report(args) -> int:
    import json
    from . import signals
    from .compare import compare_results

    found = _latest_records(Path(args.run_dir))
    if not found[0]:
        print("no run records under", args.run_dir, "— run `benchmark` first")
        return 1
    latest, env, data = found

    base_md5s = {}
    cand_md5s = {}
    base_p50 = {}
    cand_p50 = {}
    for r in data.get("events_many_small", []):
        if r.get("status") == "ok":
            base_md5s.setdefault(r["query_id"], []).append(r["md5"])
            base_p50.setdefault(r["query_id"], []).append(r["p50_ms"])
    for r in data.get("events_sorted_compact", []):
        if r.get("status") == "ok":
            cand_md5s.setdefault(r["query_id"], []).append(r["md5"])
            cand_p50.setdefault(r["query_id"], []).append(r["p50_ms"])
    verdict = compare_results(base_md5s, cand_md5s)

    sig = {t: signals.layout_signals(args.warehouse, t) for t in ("events_many_small", "events_sorted_compact")}
    ovl = {t: signals.predicate_overlap(signals.all_files(args.warehouse, t), "category", args.overlap_value)
           for t in sig}

    def row(label, vals):
        return "| " + label + " | " + " | ".join(str(v) for v in vals) + " |"

    lines = []
    lines.append("# Sample run record — spike-basic (auto-generated)")
    lines.append("")
    lines.append(f"Generated: {latest.name} · workload: {args.manifest}")
    if env:
        lines.append(f"Host: {env.get('host')} · python {env.get('python')} · iceberg-guard {env.get('iceberg_guard')} · git {env.get('git')}")
        lines.append("Engine protocol flag: `unsafe_enable_version_guessing=true` (see docs/limitations.md)")
    lines.append("")
    lines.append("## Layout signals (measured on the filesystem — provenance: measured_filesystem)")
    lines.append("")
    lines.append(row("signal", ["events_many_small", "events_sorted_compact"]))
    lines.append(row("---", ["---", "---"]))
    for key in ("files", "rows", "bytes_total", "mean_file_bytes", "size_cv", "many_small_files", "ts_min", "ts_max"):
        lines.append(row(key, [sig["events_many_small"].get(key), sig["events_sorted_compact"].get(key)]))
    lines.append("")
    lines.append(f"## Predicate prune signal — `category = '{args.overlap_value}'` (equality, containment semantics)")
    lines.append("")
    lines.append(row("fraction of files whose [min,max] contains the literal", [f"{ovl['events_many_small']}", f"{ovl['events_sorted_compact']}"]))
    lines.append("")
    lines.append("> **Signal ≠ cause.** A lower overlap means better nominal pruning for this equality predicate. It yields no performance guarantee, and neither value is a verdict.")
    lines.append("")
    lines.append("## Result comparison (correctness gate — digests per query × repetition)")
    lines.append("")
    lines.append(row("query", ["baseline digests", "candidate digests", "match"]))
    lines.append(row("---", ["---", "---", "---"]))
    for qid, ok, detail in zip(verdict["queries"]["query_id"], verdict["queries"]["match"], verdict["queries"]["detail"]):
        b = ", ".join(x[:8] for x in detail["baseline"]) or "—"
        c = ", ".join(x[:8] for x in detail["candidate"]) or "—"
        lines.append(row(qid, [b, c, "✅" if ok else "❌"]))
    lines.append(f"")
    lines.append(f"**rowset_match: {verdict['rowset_match']}** — all provenance in run records.")
    lines.append("")
    lines.append("## Indicative timing only (n small, no cache protocol — treat as signal, not benchmark)")
    lines.append("")
    lines.append(row("query", ["baseline p50 ms", "candidate p50 ms"]))
    lines.append(row("---", ["---", "---"]))
    for qid in sorted(set(base_p50) | set(cand_p50)):
        b = f"{(sum(base_p50[qid]) / len(base_p50[qid])):.2f}" if qid in base_p50 else "—"
        c = f"{(sum(cand_p50[qid]) / len(cand_p50[qid])):.2f}" if qid in cand_p50 else "—"
        lines.append(row(qid, [b, c]))
    lines.append("")
    lines.append("`q_all_scan` is the **control**: it has no layout-relevant predicate, and any timing delta here is *not* labeled an improvement.")
    lines.append("")
    lines.append("## What this does NOT show")
    lines.append("")
    lines.append("- No benefit claim for any candidate. Three repetitions, local hardware, no cold-cache protocol.")
    lines.append("- No Firebolt, production, capacity, or cost claim. DuckDB/PyIceberg local numbers for synthetic data stay local.")
    lines.append("- No claim about partitioning or multi-query workloads; both need later milestones.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report written: {out}")
    return 0 if verdict["rowset_match"] else 2


def cmd_compare(args) -> int:
    from .compare import compare_results
    import json
    runs = sorted(Path(args.run_dir).rglob("*.jsonl"))
    if not runs:
        print("no run records under", args.run_dir)
        return 1
    latest = runs[-1]
    baseline: dict[str, list[str]] = {}
    candidate: dict[str, list[str]] = {}
    with latest.open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            for layout in rec.get("results", []):
                target = baseline if layout["layout"] == "events_many_small" else candidate
                for r in layout["results"]:
                    if r.get("status") == "ok":
                        target.setdefault(r["query_id"], []).append(r["md5"])
    out = compare_results(baseline, candidate)
    print(json.dumps(out, indent=2))
    print(f"source: {latest}")
    return 0 if out["rowset_match"] else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="iceberg-guard", description="Iceberg workload reliability & layout guard")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("generate", help="write the deterministic two-layout fixture")
    sp.add_argument("--warehouse", default=DEFAULT_WAREHOUSE)
    sp.add_argument("--rows", type=int, default=60_000)
    sp.add_argument("--seed", type=int, default=20261115)
    sp.set_defaults(fn=cmd_generate)

    sp = sub.add_parser("inspect", help="print layout signals (measured filesystem)")
    sp.add_argument("--warehouse", default=DEFAULT_WAREHOUSE)
    sp.set_defaults(fn=cmd_inspect)

    sp = sub.add_parser("benchmark", help="run the manifest workload on a layout")
    sp.add_argument("--warehouse", default=DEFAULT_WAREHOUSE)
    sp.add_argument("--manifest", default="config/example-workload.yaml")
    sp.add_argument("--layout", choices=["baseline", "candidate", "both"], default="both")
    sp.add_argument("--run-dir", default="runs")
    sp.set_defaults(fn=cmd_benchmark)

    sp = sub.add_parser("compare", help="verify result equivalence from the latest run records")
    sp.add_argument("--run-dir", default="runs")
    sp.set_defaults(fn=cmd_compare)

    sp = sub.add_parser("report", help="render an auto-generated evidence report from the latest run records")
    sp.add_argument("--run-dir", default="runs")
    sp.add_argument("--warehouse", default=DEFAULT_WAREHOUSE)
    sp.add_argument("--manifest", default="config/example-workload.yaml")
    sp.add_argument("--overlap-value", default="growth")
    sp.add_argument("--out", default="docs/results-example.md")
    sp.set_defaults(fn=cmd_report)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except (ManifestError, FileNotFoundError, EngineError) as e:
        print(f"error: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
