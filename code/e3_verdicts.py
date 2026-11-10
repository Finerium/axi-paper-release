#!/usr/bin/env python3
"""cloud/t8-e3-verdicts/e3_verdicts.py: the paper's release table builder (memory/PAPER.md 2026-10-26 00:27 UTC), standard library.

Builds e3-verdicts.csv, one row per judged patch of the referee study's pool: key, task, configuration (run/arm), rep, the verdict
of every referee (R-self, R-repro from e3/pool-v1/verdicts_trace.jsonl; R-near from runs/near-c1 and runs/near-01
near/verdicts.jsonl; R-fresh from runs/judge-01 judge/verdicts.jsonl) and the hidden-test outcome (pool y: 1 = pass, 0 = fail),
verified against task_results.resolved of runs/<run>/<arm>/rep<rep>/. NO patch text, trace path or repository text is written
(the pool's `patch`, `patch_sha256` and `trace` fields stay out; every cell is checked to be short and single-line).

Prints the counts the dry run registered and refuses (exit 1, "DISCREPANCY: ...") when any differs from REGISTERED, unless
--no-expect: rows 182; outcome verified on every row, 0 mismatches; pass 89 / fail 93; the H6 pairs on wrong patches judged by both
R-self and R-fresh (preregistration P5-E3-H3-H6: discordant pairs b = self accepts and fresh rejects, c = the reverse): wrong 93,
judged by both 93, b = 10, c = 29.

Usage (from anywhere; the root is found by walking up to e3/pool-v1/pool.jsonl, or --root):
  python3 cloud/t8-e3-verdicts/e3_verdicts.py [--root DIR] [--out e3-verdicts.csv] [--no-expect]
"""
import argparse, csv, json, sys
from collections import Counter
from pathlib import Path

REFEREES = ("R-self", "R-repro", "R-near", "R-fresh")
POOL = "e3/pool-v1/pool.jsonl"
VERDICT_FILES = ("e3/pool-v1/verdicts_trace.jsonl", "runs/near-c1/near/verdicts.jsonl", "runs/near-01/near/verdicts.jsonl",
                 "runs/judge-01/judge/verdicts.jsonl")
COLUMNS = ["key", "task", "configuration", "rep"] + list(REFEREES) + ["outcome"]
REGISTERED = {"rows": 182, "mismatches": 0, "pass": 89, "fail": 93, "wrong": 93, "judged_by_both": 93, "b": 10, "c": 29}
MAX_CELL = 80  # a key is 34 characters, a task id under 40: anything longer is text that must not be released


def repo_root(start=None):
    here = Path(start or __file__).resolve()
    for d in [here] + list(here.parents):
        if (d / POOL).is_file():
            return d
    raise SystemExit(f"no {POOL} above {here}; pass --root")


def load_jsonl(path):
    """[(line number, record)] of a JSON-lines file."""
    out = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                out.append((n, json.loads(line)))
    return out


def build_rows(pool, verdict_sources):
    """(rows, problems): one row per pool record in pool order with every referee's verdict joined on `key`;
    verdict_sources = [(path, [(line, record)])]. A key judged twice by one referee, a verdict for a key outside the pool and a
    pool key missing a referee's verdict are problems (with file and line)."""
    verdicts, problems = {}, []
    pool_keys = {r["key"] for _, r in pool}
    for path, recs in verdict_sources:
        for n, v in recs:
            k, ref = v.get("key"), v.get("referee")
            if ref not in REFEREES:
                problems.append(f"{path}:{n}: unknown referee {ref!r}")
                continue
            if k not in pool_keys:
                problems.append(f"{path}:{n}: verdict for a key outside the pool")
                continue
            if (k, ref) in verdicts:
                problems.append(f"{path}:{n}: second {ref} verdict for the same key (first at {verdicts[(k, ref)][1]})")
                continue
            verdicts[(k, ref)] = (v.get("verdict"), f"{path}:{n}")
    rows = []
    for n, p in pool:
        row = {"key": p["key"], "task": p["task"], "configuration": f"{p['run']}/{p['arm']}", "rep": p.get("rep"),
               "outcome": "pass" if int(p["y"]) == 1 else "fail"}
        for ref in REFEREES:
            v = verdicts.get((p["key"], ref))
            if v is None:
                problems.append(f"pool line {n}: no {ref} verdict for its key")
                row[ref] = ""
            else:
                row[ref] = v[0]
        rows.append(row)
    return rows, problems


