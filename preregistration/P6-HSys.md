# Pre-registration P6: H-Sys, AXI-mini against the single loop at equal budget

Registered by the commit that adds this file (its timestamp is the registration); the file's SHA-256 is published on
Kaggle the same day. Written 2026-10-06, before any AXI-mini candidate has run on any task set (development, AXI-Fresh
or the holdout). The registered board probe of axi-mini-a on 2026-10-07 (probe-mini-a-01) is a counted public look and is
reported apart. Analyses not listed here are exploratory and are reported as such, next to the predictions, including
results that contradict the thesis (F19).

## Objects
- Treatment, fixed in advance: axi-mini-a v0.3 (axi-mini/DESIGN.md; tree SHA-256 249ba5674230..., reviewed by a verifier
  at commit 96a8fa8). It was ranked first by design before any AXI-mini result existed, so no selection among variants
  precedes the test.
- Control: the single loop floor-v2 (tree SHA-256 b59393a6bc2f..., ledger row r0009).
- Both arms: model gemma-4-31b-it-qat-w4a16-ct, 3.5 minutes and 50 tool calls per task, 120 s per command, the
  harness and image of the ledger's instrument, thinking settings as each candidate declares them.
- Task set: AXI-Fresh v2 (Kaggle dataset ghaisank/axi-fresh-v2, 62 tasks from public repositories with permissive
  licences, fixes merged in 2026), restricted to the tasks its gold check (fresh-gold-03, with planted must-fail cases)
  finds sound. No task of this set was used to design either arm.
- Run: one replicate per arm per task, arms interleaved task by task, one agent session at a time (concurrency 1),
  subprocess sandbox, one kernel (fresh-01, quota week from 2026-10-10).

## Prediction and test
- **H-Sys:** the treatment resolves more tasks than the control.
- Test: the ledger's gate (`ledger.py compare`), the exact one-sided paired sign-flip test on resolved tasks (the exact
  McNemar test with one replicate), at the ledger's constant alpha 0.10.
- Supported if p <= 0.10. Otherwise H-Sys is reported as not supported at this sample, with the minimum detectable
  lift below.
- The estimate reported with it: the difference in resolved tasks and in rate, with the ledger's interval.

## Secondary (reported, not part of the claim)
- Strata: the 32 tasks of AXI-Fresh v1 and the 30 of batch 3, apart.
- Per-role time, timeouts, edit errors and submissions from the traces (the mechanism behind any difference).
- E1 rung, condition (ii), exploratory and only if the week's hours allow without starving the run above. The same two
  arms at gemma-4-12b-it-qat-w4a16-ct (served under the same alias) on the 32 v1 tasks. Reported as the direction and
  size of the lift at a second model size (detectable lift 0.24 at 32 tasks).
- Board probes of axi-mini-a, -b and -c (one counted public look each). Their readings are registered in
  memory/EXPERIMENTS.md.

## What would change the main track
If H-Sys is supported, AXI-mini becomes the main-track line, and the next week compares axi-mini-b and -c with -a on the
same set. If it is not, the single loop stays the baseline, and the treatment's traces are diagnosed by stage (K11)
before any new variant. Neither outcome touches the holdout, which stays reserved for the finals decision.

## Power (planning, not a claim)
`ledger.py mde` (one replicate, base rate 0.2, alpha 0.10, 80% power; a planning aid) gives these minimum detectable
lifts:

| tasks | lift |
|---|---|
| 62 | 0.16 |
| 32 | 0.24 |
| 71 | 0.14 |
| 133 | 0.10 |

A lift smaller than 0.16 is likely to go undetected here.

## Amendments (dated, appended below; each before the run it governs)

### A1 (2026-10-06 12:04 UTC, before any AXI-mini run; D-E38)
Both arms move to the 4.0-minute budget, the largest a submission can use.
- Why: the same day, floor-v3 (floor-v2 with a 4.0-minute budget, nothing else changed) scored 0.13 on the public board
  against floor-v0's 0.06, and its scoring took about 11.0 h for about 120 tasks, which puts the scorer's overhead near
  1.8 to 1.9 min per task. The test should use the budget a submission would use. No AXI-mini result exists on any task
  set.
- Control: floor-v3 (tree SHA-256 0065a8db0acd..., ledger row r0010).
- Treatment: axi-mini-a4, which is axi-mini-a v0.3 with the 4.0-minute budget and its prompts' time thresholds rescaled
  from 210 s to 240 s, shares unchanged (tree SHA-256 79bb7ebf2b75..., reviewed 2026-10-06).
- Unchanged: the task set (AXI-Fresh v2, all 62 tasks sound, r0013), the test, alpha 0.10, the secondary analyses and
  the detectable lift (0.16 at 62 tasks). The E1 rung uses the same two arms at gemma-4-12b-it-qat-w4a16-ct.

