#!/usr/bin/env python3
"""
basket_meta.py — recover InvoiceNo / InvoiceDate / CustomerID / Country for every basket of
transactions.js. Nothing is simulated: the instructor's own generator (tools/build_week4_data.py)
is re-run on the source CSV, its baskets are asserted equal to window.HW4.baskets one by one, and
the first source row of each invoice gives the date, customer and country.

Used as a module by rebuild_check.py, rule_card.py and temporal_check.py. Result is cached in
results/basket_meta.json.
"""
import csv, datetime, importlib.util, json, pathlib
from ar_core import load

CACHE = pathlib.Path("results/basket_meta.json")

def _parse_date(s):
    for fmt in ("%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%m/%d/%y %H:%M"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"unknown date format: {s!r}")

def load_tool(tool_path):
    spec = importlib.util.spec_from_file_location("build_week4_data", tool_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def compute(csv_path, tool_path, data="transactions.js"):
    bw = load_tool(tool_path)
    kept, counters = bw.read_and_filter(csv_path)
    canon = bw.canonical_descriptions(kept)
    baskets, invoices = bw.build_baskets(kept, canon)
    _, B, _ = load(data)
    if len(baskets) != len(B) or any(sorted(i["stock"] for i in x) != sorted(y) for x, y in zip(baskets, B)):
        raise SystemExit("rebuilt baskets differ from transactions.js - wrong CSV?")
    first = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["InvoiceNo"] not in first:
                first[r["InvoiceNo"]] = (r["InvoiceDate"], r["CustomerID"].split(".")[0], r["Country"])
    meta = [dict(invoice=inv, date=_parse_date(first[inv][0]).isoformat(timespec="minutes"),
                 customer=first[inv][1], country=first[inv][2]) for inv in invoices]
    return meta, counters

def get(csv_path="data/online-retail-dataset.csv", tool_path="../RecSys-LLMs/tools/build_week4_data.py", data="transactions.js"):
    if CACHE.exists():
        meta = json.loads(CACHE.read_text())
        if len(meta) == len(load(data)[1]):
            return meta
    meta, _ = compute(csv_path, tool_path, data)
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(meta))
    return meta
