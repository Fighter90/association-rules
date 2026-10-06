# A04 — Association rules

HW4 for the HSE LLM4Rec course: association-rule mining on UCI Online Retail,
with an unchanged starter, a pinned implementation, independent reference
checks, later-period validation, a repaired specification, and a regenerated
browser site.

Open `site/index.html` directly in a modern browser. No server, build, or Python
installation is needed to use the page. At **1% support / 30% confidence**, the
verified implementation returns **1,219 frequent itemsets and 950 rules**; its
**11 self-checks pass**, and the browser-function sweep matches the reference at
**35/35 threshold settings**. Python is used for development verification, not
for the browser application or the homework's browser-file deliverable.

## 1. Starter, findings, and implementation scope

### What the starter contained

The root `index.html`, `style.css`, `transactions.js`, and `script.js` preserve
the supplied browser starter. It already decoded the embedded dataset, built an
inverted index, displayed the summary and worked example, wired the sliders and
buttons, rendered selected rules and their reversals, and provided 11 checks.
Exactly seven functions threw `TODO(hw4)` errors: `dedupeBasket`, `countItemset`,
`computeSupport`, `computeConfidence`, `computeLift`, `findFrequentItemsets`, and
`generateRules`. Before implementation, Run tests reported **2 passed / 0 failed
/ 9 pending**, and Run rules stopped at `findFrequentItemsets`.

### Specification and scaffold findings

These findings explain the repairs in `prompt_fixed.md`; they are separate from
the assignment's implementation tasks. The original prompt, embedded dataset,
and scaffold comments remain preserved for comparison.

| Location | Finding and evidence |
|---|---|
| `prompt.md` §3 and the `transactions.js` header | The starter uses the introductory paper as the dataset citation, misspells **Sai Laing Sain** as **Sai Liang Sain**, and names the wrong venue, **Journal of Cases on Information Technology**. The dataset citation and introductory-paper citation are separate UCI entries; corrected references appear below. |
| Page dataset summary | The unchanged `window.HW4.dataset_provenance` repeats **Sai Liang Sain** and **"384,911 rows"**. The summary exposes that inherited text even in the working pages (`check-13`). Correcting the prompt does not silently rewrite the provided dataset. |
| `prompt.md` §3 cleaning summary | **396,244 source rows** survive the row filters; **384,911** counts distinct `(InvoiceNo, StockCode)` pairs in the final **17,080 baskets**, after merging duplicate pairs and removing baskets with fewer than two items (`check-2`). Calling 384,911 the immediate row-filter result is inaccurate. |
| `prompt.md` §4.2(6) | The export contains neither dates nor invoice IDs, but timestamps are recoverable from the source. Re-running the generator recovers its aligned invoice list, then each invoice's first source row supplies `InvoiceDate`, `CustomerID`, and `Country`. All **17,080 baskets** match one by one; their recovered dates run **2010-12-01–2011-12-09** (`check-2`). Nothing is simulated. |
| `prompt.md` §1 | Item and pairwise counts are not sufficient for arbitrary larger-itemset rules. At 1% / 30%, **434 of the 950 rules** involve unions of three or four items; those rules need the union and antecedent/consequent itemset counts (`check-6`). |
| `prompt.md` §4.1(5) and §6(5) | "Both ways" or "both directions" is ambiguous for `k >= 3`. The pinned interpretation enumerates **every nonempty proper antecedent subset**, with its complement as consequent: **2^k - 2 candidates**, including six for a triple, before confidence filtering. |
| Support comparison | Eligibility is **`count / N >= minSupport`**, not `count >= Math.floor(minSupport * N)`. At 1% of 17,080, **171 baskets** are required; the floor mutation incorrectly accepts **170** (`check-4b`). Such a row has **0.995316...%** actual support but displays **1.00%** after rounding. |
| Lift filtering | The greatest singleton support is **1,959 / 17,080 = 11.47%**. Every nonempty consequent has support at most that value, so confidence above it guarantees lift > 1. At **30% confidence**, the downstream lift filter removes **zero** rules; the correct table itself is filtered only by support and confidence (`check-6`). |
| Tests 10–11 | Test 10 checks only that **at least one frequent pair** is returned; test 11 checks only that **at least one rule** is returned. Their names suggest stronger fixture verification than their assertions perform (`check-1`, `check-12`). |
| Fixture boundary coverage | The miner checks use **0.4 × 5 = 2** and **0.2 × 5 = 1**. These whole-count boundaries do not expose the support-floor error: all **11 checks still pass** under the mutation, while the reference finds **22 extra rules**, **20 extra itemsets**, and **23 mismatch-counter increments** (`check-4b`). Restoration returns **950 rules**, **1,219 itemsets**, and **zero mismatches** (`check-4c`). |
| `prompt.md` §5 | Its zero-denominator note names `N` and `count(A)` but omits **`count(B)` in lift**. The stub contract, §4.1(8), and test 9 already account for the missing case. |
| `reverseRule` scaffold comment | It claims reversal changes "confidence and support". For ROSES teacup ↔ cakestand, confidence is **53.85% / 24.99%**, but support remains **2.46%** and lift **5.4711** (`check-7`, `check-13`). The comment is preserved; `prompt_fixed.md` identifies the error. |
| `prompt.md` §8 | The cited `docs/homework-guidelines/guidelines.md` is absent from the checked course repository at commit `a4f53be6c550c1ee98ee6f067aee787b3cc5adb2`; the GitHub contents endpoint also returned **HTTP 404**. Do not claim to have read that unavailable file. |

