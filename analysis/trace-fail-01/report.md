# trace-fail-01: where the single-loop Gemma 4 agents fail on the 71 development tasks

Data: our own run directories only (runs/dev-02/{pi0, floor-v0, m02-nothink}/rep1, runs/dev-03/floor-v2/rep1, runs/dev-04/floor-v3/rep1),
task_results.jsonl, patches/, traces/ (full tool arguments). 5 arms x 71 tasks = 355 (arm, task) pairs. Resolved counts per arm here are
read from task_results.jsonl (pi0 16, floor-v0 19, m02-nothink 15, floor-v2 21, floor-v3 19, union 31 tasks); the authoritative numbers are the
ledger rows for dev-02/03/04, not this file. Code: analyze.py (per-pair features, rows.json) and tables.py (this file's tables), stdlib only.

## Definitions (read these before the tables)
- Seconds are the session clock in each tool call's `extra.elapsed_s` (0 = session start; the first tool call lands at a median 5 to 10 s).
- Edit = a successful edit_file or write_file on a repository path, plus any repository file in the final patch (shell edits of repo files
  were checked: 1 instance in 4,212 run_command calls, all other shell writes went to /tmp). Root-level ad-hoc scripts (repro.py) and /tmp
  do not count. "Source edit" excludes tests/.
- Edit-site files (proxy): union of non-test, non-scratch files changed by any resolving patch of any arm. 30 of the 31 tasks have one;
  fastapi_14851 was resolved by m02-nothink with an empty patch and is excluded from Q2. A different valid fix site would be invisible to this proxy.
- Found = the site file's path (last two components, so fastapi/dependencies/utils.py is not confused with fastapi/openapi/utils.py) appears
  in a read_file path, in a run_command string, or in any tool output (grep -rn, find, search hits). "Strict" = only read_file or command string.
- Classes for failing pairs on those 30 tasks: (a) never found; (b) found, never edited a site file; (c) edited a site file, patch still wrong.
- Wasted calls: paging = read_file calls on a file read 5+ times in that pair; tool-level failure = an error that is not a non-zero shell exit
  (malformed arguments, old_string not found, write outside workspace, missing file, budget); repeated = identical function and arguments
  seen earlier in the same pair.

### Q1 outcome x timeout (cells: timeout / no timeout)

| arm | resolved | wrong patch | empty patch | timeouts | context-window error | n |
|---|---|---|---|---|---|---|
| pi0 | 0 / 16 | 14 / 2 | 39 / 0 | 53 | 0 | 71 |
| floor-v0 | 0 / 19 | 14 / 3 | 34 / 1 | 48 | 1 | 71 |
| m02-nothink | 0 / 15 | 5 / 19 | 12 / 20 | 17 | 0 | 71 |
| floor-v2 | 0 / 21 | 12 / 6 | 32 / 0 | 44 | 0 | 71 |
| floor-v3 | 0 / 19 | 10 / 8 | 33 / 1 | 43 | 1 | 71 |
| pooled | 0 / 90 | 55 / 38 | 150 / 22 | 205 | 2 | 355 |

### Q2 localisation on the 30 tasks some arm resolved (failing arm-task pairs)

| arm | failures | (a) never found | (b) found, never edited | (c) edited site, wrong | strict a/b/c (opened, not just in output) | (c) with site file in final patch | (c) that timed out |
|---|---|---|---|---|---|---|---|
| pi0 | 14 | 0 | 13 | 1 | 0/13/1 | 1 | 1 |
| floor-v0 | 11 | 0 | 8 | 3 | 1/7/3 | 3 | 3 |
| m02-nothink | 16 | 1 | 11 | 4 | 1/11/4 | 4 | 1 |
| floor-v2 | 9 | 0 | 6 | 3 | 0/6/3 | 3 | 1 |
| floor-v3 | 11 | 0 | 8 | 3 | 0/8/3 | 3 | 2 |
| pooled | 61 | 1 | 46 | 14 | 2/45/14 | 14 | 8 |

Per class, pooled: outcome, timeout, seconds to first sight / open / first source edit / site edit

| class | n | empty | wrong | timeout | first sight s | first open s | first edit s | first site edit s |
|---|---|---|---|---|---|---|---|---|
| a | 1 | 1 | 0 | 1 | n=0 | n=0 | n=0 | n=0 |
| b | 46 | 42 | 4 | 40 | n=46 13 [6, 32] | n=45 19 [10, 34] | n=2 med 174 | n=0 |
| c | 14 | 0 | 14 | 8 | n=14 9 [6, 13] | n=14 10 [7, 13] | n=14 101 [71, 154] | n=14 101 [71, 154] |

Reference, resolved pairs (n=89): first sight n=89 9 [7, 14]; first open n=89 12 [9, 17]; first site edit n=89 75 [48, 125]

What the failures edited instead (class a and b, files in final patch or edited, pooled)

| edited file | pairs |
|---|---|
| (nothing) | 45 |
| fastapi/encoders.py | 2 |

### Q2b the 40 tasks no arm resolved

| arm | pairs | first edit s, median [q1, q3] | never edited source | timeout | empty patch |
|---|---|---|---|---|---|
| pi0 | 40 | n=12 101 [61, 159] | 28/40 (70%) | 38/40 (95%) | 27/40 (68%) |
| floor-v0 | 40 | n=13 120 [65, 133] | 27/40 (68%) | 36/40 (90%) | 27/40 (68%) |
| m02-nothink | 40 | n=16 77 [35, 129] | 24/40 (60%) | 10/40 (25%) | 21/40 (52%) |
| floor-v2 | 40 | n=14 110 [70, 184] | 26/40 (65%) | 36/40 (90%) | 25/40 (62%) |
| floor-v3 | 40 | n=15 88 [50, 198] | 25/40 (62%) | 32/40 (80%) | 25/40 (62%) |
| pooled | 200 | n=70 95 [58, 144] | 130/200 (65%) | 152/200 (76%) | 125/200 (62%) |

### Q3 time budget

| arm | first edit s, resolved | first edit s, failed | s after first edit, resolved | s after first edit, failed |
|---|---|---|---|---|
| pi0 | n=16 74 [60, 94] | n=14 101 [70, 171] | n=16 44 [26, 72] | n=14 53 [0, 98] |
| floor-v0 | n=19 92 [46, 143] | n=17 120 [67, 143] | n=19 35 [16, 53] | n=17 34 [16, 78] |
| m02-nothink | n=14 47 [22, 88] | n=20 85 [35, 136] | n=14 11 [4, 36] | n=20 16 [5, 36] |
| floor-v2 | n=21 75 [50, 143] | n=17 104 [70, 179] | n=21 47 [12, 77] | n=17 42 [11, 84] |
| floor-v3 | n=19 73 [53, 135] | n=18 101 [69, 202] | n=19 69 [46, 106] | n=18 78 [25, 129] |
| pooled | n=89 75 [48, 125] | n=86 101 [65, 150] | n=89 41 [18, 71] | n=86 37 [8, 88] |

| arm | resolved pairs that hit the timeout | timeout after a site-file edit (class c) | timeout among failed pairs with a source edit | timeout among failed pairs with no source edit |
|---|---|---|---|---|
| pi0 | 0/16 (0%) | 1/1 (100%) | 12/14 (86%) | 41/41 (100%) |
| floor-v0 | 0/19 (0%) | 3/3 (100%) | 14/17 (82%) | 34/35 (97%) |
| m02-nothink | 0/15 (0%) | 1/4 (25%) | 2/20 (10%) | 15/36 (42%) |
| floor-v2 | 0/21 (0%) | 1/3 (33%) | 12/17 (71%) | 32/33 (97%) |
| floor-v3 | 0/19 (0%) | 2/3 (67%) | 10/18 (56%) | 33/34 (97%) |
| pooled | 0/90 (0%) | 8/14 (57%) | 50/86 (58%) | 155/179 (87%) |

### Q4 verification after the last source edit, and explicit submit

| arm | group | n | ran tests after last edit | ran repro (python) after last edit | either | submit_patch called |
|---|---|---|---|---|---|---|
| pi0 | resolved | 16 | 6/16 (38%) | 11/16 (69%) | 14/16 (88%) | 12/16 (75%) |
| pi0 | failed, edited | 14 | 1/14 (7%) | 7/14 (50%) | 7/14 (50%) | 2/14 (14%) |
| floor-v0 | resolved | 19 | 6/19 (32%) | 15/19 (79%) | 19/19 (100%) | 11/19 (58%) |
| floor-v0 | failed, edited | 17 | 2/17 (12%) | 10/17 (59%) | 11/17 (65%) | 4/17 (24%) |
| m02-nothink | resolved | 15 | 4/15 (27%) | 10/15 (67%) | 12/15 (80%) | 14/15 (93%) |
| m02-nothink | failed, edited | 20 | 1/20 (5%) | 11/20 (55%) | 12/20 (60%) | 18/20 (90%) |
| floor-v2 | resolved | 21 | 6/21 (29%) | 15/21 (71%) | 18/21 (86%) | 15/21 (71%) |
| floor-v2 | failed, edited | 17 | 3/17 (18%) | 5/17 (29%) | 7/17 (41%) | 5/17 (29%) |
| floor-v3 | resolved | 19 | 8/19 (42%) | 14/19 (74%) | 17/19 (89%) | 14/19 (74%) |
| floor-v3 | failed, edited | 18 | 2/18 (11%) | 11/18 (61%) | 11/18 (61%) | 8/18 (44%) |
| pooled | resolved | 90 | 30/90 (33%) | 65/90 (72%) | 80/90 (89%) | 66/90 (73%) |
| pooled | failed, edited | 86 | 9/86 (10%) | 44/86 (51%) | 48/86 (56%) | 37/86 (43%) |

| arm | submitted, all pairs | submitted among timeouts | resolve rate if submitted | resolve rate if not submitted |
|---|---|---|---|---|
| pi0 | 14/71 (20%) | 0/53 (0%) | 12/14 (86%) | 4/57 (7%) |
| floor-v0 | 15/71 (21%) | 1/48 (2%) | 11/15 (73%) | 8/56 (14%) |
| m02-nothink | 54/71 (76%) | 1/17 (6%) | 14/54 (26%) | 1/17 (6%) |
| floor-v2 | 21/71 (30%) | 0/44 (0%) | 15/21 (71%) | 6/50 (12%) |
| floor-v3 | 22/71 (31%) | 0/43 (0%) | 14/22 (64%) | 5/49 (10%) |
| pooled | 126/355 (35%) | 2/205 (1%) | 66/126 (52%) | 24/229 (10%) |

### Q5 wasted calls (shares of all tool calls)

| arm | calls | read_file calls on a file read 5+ times | pairs with such a file | tool-level failures | run_command non-zero exit | repeated identical call | edit/write calls with malformed arguments | edit_file old_string not found | write_file outside workspace (/tmp) |
|---|---|---|---|---|---|---|---|---|---|
| pi0 | 1321 | 269/1321 (20%) | 29 | 78/1321 (6%) | 106/1321 (8%) | 87/1321 (7%) | 17/134 (13%) | 9/134 (7%) | 44/134 (33%) |
| floor-v0 | 1277 | 256/1277 (20%) | 28 | 70/1277 (5%) | 109/1277 (9%) | 69/1277 (5%) | 9/129 (7%) | 6/129 (5%) | 47/129 (36%) |
| m02-nothink | 2610 | 454/2610 (17%) | 31 | 295/2610 (11%) | 420/2610 (16%) | 995/2610 (38%) | 228/383 (60%) | 17/383 (4%) | 27/383 (7%) |
| floor-v2 | 1406 | 269/1406 (19%) | 30 | 53/1406 (4%) | 115/1406 (8%) | 90/1406 (6%) | 35/115 (30%) | 3/115 (3%) | 1/115 (1%) |
| floor-v3 | 1575 | 323/1575 (21%) | 30 | 52/1575 (3%) | 132/1575 (8%) | 75/1575 (5%) | 16/115 (14%) | 14/115 (12%) | 1/115 (1%) |
| pooled | 8189 | 1571/8189 (19%) | 148 | 548/8189 (7%) | 882/8189 (11%) | 1316/8189 (16%) | 305/876 (35%) | 49/876 (6%) | 120/876 (14%) |

Pairs with at least one malformed edit/write call: 31/355 (9%); of those resolved 7/31 (23%); failed pairs among them with no successful source edit 11


### Extra measurements that the questions did not ask for but that explain the tables

Class (b) split (46 pairs). Share of file-touching calls after first sight that name the site file: >= 50% in 21 pairs ("stayed on the
file", 30 of 46 were still touching it in their last 5 calls), < 50% in 25 pairs ("drifted": read it, then went back to other files).
Only 7 of the 46 attempted a source edit at all: 2 edited a non-site file (two pairs),
5 tried the site file and failed at the tool layer (3 m02-nothink pairs with malformed arguments on every try, 2 with old_string not
found); the other 39 never issued a source edit (their failed write_file calls were repro scripts aimed at /tmp). After first sight the 46 pairs made 443 run_command (279 grep, 81 cat/sed/head,
50 python, 9 pytest) and 406 read_file calls.

Wall clock. 95 to 99% of every arm's wall time is model generation between calls, 1 to 5% is tool execution. Thinking-on arms: median
3.5 s between calls but the steps over 20 s (about 11% of steps, median 834 completion tokens) hold 43% (pi0) and 52% (floor-v3) of
generation time [corrected 2026-10-06 to the values analysis/release/check.py reproduces from the released derivative; the first
figures, 3.3 s, 10%, 800 and 51%, came from an ad-hoc script that was not saved]. Thinking-off (m02-nothink): 1.5 s median, steps over 20 s hold 9%. Among failed timeouts of the four thinking-on arms
(n=188), 45 contain a single generation of 60 s or more and 53 end with 30 s or more of silence (a generation in flight when the clock ran
out); resolved pairs (n=75) have 8 such long generations.

Argument mangling. 305 of 876 edit_file/write_file calls (35%) arrived with a mandatory parameter missing (the arguments dict carries keys
such as `<|"|>,new_string` or code fragments: the tool-call parser split the string at a quote). 228 of the 305 are m02-nothink. Likewise
read_file keys `start_line"`/`end_line"`: 194 of 666 m02-nothink read_file calls (13 pairs), so the line range was ignored and the same
page came back, which feeds the repeat loops. m02-nothink: 38 pairs with 10+ identical repeated calls (911 calls), and 18 of its 20
non-timeout empty patches stopped at or near the 50-call budget (41 to 58 calls).




## Follow-up (trace-fail-01b): the malformed edit calls

Measurement (edit_parse.py, output in edit_parse.out).
- Missing argument in 305 malformed calls: old_string 264, old_string+new_string 20, new_string 12, write_file filepath 8, filepath+new_string 1.
- Mechanism: the model always emits edit_file arguments in the order filepath, new_string, old_string (403 of 404 well-formed calls).
  In 296 of the 305 calls the value of the argument before the last one ends with a closer followed by `,old_string:` (or `,filepath:`),
  so the parser kept reading past the intended end and swallowed the next argument name. The remainder was split at every `:` and `,`
  into junk keys. The closer is a backtick in 277 calls, an escaped quote in 13, a double quote in 3 and a triple quote in 3. No swallowed
  name was found in 9 calls.

- The 305 calls are mostly identical retries. Counting distinct calls per (arm, task, arguments), 55 of 452 edit_file calls are malformed (12%).
- Malformed share of distinct calls, by content feature (with / without): escaped quote \" 30% / 6%; backtick 33% / 10%; triple quote
  20% / 11%; plain double quote 15% / 11%; 3+ lines 14% / 3%.
- run_command: 0 of 4,212 calls are corrupted. Of these, 3,671 contain a double quote and 500 are 3+ lines. command is the last argument in 4,211 of them.
- Thinking. Distinct malformed edit_file calls per arm: m02-nothink (off) 31/114 (27%); pi0 3/72, floor-v0 5/76, floor-v2 10/88,
  floor-v3 6/102 (on, 7% pooled). First edit or write call of each pair: off 8/47 vs on 10/185. Thinking off also retries the same broken
  call (228 raw vs 31 distinct).
- Not a loss: 119 of 355 successful edit_file calls had literal \n or \" in new_string. The tool unescaped them, and the diffs are clean.

Inference. The failure is a wrong closing delimiter on a long, multi-line string argument that is not the last argument. A single string
argument in last position is the only shape with zero corruption in these traces. Recommended edit path: one tool, one string argument,
payload in last position, no quoting inside, for example a search/replace block (path line, SEARCH lines, divider, REPLACE lines). The
harness can also repair at parse time: a backtick or quote directly before `,old_string:` / `,new_string:` / `,filepath:` closes the
value. That would recover up to 296 of the 305 calls (an upper bound, not tested).
