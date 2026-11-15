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
- Correctness gate is fail-closed against **manifest-expected units** (recorded `expected_units`): every expected unit must appear on both sides with status=ok, samples_recorded == repetitions, digest sets equal; a unit missing on both sides is a named failure, not a silent pass. `benchmark --baseline/--candidate` selects the operand pair; the committed example compares the intervention's actual output; rewrite records end-to-end timing (read+sort+write+verify)
- Auto-generated report (`docs/results-example.md`); `docs/BUGS.md` is a standing defect log (10+ entries)
- 31 unit tests passing (non-Linux; Linux runs add the 2 C++ cross-check tests); no production/capacity/vendor claims anywhere

## Verify this repo yourself (fresh clone, ~10 minutes)

Everything in this README and `docs/` is **maintainer-produced evidence, not independently verified by you**. Please rerun it:

```bash
git clone https://github.com/danielosinor123-gif/iceberg-guard && cd iceberg-guard
uv venv --python 3.12 .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e '.[dev]'
python -m pytest -q                                     # expect: 31 passed, 2 skipped (Linux: 33 passed)
python -m iceberg_guard.cli generate
python -m iceberg_guard.cli rewrite --mode sort --target events_intervention_sorted --batches 4
python -m iceberg_guard.cli benchmark --baseline events_many_small --candidate events_intervention_sorted --manifest config/example-workload.yaml --repetitions 10
python -m iceberg_guard.cli compare                     # expect: rowset_match true
python -m iceberg_guard.cli report --out /tmp/my-report.md
```

The `repro` CI job runs the same sequence on a clean ubuntu-latest on every push to `main` (as do unit tests and the sanitized C++ build). Numbers will differ from this machine's runs to the extent any machine differs — that's the point of reruns.

**What this shows vs. what it does not:** this project passed its own checks *on this machine, from a pristine clone, right now*. It does not prove those checks exhaustive, nor that your rerun matches my timings, nor anything about production data.

## Quickstart (target: Linux; works on Windows/WSL too)

```bash
uv venv --python 3.12 .venv && source .venv/bin/activate   # activate as appropriate
uv pip install -e '.[dev]'
python scripts/generate_fixture.py                          # writes warehouse/ (git-ignored)
pyiceberg-guard benchmark --layout both --manifest config/example-workload.yaml
pyiceberg-guard compare
```

Or use `iceberg-guard` as a console script after install. See `docs/limitations.md` for what is not yet implemented.
