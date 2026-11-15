# Copyright 2026 The iceberg-guard Authors
# Licensed under the Apache License, Version 2.0 (the "License") with NOTICE; see LICENSE file.
from iceberg_guard.cli import main


def test_generate_is_idempotent_no_data_file_accumulation(tmp_path):
    wh = tmp_path / "warehouse"
    for _ in range(2):  # second generate must NOT double the files (drop_table leaves data behind)
        assert main(["generate", "--rows", "3000", "--seed", "5", "--warehouse", str(wh)]) == 0
    small = len(list((wh / "spike" / "events_many_small").rglob("*.parquet")))
    compact = len(list((wh / "spike" / "events_sorted_compact").rglob("*.parquet")))
    assert small == 30
    assert compact == 4
