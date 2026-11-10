#!/usr/bin/env python3
"""Public copy of the ledger for the paper dataset (K2: every number a row; N-holdout-1: the holdout stays sealed).
Writes ledger-public.jsonl = ledger.jsonl with the per-task maps of the gold rows restricted to the 71 development
ids (the 34 holdout ids are removed and counted in "per_task_redacted"); every other row is copied unchanged.
Reads the holdout ids only to remove them; prints counts, never an id.
Usage: /usr/bin/python3 paper/release/ledger_public.py --out OUT.jsonl [--ledger ledger.jsonl]"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def redact(rows, holdout):
    out, removed = [], 0
    for r in rows:
        r = json.loads(json.dumps(r))
        pt = r.get("per_task")
        if isinstance(pt, dict):
            keep = {k: v for k, v in pt.items() if k not in holdout}
            n = len(pt) - len(keep)
            if n:
                r["per_task"], r["per_task_redacted"] = keep, n
                removed += n
        out.append(r)
    return out, removed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ledger", default=str(ROOT / "ledger.jsonl"))
    ap.add_argument("--holdout", default=None, help="test only; default: the vault's holdout_ids.txt")
    a = ap.parse_args(argv)
    if a.holdout:
        holdout = set(l.strip() for l in open(a.holdout) if l.strip())
    else:
        from common import VAULT
        holdout = set(l.strip() for l in open(VAULT / "holdout_ids.txt") if l.strip())
    rows = [json.loads(l) for l in open(a.ledger) if l.strip()]
    out, removed = redact(rows, holdout)
    text = "\n".join(json.dumps(r, sort_keys=True) for r in out) + "\n"
    assert not any(i in text for i in holdout), "a holdout id survived redaction"
    Path(a.out).write_text(text)
    print(json.dumps({"rows": len(out), "per_task_entries_removed": removed, "rows_redacted": sum(1 for r in out if r.get("per_task_redacted"))}))


if __name__ == "__main__":
    main()
