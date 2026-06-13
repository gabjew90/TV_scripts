# Jamal Fable â€” Backfill Campaign Report (2026-06-13)

## Pre-registered annotations (read FIRST â€” discovering these is not a finding)
- Deeper pullbacks mechanically have larger R-to-T1 (trend-high T1 definition).
- Flush entries are mechanically deeper than pullback entries.
- V-shaped pullbacks cannot trigger T1 (no micro-LH) â€” ARM-without-ENT counts measure the hole.
- Ambiguous bars (stop AND target touched) grade STOP-FIRST: results are conservative.
- R accounting v1: full position at T1 (rt1); NO trail/partial simulation â€” stated scope cut.
- Monthly windows are reported separately; pooled rows carry no significance claims.
- Pseudo-episodes are walked independently (no portfolio sequencing) â€” they answer
  "what would this class of skipped signal have done", not "what would the book have done".
- Liquidation totals correlate mechanically with sweep depth; lq is read WITHIN swd bands.
- rt1 is conditioned per trade type; the pooled rt1 table from the 2026-06 campaign mixed geometries.
- CAMPAIGN-2 HYPOTHESIS (pre-registered 2026-06-11, BEFORE any s0.5.0 data was seen):
  quiet, shallow sweeps revert; violent ones don't - CONDITIONAL ON CHOP (er>0.45 had
  ZERO events in campaign 1; the violence prior is untested in trends, not refuted).
