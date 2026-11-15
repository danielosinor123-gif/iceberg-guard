# Benchmark method (MVP)

1. Same seeded dataset, two layouts written from it (never modified in place): `events_many_small` (30 batches) and `events_sorted_compact` (sorted by (category, ts), 4 batches).
2. Candidate interventions can be produced *by the tool*: `iceberg-guard rewrite --mode sort|compact` times the rewrite end-to-end, writes into a declared batch count, and verifies `digest_match` between source and rewritten table (correctness of the rewrite itself is a gate, not a nicety).
3. Workload = YAML manifest (`config/example-workload.yaml`): SQL templates with `{placeholder}` params, per-param weight, order-sensitivity, repetitions, timeout.
4. Every query × param set × repetition × layout: samples (ms), rowcount, digest. No best-of-run cherry picking; p50/p95 reported with rep count; layouts alternate within repetitions (interleaved) to damp ordering bias.
5. Result digest equality between layouts **gates** all timing claims — a diff invalidates the comparison. Float aggregates can legitimately differ in the 11th significant digit across layouts (DuckDB re-associates the sum across file splits); the cross-layout digest therefore rounds numeric columns to 1e-9 before hashing, a disclosed convention (see docs/limitations.md). Raw sums remain available in run logs; integer/string results are compared exactly.
6. Cost-benefit framing: rewrite elapsed_sec and output layout are recorded, but conversion to an "is it worth it" verdict requires a read-frequency profile, which this synthetic workload lacks — no amortization claim is made or implied.
