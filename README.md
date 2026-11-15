# iceberg-guard — Iceberg Workload Reliability & Layout Guard

> For a synthetic-but-controlled workload on Iceberg tables, does a declared layout change
> improve measured evidence without changing query results — and is the rewrite cost acceptable?

- **Mode supported (MVP):** local Iceberg tables via PyIceberg (SQL catalog on sqlite, local warehouse) queried through DuckDB (`iceberg_scan`, `unsafe_enable_version_guessing=true`). No catalog service, no network, no cluster.
- **Evidence-first:** every result compares baseline and candidate runs on the same data and parameters; correctness gates performance. Nothing here is a Firebolt measurement or a production-ready optimizer.

## Status (2026-11-15)

Milestones 0–4 in progress. Verified (see `docs/SPIKE_RESULT.md`, `docs/results-example.md`):

- Deterministic fixture, 2 layouts, exact rowset equivalence (disclosed 1e-9 float digest normalization)
- DuckDB reads Iceberg tables; `iceberg-guard rewrite` performs the declared intervention and proves row-equivalence (digest match) before any comparison is honored
- 10 interleaved repetitions; p50/p95 with dispersion; control query not labeled an improvement; report carries rewrite cost and full caveats
- C++20 core (`src_cpp/`): `AggregateStats` streaming Welford aggregate, ASan+UBSan clean, Release build ~26M adds/s (machine-specific); Python cross-check to 1e-9 vs `statistics.pvariance`
- Auto-generated report (`docs/results-example.md`); `docs/BUGS.md` is a standing defect log (10+ entries)
- 20 unit tests passing (Linux: C++ cross-check tests included); no production/capacity/vendor claims anywhere

## Quickstart (target: Linux; works on Windows/WSL too)

```bash
uv venv --python 3.12 .venv && source .venv/bin/activate   # activate as appropriate
uv pip install -e '.[dev]'
python scripts/generate_fixture.py                          # writes warehouse/ (git-ignored)
pyiceberg-guard benchmark --layout both --manifest config/example-workload.yaml
pyiceberg-guard compare
```

Or use `iceberg-guard` as a console script after install. See `docs/limitations.md` for what is not yet implemented.
