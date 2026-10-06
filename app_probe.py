#!/usr/bin/env python3
"""
app_probe.py — drive the real HW4 page in headless Chromium and compare what it shows with the
independent reference (ar_core.py, mlxtend FP-Growth).

A folder is opened as file://.../index.html (the readme says the page must work from file://);
a URL is opened as is.

    python3 app_probe.py --page . --inspect                         # starter: status, self-tests, Run rules
    python3 app_probe.py --page fixed --inspect --run 0.01 0.3      # UI path: sliders -> Run rules -> table
    python3 app_probe.py --page fixed --run 0.01 0.3 --rule 22699 22423 --reverse --screenshot figures/fig2.png
    python3 app_probe.py --page fixed --sweep                       # 7 supports x 5 confidences, every rule
"""
import argparse, os, pathlib, re, sys, time
from playwright.sync_api import sync_playwright
import ar_core

SUPPORTS = [0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.05]
CONFIDENCES = [0.1, 0.3, 0.5, 0.6, 0.8]

def shot(pg, path, panel=False):
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    if panel:  # bring the "Selected rule" panel (below the table) into view next to the sticky controls
        pg.evaluate("document.getElementById('detail-heading').scrollIntoView({block: 'start'})")
    pg.screenshot(path=path)
    print(f"[screenshot] {path}")


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--page", required=True, help="folder with index.html, or http(s) URL")
ap.add_argument("--data", default="transactions.js", help="dataset used by the reference")
ap.add_argument("--inspect", action="store_true")
ap.add_argument("--run", nargs=2, type=float, metavar=("SUPPORT", "CONFIDENCE"))
ap.add_argument("--rule", nargs=2, metavar=("A", "B"), help="stock codes, comma-separated for itemsets")
ap.add_argument("--reverse", action="store_true")
ap.add_argument("--sweep", action="store_true")
ap.add_argument("--screenshot")
ap.add_argument("--save-table", help="write the rule table the page rendered to this CSV file")
a = ap.parse_args()

url = a.page if re.match(r"https?://", a.page) else pathlib.Path(a.page, "index.html").resolve().as_uri()
raw, B, desc = ar_core.load(a.data)
mismatches = 0

from decimal import Decimal, ROUND_HALF_UP
def to_fixed(x, digits):
    # Number.prototype.toFixed rounds the exact binary value half-up; Python's format rounds half-even
    return str(Decimal(x).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))
def fmt_pct(x): return to_fixed(x * 100, 2) + "%"
def fmt_lift(x): return to_fixed(x, 4)
def codes(cell): return tuple(sorted(part.split(" — ")[0].strip() for part in cell.split(", ") if " — " in part)) or tuple(cell.split(", "))

