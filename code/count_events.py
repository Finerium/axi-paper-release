#!/usr/bin/env python3
"""Count the campaign's autonomy, memory and control events from the Claude Code session transcripts (primary records),
so W1's counts do not rest on the agent's own hand-kept logs. Prints counts and timestamps only, never content.

  /usr/bin/python3 analysis/events/count_events.py [PROJECT_TRANSCRIPT_DIR]

Counted, from the main session file(s) and every subagent file:
  human inputs     user records whose origin kind is "human" (typed, queued or accepted suggestions)
  peer relays      user records whose origin kind is "peer" (another Claude Code session of the author relaying the author's input)
  compactions      records flagged isCompactSummary
  session starts   attachment records from a SessionStart hook, split by its source (startup, resume, compact)
  hook blocks      error tool results carrying the worker guard hook's refusal sentence
  script refusals  results of ledger.py, split.py or kaggle_ops.py commands (not their unit tests) that refused
"""
import glob
import json
import os
import re
import sys
from collections import Counter

if len(sys.argv) < 2:
    sys.exit("usage: count_events.py PROJECT_TRANSCRIPT_DIR")
DIR = sys.argv[1]


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for b in content:
            if isinstance(b, dict):
                c = b.get("content", b.get("text", ""))
                out.append(text_of(c) if not isinstance(c, str) else c)
        return " ".join(out)
    return ""


BLOCK = "Workers build candidates and return artifacts plus lessons"  # the guard hook's refusal sentence
SCRIPTS = re.compile(r"scripts/(ledger|split|kaggle_ops)\.py")
REFUSAL = re.compile(r"REFUSED|working tree is dirty|already in the ledger|is not committed")


def scan(path, is_sub, counts, days, starts):
    commands = {}
    with open(path, errors="ignore") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            ts = r.get("timestamp") or ""
            origin = r.get("origin") if isinstance(r.get("origin"), dict) else {}
            if r.get("type") == "user" and not is_sub:
                kind = origin.get("kind")
                if kind in ("human", "peer"):
                    key = "human inputs" if kind == "human" else "peer relays"
                    counts[key] += 1
                    days[key][ts[:10]] += 1
            if r.get("isCompactSummary"):
                counts["compactions"] += 1
                days["compactions"][ts[:10]] += 1
            blob = json.dumps(r)
            if not is_sub:
                n = blob.count("cross-session-message from=")
                if n and r.get("type") != "assistant":
                    starts.setdefault("peer_msgs", set()).add((ts[:16], n))
            if r.get("type") == "attachment":
                m = re.search(r"SessionStart:(startup|resume|compact|clear)", blob)
                if m:
                    starts.setdefault(m.group(1), set()).add(ts[:16])
            msg = r.get("message") if isinstance(r.get("message"), dict) else {}
            content = msg.get("content")
            if r.get("type") == "assistant" and isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        commands[b.get("id")] = json.dumps(b.get("input", {}))
            if isinstance(content, list) and content and isinstance(content[0], dict) and content[0].get("type") == "tool_result":
                t = text_of(content)
                who = " (subagents)" if is_sub else " (main)"
                if BLOCK in t and content[0].get("is_error"):
                    counts["hook blocks" + who] += 1
                cmd = commands.get(content[0].get("tool_use_id"), "")
                if SCRIPTS.search(cmd) and "unittest" not in cmd and REFUSAL.search(t):
                    counts["script refusals" + who] += 1


def main():
    counts, days, starts = Counter(), {k: Counter() for k in ("human inputs", "peer relays", "compactions")}, {}
    mains = sorted(glob.glob(os.path.join(DIR, "*.jsonl")))
    subs = sorted(glob.glob(os.path.join(DIR, "*", "subagents", "*.jsonl")))
    for p in mains:
        scan(p, False, counts, days, starts)
    for p in subs:
        scan(p, True, counts, days, starts)
    for k in ("startup", "resume", "compact", "clear"):
        if k in starts:
            counts["session start events: " + k + " (distinct minutes)"] = len(starts[k])
    if "peer_msgs" in starts:
        counts["peer relays inside system reminders (distinct minutes)"] = len({m for m, _ in starts["peer_msgs"]})
    print(json.dumps({"main_files": len(mains), "subagent_files": len(subs), "counts": dict(sorted(counts.items())),
                      "by_day": {k: dict(sorted(v.items())) for k, v in days.items()}}, indent=1))


if __name__ == "__main__":
    main()
