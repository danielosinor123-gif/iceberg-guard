$ErrorActionPreference = "Stop"
.\.venv\Scripts\Activate.ps1
python scripts\generate_fixture.py @args
iceberg-guard inspect
iceberg-guard benchmark --layout both --manifest config\example-workload.yaml
iceberg-guard compare