with sync_playwright() as p:
    exe = os.environ.get("PW_CHROMIUM")
    br = p.chromium.launch(**({"executable_path": exe} if exe else {}))
    pg = br.new_page(viewport={"width": 1500, "height": 1100})
    errors = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    # console errors carry their source URL, so a "Failed to load resource" can be traced to the file it was for
    pg.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}  [{(m.location or {}).get('url', '')}]"))
    t0 = time.time()
    pg.goto(url)
    pg.wait_for_function("() => /Dataset ready|Failed/.test(document.body.innerText)", timeout=60000)
    print(f"[page] {url}  loaded in {time.time() - t0:.1f} s")
    print(f"[status] {pg.inner_text('#status')}")

    if a.inspect:
        print("[summary] " + pg.inner_text("#dataset-summary-body").replace("\n", " | ")[:300])
        pg.click("#run-tests")
        print("[tests]\n" + "\n".join("    " + l for l in pg.inner_text("#testLog").splitlines()))

    if a.run or (a.inspect and not a.sweep):
        s, c = a.run or (0.01, 0.3)
        pg.evaluate("""([s, c]) => {
            const a = document.getElementById('min-support'); a.value = String(s); a.dispatchEvent(new Event('input'));
            const b = document.getElementById('min-confidence'); b.value = String(c); b.dispatchEvent(new Event('input')); }""",
                    [round(s * 100, 4), round(c * 100, 4)])
        t = time.time()
        pg.click("#run-rules")
        pg.wait_for_function("() => /^(Done|TODO|Run failed)|not implemented|Error/.test(document.getElementById('status').textContent)", timeout=180000)
        print(f"[run] support >= {s}, confidence >= {c}: status '{pg.inner_text('#status')}' ({(time.time() - t) * 1000:.0f} ms)")
        rows = pg.eval_on_selector_all("#results tbody tr", "rs => rs.map(r => [...r.cells].map(c => c.textContent.trim()))")
        if not rows:
            print("[run] table: " + pg.inner_text("#results")[:300])
        else:
            fi, ref = ar_core.rules(B, s, c)
            refmap = {(r["A"], r["B"]): r for r in ref}
            bad = 0
            seen = set()
            for row in rows:
                k = (codes(row[0]), codes(row[1]))
                seen.add(k)
                r = refmap.get(k)
                want = r and [str(r["cab"]), str(r["ca"]), str(r["cb"]), fmt_pct(r["support"]), fmt_pct(r["confidence"]), fmt_lift(r["lift"])]
                if want != row[2:]:
                    bad += 1
                    if bad <= 3:
                        print(f"    MISMATCH page {row}  reference {want or '(no such rule at these thresholds)'}")
            missing = len(set(refmap) - seen)
            mismatches += bad + missing
            print(f"[run] table rows {len(rows)}; reference rules {len(ref)}; rows equal to reference {len(rows) - bad}; reference rules missing from table {missing}; "
                  f"lift <= 1 in table {sum(float(r[7]) <= 1 for r in rows)}")
            # the itemset count is not shown by the page, so call the page's own miner on the same data and threshold
            nfi = pg.evaluate("(s) => { try { return findFrequentItemsets(TRANSACTIONS, s).length; } catch (e) { return 'error: ' + e.message; } }", s)
            mismatches += nfi != len(fi)
            print(f"[run] frequent itemsets from findFrequentItemsets in the page: {nfi}; reference {len(fi)}")
            if a.save_table:
                import csv
                pathlib.Path(a.save_table).parent.mkdir(parents=True, exist_ok=True)
                with open(a.save_table, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["antecedent", "consequent", "count_AB", "count_A", "count_B", "support", "confidence", "lift"])
                    w.writerows(rows)
                print(f"[run] table saved to {a.save_table} ({len(rows)} rows, as rendered by the page)")
            print("[run] first 3 rows: ")
            for r in rows[:3]:
                print("    " + " | ".join(r))
            if a.rule:
                A = tuple(sorted(a.rule[0].split(","))); Bc = tuple(sorted(a.rule[1].split(",")))
                idx = next((i for i, row in enumerate(rows) if (codes(row[0]), codes(row[1])) == (A, Bc)), None)
                if idx is None:
                    print(f"[rule] {A} -> {Bc} is not in the table at these thresholds")
                else:
                    pg.click(f'#results tbody tr[data-rule-index="{idx}"]')
                    print(f"[rule] table row {idx + 1}; detail panel:")
                    print("    " + pg.inner_text("#rule-detail").replace("\n", " | "))
                    if a.reverse:
                        if a.screenshot:  # the figure shows the rule as selected (A -> B), before Reverse
                            shot(pg, a.screenshot, panel=True); a.screenshot = None
                        pg.click("#reverse-rule")
                        print("[rule] after 'Reverse direction (B -> A)':")
                        print("    " + pg.inner_text("#rule-detail").replace("\n", " | "))
        if a.screenshot:
            shot(pg, a.screenshot, panel=bool(a.rule))

    if a.sweep:
        ok_settings = 0
        for s in SUPPORTS:
            for c in CONFIDENCES:
                js = pg.evaluate("""([s, c]) => { const t0 = performance.now();
                    const fi = findFrequentItemsets(TRANSACTIONS, s); const t1 = performance.now();
                    const rs = generateRules(fi, c); const t2 = performance.now();
                    return {fi: fi.map(x => [x.items.slice().sort(), x.count, x.support]),
                            rs: rs.map(r => [r.antecedent.slice().sort(), r.consequent.slice().sort(), r.jointCount, r.antecedentCount,
                                             r.consequentCount, r.support, r.confidence, r.lift]),
                            ms: [t1 - t0, t2 - t1]}; }""", [s, c])
                fi, ref = ar_core.rules(B, s, c)
                jfi = {tuple(x[0]): x[1] for x in js["fi"]}
                jr = {(tuple(r[0]), tuple(r[1])): r for r in js["rs"]}
                rr = {(r["A"], r["B"]): r for r in ref}
                diff = 0.0
                same = jfi == fi and set(jr) == set(rr)
                for k in set(jr) & set(rr):
                    x, y = jr[k], rr[k]
                    same &= (x[2], x[3], x[4]) == (y["cab"], y["ca"], y["cb"])
                    diff = max(diff, abs(x[5] - y["support"]), abs(x[6] - y["confidence"]), abs(x[7] - y["lift"]))
                same &= diff < 1e-12
                ok_settings += same
                mismatches += not same
                print(f"[sweep] support {s:<6} confidence {c:<4} itemsets {len(fi):5d}/{len(jfi):<5d} rules {len(ref):6d}/{len(jr):<6d} "
                      f"max|diff| {diff:.1e}  {js['ms'][0]:6.0f}+{js['ms'][1]:4.0f} ms  {'match' if same else 'MISMATCH'}")
        print(f"[sweep] {ok_settings}/{len(SUPPORTS) * len(CONFIDENCES)} settings: every itemset and every rule equal to the reference")

    print(f"[console] errors: {len(errors)}" + ("".join("\n    " + e for e in errors[:5])))
    if errors and all(e.rstrip("]").endswith("/favicon.ico") for e in errors):
        print("[console] note: the only error is a 404 for /favicon.ico. index.html declares no icon, so over http(s) the browser"
              " asks the site root for one; it is not an error of the page.")
    print(f"[summary] mismatches: {mismatches}")
    br.close()