The generator preserves first-surviving-row invoice order, rather than sorting
on `InvoiceDate` explicitly. Chronological order is a **verified property of this
source CSV**, not a substitute for checking actual timestamps on another source.
Metadata recovery uses the first source row per invoice; it does not test
whether every row of that invoice has identical metadata.

### What the assignment asks to implement

Implement only the seven stubs: basket deduplication, itemset counting, the three
metric helpers, frequent-itemset mining, and rule generation. The existing UI
then supplies threshold controls, rule selection, reversal, and undefined-metric
notes. Keep all scaffold code and comments in place, use English for new code
and comments, and leave the three static assets byte-identical to the starter.
The business analysis belongs in the course report: useful and rejected rules,
threshold trade-offs, a concrete action and limitation, causality, and validation.

`prompt_fixed.md` is the same assignment document with targeted corrections and
§6(10), **Verification before output**; it is not a replacement project brief.
The pinned interpretation of larger-itemset rules and Apriori join/prune is
grounded in Agrawal and Srikant, §§1.1 and 2.1.1, read beyond the abstract.

## 2. Pinned implementation design

| Part | Pinned contract |
|---|---|
| `dedupeBasket(rawItems)` | One pass through `stockOf`; keep the first occurrence of each stock code; accept strings and item objects; empty input returns `[]`. |
| `countItemset(basketsOrIndex, stocks)` | Deduplicate the request; return zero for an empty request or any absent stock; use `asIndex`, walk the smallest posting set, and probe the others. Count baskets, not line items or quantities. |
| `computeSupport` | `jointCount / N`; return `{ value: 0, defined: false }` when `N === 0`. |
| `computeConfidence` | `jointCount / count(A)`; return the undefined result when `count(A) === 0`. |
| `computeLift` | `confidence.value / (count(B) / N)`; return the undefined result for missing/undefined confidence, zero `N`, or a zero consequent baseline. |
| Vertical layout | Deduplicate each basket and build stock → ascending basket IDs. Keep IDs in `Int32Array` posting lists and item codes in string order. |
| Apriori eligibility | Use `count / N >= minSupport` at every level, without rounding the count threshold or comparing displayed percentages. Return `{ items, count, support }` for every frequent itemset size. |
| Apriori join/prune/count | Join two frequent k-itemsets sharing a `(k-1)`-prefix to form a `(k+1)`-candidate; prune if any k-subset is absent from the current frequent level; count by intersecting the two parents' sorted ID lists, never by rescanning baskets. |
| Candidate rules | For each frequent union of size k ≥ 2, enumerate all nonempty proper antecedent subsets and their complements: `2^k - 2` directed candidates. Fetch `count(A)` and `count(B)` from the frequent-itemset map. |
| Rule population | Recover `N` as `Math.round(count / support)` from an input itemset, so the five-basket fixture and full dataset both work despite floating-point division. |
| Returned rules | Use the metric helpers; retain `confidence >= minConfidence`; return antecedent, consequent, joint/antecedent/consequent counts, support, confidence, and lift. |
| Table ranking | Lift descending, confidence descending, joint count descending, then antecedent and consequent code arrays in ascending string order. |
| Lift policy | Do not discard lift ≤ 1 inside the table generator; apply lift > 1 to downstream positive-association analysis. At 30% confidence it is redundant for this dataset. |
| Verification gate | **11/11 page checks**; exactly **9 fixture itemsets** at 0.4 support and **38 fixture rules** at 0.2 / 0.5; exactly **1,219 dataset itemsets and 950 rules** at 1% / 30%; ROSES → cakestand has **420 / 780 / 1,681**, **2.46%**, **53.85%**, **5.4711**. |

