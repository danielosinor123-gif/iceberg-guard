# iceberg-guard — Iceberg Workload Reliability & Layout Guard

> For a synthetic-but-controlled workload on Iceberg tables, does a declared layout change
> improve measured evidence without changing query results — and is the rewrite cost acceptable?

- **Mode supported (MVP):** local Iceberg tables via PyIceberg (SQL catalog on sqlite, local warehouse) queried through DuckDB (`iceberg_scan`, `unsafe_enable_version_guessing=true`). No catalog service, no network, no cluster.
- **Evidence-first:** every result compares baseline and candidate runs on the same data and parameters; correctness gates performance. Nothing here is a Firebolt measurement or a production-ready optimizer.

## Status (2026-11-15)

Milestone 1 build. Verified so far (see `docs/SPIKE_RESULT.md`):

- Deterministic synthetic fixture roundtrip through Iceberg (30 small files vs 4 sorted large files)
- Exact rowset equivalence proven (identical MD5 of canonicalized tables)
- DuckDB reads the Iceberg tables; PyIceberg sqlite catalog works with no service

## Quickstart (target: Linux; works on Windows/WSL too)

```bash
uv venv --python 3.12 .venv && source .venv/bin/activate   # activate as appropriate
uv pip install -e '.[dev]'
python scripts/generate_fixture.py                          # writes warehouse/ (git-ignored)
pyiceberg-guard benchmark --layout both --manifest config/example-workload.yaml
pyiceberg-guard compare
```

Or use `iceberg-guard` as a console script after install. See `docs/limitations.md` for what is not yet implemented.
