#!/usr/bin/env python3
"""
ar_core.py — independent Python reference for HW4 (association rules on UCI Online Retail).

Shares no code with week4/script.js. Two frequent-itemset engines that are implemented
differently on purpose, so they can check each other and the page:
  * "fpgrowth" — mlxtend.frequent_patterns.fpgrowth (an FP-tree, no candidate generation);
  * "bitset"   — level-wise Apriori over Python big-int bitsets (one bit per basket).
Rules are generated exhaustively: every non-empty proper subset A of a frequent itemset X,
B = X \\ A, confidence = count(X) / count(A), lift = confidence / (count(B) / N).

Used as a module by the other scripts; run directly for a quick summary:
    python3 ar_core.py --support 0.01 --confidence 0.3 --top 10
"""
import argparse, json, pathlib, re, sys, time
from itertools import combinations

def load(path="transactions.js"):
    """Parse window.HW4 from transactions.js -> (raw dict, baskets as lists of stock codes, {stock: description})."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    m = re.search(r"^window\.HW4 = (.*);\s*$", text, re.M)
    if not m:
        sys.exit(f"{path}: no 'window.HW4 = ...;' line")
    raw = json.loads(m.group(1))
    baskets = [[raw["stocks"][i] for i in b] for b in raw["baskets"]]
    return raw, baskets, dict(zip(raw["stocks"], raw["descriptions"]))

class BitIndex:
    """stock -> int bitset over basket ids; count(itemset) = popcount of the AND."""
    def __init__(self, baskets):
        self.n = len(baskets)
        acc = {}
        for i, b in enumerate(baskets):
            for s in set(b):
                acc.setdefault(s, []).append(i)
        self.bits = {s: sum(1 << i for i in ids) for s, ids in acc.items()}
    def mask(self, items):
        it = iter(items)
        m = self.bits.get(next(it), 0)
        for s in it:
            m &= self.bits.get(s, 0)
        return m
    def count(self, items):
        items = list(dict.fromkeys(items))
        return self.mask(items).bit_count() if items else 0

def _frequent(n, count, min_support):
    return count / n >= min_support          # the same comparison the page must use

def mine_bitset(baskets, min_support, index=None):
    idx = index or BitIndex(baskets)
    n = idx.n
    level = {(s,): b for s, b in idx.bits.items() if _frequent(n, b.bit_count(), min_support)}
    out = {}
    while level:
        out.update({k: v.bit_count() for k, v in level.items()})
        keys = sorted(level)
        nxt = {}
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                if a[:-1] != b[:-1]:
                    break
                cand = a + (b[-1],)
                if any(cand[:j] + cand[j + 1:] not in level for j in range(len(cand) - 2)):
                    continue
                m = level[a] & level[b]
                if _frequent(n, m.bit_count(), min_support):
                    nxt[cand] = m
        level = nxt
    return out

_DF = {}
def mine_fpgrowth(baskets, min_support):
    import pandas as pd
    from mlxtend.preprocessing import TransactionEncoder
    from mlxtend.frequent_patterns import fpgrowth
    key = id(baskets)
    if key not in _DF:
        te = TransactionEncoder()
        X = te.fit(baskets).transform(baskets, sparse=True)
        _DF[key] = pd.DataFrame.sparse.from_spmatrix(X, columns=te.columns_)
    n = len(baskets)
    fi = fpgrowth(_DF[key], min_support=max(min_support - 1e-9, 1e-12), use_colnames=True)
    out = {}
    for sup, items in zip(fi["support"], fi["itemsets"]):
        c = int(round(sup * n))
        if _frequent(n, c, min_support):
            out[tuple(sorted(items))] = c
    return out

def mine(baskets, min_support, engine="fpgrowth"):
    return mine_fpgrowth(baskets, min_support) if engine == "fpgrowth" else mine_bitset(baskets, min_support)

def rules_from(itemsets, n, min_confidence):
    res = []
    for items, cab in itemsets.items():
        for r in range(1, len(items)):
            for a in combinations(items, r):
                b = tuple(x for x in items if x not in a)
                ca, cb = itemsets[a], itemsets[b]
                conf = cab / ca
                if conf >= min_confidence:
                    res.append(dict(A=a, B=b, cab=cab, ca=ca, cb=cb, support=cab / n,
                                    confidence=conf, lift=conf / (cb / n)))
    res.sort(key=lambda r: (-r["lift"], -r["confidence"], -r["cab"], r["A"], r["B"]))
    return res

def rules(baskets, min_support, min_confidence, engine="fpgrowth"):
    fi = mine(baskets, min_support, engine)
    return fi, rules_from(fi, len(baskets), min_confidence)

def name(items, desc):
    return " + ".join(f"{s} {desc.get(s, '?')}" for s in items)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="transactions.js")
    ap.add_argument("--support", type=float, default=0.01)
    ap.add_argument("--confidence", type=float, default=0.3)
    ap.add_argument("--engine", choices=["fpgrowth", "bitset"], default="fpgrowth")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    raw, baskets, desc = load(a.data)
    t = time.time()
    fi, rs = rules(baskets, a.support, a.confidence, a.engine)
    sizes = {}
    for k in fi:
        sizes[len(k)] = sizes.get(len(k), 0) + 1
    print(f"N = {len(baskets)}  engine = {a.engine}  min_support = {a.support}  min_confidence = {a.confidence}  ({time.time() - t:.1f} s)")
    print(f"frequent itemsets: {len(fi)}  by size {sizes}")
    print(f"rules: {len(rs)}  with lift <= 1: {sum(r['lift'] <= 1 for r in rs)}")
    for r in rs[:a.top]:
        print(f"  {r['lift']:8.4f}  conf {r['confidence']:.4f}  sup {r['support']:.4f}  {r['cab']}/{r['ca']} (B {r['cb']})  "
              f"{name(r['A'], desc)}  ->  {name(r['B'], desc)}")

if __name__ == "__main__":
    main()
