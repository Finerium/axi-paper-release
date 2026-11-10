#!/usr/bin/env python3
"""public-task-audit.csv: the public tasks whose reference fix fails the competition's grader in the subprocess sandbox after
the dependency repairs (gold-02, ledger r0002: 24 of 129), plus the one development task an empty patch resolves. Columns:
instance_id, repo, outcome, test_exit_code, error (as the harness recorded it), diagnosis (repository-level, from the
gold-01/gold-02 reading in memory/DIAGNOSES.md; "not diagnosed per task" where no per-task cause was recorded).
Reads only runs/gold-02/task_results.jsonl (public task ids; no patch or statement text). Refuses unless exactly 24 tasks fail.
Usage: /usr/bin/python3 paper/release/public_task_audit.py [--out public-task-audit.csv]
"""
import argparse, csv, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "runs" / "gold-02" / "task_results.jsonl"
DIAG = {
    "psf/requests": "the repository's test server (pytest-httpbin) has compiled dependencies the sandbox lacks, so the conftest fixture fails; requests_7205 also reads a .netrc in the kernel's home",
    "Textualize/rich": "rendering tests pinned to the snapshot's Pygments; the harness injects Pygments 2.21.0 (rich_3782: environment detection sees IPython after the dependency repair)",
    "encode/httpx": "test collection error in the sandbox",
    "fastapi/fastapi": "not diagnosed per task (tests fail or a required test node does not pass with the reference fix)",
}
EMPTY_RESOLVES = {"fastapi_14851": "resolved by an empty patch in a development run (dev-02 m02-nothink, analysis trace-fail-01): the grading tests pass without the fix"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="public-task-audit.csv")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(RESULTS)]
    failing = [r for r in rows if not r["resolved"]]
    assert len(rows) == 129 and len(failing) == 24, f"expected 24 of 129 failing, got {len(failing)} of {len(rows)}"
    out = []
    for r in failing:
        out.append({"instance_id": r["instance_id"], "repo": r["repo"], "outcome": "reference fix fails",
                    "test_exit_code": r["test_exit_code"], "error": (r.get("error") or "").replace("\n", " ")[:120],
                    "diagnosis": DIAG[r["repo"]]})
    for r in rows:
        if r["instance_id"] in EMPTY_RESOLVES:
            out.append({"instance_id": r["instance_id"], "repo": r["repo"], "outcome": "reference fix passes; empty patch also passes",
                        "test_exit_code": r["test_exit_code"], "error": "", "diagnosis": EMPTY_RESOLVES[r["instance_id"]]})
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["instance_id", "repo", "outcome", "test_exit_code", "error", "diagnosis"])
        w.writeheader()
        w.writerows(out)
    print(json.dumps({"rows": len(out), "failing": len(failing), "by_repo": {k: sum(1 for r in failing if r["repo"] == k) for k in DIAG}}))


if __name__ == "__main__":
    main()
