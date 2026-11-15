#!/usr/bin/env python3
"""Milestone 0 spike: one scripted baseline and candidate run on the same data, exact result comparison.

Layouts:
  baseline  -> unsorted data, many small files
  candidate -> data sorted by (category, ts), few larger files
Same synthetic rows in both. Exit 0 only if correctness matches AND at least one Iceberg table demonstrably exists.
"""
import hashlib, json, os, sys, shutil
from pathlib import Path
import numpy as np
import pyarrow as pa
import pandas as pd

HERE = Path("/root/iceberg-guard-spike")
WH = (HERE / "warehouse").as_uri()
CAT_DB = HERE / "catalog.db"
SEED = 20261115
N = 60_000

def log(s):
    print(f"\n== {s} ==", flush=True)

def make_data():
    rng = np.random.default_rng(SEED)
    ts = np.arange(N, dtype=np.int64) * 17 + 1_700_000_000
    # power-law-ish skew on category, plus a uniform tenant
    cats = np.array(["growth", "core", "legacy", "experiment"])
    cat = rng.choice(cats, size=N, p=[0.55, 0.25, 0.12, 0.08])
    tenant = np.array([f"tenant-{i%400:03d}" for i in range(N)])
    join_key = rng.integers(1, 50_000, size=N).astype(np.int64)
    measure = np.round(rng.lognormal(mean=2.0, sigma=1.1, size=N), 6)
    return pd.DataFrame({"ts": ts, "category": cat, "tenant": tenant,
                         "join_key": join_key, "measure": measure})

log(f"ice2 run, seed={SEED}, rows={N}")
df = make_data()
print("fixture head:", df.head(3).to_dict("records"))
print("category distribution:", df.category.value_counts().to_dict())

log("pyiceberg version")
import pyiceberg
print("pyiceberg", pyiceberg.__version__)

from pyiceberg.catalog import load_catalog
import sqlite3

shutil.rmtree(HERE / "warehouse", ignore_errors=True)
if CAT_DB.exists():
    CAT_DB.unlink()
cat = load_catalog(
    "spike",
    **{
        "type": "sql",
        "uri": f"sqlite:///{CAT_DB}",
        "warehouse": WH,
    },
)
cat.purge_table = getattr(cat, "purge_table", lambda *a, **k: None)  # never auto-delete
cat.create_namespace("spike")

pschema = pa.schema([
    ("ts", pa.int64()),
    ("category", pa.string()),
    ("tenant", pa.string()),
    ("join_key", pa.int64()),
    ("measure", pa.float64()),
])

def split_df(frame, parts):
    idx = np.array_split(np.arange(len(frame)), parts)
    return [frame.iloc[i] for i in idx if len(i)]

def build(name, batches):
    ident = ("spike", name)
    if cat.table_exists(ident):
        cat.drop_table(ident)
    t = cat.create_table(ident, schema=pschema)
    with t.transaction() as tx:
        for batch in batches:
            tx.append(pa.Table.from_pandas(batch, schema=pschema, preserve_index=False))
    return cat.load_table(ident)

log("baseline: unsorted, 30 small files")
base = build("events_many_small", split_df(df, 30))
log("candidate: sorted by (category, ts), 4 largish files")
cand_df = df.sort_values(["category", "ts"]).reset_index(drop=True)
cand = build("events_sorted_compact", split_df(cand_df, 4))

log("iceberg metadata evidence")
for t in (base, cand):
    ident_str = t.name()[-1] if isinstance(t.name(), tuple) else str(t.name()).strip("()'").split(", ")[-1].strip("'")
    try:
        files = list(t.inspect_files())
        sizes = [f.file_size_in_bytes for f in files if getattr(f, "file_size_in_bytes", None)]
        counts = [f.record_count for f in files if getattr(f, "record_count", None)]
        print(f"{ident_str}: files={len(files)} bytes_total={sum(sizes) if sizes else 'unknown'} rows={sum(counts) if counts else 'unknown'} snapshots={len(t.metadata.snapshots)}")
        if sizes:
            print(f"{ident_str}: min_file_bytes={min(sizes)} max_file_bytes={max(sizes)} mean_file_bytes={sum(sizes)//len(sizes)}")
    except Exception as e:
        print(f"{ident_str}: inspect_files failed ({type(e).__name__}: {e}); falling back to filesystem scan")
        p = HERE / "warehouse" / "spike" / ident_str
        data_files = sorted(p.rglob("*.parquet")) if p.exists() else []
        print(f"{ident_str}: datafiles_on_disk={len(data_files)} walk_path={p} bytes_total={sum(f.stat().st_size for f in data_files)}")

log("correctness: read both tables, canonicalize, compare")
pa_base = base.scan().to_arrow().to_pandas()
pa_cand = cand.scan().to_arrow().to_pandas()
print("rows baseline=", len(pa_base), "candidate=", len(pa_cand))
key = ["ts", "category", "tenant", "join_key", "measure"]
canon_base = pa_base.sort_values(key).reset_index(drop=True)
canon_cand = pa_cand.sort_values(key).reset_index(drop=True)
h = lambda d: hashlib.md5(d.to_csv(index=False).encode()).hexdigest()
hb, hc = h(canon_base), h(canon_cand)
print("baseline_md5=", hb)
print("candidate_md5=", hc)
match = hb == hc and len(canon_base) == len(canon_cand)
print("ROWSET_MATCH:", match)

log("query evidence (pyiceberg filters; no timing claims)")
res_q_base = base.scan(row_filter='"category" == \'growth\' AND "ts" > 1700600000').to_arrow().num_rows
res_q_cand = cand.scan(row_filter='"category" == \'growth\' AND "ts" > 1700600000').to_arrow().num_rows
print("filtered_rows baseline=", res_q_base, "candidate=", res_q_cand, "equal=", res_q_base == res_q_cand)

log("duckdb iceberg probe (may fail; isolated)")
try:
    import duckdb, glob
    meta_base = sorted(glob.glob(str(HERE / "warehouse" / "spike" / "events_many_small" / "metadata" / "*.metadata.json")))[-1]
    con = duckdb.connect()
    con.execute("INSTALL iceberg; LOAD iceberg;")
    con.execute("SET unsafe_enable_version_guessing=true;")
    t = con.execute(f"SELECT count(*), sum(measure) FROM iceberg_scan('{meta_base}')").fetchall()
    print("duckdb iceberg_scan count/sum:", t)
except Exception as e:
    print("duckdb iceberg probe failed honestly:", type(e).__name__, str(e)[:400])

log("SPIKE RESULT")
ok = match
print(json.dumps({"seed": SEED, "rows": N, "rowset_match": match, "ok": ok}, indent=2))
sys.exit(0 if ok else 1)
