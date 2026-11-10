# e3-public-01: self-claim and own reproduction on public trajectories (exploratory)

Question: on our model (Gemma 4 31B) two in-task checks carry little information about hidden-test correctness: the
agent's self-claim (it submitted, declaring the fix done) and its own reproduction test (a script it wrote that passed
after its last edit). Do they carry as little for other agents and models? Each check has a sensitivity alpha (share of
correct patches it accepts), a false acceptance beta (share of wrong patches it accepts) and LR = alpha/beta.

Exploratory pilot, not preregistered; nothing here is a ledger number. Checked and run on 2026-10-06 (UTC).

## Run (from the repo root)

```
.venv-harness/bin/python -I analysis/e3-public/e3_public.py fetch openhands   # ~45 MB of HTTP range reads
.venv-harness/bin/python -I analysis/e3-public/e3_public.py fetch swe_agent   # ~165 MB
/usr/bin/python3 -I analysis/e3-public/e3_public.py selftest
/usr/bin/python3 -I analysis/e3-public/e3_public.py analyze                   # writes results.json
```

`fetch` reads only the parquet footer, the small columns of every row and the trajectory column of the sampled row
groups, and writes `scratch/e3-public/<source>/{meta_all.jsonl,frame.json,sample.jsonl}` (git-ignored; sample sha256
in results.json). `analyze` uses the standard library only. results.json holds per-trajectory verdicts and counts, no
trajectory text.

## Sources (checked 2026-10-06 UTC)

| source | licence and where it is stated | (b) hidden-test outcomes, both classes | (c) actions and outputs | usable |
|---|---|---|---|---|
| SWE-bench/experiments, github.com/SWE-bench/experiments (head 40f164d5, 2026-09-03) | none: no LICENSE file in the root listing, GitHub API `license: null`, nothing in README.md or checklist.md. Since mid-2026 the repo holds entries only; artifacts live in `s3://swe-bench-submissions/` (no licence) or a submitter repository. Of the 23 evaluation/verified entries dated 2025-12 or later, 22 point to S3 and 1 to github.com/SWE-bench/20260901_mini-v2.4.2_gemini-3-5-flash, which has no licence either | yes (results/) | yes | no: licence absent |
| nebius/SWE-rebench-openhands-trajectories, huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories (rev 35455389, 2025-12-27) | CC-BY-4.0: card metadata `license: cc-by-4.0` and a LICENSE file (CC BY 4.0 legal code) at the repository root | yes: `resolved`, 32,161 of 67,074 | yes: OpenHands v0.54.0 tool calls with outputs and exit codes, `exit_status` | yes: **primary** |
| nebius/SWE-agent-trajectories, huggingface.co/datasets/nebius/SWE-agent-trajectories (rev 68195a14, 2024-12-23) | CC-BY-4.0: card metadata and the card's "License" section; the card adds that use of the model outputs must comply with the Llama 3.1 License (we only count; nothing is redistributed or trained on) | yes: `target`, 13,389 of 80,036 | yes: SWE-agent actions and outputs, `exit_status`; no exit codes | yes: second source |
| SWE-Gym/OpenHands-Sampled-Trajectories (rev baf3a4e4, 2024-12-23) | none on the card; github.com/SWE-Gym/SWE-Gym is Apache-2.0 but says nothing about the HF data | yes: `resolved` (491 successful of 6,055 per the comparison table on the nebius OpenHands card) | yes | no: licence absent |
| SWE-Gym/OpenHands-Verifier-Trajectories, SWE-Gym/MoatlessTools-Sampled-Trajectories | none (the MoatlessTools repo has no README at all) | Verifier: `resolved` in the card schema; MoatlessTools: unknown | messages only | no: licence absent |
| SWE-Gym/OpenHands-SFT-Trajectories (rev 4aaa5a4a, 2025-05-10) | MIT (card metadata) | no: only the split `train.success.oss` (491 successful runs), no labels | messages | no: no unresolved runs |
| SWE-bench/SWE-smith-trajectories (rev 08e109b4, 2025-07-19) | MIT (card metadata) | yes: `resolved`; shard tool-00004 holds 1,255 resolved of 3,012 (Claude 3.5/3.7 Sonnet, GPT-4o) | yes, but no exit status field and no exit codes; all 12 trajectories inspected end with `submit`, so the release looks curated and the self-claim check may be degenerate. Tasks are synthetic (injected bugs) | yes (not piloted) |
| ByteDance-Seed/Multi-SWE-bench_trajs (rev 9180bb0c, 2025-12-19), found by search | CC0-1.0 (card metadata; not in the MIT/Apache/BSD/CC-BY list but more permissive) | no: the python/ zip checked (OpenHands + GPT-4o) holds one final LLM completion log per instance and no results or reports | partly | no: no outcomes in the release |
| tarsur385/swebench-verified-trajectories, found by search | MIT on the card, but the files are SWE-bench mini-swe-agent runs re-downloaded from Docent by a third party; the uploader cannot license data whose source carries no licence | yes | yes | no: licence not credible |
| nvidia/SWE-Zero- and SWE-Hero-openhands-trajectories, found by search | CC-BY-4.0 | no `resolved` field (SFT data) | yes | no: no outcomes |
| AlienKevin/SWE-ZERO-12M-trajectories, found by search | Apache-2.0 | no: execution-free, "no trajectory has been checked against ground-truth tests" (card) | yes | no: no outcomes |

