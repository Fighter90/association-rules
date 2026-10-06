#!/usr/bin/env python3
"""
audit_data.py — what the HW4 starter really contains, checked against what prompt.md (the week4
readme) and script.js say about it. Reads files only; changes nothing.

    python3 audit_data.py --data transactions.js --readme prompt.md --script script.js
"""
import argparse, collections, re, statistics
from ar_core import load

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--data", default="transactions.js")
ap.add_argument("--readme", default="prompt.md")
ap.add_argument("--script", default="script.js")
a = ap.parse_args()

raw, B, desc = load(a.data)
n = len(B)
items = collections.Counter(s for b in B for s in set(b))
lens = [len(b) for b in B]
print(f"[data] N_BASKETS {raw['N_BASKETS']} (len(baskets) {n}); N_ITEMS {raw['N_ITEMS']} (distinct in baskets {len(items)})")
print(f"[data] (basket, item) pairs {sum(lens):,}; basket size min {min(lens)}, median {statistics.median(lens):g}, mean {sum(lens)/n:.2f}, max {max(lens)}")
print(f"[matrix] invoice x item basket matrix {n:,} x {len(items):,} = {n * len(items):,} cells, {sum(lens):,} ones, density {sum(lens) / (n * len(items)):.4%}; "
      f"stored sparsely as one posting list (set of basket ids) per stock code")
print(f"[data] baskets with a repeated stock code: {sum(len(b) != len(set(b)) for b in B)}; single-item baskets: {sum(l < 2 for l in lens)}")
print(f"[data] baskets per item: median {statistics.median(items.values()):g}; items in >= 1% of baskets (>= {int(-(-0.01*n//1))}): {sum(c / n >= 0.01 for c in items.values())}")
print("[data] top 5 items:")
for s, c in items.most_common(5):
    print(f"    {s:7s} {desc[s]:40s} {c:5d}  {c / n:.4f}")
top = items.most_common(1)[0]
print(f"[bound] max single-item support P(B) = {top[1]}/{n} = {top[1]/n:.4f}. For any rule, lift = conf / P(B) >= conf / {top[1]/n:.4f};")
print(f"[bound] so every rule with confidence >= {top[1]/n:.4f} already has lift >= 1: the 'lift > 1' filter only bites below that confidence.")

rd = open(a.readme, encoding="utf-8").read()
print("[readme] numbers claimed:")
for pat in [r"\*\*384,911 kept rows\*\*", r"\*\*17,080 baskets\*\*", r"\*\*3,653 distinct items\*\*", r"1,959 of 17,080", r"11\.47%",
            r"2 passed /\s*0 failed / 9 pending", r"no usable per-basket timestamp", r"Do not simulate temporal data"]:
    print(f"    {'found' if re.search(pat, rd) else 'MISSING':7s} {pat}")

js = open(a.script, encoding="utf-8").read()
stubs = re.findall(r'throw new Error\("TODO\(hw4\): (\w+) is not implemented yet\."\)', js)
print(f"[script] TODO(hw4) stubs that throw: {len(stubs)} -> {', '.join(stubs) if stubs else 'none (implemented)'}")
if re.search(r"different confidence\s*\n?\s*\*?\s*and support value", js):
    print("[script] NOTE reverseRule doc comment says B -> A has a different 'confidence and support value'; support is symmetric (count(A u B)/N).")
for label, pat, what in [("test 10 (findFrequentItemsets)", r"pairs\.length === 0", "at least one frequent pair is returned, not which itemsets"),
                         ("test 11 (generateRules)", r"rules\.length === 0", "at least one rule is returned, not which rules")]:
    if re.search(pat, js):
        print(f"[script] NOTE {label} only checks that {what}.")
