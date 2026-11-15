#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
python scripts/generate_fixture.py "$@"
iceberg-guard inspect
iceberg-guard benchmark --layout both --manifest config/example-workload.yaml
iceberg-guard compare
