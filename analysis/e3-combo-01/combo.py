#!/usr/bin/env python3
"""e3-combo-01: likelihood ratios of combined in-task checks and of the self-claim on the executed checks' subsets.
Exploratory (not pre-registered). Input: the released e3-verdicts.csv (pool v1, 182 patches, 60 development tasks;
verdicts accept/reject/undefined per check, outcome pass/fail). A conjunction accepts a patch when every member accepts
it and is defined only where every member is defined. Sensitivity = accepted share of correct patches, false acceptance
= accepted share of wrong patches, LR = their ratio; 90% interval by bootstrap over tasks (10,000 draws, seed 20261004,
the ledger's convention). Usage: /usr/bin/python3 analysis/e3-combo-01/combo.py [e3-verdicts.csv] > report.md
"""
import csv, random, sys
from collections import defaultdict

CHECKS = {"R-self": "self-claim", "R-repro": "own reproduction", "R-fresh": "fresh judge", "R-near": "nearby tests"}
SETS = [
    ("self-claim", ("R-self",)), ("own reproduction", ("R-repro",)), ("fresh judge", ("R-fresh",)), ("nearby tests", ("R-near",)),
    ("self-claim, on the 107 with own reproduction", ("R-self",), ("R-repro",)),
    ("self-claim, on the 132 with nearby tests", ("R-self",), ("R-near",)),
    ("self-claim and fresh judge", ("R-self", "R-fresh")),
    ("self-claim and own reproduction", ("R-self", "R-repro")),
    ("self-claim and nearby tests", ("R-self", "R-near")),
    ("own reproduction and nearby tests", ("R-repro", "R-near")),
    ("the three executed checks", ("R-repro", "R-near", "R-fresh")),
    ("all four", ("R-self", "R-repro", "R-near", "R-fresh")),
]


def rates(rows):
    a = [r for r in rows if r["y"]]
    b = [r for r in rows if not r["y"]]
    sa = sum(r["v"] for r in a) / len(a) if a else float("nan")
    fb = sum(r["v"] for r in b) / len(b) if b else float("nan")
    return sa, fb, (sa / fb if fb else float("inf"))


def judged(rows, members, defined_on):
    out = []
    for r in rows:
        if any(r[m] == "undefined" for m in members + defined_on):
            continue
        out.append({"task": r["task"], "y": r["outcome"] == "pass", "v": int(all(r[m] == "accept" for m in members))})
    return out


def boot(rows, draws=10000, seed=20261004):
    by = defaultdict(list)
    for r in rows:
        by[r["task"]].append(r)
    tasks = sorted(by)
    rng = random.Random(seed)
    lrs = []
    for _ in range(draws):
        sample = [x for t in rng.choices(tasks, k=len(tasks)) for x in by[t]]
        sa, fb, lr = rates(sample)
        if fb > 0 and sa == sa:
            lrs.append(lr)
    lrs.sort()
    return lrs[int(0.05 * len(lrs))], lrs[int(0.95 * len(lrs)) - 1]


def main(path):
    rows = list(csv.DictReader(open(path)))
    assert len(rows) == 182 and sum(r["outcome"] == "pass" for r in rows) == 89, "pool v1 is 182 patches, 89 correct"
    print("| check(s) | judged | correct | wrong | sensitivity | false acceptance | LR [90%] |")
    print("|---|---|---|---|---|---|---|")
    for name, members, *rest in SETS:
        j = judged(rows, list(members), list(rest[0]) if rest else [])
        sa, fb, lr = rates(j)
        lo, hi = boot(j)
        print(f"| {name} | {len(j)} | {sum(r['y'] for r in j)} | {sum(not r['y'] for r in j)} | {sa:.2f} | {fb:.2f} | {lr:.2f} [{lo:.2f}, {hi:.2f}] |")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../axi-paper-release/data/e3-verdicts.csv")