### A2 (2026-10-06 12:44 UTC, before any AXI-mini run; corrects A1's reasons, no change to the test)
A1's two stated reasons are corrected; the arms, task set, test and alpha stay as amended by A1.
- "The largest budget a submission can use" is withdrawn. The competition's 12-hour limit excludes patch validation,
  so floor-v3's ~11.0 h from submission to completion overstates the counted time; by the rule text, probe-setup-01's
  bound of ~0.9 min of setup per task and floor-v3's development agent time, the counted time is about 9 to 10 h.
- That more time helps on the hidden repositories is a hypothesis, not a finding. The board comparison changes budget
  and prompts together and is about one standard error, and on the development tasks none of floor-v3's 19 resolutions
  made its last source edit after 3.5 minutes.
- The remaining reason for the 4.0-minute arms: the control is the configuration with the best board score so far,
  compared at equal budget.

### A3 (2026-10-11 07:38 UTC, after the fresh-01 run failed and before any rerun)
fresh-01 (kernel axi-fresh-01 v2, swegemma 0.2.11 with the import shim, 4 L4, 00:04 to 07:24 UTC 10-11) is not the
registered measurement: the vLLM server stopped answering during task 10 of 62 (mid-session, kernel log 4452 s) and
refused connections from task 32 (15360 s); each arm has 9 live sessions (tasks 1 to 9 in the registered order), 22
timeouts with zero tool calls and 31 model-server errors (ledger rows r0015 floor-v3 and r0016 axi-mini-a4, purpose
explore, tag server-failure). It is reported as a failed run, not as a result of either arm.
- The test reruns as fresh-02 in the quota week from 2026-10-17 (the first L4 job of that week): same arms, task set,
  test, alpha and task order. Default: all 62 tasks in one kernel, both arms interleaved as registered. Fallback, only
  if that week's hours do not allow it and named now, before fresh-02: the 53 tasks not reached (tasks 10 to 62),
  combined with fresh-01's 9 live sessions under the same protocol; the choice is written in EXPERIMENTS before the push.
- Before fresh-02 the rollout kernel gets a server watchdog (an instrument change: failing check first, verifier review,
  DECISIONS entry): a session that ends with zero tool calls and a timeout triggers a liveness probe of the server; an
  unresponsive server ends the run with the results so far, or is restarted once; the server's own log is written into
  the output. fresh-01 spent about 6 wall hours (about 12 quota hours) after the hang.
- The 9 live sessions (5 resolved in each arm, discordant 2 and 2) are reported next to the predictions as the failed
  run's partial record; they are not the test and no verdict is read from them.

## A4 (2026-11-04T13:3xZ, written before any floor-arm row exists): where the floor arm runs, and how it is paired

- The clean floor arm (floor-v3 on all 62 AXI-Fresh v2 tasks, registered 2026-11-02 20:5x UTC in EXPERIMENTS as package w11 slots k and l) did not start as scheduled [three phrases saying where the arm was scheduled and where it runs are left out of this public copy (2026-11-10); the registered bytes of this amendment, sha256 fa76f5ef30b872af..., are kept by the author]. It runs instead on ONE NVIDIA A100-SXM4-40GB (tensor parallel 1), driven by cloud/r17-colab-rollout, as one 62-task arm in the order half B (analysis/strata/fresh-b-ids.txt) then half A, run id p6-colab-01, under rollout.py sha256 b5c394bfb64bbba65cb812c75820a25f49e5d09b51e9ce728a697ab62869dcfc (the current kernel program; r0045 ran under 08441e88...), the same wheelhouse (vllm 0.19.1, swegemma 0.2.11, google-adk 1.36.1, litellm 1.82.4 pinned to r0045's record), the same candidate bundle, task set, 4.0-minute cap and sampling.
- The system arm is r0045 (fresh-edit-01, 46 of 62, Kaggle, four L4s, 2026-10-2x week). The two arms are therefore NOT interleaved in one kernel as A1 registered; they are paired by task id across runs and across hardware. Unchanged: the test (ledger.py compare, one-sided paired sign-flip), alpha 0.10, the task set, the secondary analyses.
- The gate row is produced by `ledger.py compare --a <system> --b <floor> --split fresh --allow-diff gpu_count --allow-diff gpu_model --allow-diff rollout_sha --allow-diff python --allow-diff docker_image` (the flag added 2026-11-04 with a failing test and a verifier review; the row records every difference as instrument_diff; the harness dict, sandbox, concurrency, model and hint tier must still match). The paper states the cross-hardware, cross-run pairing next to the result (K5), with the decode speed measured in that run's log against the 34.2 to 34.7 tokens per second of the L4 runs.
- Prediction unchanged from the 2026-11-02 registration: the floor resolves 16 to 26 of 62; the registered test is significant if the floor stays under 36; the claim is dead at 40 or more. A partial arm (a session cut) is reported on the tasks it reached, half B first, with --intersection.
- Digest note: the ledger's `rollout_sha` is the digest of the kernel template kernels/rollout/rollout.py at build time (d84ffe36616dc27248506cb0711dbab7da526354671246d939b77a60786b5a54); the digest above is the built kernel file with the embedded runspec. Both identify the same program version.
