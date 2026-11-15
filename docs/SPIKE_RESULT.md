# Milestone 0 — Result (PASS)

**Date:** 2026-11-15 · **Machine:** WSL Ubuntu-24.04 · **Data:** synthetic seed 20261115, 60,000 rows

## Verdict: PASS — proceed to Milestone 1

| Check | Baseline (`events_many_small`) | Candidate (`events_sorted_compact`) |
|---|---|---|
| Data files (parquet) | **30** | **4** |
| Bytes on disk | 992,775 | 1,037,806 |
| Rows read back | 60,000 | 60,000 |
| Rowset md5 | `37a1f8b34392ca5dce0bde79b9875fa7` | `37a1f8b34392ca5dce0bde79b9875fa7` |
| Filtered count (`category='growth' AND ts>...`) | 13,429 | 13,429 |

- Exact-equivalence gate: **ROWSET_MATCH = true** (full-table scan, canonicalized, identical md5)
- DuckDB probe: `iceberg_scan(...)` returned `(60000, 808814.745023)` — Iceberg read path works
- PyIceberg 0.12.0; `Table.inspect_files()` / `.files` **do not exist** in this version → for per-file stats use filesystem scan of `warehouse/spike/<table>/data/**/*.parquet` or a small Parquet footer reader (planned for M1/`src_cpp` core)
- Local catalog: PyIceberg **SQL catalog on sqlite** (warehouse local dir) — no service needed; setup = `pyiceberg[sql-sqlite]`
- Logs: `spike_run_03.log` / `spike_run_04.log`

## Honest caveats found in the spike
1. `np.array_split` on a pandas DataFrame yields ndarrays, not DataFrames (fixed with `iloc` slicing in `split_df`)
2. `pyiceberg[sql]` extra no longer exists → must use `[sql-sqlite]`
3. Only controlled property = file count/size (layout), **not** query time — no timing claims anywhere yet
4. DuckDB needed `SET unsafe_enable_version_guessing=true` — treat this as a known fragility for M1; consider pinned Iceberg spec support / explicit version handling
5. File-level statistics (min/max/record_count) not available via PyIceberg 0.12 public API → M1/M4 must read them from Parquet footers or manifests directly

## Next: Milestone 1
Workload manifest validation, repeated runs, environment capture, timeouts, raw JSON records, deterministic fixture flow. No perf claims until M3.
