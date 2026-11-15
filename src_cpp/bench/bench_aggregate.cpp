// Copyright 2026 The iceberg-guard Authors
// Licensed under the Apache License, Version 2.0
#include "iceberg_guard/aggregate.hpp"
#include <cinttypes>
#include <cstdio>

using namespace iceberg;

int main() {
    AggregateStats acc;
    for (long i = 0; i < 5'000'000; ++i) {
        const double ts = 1700000000.0 + static_cast<double>(i % 100'000) * 17.0;
        acc.add(static_cast<std::uint64_t>(100 + (i * 13) % 900),
                static_cast<std::uint64_t>(30000 + (i * 97) % 5000),
                ts, ts + 999, true);
    }
    const auto s = acc.summary();
    std::printf("bench done: files=%" PRIu64 " rows=%" PRIu64 " bytes=%" PRIu64 " ns/add done\n",
                s.files, s.rows, s.bytes);
    return 0;
}
