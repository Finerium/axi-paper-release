# Parser tax: the harness's "missing mandatory parameter" rejections in our own traces

The harness's tool-call parser rejects a call whose JSON arguments do not carry every mandatory parameter
(typically `edit_file` without `old_string`). The rejected call still costs an LLM call and wall time, the
model is told to retry, and it usually resends the same text. This directory measures that in every trace
we have, stdlib only, reproducibly.

## Command

```
/usr/bin/python3 analysis/parser-tax/audit.py --json analysis/parser-tax/audit.json      # all runs with traces
/usr/bin/python3 analysis/parser-tax/audit.py --runs cap-02 hint-01 hint-02 hint-03 k5-01 k6-01   # a subset
/usr/bin/python3 analysis/parser-tax/test_audit.py                                         # fixture check
```

`audit.py` scans `runs/<run>/<arm>/rep<k>/traces/trace_<task>.json`, lists the run directories that have
traces (runs without traces are skipped), reads `task_results.jsonl` beside `traces/` when present, prints the
Markdown below and, with `--json`, writes the same numbers plus the manifest (every trace file read with its
sha256) to `audit.json` (committed here, 959 files).

## Definitions

- **Session**: one trace file, i.e. one (run, arm, rep, task). `task` is the file name without `trace_`/`.json`
  and is joined to `task_results.jsonl` by `instance_id`.
- **Call**: one element of an agent step's `tool_calls` (any `function_name`). Tool results are not steps: the
  step's `observation` holds them. In all 959 traces the observation is a single dict per step (or `None` in 9
  steps); the four steps that carry several calls still hold one observation, which is attributed to the call
  whose `function_name` equals `observation.extra.tool_name` (fallback: the first call). A list observation
  aligned with the calls is also handled, although none exists today.
- **Rejected**: the call's observation text contains `mandatory input parameters are not present`. Nothing else
  (a tool error, an empty old_string match, a timeout) is a rejection.
- **Identical resend**: a rejected call whose `function_name` and `json.dumps(arguments, sort_keys=True)` equal
  an earlier rejected call in the same session.
- **Harness columns**: `tool_calls`, `total_llm_calls`, `duration_seconds`, `resolved` copied from the
  harness's `task_results.jsonl` row; blank (`None`) when the row is absent. The harness does not count a
  rejected call in `tool_calls` but does in `total_llm_calls` (cap-02 fastapi_14301: 35 calls in the trace, 28
  rejected, 7 counted).
- **Backtick share**: rejected calls whose serialised arguments contain a backtick, over all rejected calls.
- **Argument key sets**: the keys of the rejected call's `arguments` dict (each key truncated to 30 characters,
  newlines and pipes escaped), top 8. Keys that look like code are the parser's own recovery of a malformed
  argument string: they show how the text was split, not what the model meant.

## What the numbers do not show

- No resolve rate. `resolved` is tabulated as a count of flags among hit sessions only, and those sessions are
  not a random sample of anything: a task that attracts rejections is also a task the model finds hard.
- A rejection's cost is time and LLM calls, not harness tool calls: the harness's `tool_calls` already
  excludes them, so a budget stated in harness tool calls is not touched by the parser tax; a budget stated in
  wall time (the 480 s ceiling visible in several hit sessions) is.
- The per-tool share is over calls, not sessions: one runaway session (k3-01 ctl-spec rich_3454: 66 rejections,
  62 resends) moves the all-runs edit_file share by a few points on its own. The per-session table is the
  honest unit.
- The subset of six run directories (cap-02, hint-01, hint-02, hint-03, k5-01, k6-01; 129 sessions) is the one
  the session's hand count used; its figures below reproduce that count exactly (edit_file 81 of 381,
  write_file 3 of 169, run_command 0 of 1249, 13 sessions hit, 68 of 84 resends). Over all runs the backtick
  share is much higher (82%) than in that subset (39%): the backtick is one trigger, not the trigger.
- Runs before the current prompt family (dev-02 m02-nothink in particular) are included in the all-runs tables;
  compare arms, not the grand total, when asking whether a prompt change moved the tax.

## Output over the six-run subset (per-tool table only; the rest is in the all-runs output)

