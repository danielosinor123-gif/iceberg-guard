// Copyright 2026 The iceberg-guard Authors
// Licensed under the Apache License, Version 2.0
#include "iceberg_guard/aggregate.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace iceberg {

void AggregateStats::add(std::uint64_t rows, std::uint64_t bytes,
                         double ts_min, double ts_max, bool stats_present) noexcept {
    ++files_;
    rows_ += rows;
    bytes_ += bytes;

    // Welford's online algorithm — numerically stable, single pass.
    const double x = static_cast<double>(bytes);
    const double n = static_cast<double>(files_);
    const double delta = x - mean_;
    mean_ += delta / n;
    const double delta2 = x - mean_;
    m2_ += delta * delta2;

    bytes_min_ = (n == 1.0) ? x : std::min(bytes_min_, x);
    bytes_max_ = (n == 1.0) ? x : std::max(bytes_max_, x);

    if (stats_present) {
        if (with_stats_ == 0) {
            ts_min_ = ts_min;
            ts_max_ = ts_max;
        } else {
            ts_min_ = std::min(ts_min_, ts_min);
            ts_max_ = std::max(ts_max_, ts_max);
        }
        ++with_stats_;
    }
}

AggregateSummary AggregateStats::summary() const noexcept {
    AggregateSummary s{};
    s.files = files_;
    s.rows = rows_;
    s.bytes = bytes_;
    s.with_stats = with_stats_;

    if (files_ == 0) {  // empty input: zeros everywhere, never NaN
        return s;
    }
    s.mean_file_bytes = mean_;
    s.variance_bytes = m2_ / static_cast<double>(files_);  // population variance
    s.stdev_bytes = std::sqrt(s.variance_bytes);
    s.size_cv = (mean_ != 0.0) ? s.stdev_bytes / mean_ : 0.0;
    s.bytes_min = bytes_min_;
    s.bytes_max = bytes_max_;
    s.ts_min = (with_stats_ == 0) ? 0.0 : ts_min_;
    s.ts_max = (with_stats_ == 0) ? 0.0 : ts_max_;
    return s;
}

void AggregateStats::reset() noexcept {
    files_ = 0; rows_ = 0; bytes_ = 0; with_stats_ = 0;
    mean_ = 0.0; m2_ = 0.0;
    bytes_min_ = 0.0; bytes_max_ = 0.0;
    ts_min_ = 0.0; ts_max_ = 0.0;
}

}  // namespace iceberg
