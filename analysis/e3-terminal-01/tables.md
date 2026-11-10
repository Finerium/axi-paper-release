# e3-terminal-01: in-task checks by session exit (exploratory, post hoc)

Patches 182; timed-out sessions 55 (all wrong: {'pass': 0, 'fail': 55}); terminal 127.

| check | stratum | correct | wrong | alpha | beta | LR [90%] |
|---|---|---|---|---|---|---|
| R-self | all | 89 | 93 | 0.73 | 0.419 | 1.74 [1.41, 2.22] |
| R-self | terminal | 89 | 38 | 0.73 | 1.0 | 0.73 [0.65, 0.81] |
| R-self | timeout | 0 | 55 | None | None | undefined |
| R-repro | all | 62 | 45 | 0.952 | 0.844 | 1.13 [1.01, 1.28] |
| R-repro | terminal | 62 | 25 | 0.952 | 0.96 | 0.99 [0.92, 1.09] |
| R-repro | timeout | 0 | 20 | None | None | undefined |
| R-near | all | 61 | 71 | 1.0 | 0.93 | 1.08 [1.03, 1.15] |
| R-near | terminal | 61 | 30 | 1.0 | 0.967 | 1.03 [1.0, 1.11] |
| R-near | timeout | 0 | 41 | None | None | undefined |
| R-fresh | all | 89 | 93 | 0.955 | 0.624 | 1.53 [1.35, 1.78] |
| R-fresh | terminal | 89 | 38 | 0.955 | 0.737 | 1.3 [1.12, 1.56] |
| R-fresh | timeout | 0 | 55 | None | None | undefined |
| self+fresh | all | 89 | 93 | 0.708 | 0.312 | 2.27 [1.76, 3.05] |
| self+fresh | terminal | 89 | 38 | 0.708 | 0.737 | 0.96 [0.8, 1.18] |
| self+fresh | timeout | 0 | 55 | None | None | undefined |
