# Jamal Fable — Backfill Campaign Report (2026-06-11)

## Pre-registered annotations (read FIRST — discovering these is not a finding)
- Deeper pullbacks mechanically have larger R-to-T1 (trend-high T1 definition).
- Flush entries are mechanically deeper than pullback entries.
- V-shaped pullbacks cannot trigger T1 (no micro-LH) — ARM-without-ENT counts measure the hole.
- Ambiguous bars (stop AND target touched) grade STOP-FIRST: results are conservative.
- R accounting v1: full position at T1 (rt1); NO trail/partial simulation — stated scope cut.
- Monthly windows are reported separately; pooled rows carry no significance claims.
- Pseudo-episodes are walked independently (no portfolio sequencing) — they answer
  "what would this class of skipped signal have done", not "what would the book have done".


Sources (4 provenance files, s0.4.5 only):
- BTCUSDT.P_240_v1_s0.4.5_c509208_B.jsonl
- ETHUSDT.P_240_v1_s0.4.5_c509208_B.jsonl
- NEARUSDT.P_240_v1_s0.4.5_c509208_B.jsonl
- SOLUSDT.P_240_v1_s0.4.5_c509208_B.jsonl


## Headline — real episodes (sequential per symbol-direction)

| symbol | trade | dir | n | closed | win% | avg R | med MFE | ambig | open |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT.P | 2A | L | 3 | 3 | 33 | 0.16 | 0.44 | 0 | 0 |
| BTCUSDT.P | 2A | S | 2 | 2 | 50 | 1.85 | 3.36 | 0 | 0 |
| BTCUSDT.P | T1 | L | 2 | 2 | 50 | 0.32 | 0.86 | 0 | 0 |
| BTCUSDT.P | T1 | S | 1 | 0 | — | — | 1.09 | 0 | 1 |
| ETHUSDT.P | 2A | S | 1 | 1 | 100 | 2.06 | 3.53 | 0 | 0 |
| ETHUSDT.P | T1 | L | 2 | 2 | 100 | 1.97 | 2.64 | 0 | 0 |
| ETHUSDT.P | T1 | S | 1 | 0 | — | — | 0.90 | 0 | 1 |
| NEARUSDT.P | 2A | L | 4 | 4 | 50 | 0.98 | 1.83 | 0 | 0 |
| NEARUSDT.P | 2B | L | 2 | 2 | 100 | 3.69 | 3.91 | 0 | 0 |
| NEARUSDT.P | 2B | S | 2 | 2 | 50 | 0.83 | 1.61 | 0 | 0 |
| NEARUSDT.P | T1 | L | 1 | 1 | 0 | -1.00 | 0.78 | 0 | 0 |
| SOLUSDT.P | 2A | L | 1 | 1 | 100 | 3.49 | 6.71 | 0 | 0 |
| SOLUSDT.P | 2A | S | 5 | 4 | 25 | -0.12 | 1.12 | 0 | 1 |
| SOLUSDT.P | 2B | L | 1 | 1 | 0 | -0.37 | 0.38 | 0 | 0 |
| SOLUSDT.P | T1 | S | 2 | 2 | 50 | 0.32 | 1.20 | 0 | 0 |


**ALL (pooled, no significance claim):** n=30 closed=27 win%=52 avgR=0.96 medMFE=1.42 open=3 | skip_overlap dropped: 12


## Monthly windows (not pooled for significance)

| month | n | closed | win% | avg R | med MFE |
|---|---|---|---|---|---|
| 2026-04 | 14 | 14 | 64 | 1.28 | 2.23 |
| 2026-05 | 13 | 13 | 38 | 0.63 | 0.69 |
| 2026-06 | 3 | 0 | — | — | 1.09 |


## Factor conditioning (real episodes)


### by `gvb`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <0.3 | 15 | 47 | 1.17 | 1.12 |
| 0.3-0.7 | 6 | 60 | 0.86 | 2.46 |
| >0.7 | 9 | 57 | 0.60 | 1.09 |


### by `wkp`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <50 | 4 | 75 | 2.08 | 3.03 |
| 50-85 | 12 | 45 | 1.02 | 1.34 |
| >85 | 5 | 40 | 0.46 | 1.12 |
| na | 9 | 57 | 0.60 | 1.09 |


### by `fp`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <25 | 6 | 80 | 1.91 | 2.34 |
| 25-75 | 16 | 43 | 0.49 | 1.01 |
| >75 | 8 | 50 | 1.21 | 1.38 |


### by `oi_d`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <0 (contracting) | 19 | 50 | 0.74 | 1.09 |
| >=0 (building) | 11 | 55 | 1.29 | 2.93 |


### by `d_pct`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <60 | 0 | — | — | — |
| 60-100 | 4 | 50 | 0.32 | 1.25 |
| >100 (wick-swept) | 5 | 67 | 0.98 | 1.09 |
| na | 21 | 50 | 1.09 | 1.98 |


### by `age`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <10 | 3 | 67 | 1.99 | 3.12 |
| 10-50 | 22 | 48 | 0.79 | 0.84 |
| >50 | 5 | 67 | 1.18 | 1.98 |


### by `rt1`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| 1.5-2 | 13 | 42 | 0.25 | 0.78 |
| 2-3 | 12 | 40 | 0.39 | 1.01 |
| >3 | 5 | 100 | 3.84 | 4.70 |


### by `q`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| PD.OD | 10 | 60 | 1.31 | 2.41 |
| PD.OU | 5 | 40 | 0.85 | 0.38 |
| PU.OD | 8 | 60 | 1.22 | 1.54 |
| PU.OU | 7 | 43 | 0.37 | 1.12 |


### by `t1co`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| 0 | 21 | 50 | 1.09 | 1.98 |
| na | 9 | 57 | 0.60 | 1.09 |


### by `reg1d`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| C | 19 | 53 | 0.90 | 1.75 |
| D | 4 | 100 | 4.49 | 1.54 |
| U | 7 | 43 | 0.62 | 0.78 |


## Gate questions (pseudo-episodes, walked independently)


### (a) rr gate — skipped-on-R signals, bucketed by their rt1

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <0.5 | 67 | 94 | -0.09 | 0.30 |
| 0.5-1.0 | 33 | 71 | 0.24 | 0.71 |
| 1.0-1.25 | 12 | 55 | 0.24 | 0.75 |
| 1.25-1.5 | 11 | 55 | 0.44 | 1.45 |


### (b) 1D gate — blocked sweeps, graded as if taken

n=9 closed=9 win%=33 avgR=-0.25 medMFE=0.30


### (c) thesis-exit counterfactuals (hold-to-stop instead)

| outcome if held | n |
|---|---|
| recovered | 2 |
| stopped | 2 |