The JavaScript pages are checked against `ar_core.py`, whose FP-Growth miner uses
mlxtend's FP-tree and whose second miner uses level-wise Python integer bitsets.
These two Python miners return identical itemset identities and counts at all
seven support settings (`check-6`). The browser sweeps separately compare rule
identities, three counts, and all rule metrics at 35 settings (`check-5`,
`check-14`). The sweeps compare itemset identities/counts; their numeric-difference
column measures **rule metrics**, not a separate itemset-support assertion.
The supports are **0.5%, 0.75%, 1%, 1.5%, 2%, 3%, and 5%**, crossed with
confidence thresholds **10%, 30%, 50%, 60%, and 80%**.

## 3. Files, data, and evidence

### Repository and local-file inventory

| Path | Purpose | Git policy |
|---|---|---|
| `README.md` | Findings, pinned design, inventory, and reproduction instructions. | Committed |
| `prompt.md` | Original week4 readme/specification, preserved. | Committed |
| `prompt_fixed.md` | Targeted repairs to the original document and its verification gate. | Committed |
| `index.html` | Starter page structure and script loading. | Committed, unchanged |
| `style.css` | Starter page styling. | Committed, unchanged |
| `transactions.js` | Dictionary-encoded dataset and original provenance text. | Committed, unchanged |
| `script.js` | Starter scaffold with seven throwing stubs. | Committed, unchanged |
| `fixed/` | Implementation written by the agent in this session (**T8**) from the pinned design, checked against the independent reference. | Committed |
| `fixed/index.html`, `fixed/style.css`, `fixed/transactions.js` | Byte-identical copies of the three starter assets. | Committed, unchanged copies |
| `fixed/script.js` | First implementation; only seven function bodies differ from the starter. | Committed |
| `site/` | Regenerated implementation using `prompt_fixed.md` as the specification; the browser directory the Pages workflow publishes. | Committed; deployment source |
| `site/index.html`, `site/style.css`, `site/transactions.js` | Byte-identical copies of the three starter assets. | Committed, unchanged copies |
| `site/script.js` | Independently regenerated from the starter without opening `fixed/`; only the seven bodies change. | Committed |
| `ar_core.py` | Independent reference: JSON loader, bitset index, FP-Growth and bitset Apriori, exhaustive rule generation. | Committed; development tooling |
| `audit_data.py` | Counts what the export contains and scans readme/scaffold claims; does not run browser tests. | Committed; development tooling |
| `basket_meta.py` | Reuses the instructor's cleaning, checks ordered basket membership, and recovers invoice metadata. | Committed; development tooling |
| `rebuild_check.py` | Byte-for-byte generator rebuild, row-count distinction, and metadata/date checks. | Committed; development tooling |
| `app_probe.py` | Headless Chromium UI probe and direct in-page function sweep against the reference. | Committed; development tooling |
| `threshold_grid.py` | Cross-checks the two reference miners, reports threshold effects, and plots their counts. | Committed; development tooling |
| `rule_card.py` | Counts, both directions, confidence intervals, headroom, customer/month/split summaries, optional family distribution. | Committed; development tooling |
| `temporal_check.py` | Mines earlier/later periods and measures retention using recovered real dates. | Committed; development tooling |
| `requirements.txt` | Pins Playwright and mlxtend; sets minimum pandas/matplotlib versions. | Committed |
| `.gitignore` | Excludes local data, generated evidence, environments, caches, session files, and OS metadata. | Committed |
| `.github/`, `.github/workflows/`, `.github/workflows/pages.yml` | GitHub Actions workflow uploading and deploying `./site`. | Committed |
| `data/`, `data/online-retail-dataset.csv` | Local source log used to rebuild baskets and recover dates. | **Ignored; not committed** |
| `results/`, `results/check-*.txt` | Audit, probe, mutation, threshold, rule-card, temporal, and diff logs; every existing check is reproduced in §4 below. | **Ignored; report evidence** |
| `results/basket_meta.json` | Recovered metadata aligned to the 17,080 exported baskets; generated by `rebuild_check.py`. | Ignored |
| `results/rules_support1_conf30.csv` | The page's 950-row table at 1% / 30%. | Ignored |
| `results/rules_support3_conf30.csv` | The page's 12-row table at 3% / 30%. | Ignored |
| `results/rules_support1_conf60.csv` | The page's 238-row table at 1% / 60%. | Ignored |
| `results/versions.txt` | Environment snapshot for the recorded runs. | Ignored |
| `figures/`, `figures/fig1_thresholds.png` | Generated threshold plot. | **Ignored; report evidence** |
| `figures/fig2_fixed.png`, `figures/fig2_site.png` | Generated selected-rule screenshots, captured before reversal. | Ignored |
| `.venv/`, `__pycache__/` | Local Python environment and generated bytecode. | Ignored |
| `.DS_Store`, `*_session.json` | Local OS metadata and optional session state. | Ignored |
| `.git/` | Local Git history and administrative metadata. | Managed by Git, not project content |

