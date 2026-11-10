#!/usr/bin/env python3
"""public-trajectories.csv for the paper dataset (W1 Table 3 / supplement S5): one row per sampled public trajectory and
referee, from analysis/e3-public/results.json (the per-trajectory verdicts e3_public.py computed; CC BY 4.0 sources, nebius).
Columns: source, model, instance, trajectory, referee, verdict (accept | reject | undefined), outcome (pass | fail).
Usage: /usr/bin/python3 paper/release/public_trajectories.py --out OUT.csv [--results analysis/e3-public/results.json]"""
import argparse, csv, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
MODEL = {"openhands": "Qwen3-Coder-480B-A35B-Instruct"}  # one model per source frame; swe_agent rows carry model_name
REFEREES = (("self_claim", "self-claim"), ("own_repro", "own reproduction"))


def rows_of(results):
    out = []
    for source, v in results["sources"].items():
        for i, r in enumerate(v["rows"]):
            for key, name in REFEREES:
                out.append({"source": source, "model": r.get("model_name") or MODEL.get(source, ""), "instance": r.get("instance_id", ""),
                            "trajectory": r.get("trajectory_id") or f"{source}-{i}", "referee": name,
                            "verdict": r.get(key) or "undefined", "outcome": "pass" if r.get("resolved") else "fail"})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--results", default=str(ROOT / "analysis/e3-public/results.json"))
    a = ap.parse_args(argv)
    out = rows_of(json.load(open(a.results)))
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, ["source", "model", "instance", "trajectory", "referee", "verdict", "outcome"])
        w.writeheader(); w.writerows(out)
    print(json.dumps({"rows": len(out), "sources": sorted({r["source"] for r in out})}))


if __name__ == "__main__":
    main()
