# Study: the Waterfall Blind-Spot & the Option-3 Fallback Chain (2026-06-12)

## The question (user-identified gap)

In a strong downtrend, price trades below its last *confirmed* pivot low (pivots
confirm 3 bars late). A with-trend short's target — the trend extreme — is then
already overtaken, so every with-trend sweep entry (bear-FVG retest, prev-day-high
tag) fails geometry and logs `SKP rsn=rr, rt1=na`. Mirror for longs in melt-ups.
**Is this blind spot costing money, and does a structural fallback target fix it?**

## The candidate fix ("option 3")

Target fallback chain, scoped to the broken case only: when the trend extreme is
overtaken, fall through to the nearest *reachable* calendar level on the profit
side — prev-day low, then prev-week low (shorts; mirror for longs) — re-apply the
1.5R gate, take the trade if it passes. Counter-trend (fv) and chop (mid) targets
are untouched (their "overtaken" skips are correct by thesis).

## Method

Every with-trend target-overtaken skip in the s0.7.1 dataset (4 symbols, Jan 1 →
Jun 12, trades 2A/OSD/OSW/OSF with `tgt=tex`) carries its full entry/stop snapshot.
The fallback rule was applied retroactively: recompute prev-day/week extremes from
raw ccxt bars at each skip, pick the nearest reachable one, re-gate at 1.5R, and
walk the unlocked trades to stop/target (third exit off, per current rules).
Script: `harness/evaluator/fallback_study_v071.py`.

## Results

| population | n | outcome |
|---|---|---|
| with-trend target-overtaken skips (total) | **94** | |
| → no reachable calendar level either ("true abyss") | 39 | stays skipped — nothing to aim at |
| → fallback exists but pays < 1.5R vs the wick stop | 37 | stays skipped — gate rejects |
| → **UNLOCKED by option 3** | **18** | **28% win, −0.05R avg** |

Unlocked trades by fallback level:

| fallback target | n | win% | avg R |
|---|---|---|---|
| prev-day low (shorts) | 3 | 100% | +2.24 |
| prev-day high (longs) | 4 | 0% | −1.00 |
| prev-week high (longs) | 4 | 25% | +0.08 |
| prev-week low (shorts) | 7 | 14% | −0.57 |

## Conclusion

**The blind spot is protective, not costly.** 81% of the "missed" sweeps either had
no landing zone at all or couldn't pay 1.5R even with one; the 18 trades option 3
would have added were breakeven noise (−0.05R avg ≈ −1R cumulative across four
symbols and 5.5 months). When price makes fresh extremes beyond every confirmed
level, the market has consumed all measurable objectives — declining to chase is
the correct behavior, now with a price tag. With-trend entries regain valid
geometry as soon as a pullback or base forms, which the existing trend-extreme
target already handles.

**Verdict: do not build the full fallback chain.** Caveats for the record: n=18 is
small; the single positive cell (prev-day-low fallback shorts, 3/3, +2.24R) leaves
a narrow variant on the table — *daily-level fallback only, never weekly* — which
would have added ~7 trades (3 pdl + 4 pdh = +0.39R avg pooled, carried entirely by
the short side). If built, it ships as a tagged, reversible `tgt=` fallback with a
standing scoreboard, same as every ruling. Status: **user decision pending** (drop /
full / narrow).
