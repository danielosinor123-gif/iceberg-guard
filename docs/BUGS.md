# Bug & Defect Log — iceberg-guard

Each entry: what broke, root cause, fix, severity. Newest at top.

## BUG-2026-11-15-02 — Cross-layout MD5 equality failed for float aggregates
- **Symptom:** `benchmark → compare` reported `rowset_match: false` for `q_growth_agg` despite identical row counts (13,429) and identical sums to ~10 significant digits (`180226.12728600012` vs `...28599983`).
- **Root cause:** DuckDB re-associates floating-point aggregates across file-processing splits; bit-level sums legitimately differ between layouts. Our digest hashed the raw floats.
- **Fix:** New `df_digest()` rounds numeric columns to 1e-9 for the comparison token (disclosed convention, see `docs/limitations.md`). Raw md5 still recorded, never used for pass/fail. Verified: match now `true` for all queries × layouts.
- **Tests:** `tests/test_digest.py` (rounding accepted, real diffs rejected, strings exact).
- **Severity:** correctness-gate — would have invalidated all future comparisons; caught because the harness is evidence-first, not because it was lucky.
- **Lesson:** exact md5 is a useful *fingerprint*, never a *correctness criterion*, for non-integer floats from parallel aggregators.

## BUG-2026-11-15-01 — Six environment/program bugs during Windows+M1 bring-up
1. `pyiceberg[sql]` extra **does not exist** → correct is `[sql-sqlite]`; extra `[sql]` prints warning and installs without SQLAlchemy (then `SqlCatalog` import fails with `ModuleNotFoundError`).
2. `np.array_split(df, n)` on a pandas DataFrame **returns ndarrays**, feeding `pa.Table.from_pandas` an ndarray → `AttributeError: 'numpy.ndarray' object has no attribute 'columns'`. Fixed with `iloc` slicing (`split_df`).
3. `SqlCatalog` has **no `.exists()`** — create_namespace raises on re-run; guarded with try/except.
4. `.as_uri()` warehouse path on Windows (`file:///C:/...`) was mangled into `/C:/...` → `WinError 123` at table metadata write. Fix: pass plain forward-slashed paths (`C:/...` normalized), no URI scheme.
5. `Table.files()` / `Table.inspect_files()` **do not exist in pyiceberg 0.12** → layout evidence via filesystem scan (`metadata_adapter.layout_summary`) reading parquet files directly. Documented in limitations.
6. `compare` used `glob()` (immediate children only) on `runs/*/​*.jsonl` nest-structure → reported "no run records" despite files existing. Fixed with `rglob()`.

## BUG-2026-11-15-03 — Process/PATH regressions (environment)
- `wsl`-launched shells: unqualified `$PATH` could carry Windows paths with spaces/parentheses into `export` unquoted → `syntax error near unexpected token '('`. Rule: always quote expansions; verify in `wsl -lc` first.
- WSL `/root` checkout tags: `WSL2 kernel missing ip_tables/iso9660 modules` (custom sched_ext kernel in `.wslconfig`) — outside this repo, resolved + documented: Docker Desktop + stock kernel.
- `uv` and Harbor installed but PATH did not include `~/.local/bin` — always extend PATH inside WSL scripts.

## BUG-2026-11-15-06 — M4 wiring slips (C++/Linux-only mismatch)
1. **`# Copyright 2026` used as a C++ comment** — a plain-text search&replace propagated Python-style comments into C++ files → `invalid preprocessing directive error` at compile time. Fixed across 6 files; lesson: when sed-ing across languages, scope the pattern to the language, then rebuild and let the compiler be the referee.
2. **Sed also matched `#` comments in `CMakeLists.txt`** (which legitimately uses `#`) and briefly rewrote them to `//`, which CMake does not recognize as comments. Restored; cmake build re-verified from scratch.
3. **Cross-platform binary mismatch:** the committed C++ build is Linux-only; tests must not `exec` a Linux ELF on Windows. Gate is platform **and** binary existence; on other platforms the UI shows `unavailable`, never a mislabeled substitute.

## BUG-2026-11-15-05 — Four bugs found during M3 wiring (rewrite + evidence)
1. **Data-file accumulation on re-generate:** pyiceberg `drop_table()` never removes data files; rerunning `generate` silently doubled the fixture (60 files / 120k rows) while `inspect` reported it as truth. Fix: drop catalog entry first, then `shutil.rmtree` the table dir (drop must happen first — it reads the metadata pointer). Regression test: `test_generate.py`.
2. **Rewrite had the same accumulation pattern** — same fix applied to `rewrite --target`.
3. **`report`/`compare` picked the wrong record:** `rglob` sorted filenames and took the absolute latest `*.jsonl`, which after a `rewrite` run is a rewrite-only record → empty comparison tables and a **vacuous `rowset_match: true`**. Certification code must not be vacuous. Fix: `_latest_benchmark_records()` selects only records containing benchmark `results`. Lesson: "rowset_match: true" on empty inputs is a *bug*, not a pass.
4. **Minor:** report's static "Three repetitions" text became a stale claim once repetitions were configurable — now parameterized from the record.

## BUG-2026-11-15-04 — Two bugs found during M2 wiring (signals)
1. `FileMetaData.row_groups` attribute **does not exist** in pyarrow → correct API is `md.row_group(i)` looping `md.num_row_groups`; direct attribute access raised `AttributeError` and signals silently fell back to `None` (test caught it: `predicate_overlap` returned `None` where overlap existed).
2. Categorical min/max stats can arrive as **bytes**; `str()` produced `"b'growth'..."` and would have failed containment for string predicates. Fixed with `_decode()` (bytes→utf-8), verified by tests.
3. Related: initial multi-column `rg.column(name)` assumption — `row_group().column()` takes **positional index**, not column names (col_by_name helper handles it).

## Notes on non-bugs (diagnose first)
- float aggregate mismatch above is **not** a logic error (raw md5 comparison of parallel-aggregated floats is invalid).
- `git` warnings during runs: "fatal: not a git repository" before repo init — expected, then fixed by initializing the repo.
