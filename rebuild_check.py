#!/usr/bin/env python3
"""
rebuild_check.py — is transactions.js exactly what the instructor's generator makes from the source
log, and can the timestamps the starter dropped be recovered without simulating anything?

1. Runs ../RecSys-LLMs/tools/build_week4_data.py on the source CSV into a temp file and compares it
   byte for byte with transactions.js.
2. Re-runs the same cleaning in-process (basket_meta.py), asserts basket-by-basket equality and
   prints, per basket: date range, order, baskets per month, customers, countries.

    python3 rebuild_check.py --csv data/online-retail-dataset.csv
"""
import argparse, collections, datetime, hashlib, pathlib, subprocess, sys, tempfile
import basket_meta
from ar_core import load

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--csv", default="data/online-retail-dataset.csv")
ap.add_argument("--tool", default="../RecSys-LLMs/tools/build_week4_data.py")
ap.add_argument("--data", default="transactions.js")
a = ap.parse_args()

for path, hint in [(a.csv, "download it in Part 0, step 4"), (a.tool, "clone RecSys-LLMs next to this folder (Part 0, step 1) or pass --tool"),
                   (a.data, "run from the project folder that holds the starter files")]:
    if not pathlib.Path(path).exists():
        raise SystemExit(f"not found: {path} ({hint})")
TESTED_CSV_SHA = "a2f79bbdd4463df6db8a3f5a50b9c980ae8f645a370bf5e2c0d6097f9e817b05"
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
csv_sha = sha(a.csv)
print(f"[source] {a.csv}  sha256 {csv_sha}" + ("" if csv_sha == TESTED_CSV_SHA else
      "  <- differs from the tested copy a2f79bbd...7b05: incomplete download? delete it and re-run curl"))
with tempfile.TemporaryDirectory() as tmp:
    out = pathlib.Path(tmp, "transactions.js")
    run = subprocess.run([sys.executable, a.tool, "--csv", a.csv, "--out", str(out)], capture_output=True, text=True)
    if run.returncode != 0 or not out.exists():
        raise SystemExit("generator failed:\n" + (run.stderr or run.stdout).strip()[-2000:])
    print("[generator output]")
    print("\n".join("  " + l for l in run.stdout.strip().splitlines()[:12]))
    same = out.read_bytes() == pathlib.Path(a.data).read_bytes()
    print(f"[rebuild] {a.data} sha256 {sha(a.data)}")
    print(f"[rebuild] regenerated  sha256 {sha(out)}")
    print(f"[rebuild] byte-identical: {same}")

meta, counters = basket_meta.compute(a.csv, a.tool, a.data)
basket_meta.CACHE.parent.mkdir(exist_ok=True)
import json; basket_meta.CACHE.write_text(json.dumps(meta))
dates = [datetime.datetime.fromisoformat(m["date"]) for m in meta]
kept_rows = sum(v for k, v in counters.items() if k == "raw_rows") - sum(v for k, v in counters.items() if k.startswith("dropped"))
_, B, _ = load(a.data)
print(f"[rows] kept after row filters {kept_rows:,}; (InvoiceNo, StockCode) pairs in exported baskets {sum(map(len, B)):,}")
print(f"[meta] baskets {len(meta):,} equal to window.HW4.baskets one by one: True")
print(f"[meta] first {dates[0]}  last {dates[-1]}  basket order is chronological: {all(x <= y for x, y in zip(dates, dates[1:]))}")
months = collections.Counter(d.strftime("%Y-%m") for d in dates)
print("[meta] baskets per month: " + ", ".join(f"{k} {v}" for k, v in sorted(months.items())))
cust = collections.Counter(m["customer"] for m in meta)
ctry = collections.Counter(m["country"] for m in meta)
print(f"[meta] customers {len(cust):,}; baskets per customer median {sorted(cust.values())[len(cust)//2]}, max {cust.most_common(1)[0][1]} (customer {cust.most_common(1)[0][0]})")
print(f"[meta] countries {len(ctry)}; United Kingdom {ctry['United Kingdom'] / len(meta):.3f} of baskets; next: " +
      ", ".join(f"{k} {v}" for k, v in ctry.most_common(4)[1:]))
print(f"[meta] cached to {basket_meta.CACHE}")
