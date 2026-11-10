# Pre-registration (P5): the commit time is the registration; its SHA-256 goes public on Kaggle the same day

Amendments (2026-10-14): an amendment is registered by its commit and is public only when its SHA-256 row is in the Kaggle dataset; the two
are one step: append the row to kernels/.build/prereg-hashes/SHA256SUMS.txt and run `/usr/bin/python3 scripts/kaggle_ops.py dataset-push
--dir kernels/.build/prereg-hashes --slug axi-preregistration-hashes` in the same session (P6 A3 was published three days late; CONTROL 31).

## Public copy of P6-HSys.md (2026-11-10)

In this public copy three phrases of P6's amendment A4, which say where the floor arm had been scheduled and where it ran, are left out; the place is marked in the text. Nothing else differs from the registered file. The registration and amendments A1 to A3 are byte prefixes of the file: cut it before the lines `### A1`, `### A2`, `### A3` and `## A4` (without the blank line above each) and the SHA-256 of each prefix is the published one. The published hash of amendment A4 (fa76f5ef...) is that of the registered bytes, which the author keeps and can show to the competition hosts; the hash of this public copy is the last line of SHA256SUMS.txt.
