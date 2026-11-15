# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
"""Thin wrapper: regenerate the fixture exactly as the CLI does. Uses only seeded inputs."""
import sys

from iceberg_guard.cli import main

if __name__ == "__main__":
    sys.exit(main(["generate", *sys.argv[1:]]))
