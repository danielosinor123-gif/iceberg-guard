# Milestone 0 Spike — Design Log

**Question:** Can a seeded synthetic fixture be written as two controlled Iceberg table layouts locally, and can exact-read equivalence be proven?

**Environment**
- WSL Ubuntu-24.04 (Linux), `/root/iceberg-guard-spike/`
- Python 3.12 venv, pyiceberg (SQL/sqlite catalog, local file warehouse), DuckDB (iceberg probe, may fail)

**Fixture**
- 60,000 rows, seed = 20261115, generated once, same rows in both tables:
  - `ts` int64 (seconds since epoch), `category` ∈ {growth, core, legacy, experiment} (power-law weights: 0.55/0.25/0.12/0.08), `tenant` = tenant-NNN (uniform 400), `join_key` int64 uniform, `measure` lognormal(2.0, 1.1), rounded 6dp

**Layouts (one controlled property)**
- `spike.events_many_small` — unsorted, 30 append batches (many small files)
- `spike.events_sorted_compact` — sorted by (category, ts), 4 batches (few larger files)

**Acceptance gate**
- `ROWSET_MATCH: true` — full-table scan → canonicalized (sort on all columns) → identical md5 — **and** at least one Iceberg metadata path verified. Exit 0 only then.
- Metadata evidence: snapshot/file counts and byte totals (API permitting) with filesystem fallback.

**Measures (honest, no perf claims)**
- No timing claims from this spike; the spike proves write/read/compare works end-to-end. DuckDB `iceberg_scan` probe is a bonus check, failures allowed.

**Known risks (documented honestly if they bite)**
- PyIceberg local file + sqlite catalog version quirks
- DuckDB iceberg extension availability/version guessing flag

**Verdict rules**
- If PASS: proceed to M1 (workload manifest, repeated runs, env capture) next
- If FAIL on write path: pivot writer (Spark) or narrow fixture scope, record the gap — do NOT call it an Iceberg test over Parquet
- If FAIL on read path: inspect warehouse dir structure; compare with pyarrow parquet reader as diagnostic, record limitation
