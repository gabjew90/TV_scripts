# Study: Single-Use FVGs & Zone Freshness (2026-06-12)

## Question (user hypothesis)

"FVGs can only be used once it gets wicked through" — does consuming a zone on
its first wick improve OSF?

## Method

All 199 OSF ENTs (s0.7.1, post-Feb warm-up, 4 symbols) matched to their zone via
full lifecycle re-simulation from raw bars; prior wick-touches since zone birth
counted; entries walked independently to stop/target.
Script: `harness/evaluator/fvg_single_use_study.py` (binary split; deep cuts in
this doc reproduced from the same machinery).

## Result 1 — the single-use premise is empty

| prior touches | n | win% | avg R |
|---|---|---|---|
| 0 (virgin) | 43 | 33% | +0.03 |
| 1 | 41 | 39% | +0.24 |
| 2–3 | 44 | 36% | +0.07 |
| 4+ | 71 | 35% | +0.14 |

Touch count carries no signal in either direction. Single-use would delete 78%
of OSF volume (156/199) on a dimension that is noise — and the deleted group is
(insignificantly) the better one. **REJECTED.**

## Result 2 — the real variable is TIME (pre-registered for campaign 6)

Zone age at entry:

| age | n | win% | avg R |
|---|---|---|---|
| < 1 day | 35 | **49%** | **+0.47** |
| 1–5 days | 88 | 35% | +0.03 |
| 5–15 days | 39 | 31% | +0.16 |
| > 15 days | 37 | 30% | **−0.05** |

Bars since the zone's last touch (re-touch entries):

| gap | n | win% | avg R |
|---|---|---|---|
| 1–2 (immediate re-test) | 99 | 37% | +0.13 |
| 3–10 (short pause) | 27 | **52%** | **+0.71** |
| > 10 (returned later) | 30 | **20%** | **−0.31** |

Zone size: flat among ENTs (gate pre-screens dust geometry). Per-symbol: the
virgin-vs-retouch null result is consistent across all four symbols.

## Interpretation

An FVG is a perishable object whose relevance decays with TIME, not with use.
Best: zones under a day old, or in an active test-hold-pause-sweep rhythm.
Worst: price wandering back to a zone it abandoned 10+ bars ago. The defense
that keeps a zone alive through wicks neither strengthens nor spends it.

## Caveats

~16 cells on n=199: the standout cells (n=27–35) are chance-sized. This is a
PRE-REGISTERED hypothesis, not a gate: "OSF quality decays with zone age;
fresh/recently-active zones outperform; 10+-bar-absent returns underperform."
`age_t` is logged on every event — campaign 6 tests it for free. The 1–2-bar
re-test bucket contains consecutive-bar clusters that the sequential book
collapses; its live weight is smaller than raw n.

**Status: single-use rejected; freshness hypothesis registered, awaiting
campaign 6.**