`results/` and `figures/` are **git-ignored on purpose**: `prompt.md` §7 forbids
committing generated artefacts, environments, and logs. The course report carries
the cited tables, figures, verification evidence, and analysis in the separate
course submission; no report file is tracked here. These are not missing
repository attachments. A fresh checkout recreates the evidence with §4.
The Python verification tools are development assets, not files to add to the
homework's browser-directory submission.

Temporary helpers and the intentional mutation live outside the project, in
`/tmp`; they are not application files or committed deliverables. The instructor's
generator is also external, at `../RecSys-LLMs/tools/build_week4_data.py`.

### Source CSV and provenance

- Official dataset: [UCI Online Retail, dataset 352](https://archive.ics.uci.edu/dataset/352/online+retail).
- Official workbook archive: `https://archive.ics.uci.edu/static/public/352/online+retail.zip`.
- CSV mirror used for the checks:
  `https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/master/data/retail-data/all/online-retail-dataset.csv`.
- CSV SHA-256:
  `a2f79bbdd4463df6db8a3f5a50b9c980ae8f645a370bf5e2c0d6097f9e817b05`.
- Original UCI workbook SHA-256 recorded by the instructor:
  `43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d`.
- Export SHA-256, shared by the starter and rebuilt `transactions.js`:
  `c14ed6f8c83124c37d06f752e386a3e389a1fb285ed1184e952fc8810d05c1b3`.

The CSV mirror was fetched and compared byte-for-byte with the local CSV; its
hash matches `check-2`. The instructor's generator at course commit
`a4f53be6c550c1ee98ee6f067aee787b3cc5adb2` produces a byte-identical export from
that CSV. The CSV and workbook hashes identify **different files**, not two
representations expected to have the same checksum.

Correct references, kept separate:

1. Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository.
   https://doi.org/10.24432/C5BW33.
2. Daqing Chen, Sai Laing Sain, Kun Guo, "Data mining for the online retail
   industry: A case study of RFM model-based customer segmentation using data
   mining," *Journal of Database Marketing and Customer Strategy Management*,
   19(3), 197–208, 2012. https://doi.org/10.1057/dbm.2012.17.
3. Rakesh Agrawal and Ramakrishnan Srikant, "Fast Algorithms for Mining
   Association Rules," *Proceedings of the 20th International Conference on
   Very Large Data Bases*, 487–499, 1994. §§1.1 and 2.1.1:
   https://www.vldb.org/conf/1994/P487.PDF.

## 4. Reproduce every `results/check-*.txt`

Run commands from this repository's root. These are the commands used for the
named logs; elapsed times and absolute file URLs may differ on another machine.
The check numbering records the investigation sequence, not a test-suite name.
For failure-sensitive verification pipelines, enable `set -o pipefail` in Bash
or Zsh: otherwise `tee` can mask an upstream command failure. The commands below
preserve the original stdout-only logs; producer stderr remains on the terminal.

### Preparation

For a fresh checkout, create the local environment and output directories:

```bash
python3 -m venv .venv
.venv/bin/python3 -m pip install -r requirements.txt
.venv/bin/python3 -m playwright install chromium
mkdir -p data results figures
```

The recorded environment was **Python 3.14.6 on macOS 26.3.1 / Apple M1**, with
Playwright **1.63.0**, mlxtend **0.25.0**, pandas **3.0.6**, NumPy **2.5.3**, and
matplotlib **3.11.2** (`results/versions.txt`). `requirements.txt` is not a full
transitive dependency lock; the checks verify output equality rather than
identical elapsed times across environments.

Place a checkout of the course repository next to this repository. The recorded
generator revision is given above; use that revision for an exact rebuild.

```bash
git clone https://github.com/dryjins/RecSys-LLMs.git ../RecSys-LLMs
git -C ../RecSys-LLMs checkout a4f53be6c550c1ee98ee6f067aee787b3cc5adb2
curl -fL "https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/master/data/retail-data/all/online-retail-dataset.csv" -o data/online-retail-dataset.csv
shasum -a 256 data/online-retail-dataset.csv
```

The `git clone` commands are for a fresh sibling checkout; do not overwrite an
existing checkout with local work. Chromium can also be supplied through the
`PW_CHROMIUM` environment variable. The browser pages do not need the CSV;
metadata-dependent checks do, and `check-2` must run before them.

### Starter audit and rebuild: checks 1–3

```bash
.venv/bin/python3 audit_data.py | tee results/check-1-audit-starter.txt
.venv/bin/python3 rebuild_check.py | tee results/check-2-rebuild.txt
.venv/bin/python3 app_probe.py --page . --inspect | tee results/check-3-probe-starter.txt
```

`check-2` also writes `results/basket_meta.json`. The starter's `check-3` has no
rendered rules, so **zero mismatches does not mean a reference comparison ran**.

### Pinned implementation and intentional mutation: checks 4, 4b, 4c, 5

```bash
.venv/bin/python3 app_probe.py --page fixed --inspect --run 0.01 0.3 --rule 22699 22423 --reverse --save-table results/rules_support1_conf30.csv --screenshot figures/fig2_fixed.png | tee results/check-4-probe-fixed.txt
```

Prepare the deliberate support-floor mutation outside the project. This is an
injected fault used to test the checks, not a naturally occurring implementation
failure. The two replacements affect only the support comparisons in the
`fixed/script.js` copy:

```bash
rm -rf /tmp/a04-floor
cp -R fixed /tmp/a04-floor
.venv/bin/python3 -c 'from pathlib import Path; p = Path("/tmp/a04-floor/script.js"); s = p.read_text(); s = s.replace("ids.length / n >= minSupport", "ids.length >= Math.floor(minSupport * n)").replace("count / n >= minSupport", "count >= Math.floor(minSupport * n)"); p.write_text(s)'
diff fixed/script.js /tmp/a04-floor/script.js
.venv/bin/python3 app_probe.py --page /tmp/a04-floor --inspect --run 0.01 0.3 | tee results/check-4b-mutation-floor.txt
```

Restore the copy, establish byte equality, and repeat the probe:

```bash
cp fixed/script.js /tmp/a04-floor/script.js
cmp fixed/script.js /tmp/a04-floor/script.js
.venv/bin/python3 app_probe.py --page /tmp/a04-floor --inspect --run 0.01 0.3 | tee results/check-4c-mutation-fixed.txt
.venv/bin/python3 app_probe.py --page fixed --sweep | tee results/check-5-sweep-fixed.txt
```

### Thresholds and two additional rendered tables: checks 6, 6b, 6c

```bash
.venv/bin/python3 threshold_grid.py --cross-check --plot figures/fig1_thresholds.png | tee results/check-6-thresholds.txt
.venv/bin/python3 app_probe.py --page fixed --run 0.03 0.3 --save-table results/rules_support3_conf30.csv | tee results/check-6b-table-3pct.txt
.venv/bin/python3 app_probe.py --page fixed --run 0.01 0.6 --save-table results/rules_support1_conf60.csv | tee results/check-6c-table-60pct.txt
```

The baseline table has **950 rules**; the stricter-support table has **12**, and
the stricter-confidence table **238**. Exactly **five directed rules** survive
both stricter settings. The 0.75% support sweep setting calls functions directly;
it is not representable by the starter slider's 0.5-percentage-point step.

### Rule evidence: checks 7, 7b, 7c, 7d, 8, 9

```bash
.venv/bin/python3 rule_card.py --rule 22699 22423 > results/check-7-rule-useful.txt && head -3 results/check-7-rule-useful.txt
.venv/bin/python3 rule_card.py --rule 22697 22423 > results/check-7b-rule-green.txt
.venv/bin/python3 rule_card.py --rule 22698 22423 > results/check-7c-rule-pink.txt
.venv/bin/python3 rule_card.py --rule 22699 85123A > results/check-7d-baseline-popular.txt
.venv/bin/python3 rule_card.py --rule 22916 22917 --family "HERB MARKER" | tee results/check-8-rule-reject.txt
.venv/bin/python3 rule_card.py --rule 22727 85123A | tee results/check-9-rule-anchor.txt
```

The `head -3` step intentionally exposes only the raw counts before a hand
calculation. It still writes the complete rule card to the log. Manual Chrome
verification was supplied by the user; these commands reproduce the automated
evidence, not a claim that the agent performed the user's manual calculations.

### Later-period validation and prompt repair: checks 10–11

```bash
.venv/bin/python3 temporal_check.py | tee results/check-10-temporal.txt
diff prompt.md prompt_fixed.md | tee results/check-11-prompt-diff.txt
```

The default split is **2011-09-01**: **10,481 earlier** and **6,599 later baskets**.
Each period uses **1% support / 30% confidence** with its own basket denominator,
requiring **105 earlier** or **66 later joint baskets**, respectively.
Of **1,845 earlier rules**, all retain lift > 2 later, but only **467 (25.3%)**
still pass both thresholds. This is historical chronological validation using
recovered dates, not a randomised experiment or proof of causal sales uplift.
For missing later counts, the temporal helper uses zero-valued reporting
placeholders rather than the browser helpers' undefined-metric flags.

### Regenerated site: checks 12, 12b, 12c, 13, 14

```bash
.venv/bin/python3 audit_data.py --script site/script.js | tee results/check-12-audit-site.txt
.venv/bin/python3 app_probe.py --page site --inspect --run 0.01 0.3 --rule 22699 22423 --reverse --screenshot figures/fig2_site.png | tee results/check-13-probe-site.txt
.venv/bin/python3 app_probe.py --page site --sweep | tee results/check-14-sweep-site.txt
git diff --no-index script.js site/script.js | tee results/check-12b-diff-site.txt
(for f in index.html style.css transactions.js; do cmp $f fixed/$f; cmp $f site/$f; done; echo "static files compared") 2>&1 | tee results/check-12c-static-files.txt
```

The requested `check-12` command retains `audit_data.py`'s default readme,
`prompt.md`; its text searches therefore scan the original document, while its
script scan checks `site/script.js`. The static-file log should contain only
`static files compared`: each `cmp` is silent on equality. Its final message
alone is not a failure-sensitive assertion, so inspect any preceding diagnostics.
`diff` and `git diff --no-index` normally return **1 when differences exist**;
that is expected for the implementation and repaired-prompt logs, not a failed
comparison with the numeric reference. If using `set -e`/`pipefail`, handle those
expected diff statuses when running the commands as a batch.

## 5. GitHub Pages

`.github/workflows/pages.yml` matches the workflow in
`Fighter90/cf-movie-recommender`: push to **main** or **workflow_dispatch** runs
checkout/configure, uploads **`./site`** with
**`actions/upload-pages-artifact@v3`**, then deploys with
**`actions/deploy-pages@v4`**. The workflow grants `contents: read`, `pages: write`,
and `id-token: write`, uses a `pages` concurrency group, and publishes through
the `github-pages` environment.

Enable **Settings → Pages → Source: GitHub Actions** in the GitHub repository.
After pushing `main`, or manually dispatching the workflow, the deploy job's
environment URL identifies the published site. A local commit does not itself
run GitHub Actions; this checkout initially had no Git remote configured.
Only `site/` is uploaded, not the starter, reference scripts, raw CSV, logs, or
report figures.
