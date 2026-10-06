#!/usr/bin/env python3
"""
temporal_check.py — do rules mined on an earlier period still hold later? Uses the real invoice
dates recovered by rebuild_check.py (results/basket_meta.json); nothing is simulated.

Mines rules on baskets dated before --split with the same thresholds, then measures every rule on
the baskets from --split on: is its lift still > 1, does it still pass both thresholds, how much did
confidence move; and which later rules did not exist earlier.

    python3 temporal_check.py --split 2011-09-01 --support 0.01 --confidence 0.3
"""
import argparse, json, pathlib, statistics
import ar_core

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--data", default="transactions.js")
ap.add_argument("--split", default="2011-09-01")
ap.add_argument("--support", type=float, default=0.01)
ap.add_argument("--confidence", type=float, default=0.3)
ap.add_argument("--show", type=int, default=5)
a = ap.parse_args()
raw, B, desc = ar_core.load(a.data)
meta_path = pathlib.Path("results/basket_meta.json")
if not meta_path.exists():
    raise SystemExit("results/basket_meta.json not found: run python3 rebuild_check.py first (step T4)")
meta = json.loads(meta_path.read_text())
if len(meta) != len(B):
    raise SystemExit(f"results/basket_meta.json has {len(meta)} baskets, {a.data} has {len(B)}: re-run python3 rebuild_check.py")
early = [b for b, m in zip(B, meta) if m["date"] < a.split]
late = [b for b, m in zip(B, meta) if m["date"] >= a.split]
print(f"[split] before {a.split}: {len(early)} baskets ({meta[0]['date'][:10]} .. {meta[len(early) - 1]['date'][:10]}); "
      f"from {a.split}: {len(late)} baskets (.. {meta[-1]['date'][:10]})")

_, R1 = ar_core.rules(early, a.support, a.confidence)
_, R2 = ar_core.rules(late, a.support, a.confidence)
idx2 = ar_core.BitIndex(late); n2 = idx2.n
later = {}
for r in R1:
    ca, cb, cab = idx2.count(r["A"]), idx2.count(r["B"]), idx2.count(r["A"] + r["B"])
    conf = cab / ca if ca else 0.0
    later[(r["A"], r["B"])] = dict(ca=ca, cb=cb, cab=cab, conf=conf, lift=(conf / (cb / n2) if ca and cb else 0.0),
                                   passes=ca > 0 and cab / n2 >= a.support and conf >= a.confidence)
keys2 = {(r["A"], r["B"]) for r in R2}
L = list(later.values())
print(f"[early] rules {len(R1)} at support >= {a.support}, confidence >= {a.confidence}")
print(f"[later] of these: lift > 1 later {sum(x['lift'] > 1 for x in L)} ({sum(x['lift'] > 1 for x in L) / len(L):.1%}); "
      f"lift > 2 later {sum(x['lift'] > 2 for x in L)}; still pass both thresholds {sum(x['passes'] for x in L)} ({sum(x['passes'] for x in L) / len(L):.1%})")
ratios = [later[(r['A'], r['B'])]['conf'] / r['confidence'] for r in R1]
print(f"[later] confidence later / earlier: median {statistics.median(ratios):.3f}; quartiles {statistics.quantiles(ratios, n=4)[0]:.3f} .. {statistics.quantiles(ratios, n=4)[2]:.3f}")
print(f"[later] rules mined on the later period: {len(R2)}; of them new (absent from the earlier rule list): {len(keys2 - set(later))}")
def show(title, items):
    print(title)
    for r, x in items[:a.show]:
        print(f"    conf {r['confidence']:.3f} -> {x['conf']:.3f}  lift {r['lift']:6.2f} -> {x['lift']:6.2f}  ({r['cab']}/{r['ca']} -> {x['cab']}/{x['ca']})  "
              f"{ar_core.name(r['A'], desc)} -> {ar_core.name(r['B'], desc)}")
pairs = [(r, later[(r['A'], r['B'])]) for r in R1]
show("[drop] largest confidence drops:", sorted(pairs, key=lambda t: t[1]["conf"] - t[0]["confidence"]))
idx1 = ar_core.BitIndex(early); n1 = idx1.n
new = [r for r in R2 if (r["A"], r["B"]) not in later]
new.sort(key=lambda r: -r["cab"])
print("[new] largest rules that exist only later (earlier counts in brackets):")
for r in new[:a.show]:
    ca1, cab1 = idx1.count(r["A"]), idx1.count(r["A"] + r["B"])
    print(f"    {r['cab']}/{r['ca']} conf {r['confidence']:.3f} lift {r['lift']:6.2f}  [earlier {cab1}/{ca1}]  {ar_core.name(r['A'], desc)} -> {ar_core.name(r['B'], desc)}")
