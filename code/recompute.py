#!/usr/bin/env python3
"""Recompute W1's Table 1 (in-task checks against the hidden grading tests) and Table 2 (task-paired tests of the five
organisational changes) from the released files of the Kaggle dataset ghaisank/axi-paper-release. Standard library only.

Inputs (in INPUT, default /kaggle/input/axi-paper-release): e3-verdicts.csv (one row per judged patch: task, configuration,
R-self, R-repro, R-near, R-fresh verdicts, outcome), e3-session-exit.csv (configuration, task, exit: terminal or timeout),
ledger-public.jsonl (every run, leaderboard and test number of the papers as a row; run rows carry per_task maps; trace
statistics are in analysis/).

Conventions, as in the papers: sensitivity alpha = share of correct patches a check accepts, false acceptance beta = share of
wrong patches it accepts, LR = alpha / beta on the patches where the check's verdict is defined; the 90 percent interval is a
bootstrap over tasks (resample the 60 pool tasks with replacement, 10,000 draws, seed 20261108; the papers' registered rows
used the campaign's referee.py with its own seed, so intervals agree to about 0.02). The paired test is the exact one-sided
sign-flip (McNemar) test on the tasks the two arms resolve differently.
"""
import csv, json, os, random, sys
from collections import defaultdict

INPUT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("AXI_PAPER_INPUT", "/kaggle/input/axi-paper")
if not os.path.exists(os.path.join(INPUT, "e3-verdicts.csv")):  # Kaggle may mount the dataset under another folder name
    INPUT = next((r for r, _, fs in os.walk("/kaggle/input") if "e3-verdicts.csv" in fs), INPUT)
print("input folder:", INPUT, sorted(os.listdir(INPUT)) if os.path.isdir(INPUT) else "missing")
CHECKS = [("R-self", "self-claim"), ("R-repro", "own reproduction"), ("R-fresh", "fresh judge"), ("R-near", "nearby tests")]


def read_csv(name):
    with open(os.path.join(INPUT, name), newline="") as f:
        return list(csv.DictReader(f))


def accepts(row, check):
    if check == "both":
        if row["R-self"] not in ("accept", "reject") or row["R-fresh"] not in ("accept", "reject"):
            return None
        return row["R-self"] == "accept" and row["R-fresh"] == "accept"
    v = row[check]
    return None if v not in ("accept", "reject") else v == "accept"


def rates(rows, check):
    corr = [a for a in (accepts(r, check) for r in rows if r["outcome"] == "pass") if a is not None]
    wrong = [a for a in (accepts(r, check) for r in rows if r["outcome"] == "fail") if a is not None]
    if not corr or not wrong or sum(wrong) == 0:
        return None
    alpha, beta = sum(corr) / len(corr), sum(wrong) / len(wrong)
    return {"judged": len(corr) + len(wrong), "alpha": alpha, "beta": beta, "lr": alpha / beta}


def bootstrap_over_tasks(rows, check, draws=10000, seed=20261108):
    by_task = defaultdict(list)
    for r in rows:
        by_task[r["task"]].append(r)
    tasks = sorted(by_task)
    rng = random.Random(seed)
    vals = []
    for _ in range(draws):
        sample = [x for t in (rng.choice(tasks) for _ in tasks) for x in by_task[t]]
        d = rates(sample, check)
        if d:
            vals.append(d["lr"])
    vals.sort()
    return (vals[int(0.05 * len(vals))], vals[int(0.95 * len(vals)) - 1]) if vals else None


def sign_flip_p(a_counts, b_counts):
    """Exact one-sided paired test that B resolves more: per task d = B - A; under H0 each non-zero d flips its sign with
    probability 1/2. Returns (p, observed sum, number of differing tasks)."""
    d = [b_counts[t] - a_counts[t] for t in a_counts]
    w = [abs(x) for x in d if x]
    t_obs = sum(d)
    dist = {0: 1}
    for x in w:
        nxt = defaultdict(int)
        for s, c in dist.items():
            nxt[s + x] += c
            nxt[s - x] += c
        dist = nxt
    return sum(c for s, c in dist.items() if s >= t_obs) / 2 ** len(w), t_obs, len(w)


def main():
    verdicts = read_csv("e3-verdicts.csv")
    print(f"Table 1: in-task checks, pool v1 ({len(verdicts)} patches, {len({r['task'] for r in verdicts})} tasks)")
    print(f"{'check':34s} {'judged':>6s} {'alpha':>6s} {'beta':>6s} {'LR':>6s}  90% interval")
    for key, name in CHECKS + [("both", "self-claim and fresh judge, both accept")]:
        d = rates(verdicts, key)
        ci = bootstrap_over_tasks(verdicts, key)
        print(f"{name:34s} {d['judged']:6d} {d['alpha']:6.2f} {d['beta']:6.2f} {d['lr']:6.2f}  [{ci[0]:.2f}, {ci[1]:.2f}]")
    try:
        exits = {(r["configuration"], r["task"]): r["exit"] for r in read_csv("e3-session-exit.csv")}
        finished = [r for r in verdicts if exits.get((r["configuration"], r["task"])) == "terminal"]
        timed = [r for r in verdicts if exits.get((r["configuration"], r["task"])) == "timeout"]
        print(f"\nFinished sessions only ({len(finished)} patches; the {len(timed)} patches from timed-out sessions: "
              f"{sum(r['outcome'] == 'pass' for r in timed)} correct)")
        for key, name in CHECKS + [("both", "both accept")]:
            d = rates(finished, key)
            print(f"{name:34s} {d['judged']:6d} {d['alpha']:6.2f} {d['beta']:6.2f} {d['lr']:6.2f}")
    except FileNotFoundError:
        print("\n(e3-session-exit.csv not found: the finished-session block is skipped)")

    rows = {}
    with open(os.path.join(INPUT, "ledger-public.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            if r.get("kind") == "run":
                rows[r["row_id"]] = r
    print("\nTable 2: task-paired tests (change against control; b = change only, c = control only)")
    pairs = [("two-stage split", "r0052", "r0049"), ("shared default stack", "r0050", "r0049"),
             ("session-state notes, with defaults and edit form", "r0053", "r0049"),
             ("parser-safe edit form", "r0044", "r0045"), ("time-budget governance (P6 after A4, across hardware)", "r0045", "r0054")]
    for name, change, control in pairs:
        a, b = rows[control]["per_task"], rows[change]["per_task"]
        common = sorted(set(a) & set(b))
        a, b = {t: a[t] for t in common}, {t: b[t] for t in common}
        p, t_obs, n_diff = sign_flip_p(a, b)
        bb = sum(1 for t in common if b[t] and not a[t]); cc = sum(1 for t in common if a[t] and not b[t])
        note = "" if "across hardware" not in name else "  (the registered P6 test; the arms ran on different hardware)"
        print(f"{name:38s} {sum(b.values()):3d} against {sum(a.values()):3d} of {len(common)}  b {bb:2d}  c {cc:2d}  p {p:.2f}{note}")


if __name__ == "__main__":
    main()
