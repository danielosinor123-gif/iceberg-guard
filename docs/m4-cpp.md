# Milestone 4 — C++20 analysis core

## What was built

`src_cpp/` — a deliberately narrow C++20 component:

- `iceberg_guard_core` (static lib) — `AggregateStats`: streaming file-layout aggregate
  (files, rows, bytes, mean/variance/stdev/cv of file size, byte min/max, ts extent, with/without stats).
  Variance via **Welford's online algorithm** (single pass, numerically stable, population denominator n).
- `iceberg-guard-agg` (CLI) — reads normalized tab-separated file statistics on stdin,
  writes one JSON line to stdout. No I/O beyond that, no Iceberg semantics, no vendor formats.
- `test_aggregate` — self-contained unit tests (empty input, single file, known Welford values,
  stat-less files excluded from ts extent, big values, `reset()`).
- `bench_aggregate` — component benchmark.

## Interface contract

Input line: `<rows>\t<bytes>\t<ts_min>\t<ts_max>\t<stats_present 0|1>`.
Files without usable stats report `stats_present=0` and are excluded from ts extent
(`ts_min`/`ts_max` print as `0` — never guessed).

Python ↔ C++: `iceberg_guard.cpp_adapter.run_aggregate(file_stats) -> dict`.
`iceberg-guard inspect --cpp` runs both paths and prints them side by side.
The core is Linux-only (the committed build uses Linux CMake + gcc); on other platforms the
key `layout` shows `unavailable` rather than a mislabeled substitute.

## Build & verify (Linux/WSL)

```bash
cmake -S src_cpp -B src_cpp/build -DCMAKE_BUILD_TYPE=Debug -DICEBERG_GUARD_SANITIZERS=ON
cmake --build src_cpp/build -j
cd src_cpp/build && ctest --output-on-failure
src_cpp/build/iceberg-guard-agg --bench 5000000
```

## Verification (2026-11-15, this machine)

- ASan + UBSan Debug build: **1/1 tests passed** (sanitizers clean, `-fno-sanitize-recover=all`)
- Release build: **1/1 passed**
- Python ↔ C++ cross-check on repo fixtures (`tests/test_cpp_agg.py`): files/rows/bytes/exact;
  mean, population variance, stdev, cv to 1e-9 relative; ts extent exact
- Component bench (this machine only): **≈ 26.1M adds/s** Release (5,000,000 lines, ~192 ms);
  **≈ 2.2M adds/s** under ASan+UBSan (sanitizer overhead disclosed; both are machine-specific,
  not a general throughput claim)

## Intentionally NOT done

- Pruning-overlap estimation in C++ (per-column stats plumbing stays in Python — selective,
  not API surface); there will be no rushed "one more pass in C++" at the cost of correctness.
- Threading/parallelism in the accumulator (single-threaded by design; a test harness, not a data engine).
- No vendor or production throughput claims. Ever.
