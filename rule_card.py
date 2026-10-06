#!/usr/bin/env python3
"""
rule_card.py — everything needed to judge one rule A -> B: raw counts, support / confidence / lift
in both directions with the arithmetic written out, a 95% Wilson interval for the confidence, the
'headroom' (A-baskets without B — the only baskets a recommendation could still change), who the
baskets come from (customers, countries) and how the rule behaves month by month and before/after
a date split. Needs results/basket_meta.json (made by rebuild_check.py) for the last three parts.

    python3 rule_card.py --rule 22699 22423
    python3 rule_card.py --rule 22916 22917 --family "HERB MARKER"
"""
import argparse, collections, datetime, math, pathlib, json
import ar_core

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--data", default="transactions.js")
ap.add_argument("--rule", nargs=2, required=True, metavar=("A", "B"), help="stock codes; comma-separated for itemsets")
ap.add_argument("--split", default="2011-09-01")
ap.add_argument("--family", help="description substring: show how items of one product family co-occur")
a = ap.parse_args()
raw, B, desc = ar_core.load(a.data)
idx = ar_core.BitIndex(B)
n = idx.n
A = a.rule[0].split(","); C = a.rule[1].split(",")

def wilson(k, m, z=1.96):
    if m == 0: return (float("nan"),) * 2
    p = k / m; d = 1 + z * z / m
    c = (p + z * z / (2 * m)) / d; h = z * math.sqrt(p * (1 - p) / m + z * z / (4 * m * m)) / d
    return c - h, c + h

ca, cb, cab = idx.count(A), idx.count(C), idx.count(A + C)
print(f"A = {ar_core.name(A, desc)}")
print(f"B = {ar_core.name(C, desc)}")
print(f"N = {n}; count(A) = {ca}; count(B) = {cb}; count(A u B) = {cab}")
for lab, x, y, cx, cy in [("A -> B", A, C, ca, cb), ("B -> A", C, A, cb, ca)]:
    conf = cab / cx; base = cy / n; lift = conf / base; lo, hi = wilson(cab, cx)
    print(f"[{lab}] support = {cab}/{n} = {cab / n:.4f} ({cab / n * 100:.2f}%)")
    print(f"[{lab}] confidence = {cab}/{cx} = {conf:.4f} ({conf * 100:.2f}%), 95% Wilson [{lo:.3f}, {hi:.3f}]")
    print(f"[{lab}] baseline P(consequent) = {cy}/{n} = {base:.4f}; lift = {conf:.4f} / {base:.4f} = {lift:.4f}")
    print(f"[{lab}] headroom: {cx - cab} antecedent baskets without the consequent ({(cx - cab) / cx:.1%} of {cx})")

meta_path = pathlib.Path("results/basket_meta.json")
if meta_path.exists():
    meta = json.loads(meta_path.read_text())
    joint = [i for i in range(n) if (idx.mask(A + C) >> i) & 1]
    cust = collections.Counter(meta[i]["customer"] for i in joint)
    ctry = collections.Counter(meta[i]["country"] for i in joint)
    top3 = cust.most_common(3)
    print(f"[who] A u B baskets come from {len(cust)} customers; top customer {top3[0][0]} has {top3[0][1]} ({top3[0][1] / len(joint):.1%}); "
          f"top 3 {sum(c for _, c in top3) / len(joint):.1%}; United Kingdom {ctry['United Kingdom'] / len(joint):.1%}")
    mA, mC = idx.mask(A), idx.mask(C)
    def window(pred):
        ids = [i for i in range(n) if pred(meta[i]["date"])]
        w = sum(1 << i for i in ids)
        na, nb, nab = (mA & w).bit_count(), (mC & w).bit_count(), (mA & mC & w).bit_count()
        conf = nab / na if na else float("nan"); lift = conf / (nb / len(ids)) if na and nb else float("nan")
        return len(ids), nab, na, nb, conf, lift
    print("[month] month    N    A&B    A    B   conf   lift")
    for m in sorted({x["date"][:7] for x in meta}):
        N_, nab, na, nb, conf, lift = window(lambda d, m=m: d.startswith(m))
        print(f"[month] {m} {N_:5d} {nab:5d} {na:5d} {nb:4d} {conf:6.3f} {lift:6.2f}")
    for lab, pred in [(f"before {a.split}", lambda d: d < a.split), (f"from {a.split}", lambda d: d >= a.split)]:
        N_, nab, na, nb, conf, lift = window(pred)
        lo, hi = wilson(nab, na)
        print(f"[split] {lab:18s} N {N_:5d}  A&B {nab:4d}  A {na:4d}  B {nb:4d}  conf {conf:.3f} [{lo:.3f}, {hi:.3f}]  lift {lift:.2f}")
else:
    print("[who/month/split] skipped: run rebuild_check.py first (results/basket_meta.json)")

if a.family:
    fam = sorted(s for s, d in desc.items() if a.family.upper() in d)
    sets = [set(b) & set(fam) for b in B]
    hit = [x for x in sets if x]
    print(f"[family] '{a.family}': {len(fam)} stock codes: " + "; ".join(f"{s} {desc[s]} ({idx.count([s])})" for s in fam))
    dist = collections.Counter(len(x) for x in hit)
    print(f"[family] baskets with any of them: {len(hit)}; how many of the {len(fam)} per basket: " + ", ".join(f"{k}: {v}" for k, v in sorted(dist.items())))
