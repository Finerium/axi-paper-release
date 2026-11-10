#!/usr/bin/env python3
"""The detectable-lift planning aid behind the "detectable lift at 80% power" figures of W1 (Table 2 caption, supplement S4) and W2
(Sections 4 and 8). Standard library only. sign_flip_p and cmd_mde are copied verbatim from the campaign's ledger tool (ledger.py);
the seed is fixed, so the output is reproducible:  python3 mde.py --n 62 --k 1 --base 0.2
A planning aid, not evidence: it simulates heterogeneous per-task solve probabilities (Beta with the given mean), adds the lift
to every task (capped at 1) and reports the smallest lift the exact one-sided paired sign-flip test detects with 80% power."""
import argparse
import json
import random
from collections import defaultdict

ALPHA = 0.10


def sign_flip_p(a_counts: dict, b_counts: dict) -> tuple:
    """Exact one-sided paired permutation test that B beats A.

    Per task, d = (B successes - A successes) over equal replicates; under H0 the arm labels are exchangeable within a
    task, so each d keeps its size and flips its sign with probability 1/2. With one replicate this is the exact
    McNemar (sign) test on discordant tasks. Returns (p, observed statistic, number of non-zero tasks)."""
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
    total = 2 ** len(w)
    return sum(c for s, c in dist.items() if s >= t_obs) / total, t_obs, len(w)


def cmd_mde(a) -> None:
    """Power of the gate by simulation: per-task solve probabilities are heterogeneous (Beta with the given mean and
    concentration), arm B adds `delta` to each. Prints the power per delta and the smallest delta with 80% power."""
    rng = random.Random(20261004)
    a_beta = a.base * a.concentration
    b_beta = (1 - a.base) * a.concentration
    out = []
    for step in range(1, 16):
        delta = step * 0.02
        hits = 0
        for _ in range(a.sims):
            ps = [rng.betavariate(a_beta, b_beta) for _ in range(a.n)]
            ca = {i: sum(rng.random() < p for _ in range(a.k)) for i, p in enumerate(ps)}
            cb = {i: sum(rng.random() < min(1.0, p + delta) for _ in range(a.k)) for i, p in enumerate(ps)}
            if sign_flip_p(ca, cb)[0] < ALPHA:
                hits += 1
        out.append({"delta": round(delta, 2), "tasks": round(delta * a.n, 1), "power": round(hits / a.sims, 3)})
        if hits / a.sims >= 0.8:
            break
    mde = next((r for r in out if r["power"] >= 0.8), None)
    print(json.dumps({"n": a.n, "k": a.k, "base": a.base, "alpha": ALPHA, "planning_aid_not_evidence": True,
                      "mde_80": mde, "curve": out}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--base", type=float, default=0.2)
    ap.add_argument("--concentration", type=float, default=1.0)
    ap.add_argument("--sims", type=int, default=400)
    cmd_mde(ap.parse_args())
