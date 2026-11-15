# Architecture

```
CLI (cli.py)
  generate  → fixture.py (seeded) + pyiceberg (SQL/sqlite local warehouse) → 2 layouts
  inspect   → signals.py (filesystem + Parquet footer stats: counts, bytes, skew, overlap)
  benchmark → workload.py (manifest) + engine_adapter.py (DuckDB iceberg_scan, watchdog interrupt)
  compare   → compare.py (disclosed 1e-9 digest, match gates timings)
  record    → report.py (append-only JSONL under runs/)
  report    → renders docs/results-example.md from the latest records (measured-vs-estimated labeled)
```

Layers are replaceable by design: the metadata adapter knows nothing of the engine; the engine knows
nothing of manifests. The warehouse is regenerable from `fixtures/generator-config.yaml` (seed 20261115),
so it is **never committed**.

Anything not listed above is deliberately out of scope (see docs/limitations.md).
