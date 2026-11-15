// Copyright 2026 The iceberg-guard Authors
// Licensed under the Apache License, Version 2.0
// Minimal self-contained test runner (no external test framework needed).
#include "iceberg_guard/aggregate.hpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

using namespace iceberg;

static int failures = 0;
static void check(bool ok, const char* name) {
    if (ok) { std::printf("PASS %s\n", name); }
    else    { std::printf("FAIL %s\n", name); ++failures; }
}
static bool close(double a, double b, double rel_tol = 1e-9, double abs_tol = 1e-9) {
    return std::fabs(a - b) <= abs_tol + rel_tol * std::fabs(b);
}

int main() {
    {  // 1. empty input: zeros everywhere, never NaN
        AggregateStats acc;
        const auto s = acc.summary();
        check(s.files == 0 && s.rows == 0 && s.bytes == 0 && s.with_stats == 0
              && s.mean_file_bytes == 0.0 && s.variance_bytes == 0.0 && s.stdev_bytes == 0.0
              && s.size_cv == 0.0 && s.bytes_min == 0.0 && s.bytes_max == 0.0
              && s.ts_min == 0.0 && s.ts_max == 0.0, "empty input is zero, not NaN");
    }
    {  // 2. single file: zero variance, zero cv
        AggregateStats acc;
        acc.add(100, 33092, 1.0, 100.0, true);
        const auto s = acc.summary();
        check(s.files == 1 && s.rows == 100 && s.bytes == 33092, "single file counts");
        check(close(s.mean_file_bytes, 33092.0) && close(s.variance_bytes, 0.0)
              && close(s.stdev_bytes, 0.0) && close(s.size_cv, 0.0), "single file: var=0 cv=0");
        check(close(s.ts_min, 1.0) && close(s.ts_max, 100.0), "single file ts extent");
    }
    {  // 3. known Welford values: bytes 100,110,120 → mean 110, population var 66.666..., cv=stdev/mean
        AggregateStats acc;
        acc.add(10, 100, 1.0, 10.0, true);
        acc.add(20, 110, 2.0, 20.0, true);
        acc.add(30, 120, 3.0, 30.0, true);
        const auto s = acc.summary();
        check(s.files == 3 && s.rows == 60 && s.bytes == 330, "three-file sums");
        check(close(s.mean_file_bytes, 110.0), "mean");
        check(close(s.variance_bytes, 200.0 / 3.0), "population variance");
        const double expect_stdev = std::sqrt(200.0 / 3.0);
        check(close(s.stdev_bytes, expect_stdev), "stdev");
        check(close(s.size_cv, expect_stdev / 110.0), "cv");
        check(close(s.bytes_min, 100.0) && close(s.bytes_max, 120.0), "min/max");
    }
    {  // 4. files without stats don't pollute ts extent; empty with_stats → zeros
        AggregateStats acc;
        acc.add(10, 100, 5.0, 50.0, true);
        acc.add(10, 200, 6.0, 60.0, false);   // no ts info → excluded from ts extent
        acc.add(10, 300, 7.0, 70.0, true);
        const auto s = acc.summary();
        check(s.with_stats == 2, "with_stats counts only stats_present files");
        check(close(s.ts_min, 5.0) && close(s.ts_max, 70.0), "ts extent ignores statless files");
        check(s.bytes == 600 && s.files == 3, "statless files still count for size stats");

        AggregateStats none;
        none.add(10, 100, 1.0, 10.0, false);
        const auto sn = none.summary();
        check(sn.with_stats == 0 && sn.ts_min == 0.0 && sn.ts_max == 0.0, "no stats → ts zeros, never guessed");
    }
    {  // 5. large numbers: 2^63-ish ts and big bytes stay exact in double arithmetic for integers < 2^53
        AggregateStats acc;
        const std::uint64_t big = 1701019983ULL;
        acc.add(1ULL << 40, 1ULL << 50, static_cast<double>(big), static_cast<double>(big) + 1e6, true);
        const auto s = acc.summary();
        check(s.files == 1 && s.bytes == (1ULL << 50), "big values sum exactly");
    }
    {  // 6. reset() clears all state
        AggregateStats acc;
        acc.add(1, 1, 1.0, 1.0, true);
        acc.reset();
        const auto s = acc.summary();
        check(s.files == 0 && s.rows == 0 && s.bytes == 0, "reset clears accumulator");
    }
    std::printf("%s (%d failure%s)\n", failures == 0 ? "ALL PASS" : "FAILURES",
                failures, failures == 1 ? "" : "s");
    return failures == 0 ? 0 : 1;
}
