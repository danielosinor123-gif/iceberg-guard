# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0
cmake_minimum_required(VERSION 3.16)
project(iceberg_guard_core VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(ICEBERG_GUARD_SANITIZERS "Enable AddressSanitizer + UBSan on the library and tests" OFF)

add_library(iceberg_guard_core src/aggregate.cpp)
target_include_directories(iceberg_guard_core PUBLIC include)
target_compile_options(iceberg_guard_core PRIVATE -Wall -Wextra -Werror)

if(ICEBERG_GUARD_SANITIZERS)
  target_compile_options(iceberg_guard_core PUBLIC -fsanitize=address,undefined -fno-sanitize-recover=all)
  target_link_options(iceberg_guard_core PUBLIC -fsanitize=address,undefined)
endif()

add_executable(iceberg-guard-agg src/main.cpp)
target_link_libraries(iceberg-guard-agg PRIVATE iceberg_guard_core)

add_executable(test_aggregate tests/test_aggregate.cpp)
target_link_libraries(test_aggregate PRIVATE iceberg_guard_core)

add_executable(bench_aggregate bench/bench_aggregate.cpp)
target_link_libraries(bench_aggregate PRIVATE iceberg_guard_core)

enable_testing()
add_test(NAME aggregate COMMAND test_aggregate)
