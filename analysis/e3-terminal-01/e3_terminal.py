#!/usr/bin/env python3
"""e3-terminal-01 (exploratory, post hoc; the adversarial reviewer's objection of panel round 5, 2026-11-05): the in-task check
likelihood ratios of the referee study, split by whether the session that produced the patch timed out. A timed-out session
has no final submit and no closing message, so it scores "no claim" by construction; if every timed-out patch is wrong, the
pooled self-claim LR measures finishing in time, not judgement. Reads the release table built by paper/release/e3_verdicts.py
and the pool runs' task_results.jsonl (the session's error field). Writes results.json and tables.md next to this file.
Usage: /usr/bin/python3 analysis/e3-terminal-01/e3_terminal.py [--verdicts e3-verdicts.csv] [--draws 10000]"""
import argparse, csv, json, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RUNS = {"dev-02/floor-v0": "runs/dev-02/floor-v0/rep1/task_results.jsonl", "dev-02/pi0": "runs/dev-02/pi0/rep1/task_results.jsonl",
        "dev-02/m02-nothink": "runs/dev-02/m02-nothink/rep1/task_results.jsonl", "dev-03/floor-v2": "runs/dev-03/floor-v2/rep1/task_results.jsonl",
        "dev-04/floor-v3": "runs/dev-04/floor-v3/rep1/task_results.jsonl"}
CHECKS = ["R-self", "R-repro", "R-near", "R-fresh"]


def stratum(rec):
    return "timeout" if "timeout" in str(rec.get("error") or "").lower() else "terminal"


def accepts(x, check):
    if check == "self+fresh":  # the conjunction: accepts when both accept, defined where both are
        if x["R-self"] not in ("accept", "reject") or x["R-fresh"] not in ("accept", "reject"):
            return None
        return x["R-self"] == "accept" and x["R-fresh"] == "accept"
    v = x[check]
    return None if v not in ("accept", "reject") else v == "accept"


def rates(sub, check):
    corr = [a for a in (accepts(x, check) for x in sub if x["outcome"] == "pass") if a is not None]
    wrong = [a for a in (accepts(x, check) for x in sub if x["outcome"] == "fail") if a is not None]
    if not corr or not wrong:
        return {"n_correct": len(corr), "n_wrong": len(wrong), "alpha": None, "beta": None, "lr": None}
    alpha, beta = sum(corr) / len(corr), sum(wrong) / len(wrong)
    return {"n_correct": len(corr), "n_wrong": len(wrong), "alpha": round(alpha, 3), "beta": round(beta, 3),
            "lr": round(alpha / beta, 2) if beta > 0 else None}


def bootstrap_lr(sub, check, draws, seed=20261105):
    """90 percent interval of the LR over patches (resampled within outcome, so both rates stay defined)."""
    rng = random.Random(seed)
    corr = [a for a in (accepts(x, check) for x in sub if x["outcome"] == "pass") if a is not None]
    wrong = [a for a in (accepts(x, check) for x in sub if x["outcome"] == "fail") if a is not None]
    if not corr or not wrong:
        return None
    vals = []
    for _ in range(draws):
        a = sum(rng.choice(corr) for _ in corr) / len(corr)
        b = sum(rng.choice(wrong) for _ in wrong) / len(wrong)
        if b > 0:
            vals.append(a / b)
    vals.sort()
    return [round(vals[int(0.05 * len(vals))], 2), round(vals[int(0.95 * len(vals)) - 1], 2)] if vals else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdicts", default=str(Path(__file__).with_name("e3-verdicts.csv")))
    ap.add_argument("--draws", type=int, default=10000)
    a = ap.parse_args(argv)
    rows = list(csv.DictReader(open(a.verdicts)))
    rec = {}
    for cfg, p in RUNS.items():
        for line in open(ROOT / p):
            r = json.loads(line)
            rec[(cfg, r["instance_id"])] = r
    strata = {"all": [], "terminal": [], "timeout": []}
    for x in rows:
        r = rec[(x["configuration"], x["task"])]
        strata["all"].append(x)
        strata[stratum(r)].append(x)
    out = {"id": "e3-terminal-01", "exploratory": True, "post_hoc": True, "patches": len(rows),
           "strata": {k: len(v) for k, v in strata.items()},
           "timeout_outcomes": {"pass": sum(x["outcome"] == "pass" for x in strata["timeout"]),
                                "fail": sum(x["outcome"] == "fail" for x in strata["timeout"])},
           "checks": {}}
    for check in CHECKS + ["self+fresh"]:
        out["checks"][check] = {}
        for s in ("all", "terminal", "timeout"):
            d = rates(strata[s], check)
            if s != "timeout":
                d["lr_90"] = bootstrap_lr(strata[s], check, a.draws)
            out["checks"][check][s] = d
    here = Path(__file__).parent
    json.dump(out, open(here / "results.json", "w"), indent=1)
    lines = ["| check | stratum | correct | wrong | alpha | beta | LR [90%] |", "|---|---|---|---|---|---|---|"]
    for check, per in out["checks"].items():
        for s, d in per.items():
            lr = f"{d['lr']} {d.get('lr_90')}" if d.get("lr") is not None else "undefined"
            lines.append(f"| {check} | {s} | {d['n_correct']} | {d['n_wrong']} | {d['alpha']} | {d['beta']} | {lr} |")
    (here / "tables.md").write_text("# e3-terminal-01: in-task checks by session exit (exploratory, post hoc)\n\n"
                                    f"Patches {len(rows)}; timed-out sessions {out['strata']['timeout']} (all wrong: "
                                    f"{out['timeout_outcomes']}); terminal {out['strata']['terminal']}.\n\n" + "\n".join(lines) + "\n")
    print(json.dumps({k: out[k] for k in ("patches", "strata", "timeout_outcomes")}))
    for check in CHECKS + ["self+fresh"]:
        print(check, "pooled", out["checks"][check]["all"]["lr"], "terminal", out["checks"][check]["terminal"]["lr"], out["checks"][check]["terminal"].get("lr_90"))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":  # the one check: a timed-out session is the timeout stratum, a clean one is terminal
        assert stratum({"error": "Agent exceeded session timeout (4.0 min)"}) == "timeout" and stratum({"error": None}) == "terminal"
        x = {"R-self": "accept", "R-fresh": "reject"}
        assert accepts(x, "self+fresh") is False and accepts({"R-self": "undefined", "R-fresh": "accept"}, "self+fresh") is None
        print("selftest ok")
    else:
        main()
