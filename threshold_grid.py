#!/usr/bin/env python3
"""
threshold_grid.py — how minimum support and minimum confidence change the number of frequent
itemsets and rules, and what the 'lift > 1' filter actually removes.

    python3 threshold_grid.py --plot figures/fig1_thresholds.png
    python3 threshold_grid.py --cross-check          # FP-Growth (mlxtend) vs bitset Apriori on every support
"""
import argparse, math, statistics, time
import ar_core

SUPPORTS = [0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.05]
CONFIDENCES = [0.1, 0.3, 0.5, 0.6, 0.8]

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--data", default="transactions.js")
ap.add_argument("--plot")
ap.add_argument("--cross-check", action="store_true")
a = ap.parse_args()
raw, B, desc = ar_core.load(a.data)
n = len(B)

if a.cross_check:
    idx = ar_core.BitIndex(B)
    for s in SUPPORTS:
        t = time.time(); f1 = ar_core.mine_fpgrowth(B, s); t1 = time.time() - t
        t = time.time(); f2 = ar_core.mine_bitset(B, s, idx); t2 = time.time() - t
        print(f"[cross-check] support {s:<6} fpgrowth {len(f1):5d} itemsets ({t1:.1f} s)  bitset-apriori {len(f2):5d} ({t2:.1f} s)  identical: {f1 == f2}")

print(f"N = {n}; max single-item support {max(ar_core.BitIndex(B).bits[s].bit_count() for s in ['85123A']) / n:.4f} (85123A)")
print(f"{'minsup':>7} {'count>=':>7} {'itemsets':>8} {'by size':<38} {'minconf':>7} {'rules':>6} {'lift<=1':>7} {'min lift':>8} {'med lift':>8} {'k>=3':>5}")
grid = {}
for s in SUPPORTS:
    fi = ar_core.mine(B, s)
    sizes = {}
    for k in fi:
        sizes[len(k)] = sizes.get(len(k), 0) + 1
    for c in CONFIDENCES:
        rs = ar_core.rules_from(fi, n, c)
        grid[(s, c)] = (len(fi), len(rs))
        lifts = [r["lift"] for r in rs]
        print(f"{s:7.4f} {math.ceil(s * n - 1e-9):7d} {len(fi):8d} {str(sizes):<38} {c:7.2f} {len(rs):6d} {sum(l <= 1 for l in lifts):7d} "
              f"{(min(lifts) if lifts else float('nan')):8.3f} {(statistics.median(lifts) if lifts else float('nan')):8.2f} "
              f"{sum(len(r['A']) + len(r['B']) >= 3 for r in rs):5d}")
    print()

if a.plot:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    xs = [s * 100 for s in SUPPORTS]
    ax.plot(xs, [grid[(s, CONFIDENCES[0])][0] for s in SUPPORTS], "k--", marker="o", label="frequent itemsets")
    for c, col in zip(CONFIDENCES, ["#9ecae1", "#3182bd", "#e6550d", "#a63603", "#31a354"]):
        ys = [max(grid[(s, c)][1], 0.8) for s in SUPPORTS]
        ax.plot(xs, ys, marker="o", color=col, label=f"rules, min confidence {int(c * 100)}%")
    ax.axvline(1.0, color="grey", lw=0.8, ls=":")
    ax.set_xscale("log"); ax.set_yscale("log")
    from matplotlib.ticker import NullFormatter
    ax.set_xticks(xs); ax.set_xticklabels([f"{x:g}" for x in xs]); ax.xaxis.set_minor_formatter(NullFormatter())
    ax.text(5, 0.8, " 0 rules", fontsize=7, va="center")
    ax.set_xlabel("minimum support, % of 17,080 baskets"); ax.set_ylabel("count (log)")
    ax.legend(fontsize=7, frameon=False); ax.grid(alpha=0.3, which="both")
    fig.tight_layout(); fig.savefig(a.plot, dpi=200)
    print(f"[plot] {a.plot}")