```
Runs with traces: cap-02, hint-01, hint-02, hint-03, k5-01, k6-01 (129 sessions)

### Per tool

| tool | calls | rejected | share |
|---|---:|---:|---:|
| edit_file | 381 | 81 | 21.3% |
| get_status | 19 | 0 | 0.0% |
| list_skills | 1 | 0 | 0.0% |
| read_file | 997 | 0 | 0.0% |
| run_command | 1249 | 0 | 0.0% |
| run_skill_script | 7 | 0 | 0.0% |
| submit_patch | 156 | 0 | 0.0% |
| write_file | 169 | 3 | 1.8% |
```

## Output over all runs with traces (`audit.py --json audit.json`, 2026-10-26)

Runs with traces: budget-01, cap-01, cap-02, dev-02, dev-03, dev-04, dl-01, e4b-01, e4b-02, fresh-01, gap-01, hint-01, hint-02, hint-03, k1-01, k2-01, k3-01, k4-01, k5-01, k6-01, k7-01, smoke-12b-01 (959 sessions)

### Per tool

| tool | calls | rejected | share |
|---|---:|---:|---:|
| code_analyzer_agent | 6 | 0 | 0.0% |
| edit_file | 2057 | 601 | 29.2% |
| get_code_neighbors | 10 | 0 | 0.0% |
| get_status | 96 | 0 | 0.0% |
| list_skills | 8 | 0 | 0.0% |
| load_skill | 11 | 0 | 0.0% |
| read_file | 6331 | 0 | 0.0% |
| run_command | 9128 | 0 | 0.0% |
| run_skill_script | 88 | 0 | 0.0% |
| search_similar_code | 178 | 0 | 0.0% |
| submit_patch | 628 | 0 | 0.0% |
| write_file | 509 | 27 | 5.3% |

### Per session (only sessions with >= 1 rejection; 86 of 959)