Raw cards, API answers and licence files are in scratch/e3-public/{cards,hfapi,swebench_exp,swegym,openhands_files}.

## Sample

Per source: parquet row groups are taken in a seeded random order (seed 20261006) until each class has at least 150
distinct instances; that is the frame. In the frame, 150 resolved and 150 unresolved instances are drawn at random and
one random trajectory of the class is taken from each. An instance can appear once per class. Intervals: 90%
percentile bootstrap, 10,000 resamples of instances (clusters), alpha, beta and LR recomputed in each resample.

- openhands: frame = row group 16 of 17 (1,538 of 67,074 rows; the publisher's rows look shuffled: one row group spans
  about 3,000 instances). 300 trajectories, 300 instances.
- swe_agent: frame = 14 of 84 row groups in 8 of the 12 files (13,670 of 80,036 rows). Rows are grouped by instance
  (about 50 instances per 1,000-row group, about 10 of them with a resolved run), hence several row groups. 300
  trajectories over 262 instances (38 instances appear in both classes); models 288 swe-agent-llama-70b, 9 -8b, 3 -405b.

## Rules as applied

**Self-claim.** Accept when the trajectory ends with the agent's own terminating action: OpenHands `finish`; SWE-agent
`submit` (exit status `submitted` or `submitted_no_patch`). Reject otherwise: OpenHands stops at 100 iterations, stuck-loop
detection, LLM timeouts and runtime errors; SWE-agent automatic submission on context, cost or format limits
(`submitted (exit_context)` etc.), `exit_context`, `early_exit`. The trajectory-derived verdict agrees with `exit_status` in
every sampled row (`check_self_claim_vs_exit_status`); the same check is also computed from `exit_status` over every row
of both datasets (`self_claim_full_dataset_exit_status`, by model for SWE-agent).

