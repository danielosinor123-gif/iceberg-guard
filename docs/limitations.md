# Limitations & known gaps (MVP)

- DuckDB reads Iceberg with `SET unsafe_enable_version_guessing=true`; Spec compliance of tables is assumed, not guaranteed — the setting exists only for local fixtures and is recorded in every run record's env block.
- PyIceberg 0.12 has no public per-file stats API; layout signals here are **filesystem measurements** (file count/bytes/skew), not Iceberg manifests.
- No automated cold/warm cache protocol; no concurrency dimension; no cost model for candidate rewrite time yet.
- Query timeouts are watchdog-interrupt based (`connection.interrupt()`); a pathological query may not honor them exactly.
- No Firebolt anything: all measurements are local DuckDB/PyIceberg over synthetic data. No production, capacity, or vendor claims are made or implied.
- **Floating-point comparison convention:** `iceberg_guard.fixture.df_digest` rounds numeric columns to 1e-9 (9 decimal places) before hashing when comparing layouts. Raw md5 (unrounded) is also computed for logging but must not be used for pass/fail — DuckDB re-associates float aggregates across file splits, so bitwise equality is not a correctness criterion. Integer/string results are always compared exactly.
- Layout signals are filesystem measurements (file count/bytes/skew), not Iceberg manifests (PyIceberg 0.12 exposes no public per-file stats API).
- Benchmarks are not in CI. CI runs unit tests only.
- AI assistance: this project advances with AI pair-programming; all claims are verified by the listed tests and the SPIKE results, and the human owner is responsible for every claim made about this repository.