| run | arm | rep | task | trace calls | rejected | resends | harness tool_calls | total_llm_calls | duration s | resolved |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| budget-01 | floor-v5-8 | rep1 | fresh_jsonpickle_588 | 33 | 4 | 1 | 28 | 34 | 268.32 | True |
| budget-01 | floor-v5-8 | rep1 | fresh_mashumaro_313 | 31 | 12 | 10 | 18 | 32 | 432.58 | True |
| budget-01 | floor-v5-8 | rep1 | fresh_parse_221 | 26 | 2 | 1 | 23 | 27 | 294.09 | True |
| budget-01 | floor-v5-8 | rep1 | fresh_pygments_3171 | 11 | 1 | 0 | 9 | 12 | 143.68 | True |
| cap-02 | ref-budget-fit | rep1 | fastapi_11194 | 17 | 1 | 0 | 15 | 18 | 161.66 | True |
| cap-02 | ref-budget-fit | rep1 | fastapi_14297 | 21 | 1 | 0 | 17 | 22 | 164.03 | True |
| cap-02 | ref-budget-fit | rep1 | fastapi_14301 | 35 | 28 | 27 | 7 | 35 | 483.7 | False |
| cap-02 | ref-budget-fit | rep1 | fastapi_14360 | 17 | 1 | 0 | 13 | 18 | 323.25 | True |
| cap-02 | ref-budget-fit | rep1 | rich_3278 | 25 | 11 | 9 | 13 | 26 | 409.17 | True |
| dev-02 | floor-v0 | rep1 | fastapi_13713 | 23 | 3 | 1 | 20 | 23 | 183.46 | False |
| dev-02 | floor-v0 | rep1 | fastapi_14258 | 21 | 2 | 1 | 18 | 22 | 114.2 | False |
| dev-02 | floor-v0 | rep1 | fastapi_14964 | 19 | 3 | 2 | 16 | 19 | 189.12 | False |
| dev-02 | floor-v0 | rep1 | rich_3454 | 9 | 1 | 0 | 7 | 10 | 79.96 | True |
| dev-02 | m02-nothink | rep1 | fastapi_13713 | 37 | 3 | 2 | 34 | 37 | 181.39 | False |
| dev-02 | m02-nothink | rep1 | fastapi_14258 | 33 | 17 | 13 | 16 | 33 | 184.8 | False |
| dev-02 | m02-nothink | rep1 | fastapi_14360 | 52 | 21 | 18 | 31 | 52 | 184.78 | True |
| dev-02 | m02-nothink | rep1 | fastapi_14487 | 52 | 40 | 38 | 12 | 52 | 181.49 | False |
| dev-02 | m02-nothink | rep1 | fastapi_14978 | 48 | 21 | 20 | 26 | 49 | 137.19 | False |
| dev-02 | m02-nothink | rep1 | fastapi_14986 | 46 | 31 | 24 | 15 | 46 | 181.55 | False |
| dev-02 | m02-nothink | rep1 | fastapi_15800 | 55 | 10 | 7 | 44 | 56 | 149.41 | False |
| dev-02 | m02-nothink | rep1 | requests_6644 | 32 | 18 | 16 | 14 | 32 | 180.65 | False |
| dev-02 | m02-nothink | rep1 | rich_2943 | 58 | 9 | 8 | 48 | 59 | 135.23 | False |
| dev-02 | m02-nothink | rep1 | rich_3278 | 42 | 1 | 0 | 40 | 43 | 136.98 | False |
| dev-02 | m02-nothink | rep1 | rich_3454 | 51 | 10 | 9 | 40 | 52 | 160.36 | False |
| dev-02 | m02-nothink | rep1 | rich_3718 | 51 | 39 | 37 | 12 | 51 | 180.9 | False |
| dev-02 | m02-nothink | rep1 | rich_3953 | 52 | 8 | 5 | 42 | 53 | 148.97 | False |
| dev-02 | pi0 | rep1 | fastapi_14258 | 33 | 2 | 1 | 31 | 33 | 185.01 | False |
| dev-02 | pi0 | rep1 | fastapi_14485 | 31 | 8 | 5 | 23 | 31 | 181.41 | False |
| dev-02 | pi0 | rep1 | rich_3454 | 20 | 7 | 5 | 12 | 21 | 152.54 | True |
| dev-03 | floor-v2 | rep1 | fastapi_13713 | 39 | 1 | 0 | 38 | 39 | 214.67 | False |
| dev-03 | floor-v2 | rep1 | fastapi_14258 | 35 | 12 | 8 | 22 | 36 | 196.05 | False |
| dev-03 | floor-v2 | rep1 | fastapi_14583 | 22 | 1 | 0 | 21 | 22 | 217.64 | False |
| dev-03 | floor-v2 | rep1 | fastapi_14964 | 19 | 5 | 4 | 14 | 19 | 215.48 | False |
| dev-03 | floor-v2 | rep1 | rich_3454 | 26 | 5 | 3 | 20 | 27 | 151.98 | True |
| dev-03 | floor-v2 | rep1 | rich_4070 | 38 | 11 | 10 | 27 | 38 | 215.23 | False |
| dev-04 | floor-v3 | rep1 | fastapi_14258 | 43 | 1 | 0 | 41 | 44 | 228.2 | False |
| dev-04 | floor-v3 | rep1 | fastapi_14463 | 20 | 1 | 0 | 19 | 20 | 247.54 | True |
| dev-04 | floor-v3 | rep1 | fastapi_14986 | 34 | 12 | 10 | 22 | 34 | 249.73 | False |
| dev-04 | floor-v3 | rep1 | rich_3454 | 16 | 1 | 0 | 14 | 17 | 110.29 | True |
| dev-04 | floor-v3 | rep1 | rich_3518 | 14 | 1 | 0 | 12 | 15 | 122.85 | True |
| dl-01 | floor-v6-8-dl | rep1 | fresh_pygments_3180 | 16 | 1 | 0 | 14 | 17 | 134.34 | True |
| dl-01 | floor-v6-8-dl | rep1 | fresh_queuelib_89 | 21 | 7 | 5 | 13 | 23 | 154.38 | True |
| e4b-01 | e4b-control | rep1 | rich_3454 | 13 | 3 | 0 | 9 | 14 | 67.98 | True |
| e4b-01 | e4b-control | rep1 | rich_3535 | 15 | 1 | 0 | 13 | 16 | 117.59 | False |
| e4b-02 | e4b-control | rep1 | fastapi_14978 | 27 | 4 | 0 | 22 | 28 | 228.38 | False |
| e4b-02 | e4b-control | rep1 | rich_3043 | 15 | 3 | 1 | 11 | 16 | 137.56 | False |
| e4b-02 | e4b-control | rep1 | rich_3454 | 13 | 2 | 0 | 10 | 14 | 77.58 | True |
| e4b-02 | e4b-iter | rep1 | fastapi_14986 | 19 | 1 | 0 | 17 | 20 | 201.05 | False |
| e4b-02 | e4b-iter | rep1 | rich_3043 | 16 | 2 | 0 | 13 | 17 | 141.97 | False |
| e4b-02 | e4b-iter | rep1 | rich_3278 | 23 | 6 | 2 | 16 | 24 | 157.13 | False |
| e4b-02 | e4b-iter | rep1 | rich_3454 | 10 | 1 | 0 | 8 | 11 | 56.57 | True |
| fresh-01 | floor-v3 | rep1 | fresh_jsonpickle_588 | 35 | 3 | 1 | 31 | 36 | 230.65 | True |
| gap-01 | floor-v5-8 | rep1 | rich_3454 | 18 | 1 | 0 | 16 | 19 | 89.63 | True |
| hint-01 | ref-budget-fit | rep1 | fastapi_14964 | 12 | 1 | 0 | 10 | 13 | 122.23 | False |
| hint-01 | ref-budget-fit | rep1 | rich_3061 | 31 | 1 | 0 | 28 | 32 | 335.43 | False |
| k1-01 | floor-v8-t1 | rep1 | rich_3454 | 28 | 3 | 2 | 22 | 29 | 202.98 | True |
| k1-01 | ref-budget-fit | rep1 | fastapi_13207 | 27 | 1 | 0 | 23 | 28 | 224.85 | True |
| k2-01 | floor-v5-8-12b-1k | rep1 | rich_3043 | 30 | 1 | 0 | 28 | 31 | 255.85 | False |
| k3-01 | ctl-both | rep1 | fastapi_14986 | 24 | 1 | 0 | 22 | 25 | 207.95 | False |
| k3-01 | ctl-both | rep1 | rich_3061 | 30 | 1 | 0 | 28 | 31 | 305.0 | False |
| k3-01 | ctl-both | rep1 | rich_3454 | 35 | 6 | 4 | 28 | 36 | 383.82 | True |
| k3-01 | ctl-both | rep1 | rich_3518 | 20 | 1 | 0 | 18 | 21 | 107.83 | True |
| k3-01 | ctl-repro | rep1 | fastapi_14978 | 29 | 1 | 0 | 28 | 29 | 485.29 | False |
| k3-01 | ctl-repro | rep1 | rich_3278 | 27 | 1 | 0 | 25 | 27 | 480.88 | False |
| k3-01 | ctl-repro | rep1 | rich_3454 | 38 | 11 | 10 | 26 | 39 | 337.07 | True |
| k3-01 | ctl-repro | rep1 | rich_3777 | 32 | 2 | 0 | 28 | 33 | 282.38 | False |
| k3-01 | ctl-spec | rep1 | fastapi_14301 | 27 | 1 | 0 | 24 | 28 | 180.19 | True |
| k3-01 | ctl-spec | rep1 | rich_3278 | 15 | 2 | 1 | 12 | 16 | 266.15 | False |
| k3-01 | ctl-spec | rep1 | rich_3454 | 77 | 66 | 62 | 11 | 77 | 483.47 | True |
| k3-01 | ref-budget-fit | rep1 | fastapi_5077 | 35 | 6 | 5 | 28 | 37 | 357.83 | True |
| k3-01 | ref-budget-fit | rep1 | rich_3454 | 18 | 2 | 1 | 14 | 19 | 133.83 | True |
| k4-01 | ref-v2 | rep1 | fastapi_13207 | 36 | 7 | 6 | 28 | 37 | 310.76 | True |
| k4-01 | ref-v2 | rep1 | fastapi_14986 | 29 | 2 | 0 | 27 | 30 | 488.5 | False |
| k4-01 | v2-cfg | rep1 | fastapi_14986 | 33 | 4 | 2 | 28 | 34 | 274.88 | False |
| k4-01 | v2-cfg | rep1 | rich_3278 | 11 | 3 | 1 | 8 | 11 | 483.71 | False |
| k4-01 | v2-cfg | rep1 | rich_3454 | 30 | 15 | 14 | 14 | 31 | 207.02 | True |
| k4-01 | v2-cfg | rep1 | rich_3518 | 31 | 2 | 0 | 28 | 32 | 149.55 | True |
| k5-01 | ctl-cfg | rep1 | fastapi_14986 | 49 | 23 | 20 | 25 | 50 | 368.8 | False |
| k5-01 | ctl-cfg | rep1 | rich_3278 | 29 | 1 | 0 | 27 | 30 | 375.25 | True |
| k5-01 | ref-budget-fit | rep1 | fastapi_9425 | 30 | 1 | 0 | 26 | 31 | 170.91 | True |
| k5-01 | ref-budget-fit | rep1 | rich_3278 | 34 | 7 | 6 | 23 | 35 | 361.3 | False |
| k6-01 | ctl-locate | rep1 | rich_3278 | 23 | 1 | 0 | 21 | 25 | 333.67 | False |
| k6-01 | ref-budget-fit | rep1 | rich_3278 | 17 | 7 | 6 | 10 | 17 | 480.9 | False |
| k7-01 | ctl-shim | rep1 | fastapi_13207 | 30 | 1 | 0 | 26 | 31 | 299.55 | False |
| k7-01 | ctl-shim | rep1 | fastapi_13713 | 38 | 20 | 17 | 18 | 38 | 483.57 | False |
| k7-01 | ref-budget-fit | rep1 | fastapi_13207 | 48 | 25 | 22 | 23 | 48 | 484.47 | False |

