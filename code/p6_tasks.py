#!/usr/bin/env python3
"""p6-tasks.csv for the paper dataset: one line per AXI-Fresh task with the system arm's and the floor arm's outcome,
read from the two ledger rows the paper pairs (K2: the CSV is derived from rows, never typed).
Usage: /usr/bin/python3 paper/release/p6_tasks.py --out OUT.csv [--system r0045] [--floor r0054] [--ledger ledger.jsonl]"""
import argparse, csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def rows_for(ledger, system, floor):
    want = {system: None, floor: None}
    for line in Path(ledger).read_text().splitlines():
        r = json.loads(line)
        if r.get("kind") == "run" and r.get("row_id") in want:
            want[r["row_id"]] = r
    missing = [k for k, v in want.items() if v is None]
    if missing:
        sys.exit(f"ledger rows not found: {missing}")
    return want[system], want[floor]


def table(sys_row, floor_row):
    ids = sorted(set(sys_row["per_task"]) | set(floor_row["per_task"]))
    out = []
    for t in ids:
        s, f = sys_row["per_task"].get(t), floor_row["per_task"].get(t)
        out.append({"task": t, "system_" + sys_row["row_id"]: s, "floor_" + floor_row["row_id"]: f,
                    "differs": int(s is not None and f is not None and s != f)})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--system", default="r0045")
    ap.add_argument("--floor", default="r0054")
    ap.add_argument("--ledger", default=str(ROOT / "ledger.jsonl"))
    a = ap.parse_args(argv)
    s, f = rows_for(a.ledger, a.system, a.floor)
    t = table(s, f)
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(t[0].keys()))
        w.writeheader()
        w.writerows(t)
    print(json.dumps({"tasks": len(t), "system_resolved": sum(r[f"system_{a.system}"] or 0 for r in t),
                      "floor_resolved": sum(r[f"floor_{a.floor}"] or 0 for r in t), "differing": sum(r["differs"] for r in t)}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":  # the one check: a differing task is counted once, a tie never
        t = table({"row_id": "a", "per_task": {"x": 1, "y": 0}}, {"row_id": "b", "per_task": {"x": 0, "y": 0}})
        assert [r["differs"] for r in t] == [1, 0], t
        print("selftest ok")
    else:
        main()