**Own reproduction.**
- Reproduction test: a `.py` file the agent created with the scaffold's create command (OpenHands `str_replace_editor
  create`, SWE-agent `create`) and later executed: it is python's script argument, or a target of `pytest`,
  `python -m pytest` or `python -m unittest`, in one shell segment (commands are split at `&&`, `||`, `;`, `|` and
  newlines). Matching is by file name.
- Source edit: a successful write to any other file under the repository directory: OpenHands `create`, `str_replace`,
  `insert`, `undo_edit`; SWE-agent `create` and `edit` (which rewrites the open file, read from the state footer of the
  previous output); in the shell, `sed -i` (unless it names a reproduction test) and `git checkout|restore|stash|reset|
  apply|am` or `patch -p`. Refused writes (OpenHands `ERROR:`, SWE-agent linter refusals) change nothing and do not count.
- Order is (tool call, shell segment), so in `git stash && python repro.py && git stash pop` the run sits between two edits.
- Verdict: take the last reproduction run after the last source edit. Accept when it succeeded, reject when it failed,
  undefined (counted, excluded) when there is none. A trajectory with no source edit at all is undefined too: there is
  no fix to check (the literal reading, where every run counts as "after", is the `no_edit_counts` variant).
- Success, openhands: the exit code OpenHands appends (`[The command completed with exit code N.]`) is 0. A run with no
  exit code (still running after the no-output timeout, or interrupted) did not succeed.
- Success, swe_agent: the scaffold records no exit codes, so the run succeeded when its output (without the state
  footer) shows no traceback or failure: no `Traceback (most recent call last)`, no line starting with `...Error:` or
  `...Exception:`, no `FAILED` or `FAIL`, no nonzero `N failed` or `N error(s)`, no ❌.

Variants (results.json, `variant_*`): `own_repro_strict` requires exit code 0 and no failure marker (OpenHands; equals
the primary rule for SWE-agent); `own_repro_docs_not_edits` does not count writes to `.md`, `.rst` or `.txt` files as
source edits (OpenHands agents often write a summary note after their last run, which makes the primary verdict
undefined); `own_repro_no_edit_counts` judges a trajectory without source edits by its last run.

## Deviations from our frozen rules

1. Other agents, models and tasks: OpenHands v0.54.0 + Qwen3-Coder-480B-A35B on SWE-rebench; SWE-agent + Llama-3.1-based
   fine-tunes on SWE-bench-extra and the SWE-bench dev split. Hidden-test outcomes are the publishers' evaluations
   (`resolved`, `target`); we did not re-run them.
2. Sample frame is a seeded subset of row groups, not the whole dataset (download cost). The self-claim check is also
   reported on all rows from `exit_status`.
3. Shell writes other than `sed -i`, git and `patch` (`cat >`, `echo >>`, `cp`, `mv`, `rm`, writes from python) are not
   source edits, and `.py` files written through the shell are not reproduction tests. In an exploration of 1,000
   OpenHands trajectories: redirects into `.py` files in 2, python file writes in 8, `cp`/`mv` in 11; `rm` in 592,
   almost always deleting the agent's own scratch scripts.
4. Exit code of a compound command is the shell's: `python repro.py | head` reports `head` (42 of 5,384 reproduction
   runs in an exploration of 600 OpenHands trajectories had a pipe).
5. OpenHands: a run without an exit code is a failure (24 of the same 5,384 runs).
6. SWE-agent has no exit codes: the output rule above replaces them (as the frozen rule allows).
7. Literal "any other file in the repository": a summary `.md` the agent writes after its last run makes the verdict
   undefined; the `docs_not_edits` variant shows the effect.
8. Reproduction tests are matched by file name, so a created `test_x.py` and a repository file of the same name are not
   told apart.
9. No source edit means undefined (an interpretation of "after the last source edit"; the variant shows the other one).

## Results

All numbers come from results.json (this session's run). Accepted / defined, undefined in brackets; 90% bootstrap
intervals over instances.

| source (sample) | check | resolved | unresolved | alpha | beta | LR |
|---|---|---|---|---|---|---|
| OpenHands + Qwen3-Coder-480B (300 runs, 300 instances) | self-claim | 142/150 | 118/150 | 0.947 [0.914, 0.975] | 0.787 [0.730, 0.841] | **1.20** [1.12, 1.30] |
|  | own reproduction (exit code) | 141/144 (6) | 121/133 (17) | 0.979 [0.958, 0.994] | 0.910 [0.868, 0.949] | **1.08** [1.03, 1.13] |
|  | variant: exit 0 and no failure marker | 134/144 (6) | 111/133 (17) | 0.931 [0.894, 0.963] | 0.835 [0.781, 0.886] | 1.11 [1.04, 1.20] |
|  | variant: doc writes are not edits | 141/144 (6) | 123/135 (15) | 0.979 [0.958, 0.994] | 0.911 [0.869, 0.951] | 1.07 [1.03, 1.13] |
|  | variant: no source edit, every run counts | 141/144 (6) | 124/138 (12) | 0.979 [0.958, 0.994] | 0.899 [0.855, 0.940] | 1.09 [1.04, 1.15] |
| all 67,074 rows, 6,306 instances | self-claim from `exit_status` | 31,020/32,161 | 29,719/34,913 | 0.965 [0.962, 0.967] | 0.851 [0.844, 0.859] | 1.13 [1.12, 1.14] |
| SWE-agent + swe-agent-llama (300 runs, 262 instances) | self-claim | 138/150 | 85/150 | 0.920 [0.882, 0.955] | 0.567 [0.500, 0.633] | **1.62** [1.44, 1.85] |
|  | own reproduction (output rule) | 82/98 (52) | 37/69 (81) | 0.837 [0.774, 0.897] | 0.536 [0.438, 0.633] | **1.56** [1.31, 1.92] |
|  | variant: doc writes are not edits | 82/98 (52) | 36/67 (83) | 0.837 [0.774, 0.897] | 0.537 [0.434, 0.638] | 1.56 [1.30, 1.94] |
|  | variant: no source edit, every run counts | 84/100 (50) | 50/98 (52) | 0.840 [0.779, 0.900] | 0.510 [0.426, 0.594] | 1.65 [1.40, 1.99] |
| all 80,036 rows, 3,591 instances | self-claim from `exit_status` | 12,672/13,389 | 39,481/66,647 | 0.946 [0.940, 0.952] | 0.592 [0.583, 0.602] | 1.60 [1.57, 1.62] |
| by model: swe-agent-llama-70b (74,792 rows, 3,591 inst.) | same | 11,907/12,467 | 37,767/62,325 | 0.955 [0.950, 0.960] | 0.606 [0.597, 0.615] | 1.58 [1.55, 1.60] |
| by model: swe-agent-llama-8b (4,053 rows, 528 inst.) | same | 496/614 | 1,445/3,439 | 0.808 [0.759, 0.856] | 0.420 [0.395, 0.446] | 1.92 [1.77, 2.09] |
| by model: swe-agent-llama-405b (1,191 rows, 100 inst.) | same | 269/308 | 269/883 | 0.873 [0.827, 0.915] | 0.305 [0.263, 0.346] | 2.87 [2.51, 3.33] |

Why own reproduction is undefined (derived from `rows`): OpenHands 6 resolved and 12 unresolved runs edited after
their last script run, 5 unresolved never edited a source file. SWE-agent 43 resolved and 49 unresolved never ran a
script they created, 2 and 29 never edited a source file, 7 and 3 edited after their last run. Every OpenHands run in the
sample ran at least one own script (8.9 runs on average); 69% of SWE-agent runs did (3.4 on average).

## Notes

- Verdict: on both public sources the two checks are weak evidence of correctness. The primary LRs are 1.20
  (self-claim) and 1.08 (own reproduction) for OpenHands and 1.62 and 1.56 for SWE-agent. No upper 90% bound in either
  pilot sample reaches 2, variants included. The checks are weakest for the stronger agent (OpenHands +
  Qwen3-Coder-480B): it declares the task done on 79% of its wrong patches (85% over all 67,074 rows), and its own
  final script passes on 91% of them.
- The self-claim's information depends on how failures end. In SWE-agent many wrong runs stop on the context limit and
  are auto-submitted (that lowers beta to 0.57), while OpenHands' wrong runs mostly call `finish`. The check partly
  measures the scaffold's budget, not only the model. On all SWE-agent rows the LR also varies by model (1.58 for 70b,
  1.92 for 8b, 2.87 for 405b on 100 instances).
- Own reproduction is near-saturated for Qwen3-Coder (alpha 0.98, beta 0.91): it runs its own scripts 8.9 times per
  task on average, and the last run passes almost always. For the SWE-agent Llama fine-tunes, it is defined for only 167
  of 300 runs, so the selection is different from OpenHands'.
- Before the frame rule was fixed, an exploratory draw from OpenHands row group 0 gave self-claim LR 1.14 [1.08, 1.21]
  and own-reproduction LR 1.03 [0.99, 1.08]. Those runs used the same run and edit rules except the no-edit rule and the
  marker regex. The final script does not reproduce that draw.
- The OpenHands release also carries `pred_passes_gen_tests` (agent-generated tests passed by the agent's own final
  patch, per the card) and `gen_tests_correct` (31,389 rows non-null). They are a publisher-run version of the
  own-reproduction check over the whole dataset, not analysed here.
- SWE-smith-trajectories (MIT, Claude 3.5/3.7 Sonnet and GPT-4o) is usable for the own-reproduction check with the
  output rule. It looks curated to submitted runs, and its tasks are synthetic.
