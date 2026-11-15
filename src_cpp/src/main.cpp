// Copyright 2026 The iceberg-guard Authors
// Licensed under the Apache License, Version 2.0
// iceberg-guard-agg: read normalized tab-separated file statistics on stdin,
// emit the aggregate as JSON on stdout.
// Input line:  <rows>\t<bytes>\t<ts_min>\t<ts_max>\t<stats_present(0|1)>
// Usage:       iceberg-guard-agg [--bench N]
#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <chrono>

#include "iceberg_guard/aggregate.hpp"

using namespace iceberg;

static void print_summary(const AggregateSummary& s) {
    std::printf(
        "{\"files\":%" PRIu64 ",\"rows\":%" PRIu64 ",\"bytes\":%" PRIu64 ","
        "\"mean_file_bytes\":%.17g,\"variance_bytes\":%.17g,\"stdev_bytes\":%.17g,"
        "\"size_cv\":%.17g,\"bytes_min\":%.17g,\"bytes_max\":%.17g,"
        "\"ts_min\":%.17g,\"ts_max\":%.17g,\"with_stats\":%" PRIu64 "}\n",
        s.files, s.rows, s.bytes, s.mean_file_bytes, s.variance_bytes,
        s.stdev_bytes, s.size_cv, s.bytes_min, s.bytes_max, s.ts_min, s.ts_max,
        s.with_stats);
}

static int run_bench(long n) {
    AggregateStats acc;
    const auto t0 = std::chrono::steady_clock::now();
    for (long i = 0; i < n; ++i) {
        // deterministic pseudo-input, no allocation, no I/O
        const double ts = 1700000000.0 + static_cast<double>(i % 100000) * 17.0;
        acc.add(static_cast<std::uint64_t>(100 + (i * 13) % 900),
                static_cast<std::uint64_t>(30000 + (i * 97) % 5000),
                ts, ts + 999, true);
    }
    const AggregateSummary s = acc.summary();
    const auto t1 = std::chrono::steady_clock::now();
    const double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    std::printf("bench_lines=%ld elapsed_ms=%.3f adds_per_sec=%.1f\n", n, ms,
                static_cast<double>(n) / (ms / 1000.0));
    print_summary(s);
    return 0;
}

int main(int argc, char** argv) {
    if (argc == 3 && std::strcmp(argv[1], "--bench") == 0) {
        const long n = std::atol(argv[2]);
        if (n <= 0) {
            std::fprintf(stderr, "bench: N must be positive\n");
            return 2;
        }
        return run_bench(n);
    }

    AggregateStats acc;
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        // fast path: scan via std::sscanf
        unsigned long long rows = 0, bytes = 0;
        double ts_min = 0.0, ts_max = 0.0;
        int stats = 0;
        if (std::sscanf(line.c_str(), "%llu\t%llu\t%lf\t%lf\t%d",
                        &rows, &bytes, &ts_min, &ts_max, &stats) != 5) {
            std::fprintf(stderr, "parse error: '%s'\n", line.c_str());
            return 2;
        }
        if (stats != 0 && stats != 1) {
            std::fprintf(stderr, "stats_present must be 0/1: '%s'\n", line.c_str());
            return 2;
        }
        acc.add(static_cast<std::uint64_t>(rows), static_cast<std::uint64_t>(bytes),
                ts_min, ts_max, stats != 0);
    }
    print_summary(acc.summary());
    return 0;
}