def verify_outcomes(rows, root):
    """The pool's outcome against task_results.resolved of runs/<run>/<arm>/rep<rep>/task_results.jsonl; returns
    (checked, distinct tasks, [mismatch descriptions])."""
    cache, checked, mism, tasks = {}, 0, [], set()
    for r in rows:
        run, arm = r["configuration"].split("/", 1)
        path = Path(root) / "runs" / run / arm / f"rep{r['rep']}" / "task_results.jsonl"
        if path not in cache:
            cache[path] = {rec["instance_id"]: bool(rec.get("resolved")) for _, rec in load_jsonl(path)} if path.is_file() else None
        res = cache[path]
        if res is None or r["task"] not in res:
            mism.append(f"{r['key']}: no task_results row at {path}")
            continue
        checked += 1
        tasks.add(r["task"])
        if (r["outcome"] == "pass") != res[r["task"]]:
            mism.append(f"{r['key']}: pool outcome {r['outcome']} but {path} says resolved={res[r['task']]}")
    return checked, len(tasks), mism


def h6_pairs(rows):
    """Wrong patches judged by both R-self and R-fresh (a verdict of accept or reject on each): b = self accepts and fresh rejects,
    c = self rejects and fresh accepts (preregistration P5, H6)."""
    wrong = [r for r in rows if r["outcome"] == "fail"]
    both = [r for r in wrong if r["R-self"] in ("accept", "reject") and r["R-fresh"] in ("accept", "reject")]
    b = sum(1 for r in both if r["R-self"] == "accept" and r["R-fresh"] == "reject")
    c = sum(1 for r in both if r["R-self"] == "reject" and r["R-fresh"] == "accept")
    return {"wrong": len(wrong), "judged_by_both": len(both), "b": b, "c": c}


def referee_counts(rows):
    return {ref: dict(Counter(r[ref] for r in rows)) for ref in REFEREES}


def check_release_safe(rows):
    """Every cell short and single-line: no patch, trace or repository text can slip into the table."""
    for r in rows:
        for col in COLUMNS:
            s = "" if r[col] is None else str(r[col])
            if len(s) > MAX_CELL or "\n" in s or "\r" in s:
                raise ValueError(f"column {col} of key {r['key']} holds text ({len(s)} chars): not releasable")


def write_csv(rows, out):
    check_release_safe(rows)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def summary(rows, checked, n_tasks, mism):
    out = Counter(r["outcome"] for r in rows)
    pairs = h6_pairs(rows)
    return {"rows": len(rows), "checked": checked, "tasks": n_tasks, "mismatches": len(mism), "pass": out.get("pass", 0), "fail": out.get("fail", 0),
            **pairs, "referees": referee_counts(rows), "configurations": dict(Counter(r["configuration"] for r in rows))}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="repository root (default: the first parent holding e3/pool-v1/pool.jsonl)")
    ap.add_argument("--out", default=None, help="the CSV to write (default: e3-verdicts.csv next to this script)")
    ap.add_argument("--no-expect", action="store_true", help="do not compare the counts with the registered dry run")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve() if a.root else repo_root()
    out = Path(a.out) if a.out else Path(__file__).resolve().parent / "e3-verdicts.csv"
    pool = load_jsonl(root / POOL)
    sources = [(str(root / v), load_jsonl(root / v)) for v in VERDICT_FILES]
    rows, problems = build_rows(pool, sources)
    checked, n_tasks, mism = verify_outcomes(rows, root)
    s = summary(rows, checked, n_tasks, mism)
    write_csv(rows, out)
    print(f"e3-verdicts: {s['rows']} rows -> {out}")
    print(f"outcome verified against task_results.resolved on {checked} rows over {n_tasks} tasks: {len(mism)} mismatches; pass {s['pass']} / fail {s['fail']}")
    print(f"H6 pairs (wrong patches judged by both R-self and R-fresh): wrong {s['wrong']}, judged by both {s['judged_by_both']}, b {s['b']}, c {s['c']}")
    for ref in REFEREES:
        c = s["referees"][ref]
        print(f"{ref}: " + ", ".join(f"{k or 'MISSING'} {v}" for k, v in sorted(c.items(), key=lambda kv: str(kv[0]))))
    print("configurations: " + ", ".join(f"{k} {v}" for k, v in sorted(s["configurations"].items())))
    code = 0
    for p in problems:
        print("PROBLEM: " + p)
        code = 1
    for m in mism[:20]:
        print("MISMATCH: " + m)
        code = 1
    if not a.no_expect:
        for k, want in REGISTERED.items():
            if s[k] != want:
                print(f"DISCREPANCY: {k} expected {want}, got {s[k]} (sources: {root / POOL}, " + ", ".join(VERDICT_FILES) + ")")
                code = 1
    print("registered counts reproduced" if code == 0 and not a.no_expect else ("counts not compared (--no-expect)" if code == 0 else "NOT reproduced"))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
