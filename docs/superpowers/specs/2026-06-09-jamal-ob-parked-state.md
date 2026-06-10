# Jamal OB — PARKED STATE (resume point)

**Status: PARKED 2026-06-09 at user request** (pivoting to "Jamal Fable"). Do NOT discard — this captures the validated rule-set and exactly where we left off.

The original pivot-driven approach (v0.1, commit `f2f9751`) was **scrapped** and replaced with the sweep + walk-back algorithm below. We are mid-**brainstorming/spec-validation** (superpowers flow): formation + confirmation rules are locked and user-validated against real charts; the design doc has NOT been written yet; NO code exists for the new algorithm.

- TV saved script: **"Jamal OB"** (id `USER;2ee1e9512ad04f5fb1aca04b07e3078d`) — still holds the OLD pivot v0.1 code; overwrite on next build.
- File: `jamal-ob.pine` — currently deleted from repo (git rm'd with the pivot scrap, commit `72d6ecf`); recreate when implementation starts.

---

## LOCKED RULE-SET (formation + confirmation only)

Bar classes: Red = close<open, Green = close>open, Doji = close==open. ATR(14) = 14-bar SMA of True Range.

### Bullish (demand) OB

1. **SWEEP** — a red candle T whose `low_T < low_{T-1}` arms a pending bullish OB (one pending per side at a time).
2. **WALK-BACK** — from T walk backward collecting the contiguous down-leg:
   - RED → include (always; see corrected rule 2 below).
   - GREEN where the next bar toward T made a new low (`low[j+1] < low[j]`) AND it didn't break out up (`high[j] <= high[j-1]`) → SKIP (mid-leg pause, continue).
   - GREEN that held / recovered / broke out up, or DOJI → **STOP** (this is the *stop-candle*).
   - `R` = **highest-open red** in the leg.
3. **OB ZONE** — Top = `open_R`; Bottom = lowest low over `[R..C]` (deepens with later wicks pre-confirmation).
4. **SELF-PRUNE** — while pending, a red making a new lower low (`low_k < pending.min_low`) re-runs walk-back from k; a continuous descent collapses into ONE OB anchored at the leg origin.
5. **CONFIRMATION** — first candle after T that **closes above the swing high over `[stop-candle … T]`** (see corrected rule 1).
6. **TWO GATES** (both required at confirm):
   - **Displacement** (`require_displacement=true`): ≥1 red in `[R..T]` closes below the prior bar's low.
   - **Down-move** (`down_move_atr_mult=1.5`): `confirm_level − ob_bottom ≥ 1.5 × ATR(14)` at the confirmation bar.

### Bearish (supply) OB — exact mirror

Green sweep candle T with `high_T > high_{T-1}` → walk back the up-leg of greens (red-that-held / doji / breakdown stops it; mid-leg red pauses skipped mirror-wise) → `R` = **lowest-open green** → OB **Bottom = open_R**, Top = highest high `[R..C]` → confirm = first close **below the swing low over `[stop-candle … T]`** → mirrored gates (a green in `[R..T]` closing above prior high; `ob_top − confirm_level ≥ 1.5×ATR`).

### TWO CRITICAL CORRECTED RULES (user-validated; do not regress)

1. **Confirm level = swing extreme over `[stop-candle … T]`, INCLUDING the candle that stopped the walk-back.** Not max/min over `[R..T]` excluding it. Box edge stays `open_R`; the confirm line is the swing extreme.
   - Verified: BTC `[May30…Jun5]` → 74250 (May 31 high); NEAR bear `[May30…Jun3]` → 2.209 (May 31 low); ASTER `[Jun3…Jun5]` → 0.7089 (Jun 3 high).
2. **Walk-back terminates ONLY on structure (green-that-held / doji / breakout — mirrored for bearish). NEVER on open monotonicity.** Running-max(red opens) / running-min(green opens) selects `R` only — it is not a stop condition.
   - Bug it fixed (NEAR daily): the Apr-24→May-4 down-leg got truncated at May 1 because May 1 open 1.297 was 0.001 below May 3 open 1.298 → false STOP → wrong confirm 1.319 instead of the correct Apr-24 high **1.432**. Without the open-stop the leg walks to its true origin and the block passes both gates (move 0.188 ≥ 1.5×ATR≈0.096).

### Scope decisions

- **TAG / invalidation (wick-touch freeze+fade) is DEFERRED.** Get formation + confirmation right first; a confirmed OB just stays drawn.
- **Bullish and bearish OBs COEXIST** — fully independent sides; an opposite-side confirm does NOT invalidate the other.
- Knob defaults: `atr_period=14`, `down_move_atr_mult=1.5`, `require_displacement=true`, `red_body_atr_mult=0.0` (disabled).

### Open questions (decide before/at spec-writing)

1. Down-move gate measures ATR **at the confirm bar** — an explosive confirmation candle inflates ATR(14) and can self-defeat the gate. Consider ATR at the bar *before* confirmation.
2. Drawing/rendering spec (colors, pending vs confirmed styling, markers) was drafted for the original algorithm and includes tag-dependent states — needs a pass once invalidation is back in scope.
3. More pressure-testing? Each chart example so far surfaced a real rule bug. A strongly trending and a choppy-range symbol would stress walk-back termination hardest.

---

## Validated worked examples (NEAR daily, Binance perp; ts anchor: 2026-01-01 = 1767225600, ts = anchor + (DOY−1)·86400)

| OB | Leg | R / box edge | Other edge | Confirm level (source) | Confirmed | Gates |
|---|---|---|---|---|---|---|
| Bullish | Apr 24 origin → May 4 low (greens May 2 skipped) | Apr 25 open **1.407** (top) | 1.244 (May 4 low) | **1.432** (Apr 24 high, stop-candle window `[Apr23…May4]`) | **May 6** close 1.488 | disp ✓, move 0.188 ✓ |
| Bearish | May 12 single-green up-leg (May 11 red broke down → stop) | May 12 open **1.547** (bottom) | 1.69 (May 13 high, `[R..C]`) | **1.503** (May 12 low, window `[May11…May12]`) | **May 16** close 1.496 | disp ✓, move 0.187 ✓ |
| Bullish (most recent confirmed) | May 13–16 reds (May 12 green held → stop) | May 13 open **1.607** (top) | 1.462 (May 17 low) | **1.69** (May 13 high, window `[May12…May16]`) | **May 20** close 1.702 | disp ✓ (May16 1.496<1.508), move 0.228 ✓ |
| Pending (never confirmed as of Jun 8) | May 26–30 leg | — | — | 2.978 (May 26 high) | not reached (Jun 3 close 2.816 < 2.978) | — |
| Pending | Jun 4–5 leg | — | — | 3.085 (Jun 3 high) | not reached | — |

Note the May 16 bearish + May 20 bullish pair: both sides confirm within 4 bars on overlapping price — the coexistence stress case.

## WHERE WE LEFT OFF / RESUME STEPS

1. (Optional, recommended) pressure-test formation rules on 1–2 more symbols/regimes (strong trend; chop).
2. Write the full design doc (`docs/superpowers/specs/…-jamal-ob-design.md`) from this rule-set + render spec rework; user reviews.
3. superpowers writing-plans → incremental implementation plan (one render at a time, chart-test-gated).
4. Build: recreate `jamal-ob.pine`, overwrite the TV "Jamal OB" script via Make-a-copy-safe flow, version-tag every increment, CHANGELOG + push per change.