- Multiple-comparisons honesty: ~15 conditioning tables at n~30 GUARANTEE impressive
  splits by chance (campaign 1's vz split was ~p0.1 unadjusted). Nothing promotes
  without surviving this campaign's pre-registered test.
- The 1D gate is OFF by user ruling (2026-06-11, AGAINST the n=9 campaign-1 evidence);
  the blocked-cohort table below is that ruling's standing scoreboard.
- The THIRD EXIT is REMOVED by user ruling (2026-06-12): trades run to stop or target.
  Campaigns 2-4 priced the rule net-negative (OS/2A strongly; 2B/T1 mildly positive,
  overruled). thesis_exit rows below this date are zero by construction.
- OS roll-class rt1 correlates with os by construction (target = the stretch anchor).


Sources (2 provenance files, glob `*_s0.7.2_*.jsonl`):
- BTCUSDT.P_60_v1_s0.7.2_c11295_B.jsonl
- HYPEUSDT.P_60_v1_s0.7.2_c11295_B.jsonl


## Headline â€” real episodes (sequential per symbol-direction)

| symbol | trade | dir | n | closed | win% | avg R | med MFE | ambig | open |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT.P | 2A | L | 12 | 12 | 33 | 0.01 | 1.20 | 0 | 0 |
| BTCUSDT.P | 2A | S | 11 | 11 | 18 | -0.32 | 0.53 | 0 | 0 |
| BTCUSDT.P | 2B | L | 4 | 4 | 75 | 1.62 | 2.64 | 0 | 0 |
| BTCUSDT.P | 2B | S | 17 | 17 | 29 | 0.21 | 1.40 | 0 | 0 |
| BTCUSDT.P | OSD | L | 11 | 11 | 27 | -0.23 | 0.93 | 0 | 0 |
| BTCUSDT.P | OSD | S | 6 | 6 | 17 | -0.39 | 0.50 | 0 | 0 |
| BTCUSDT.P | OSF | L | 45 | 44 | 23 | -0.16 | 1.11 | 1 | 1 |
| BTCUSDT.P | OSF | S | 41 | 41 | 27 | -0.07 | 0.87 | 1 | 0 |
| BTCUSDT.P | OSW | L | 4 | 4 | 0 | -1.00 | 0.59 | 0 | 0 |
| BTCUSDT.P | OSW | S | 6 | 6 | 50 | 0.61 | 1.88 | 0 | 0 |
| BTCUSDT.P | T1 | L | 2 | 2 | 50 | 0.40 | 1.34 | 0 | 0 |
| BTCUSDT.P | T1 | S | 4 | 4 | 25 | -0.34 | 1.31 | 0 | 0 |
| HYPEUSDT.P | 2A | L | 15 | 15 | 13 | -0.55 | 0.61 | 0 | 0 |
| HYPEUSDT.P | 2A | S | 11 | 11 | 27 | 0.09 | 1.36 | 0 | 0 |
| HYPEUSDT.P | 2B | L | 12 | 12 | 17 | -0.46 | 0.74 | 0 | 0 |
| HYPEUSDT.P | 2B | S | 12 | 12 | 25 | -0.32 | 0.73 | 0 | 0 |
| HYPEUSDT.P | OSD | L | 12 | 12 | 33 | -0.02 | 1.25 | 0 | 0 |
| HYPEUSDT.P | OSD | S | 16 | 16 | 6 | -0.81 | 0.59 | 0 | 0 |
| HYPEUSDT.P | OSF | L | 41 | 40 | 32 | -0.04 | 1.07 | 0 | 1 |
| HYPEUSDT.P | OSF | S | 31 | 31 | 32 | -0.12 | 0.92 | 0 | 0 |
| HYPEUSDT.P | OSW | L | 6 | 6 | 50 | 0.60 | 2.21 | 0 | 0 |
| HYPEUSDT.P | OSW | S | 1 | 1 | 0 | -1.00 | 0.73 | 0 | 0 |
| HYPEUSDT.P | T1 | S | 1 | 1 | 0 | -1.00 | 1.30 | 0 | 0 |


**ALL (pooled, no significance claim):** n=321 closed=319 win%=27 avgR=-0.13 medMFE=0.93 open=2 | skip_overlap dropped: 470


## Standing ruling-watch: 1D gate OFF (2026-06-11 user ruling, against n=9 evidence)

| cohort | n | closed | win% | avg R | med MFE |
|---|---|---|---|---|---|
| would-have-been-BLOCKED | 98 | 97 | 29 | -0.03 | 0.86 |
| would-have-passed | 223 | 222 | 26 | -0.18 | 0.96 |


_If the blocked cohort bleeds as n grows, flip `use_1d_gate` back on._


## Monthly windows (not pooled for significance)

| month | n | closed | win% | avg R | med MFE |
|---|---|---|---|---|---|
| 2026-01 | 55 | 55 | 22 | -0.29 | 1.03 |
| 2026-02 | 54 | 54 | 31 | 0.06 | 0.99 |
| 2026-03 | 56 | 56 | 36 | 0.25 | 1.06 |
| 2026-04 | 75 | 75 | 25 | -0.23 | 0.88 |
| 2026-05 | 65 | 65 | 22 | -0.36 | 0.89 |
| 2026-06 | 16 | 14 | 21 | -0.28 | 1.01 |


## Factor conditioning (real episodes)


### by `gvb`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <0.3 | 65 | 25 | -0.04 | 0.75 |
| 0.3-0.7 | 26 | 27 | -0.26 | 1.20 |
| >0.7 | 10 | 30 | -0.20 | 1.39 |
| na | 220 | 27 | -0.14 | 0.93 |


### by `wkp`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <50 | 13 | 23 | -0.04 | 0.89 |
| 50-85 | 43 | 33 | 0.17 | 1.26 |
| >85 | 38 | 18 | -0.44 | 0.80 |
| na | 227 | 27 | -0.15 | 0.94 |


### by `fp`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <25 | 29 | 24 | -0.21 | 0.70 |
| 25-75 | 47 | 28 | -0.16 | 0.84 |
| >75 | 25 | 24 | 0.10 | 1.54 |
| na | 220 | 27 | -0.14 | 0.93 |


### by `oi_d`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <0 (contracting) | 56 | 27 | -0.05 | 1.08 |
| >=0 (building) | 45 | 24 | -0.19 | 0.89 |
| na | 220 | 27 | -0.14 | 0.93 |


### by `d_pct`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <60 | 0 | â€” | â€” | â€” |
| 60-100 | 3 | 33 | -0.07 | 1.30 |
| >100 (wick-swept) | 4 | 25 | -0.34 | 0.78 |
| na | 314 | 27 | -0.13 | 0.91 |


### by `age`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <10 | 92 | 30 | -0.07 | 0.87 |
| 10-50 | 183 | 27 | -0.11 | 0.92 |
| >50 | 46 | 17 | -0.36 | 1.20 |


### by `rt1`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| 1.5-2 | 136 | 32 | -0.12 | 0.94 |
| 2-3 | 117 | 25 | -0.15 | 0.95 |
| >3 | 68 | 18 | -0.13 | 0.91 |


### by `os`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <-1 (stretched dn) | 100 | 30 | 0.00 | 1.30 |
| -1..1 | 120 | 25 | -0.27 | 0.64 |
| >1 (stretched up) | 101 | 26 | -0.11 | 0.96 |


### by `osp`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <50 | 137 | 28 | -0.16 | 0.80 |
| 50-85 | 131 | 29 | 0.00 | 1.26 |
| >85 | 53 | 17 | -0.39 | 0.71 |


### by `er`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <0.2 (chop) | 156 | 23 | -0.31 | 0.86 |
| 0.2-0.45 | 127 | 32 | 0.07 | 1.30 |
| >0.45 (trendy) | 38 | 24 | -0.12 | 0.78 |


### by `vz`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <0 | 173 | 30 | -0.05 | 1.03 |
| 0-1.5 | 114 | 22 | -0.27 | 0.76 |
| >1.5 (heavy) | 34 | 26 | -0.12 | 1.46 |


### by `fr`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <0 (shorts pay) | 109 | 29 | -0.04 | 0.89 |
| >=0 (longs pay) | 212 | 25 | -0.18 | 0.94 |


### by `swd`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <0.3 | 234 | 28 | -0.10 | 0.93 |
| 0.3-0.8 | 74 | 23 | -0.22 | 0.84 |
| >0.8 (deep) | 6 | 17 | -0.39 | 1.11 |
| na | 7 | 29 | -0.22 | 1.30 |


### by `age_t`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <10 | 144 | 28 | -0.10 | 0.78 |
| 10-40 | 101 | 21 | -0.35 | 0.90 |
| >40 | 52 | 29 | 0.10 | 1.23 |
| na | 24 | 33 | 0.03 | 1.33 |


### by `q`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| PD.OD | 32 | 31 | 0.02 | 0.94 |
| PD.OU | 19 | 21 | -0.41 | 0.53 |
| PU.OD | 24 | 33 | 0.28 | 1.38 |
| PU.OU | 26 | 15 | -0.43 | 0.80 |
| na | 220 | 27 | -0.14 | 0.93 |


### by `t1co`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| 0 | 93 | 25 | -0.12 | 0.84 |
| 1 | 1 | 100 | 1.51 | 1.69 |
| na | 227 | 27 | -0.15 | 0.94 |


### by `reg1d`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| C | 92 | 20 | -0.41 | 0.76 |
| D | 58 | 33 | 0.21 | 1.27 |
| U | 171 | 28 | -0.10 | 0.96 |


### by `rt1` PER TRADE TYPE (pooled rt1 mixes trade geometries â€” pre-registered)


**2A:**

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| 1.5-2 | 19 | 26 | -0.29 | 1.04 |
| 2-3 | 15 | 20 | -0.27 | 1.26 |
| >3 | 15 | 20 | -0.07 | 0.53 |


**2B:**

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| 1.5-2 | 18 | 39 | 0.06 | 0.90 |
| 2-3 | 19 | 16 | -0.40 | 0.84 |
| >3 | 8 | 38 | 0.92 | 2.86 |


**OSD:**

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| 1.5-2 | 17 | 35 | -0.01 | 1.46 |
| 2-3 | 16 | 19 | -0.38 | 0.65 |
| >3 | 12 | 0 | -1.00 | 0.56 |


**OSF:**

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| 1.5-2 | 71 | 34 | -0.09 | 0.90 |
| 2-3 | 54 | 26 | -0.11 | 0.85 |
| >3 | 33 | 19 | -0.10 | 1.33 |


**OSW:**

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| 1.5-2 | 6 | 0 | -1.00 | 0.34 |
| 2-3 | 11 | 55 | 0.75 | 2.42 |
| >3 | 0 | â€” | â€” | â€” |


**T1:**

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| 1.5-2 | 5 | 40 | 0.09 | 1.49 |
| 2-3 | 2 | 0 | -1.00 | 0.60 |
| >3 | 0 | â€” | â€” | â€” |


### by `lq_tot` WITHIN `swd` bands (mechanical correlation pre-registered in Â§8)

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| swd<0.3 | lq low | 219 | 28 | -0.10 | 0.93 |
| swd<0.3 | lq high | 15 | 36 | 0.02 | 1.61 |
| swd 0.3-0.8 | lq low | 71 | 24 | -0.19 | 0.84 |
| swd 0.3-0.8 | lq high | 3 | 0 | -1.00 | 1.37 |
| swd>0.8 | lq low | 5 | 20 | -0.27 | 1.26 |
| swd>0.8 | lq high | 1 | 0 | -1.00 | 0.04 |


## Direction-ORIENTED conditioning (supportive = positive; fixes the pooled-signed-factor wash-out)


### by oriented `os`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| against (<0) | 54 | 31 | -0.04 | 0.70 |
| supportive (>=0) | 267 | 26 | -0.15 | 0.96 |


### by oriented `fr`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| against (<0) | 145 | 24 | -0.20 | 0.94 |
| supportive (>=0) | 176 | 28 | -0.08 | 0.91 |


### by oriented `fp`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| against (<0) | 47 | 26 | -0.19 | 1.26 |
| supportive (>=0) | 54 | 26 | -0.05 | 0.80 |


### by oriented `q` (PW=price moved with trade pre-entry, PA=against)

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| PA.OD | 47 | 36 | 0.30 | 1.44 |
| PA.OU | 38 | 18 | -0.39 | 0.70 |
| PW.OD | 9 | 11 | -0.72 | 0.40 |
| PW.OU | 7 | 14 | -0.62 | 0.72 |
| na | 220 | 27 | -0.14 | 0.93 |


## OS â€” generalized sweeps (NEW population, judge separately)


### OS by `lvl_src`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| fvg | 158 | 28 | -0.10 | 0.96 |
| pdh | 22 | 9 | -0.70 | 0.59 |
| pdl | 23 | 30 | -0.12 | 1.01 |
| pwh | 7 | 43 | 0.38 | 1.33 |
| pwl | 10 | 30 | -0.04 | 1.38 |


### OS by `align`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| A | 37 | 27 | -0.18 | 0.72 |
| N | 69 | 25 | -0.14 | 0.93 |
| W | 114 | 29 | -0.13 | 1.05 |


### OS by `tgt`

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| fv | 37 | 27 | -0.18 | 0.72 |
| mid | 69 | 25 | -0.14 | 0.93 |
| tex | 114 | 29 | -0.13 | 1.05 |


### OS by `osp` (rt1~os is MECHANICAL for roll class â€” pre-registered)

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <50 | 106 | 30 | -0.09 | 0.93 |
| 50-85 | 77 | 28 | -0.07 | 1.21 |
| >85 | 37 | 17 | -0.44 | 0.68 |


### OS by `vz` (the campaign-1 quiet-bar lead, tested out-of-population)

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <0 | 124 | 31 | -0.03 | 1.04 |
| 0-1.5 | 74 | 20 | -0.36 | 0.70 |
| >1.5 | 22 | 27 | -0.01 | 1.62 |


### OSF by zone age `age_t` (FRESHNESS hypothesis — IN-SAMPLE until post-registration data accrues)

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <6 bars (fresh) | 37 | 38 | 0.19 | 0.80 |
| 6-30 | 86 | 27 | -0.17 | 1.08 |
| 30-90 | 19 | 22 | -0.29 | 1.30 |
| >90 (stale) | 16 | 19 | -0.16 | 0.68 |


## Sensitivity appendices


### (i) rr_min sensitivity â€” offline counterfactual, no knob change

| book | n | closed | win% | avg R | med MFE |
|---|---|---|---|---|---|
| book as-is (rr 1.5) | 321 | 319 | 27 | -0.13 | 0.93 |
| book if rr_min were 2.0 | 185 | 183 | 22 | -0.14 | 0.93 |


### (ii) skip_overlap sensitivity â€” every ENT walked independently (sequential rule OFF)

n=791 closed=784 win%=27 avgR=-0.05 medMFE=1.00 (sequential book: n=321) â€” if these stories diverge, the sequential rule is shaping the dataset.


## Gate questions (pseudo-episodes, walked independently)


### (a) rr gate â€” skipped-on-R signals, bucketed by their rt1

| bucket | n | win% | avg R | med MFE |
|---|---|---|---|---|
| <0.5 | 585 | 81 | -0.12 | 0.34 |
| 0.5-1.0 | 398 | 54 | -0.07 | 0.68 |
| 1.0-1.25 | 178 | 38 | -0.20 | 0.79 |
| 1.25-1.5 | 154 | 34 | -0.20 | 0.86 |


### (b) 1D gate â€” blocked sweeps, graded as if taken

n=0 closed=0 win%=â€” avgR=â€” medMFE=â€”


### (b2) OSF alignment gate (v0.7.2 ruling) — suppressed yellow OSF, graded as if taken

n=163 closed=163 win%=26 avgR=-0.15 medMFE=1.06 — _if this cohort turns profitable as n grows, flip `osf_skip_against` off._


### (c) thesis-exit v2 — net R saved by the third exit (per trade type)

| trade | n | recovered (exit cost us) | stopped (exit saved us) | NET R saved by rule |
|---|---|---|---|---|
| ALL | 0 | 0 | 0 | â€” |
