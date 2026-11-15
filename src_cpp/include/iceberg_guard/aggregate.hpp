// Copyright 2026 The iceberg-guard Authors
// Licensed under the Apache License, Version 2.0
// iceberg-guard core — streaming file-layout statistics accumulator.
// Scope deliberately narrow: aggregation over already-parsed file-level
// statistics (bytes, rows, min/max ts). No I/O, no Iceberg semantics, no
// vendor formats — a building block for the Python adapter, not a database.
#pragma once

#include <cstdint>

namespace iceberg {

struct AggregateSummary {
    uint64_t files = 0;
    uint64_t rows = 0;
    uint64_t bytes = 0;
    double mean_file_bytes = 0.0;
    double variance_bytes = 0.0;   // population variance (Welford, denominator n)
    double stdev_bytes = 0.0;
    double size_cv = 0.0;
    double bytes_min = 0.0;
    double bytes_max = 0.0;
    double ts_min = 0.0;           // 0 when with_stats == 0 (documented, never guessed)
    double ts_max = 0.0;           // 0 when with_stats == 0
    uint64_t with_stats = 0;
};

class AggregateStats {
public:
    void add(std::uint64_t rows, std::uint64_t bytes,
             double ts_min, double ts_max, bool stats_present) noexcept;
    AggregateSummary summary() const noexcept;
    void reset() noexcept;

private:
    std::uint64_t files_ = 0, rows_ = 0, bytes_ = 0, with_stats_ = 0;
    double mean_ = 0.0, m2_ = 0.0;        // Welford's online variance
    double bytes_min_ = 0.0, bytes_max_ = 0.0;
    double ts_min_ = 0.0, ts_max_ = 0.0;
};

}  // namespace iceberg