Sessions hit: 86 of 959; rejections: 628; identical resends: 483; resolved among hit sessions: 36 of 86 with a harness row

### Per task (only tasks with >= 1 hit session)

| task | sessions | with >= 1 rejection | with >= 7 |
|---|---:|---:|---:|
| fastapi_11194 | 6 | 1 | 0 |
| fastapi_13207 | 24 | 4 | 2 |
| fastapi_13713 | 8 | 4 | 1 |
| fastapi_14258 | 6 | 5 | 2 |
| fastapi_14297 | 6 | 1 | 0 |
| fastapi_14301 | 25 | 2 | 1 |
| fastapi_14360 | 6 | 2 | 1 |
| fastapi_14463 | 6 | 1 | 0 |
| fastapi_14485 | 6 | 1 | 1 |
| fastapi_14487 | 25 | 1 | 1 |
| fastapi_14583 | 7 | 1 | 0 |
| fastapi_14964 | 6 | 3 | 0 |
| fastapi_14978 | 21 | 3 | 1 |
| fastapi_14986 | 25 | 7 | 3 |
| fastapi_15800 | 7 | 1 | 1 |
| fastapi_5077 | 25 | 1 | 0 |
| fastapi_9425 | 25 | 1 | 0 |
| fresh_jsonpickle_588 | 4 | 2 | 0 |
| fresh_mashumaro_313 | 4 | 1 | 1 |
| fresh_parse_221 | 4 | 1 | 0 |
| fresh_pygments_3171 | 4 | 1 | 0 |
| fresh_pygments_3180 | 4 | 1 | 0 |
| fresh_queuelib_89 | 4 | 1 | 1 |
| requests_6644 | 26 | 1 | 1 |
| rich_2943 | 6 | 1 | 1 |
| rich_3043 | 21 | 3 | 0 |
| rich_3061 | 25 | 2 | 0 |
| rich_3278 | 25 | 10 | 3 |
| rich_3454 | 22 | 15 | 5 |
| rich_3518 | 21 | 3 | 0 |
| rich_3535 | 25 | 1 | 0 |
| rich_3718 | 6 | 1 | 1 |
| rich_3777 | 25 | 1 | 0 |
| rich_3953 | 6 | 1 | 1 |
| rich_4070 | 6 | 1 | 1 |

### Rejected argument sets

With a backtick: 515 of 628 (82.0%)

| argument keys | rejected calls |
|---|---:|
| filepath, new_string | 87 |
| (" https, [Span(1, 20, "repr.url")]),\n , filepath, new_string | 55 |
| .?/;, filepath, new_string, r\"(?P<url>(file\|https\|http\|ws | 45 |
| @app.exception_handler(Request, filepath, new_string | 40 |
| filepath, new_string, title_text = self._title\n     | 39 |
| (?, filepath, new_string | 30 |
| content | 23 |
| allow_multiple, filepath, new_string, override_mode | 23 |

Manifest: 959 trace files (sha256 in --json output).

## Fixture check

```
$ /usr/bin/python3 analysis/parser-tax/test_audit.py
test_audit: ok (per-tool, per-session, resends, per-task, backtick share, manifest, markdown)
```

The fixture writes two traces into a temp dir: one with a rejected `edit_file`, its identical resend, a
third rejected `edit_file` with different arguments and an accepted `run_command`; one clean. It asserts the
per-tool counts (edit_file 3 of 3, run_command 0 of 2), the per-session row (4 calls, 3 rejected, 1 resend,
the harness columns), the per-task counts, the backtick share (2 of 3), the key-set histogram and the manifest.
