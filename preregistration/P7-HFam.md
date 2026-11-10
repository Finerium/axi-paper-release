# Pre-registration P7: H-Fam, memory-only localisation on familiar and fresh tasks

Registered by the commit that adds this file (its timestamp is the registration); the file's SHA-256 is published on
Kaggle (dataset ghaisank/axi-preregistration-hashes) the same day. Written in the night of 2026-10-06/07 (UTC), before
any familiarity probe has run: no answer of this probe has been seen by anyone.

## Question
W2 calls AXI-Fresh "unfamiliar code" and attributes part of the gap between the development tasks (19 of 71, r0005) and
the hidden board (0.06 and 0.13) to familiarity. This measures familiarity instead of assuming it: from the problem
statement alone, without the repository, how often does the model name a file that the reference fix changes?

## Objects
- Model and serving: gemma-4-31b-it-qat-w4a16-ct, served by the rollout kernel as in agent mode (vllm_server); fam mode
  of kernels/rollout/rollout.py at the commit that registers this file (reviewed by a verifier before it): one request
  per task, no tools, no system instruction, thinking off (thinking_budget 0), temperature 0.2, top_p 0.95, at most 512
  completion tokens; one retry when the visible answer has no FILE line.
- Prompt: FAM_PROMPT in that file, verbatim, with the task's repository (owner/name) and problem statement inserted.
- Tasks: the 71 development tasks of split v1 (their ids listed in the run's runspec; the mode refuses to run without
  the list, so no holdout task can be sent) and all 62 AXI-Fresh v2 tasks (dataset ghaisank/axi-fresh-v2, task file
  SHA-256 033e02900d981f7a...).
- Reference: the source files the task's reference fix changes (the kernel's changed_paths: .py files outside test
  directories; setup.py, conftest.py and noxfile.py excluded), deduplicated.
- Denominators: a task whose reference fix changes no such file (n_gold 0), a task whose row records an error
  (n_gold null: finish_reason "error", a failure outside the request) and a task without a row (a time stop) are
  excluded from its set; each kind is counted and reported. A failed request (finish_reason "exception" or "timeout"
  on both attempts) is a scored miss, not an exclusion.
- Parsing: the first three distinct paths on lines starting "FILE:" (also after a list marker -, *, +, >, 1. or 2),
  and inside emphasis or backticks), with a trailing :line[:col] and trailing punctuation removed, a leading
  /workspace/, ./ and / removed once each, and a leading repository slug (owner/name/) or a doubled package prefix
  (name/name/) removed; "<path>" and other placeholders are not paths. Known misses, rare and the same in both sets:
  text before "FILE:" on the line, or a space between emphasis marks and "FILE:".
- Scoring, in the kernel: hit@1 (the first named file is a reference file), hit@3 (any of the first three), base@1
  (the first named file's name equals a reference file's name; secondary) and name_in_issue (a reference file's name appears in the problem statement itself as a whole word, a cue
  unrelated to memory; it stays in the tree because it says at most that a file the issue already names is changed). results.jsonl holds these flags and counts
  only; the parsed paths and raw answers go to fam/test_outputs/, which `kaggle_ops.py output` moves into the vault,
  because joined with the flags they would show reference files.
- Run: kernel fam-01 in the quota week from 2026-10-10, after judge-01, concurrency 4. If the week cannot hold it
  without taking hours from fresh-01 or judge-01, it moves to the next week unchanged.

## Prediction and test
- **H-Fam:** hit@1 is higher on the development tasks than on AXI-Fresh.
- Test: the one-sided Fisher exact test on the 2x2 table (hit@1 yes or no, by set) at the campaign's alpha 0.10,
  computed by scripts/ledger.py from the committed run directory (an add-fam command, built with a failing check and a
  verifier review before fam-01 runs). Supported if p <= 0.10; otherwise not supported at this sample.
- Reported with it: each set's hit@1 rate with its Wilson 90% interval and the difference with Newcombe's 90% interval.

## What the result changes
- Supported: W2 states that AXI-Fresh is less familiar to the model by this measure, with the numbers, and W1 keeps the
  editing bottleneck scoped to familiar tasks with this as the reason.
- Not supported: W2's title and every sentence that calls AXI-Fresh unfamiliar code are revised to what was built
  (fresh fixes from small repositories), and W1's "unfamiliar repositories" wording is revised the same way.

## Secondary (reported, not part of the claim)
- hit@1 by set on the tasks whose problem statement does not name a reference file (name_in_issue false).
- hit@3 and base@1 by set; hit@1 for each AXI-Fresh repository, and for the five most widely installed ones (pygments,
  pyparsing, fsspec, traitlets, pyfakefs) against the other seventeen; retries, finish reasons, excluded tasks.
- A known cue in the design: the prompt names the repository, whose package directory is often its name, so a correct
  directory can come from the name alone. It applies to both sets alike; base@1 is reported to show its size.

## Power (planning, not a claim)
Simulated (seed 20261007, 3,000 draws per cell; one-sided Fisher at 0.10, 71 against 62 tasks): with a development
hit@1 between 0.4 and 0.6, a difference of 0.20 is detected about 80% of the time, 0.15 about 60%, 0.10 about 38%.
A difference smaller than about 0.15 is likely to go undetected.

## Amendments (dated, appended below; each before the run it governs)
