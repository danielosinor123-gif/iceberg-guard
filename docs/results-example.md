# Sample run record — spike-basic (auto-generated)

Generated: 20261115T145640Z.jsonl · workload: config/example-workload.yaml
Host: Windows-11-10.0.26200-SP0 · python 3.12.16 · iceberg-guard 0.1.0 · git b24aaa311a34
Engine protocol flag: `unsafe_enable_version_guessing=true` (see docs/limitations.md)

## Layout signals (measured on the filesystem — provenance: measured_filesystem)

| signal | events_many_small | events_sorted_compact |
| --- | --- | --- |
| files | 30 | 4 |
| rows | 60000 | 60000 |
| bytes_total | 992775 | 1037806 |
| mean_file_bytes | 33092 | 259451 |
| size_cv | 0.002 | 0.007 |
| many_small_files | True | False |
| ts_min | 1700000000 | 1700000000 |
| ts_max | 1701019983 | 1701019983 |

## Predicate prune signal — `category = 'growth'` (equality, containment semantics)

| fraction of files whose [min,max] contains the literal | 1.0 | 0.75 |

> **Signal ≠ cause.** A lower overlap means better nominal pruning for this equality predicate. It yields no performance guarantee, and neither value is a verdict.

## Result comparison (correctness gate — digests per query × repetition)

| query | baseline digests | candidate digests | match |
| --- | --- | --- | --- |
| q_all_scan | a0f583e4 | a0f583e4 | ✅ |
| q_growth_agg | e173ec3f, f5b4e3f1 | e173ec3f, f5b4e3f1 | ✅ |

**rowset_match: True** — all provenance in run records.

## Indicative timing only (n small, no cache protocol — treat as signal, not benchmark)

| query | baseline p50 ms | candidate p50 ms |
| --- | --- | --- |
| q_all_scan | 6.33 | 4.76 |
| q_growth_agg | 70.48 | 24.82 |

`q_all_scan` is the **control**: it has no layout-relevant predicate, and any timing delta here is *not* labeled an improvement.

## What this does NOT show

- No benefit claim for any candidate. Three repetitions, local hardware, no cold-cache protocol.
- No Firebolt, production, capacity, or cost claim. DuckDB/PyIceberg local numbers for synthetic data stay local.
- No claim about partitioning or multi-query workloads; both need later milestones.
