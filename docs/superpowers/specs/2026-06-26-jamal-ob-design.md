# Jamal OB — Design (v0.1, sweep-driven two-line render)

**Date:** 2026-06-26
**Status:** Design approved (brainstorming complete) — ready for implementation plan.
**Supersedes scope of:** `docs/superpowers/specs/2026-06-09-jamal-ob-parked-state.md` (the parked rule-set). The walk-back rules below are inherited verbatim from that parked spec; this doc narrows the deliverable to a minimal, sweep-driven, two-line indicator.

---

## 1. Purpose

A new standalone Pine v6 overlay indicator, `jamal-ob.pine`, that draws **exactly two horizontal lines** — a lower (demand) line and an upper (supply) line — analogous to the two "kill lines" rendered by `jamal-fable.pine` ([jamal-fable.pine:831-836](../../../jamal-fable.pine#L831)), **except the line levels come from order-block logic instead of pivot logic.**

This is a discretionary detection/context tool, not a validated edge.

## 2. Relationship to fable's kill lines

Fable's two structure lines are **regime-conditional** and **pivot-driven**: `hl_ref` / `lh_ref` / `trend_high` / `trend_low` / `range_hi` / `range_lo`, all seeded from `ta.pivothigh/low(…, 3, 3)`, selected by an UP/CHOP/DOWN FSM.

Jamal OB throws that away:

- **Regime-less.** No UP/CHOP/DOWN state machine. Two independent sides — a bullish (demand) side feeding the lower line and a bearish (supply) side feeding the upper line. Each lives on its own; both can show at once, or neither.
- **OB-driven levels.** Each line is the `open_R` of the order block implied by the most recent **sweep** on that side.

## 3. Locked decisions (from brainstorming, 2026-06-26)

1. **Architecture:** regime-less, two independent zones (no FSM).
2. **Kill-line level = `open_R`** — the open of `R`, the leg's `R`-selected red/green. For bullish this is the OB **box top**; for bearish the OB **box bottom** (the box's anchor edge in both cases). *(Note: an earlier moment in the conversation considered `open_T` (the sweep candle's open); this was explicitly retracted in favor of `open_R`.)*
3. **Trigger = sweep, not confirmation.** The line moves whenever a new same-side sweep prints. `open_R` is fully determined the instant the sweep prints (the walk-back scans already-closed bars), so no reclaim/confirmation wait is required.
4. **Pure sweep-driven for v1.** Confirmation, the displacement gate, and the down-move gate are **NOT built** in v1. The line is simply `open_R` of the latest sweep per side.
5. **Defer invalidation.** No "kill"/invalidation behavior. A line, once set, holds (stepline) until the next same-side sweep moves it. No disappearing on breach, no fallback stack.
6. **Latest sweep per side wins.** Exactly one lower line and one upper line. Each new same-side sweep re-runs the walk-back and relocates that side's line. (A continuous descent/ascent re-walks to the same origin → same `R` → the line stays put — this is the parked spec's self-prune, achieved statelessly.)
7. **Build approach:** fresh minimal script (~100 lines), not a fork of fable. The OB walk-back shares nothing with fable's pivot engine.

## 4. Algorithm

Two fully independent, mirrored sides. Evaluated on confirmed bars. Pine offset convention: offset `0` = current bar, higher offset = further back in time.

**Bar class:** `red = close < open`, `green = close > open`, `doji = close == open`.

### 4.1 Bullish side (lower line)

1. **Sweep trigger** (bar `T` = offset 0): current bar is **red** AND `low[0] < low[1]` (new low vs prior bar). Every bar meeting this recomputes the walk-back and moves `lower_line`.

2. **Walk-back** — scan backward `i = 1, 2, 3, …` from `T` until a structural stop or `i > max_lookback`:
   - bar `i` **red** → in the down-leg (a candidate for `R`). Continue.
   - bar `i` **green**:
     - **mid-leg pause → SKIP & continue** if `low[i-1] < low[i]` (bar toward `T` made a new low) **AND** `high[i] <= high[i+1]` (this green did not break out up vs the earlier bar).
     - **otherwise → STOP** (green held / recovered / broke out — the stop-candle).
   - bar `i` **doji** → **STOP**.
   - Termination is **structure-only** — never open-monotonicity (the validated correction from the parked spec). The running `open` max selects `R`; it never stops the walk.

3. **`R` selection:** `R` = the **highest-open red** among all leg bars (offsets `0 … stop-1`). Seed the running max with `open[0]` (T is always red), update on each red with a higher open.

4. **Output:** `lower_line := open_R`. Stepline holds until the next bullish sweep.

### 4.2 Bearish side (upper line) — exact mirror

1. **Sweep trigger:** current bar is **green** AND `high[0] > high[1]`.
2. **Walk-back** — up-leg of greens:
   - bar `i` **green** → in the up-leg (candidate for `R`). Continue.
   - bar `i` **red**:
     - **mid-leg pause → SKIP & continue** if `high[i-1] > high[i]` (bar toward `T` made a new high) **AND** `low[i] >= low[i+1]` (this red did not break down vs the earlier bar).
     - **otherwise → STOP** (red held / broke down — the stop-candle).
   - bar `i` **doji** → **STOP**.
3. **`R` selection:** `R` = the **lowest-open green** among all leg bars. Seed with `open[0]` (T is always green), update on each green with a lower open.
4. **Output:** `upper_line := open_R`.

### 4.3 Bounded loop

Pine requires a finite loop bound. The walk-back caps at `max_lookback` (input, default 200) and breaks early at the stop-candle. Legs are short, so this never truncates a real leg; the cap is purely a safety bound.

## 5. Rendering

- **Two `plot()` steplines**, `linewidth = 2`, `style = plot.style_stepline`.
- **Lower line** (bullish demand `open_R`): opaque **green**.
- **Upper line** (bearish supply `open_R`): opaque **red**.
- (Matches fable's UP-lower-kill green / DOWN-upper-kill red for visual consistency.)
- Each line is `na` until its side's first sweep prints (stepline gaps on `na`).
- **No** bgcolor, **no** boxes, **no** labels — just the two lines.
- Small **version table** (top-right, 1 cell) showing `Jamal OB v0.1.0` to confirm on-chart that a push landed.

## 6. File structure

New `jamal-ob.pine`, ~100 lines, in order:

1. `//@version=6` + `indicator("Jamal OB v0.1.0", shorttitle="JamalOB", overlay=true)` (shorttitle ≤ 10 chars).
2. **Inputs:** `max_lookback` (int, default 200, minval 10). Nothing else for v1.
3. **Bar-class** helpers (red/green/doji expressions).
4. **Bullish** routine: sweep test → walk-back function returns `open_R` → `var float lower_line` updates on sweep.
5. **Bearish** routine: mirror → `var float upper_line` updates on sweep.
6. **Two stepline plots.**
7. **Version table.**

The walk-back is a function per side (returns `open_R`; the caller only assigns when the bar is a sweep). Two explicit mirrored functions rather than one parameterized one — the mirror is bug-prone to fold together.

## 7. Out of scope (v1) / future

Deferred, in rough priority order for later versions:

1. **Confirmation + gates** — first close above the swing high `[stop-candle…T]` (bullish); displacement gate; down-move (`≥ 1.5×ATR`) gate. Would gate whether a line is "validated" (e.g. solid vs dashed styling).
2. **Invalidation / kill behavior** — what happens when price closes through `open_R`. Would turn these from "latest-sweep level" into true kill lines with disappear/fallback semantics.
3. **Multiplicity / fallback stack** — tracking multiple live OBs per side and choosing among them (most-recent vs nearest-below-price) when the active one is killed.
4. **OB boxes / tags** — drawing the full zone and wick-touch mitigation (the parked spec's deferred TAG behavior).

### v0.2.0 addendum (2026-06-27) — `hold_until_swept` sticky mode

An optional input (default OFF = v1 behavior). When ON, each line locks at its current OB and relocates only when its anchor low/high is wicked out **or**, after a **structure break** (a close beyond the down-/up-leg origin), on the next sweep. This pulls a slice of item 1 forward: the walk-back now also returns the leg swing high/low (the BOS level). Two testing-found corrections are baked in: (a) a pure "hold until swept" rule is degenerate — it ratchets to the all-time low/high and sticks — so an opposite-side structure break is required to relocate the line back toward price; (b) a green bullish anchor (red bearish anchor) starts its walk-back one bar earlier so a green candle's open is never the OB level. Still deferred: the displacement / down-move gates, full invalidation, multiplicity, and boxes. See CHANGELOG "OB v0.2.0".

## 8. References

- Parked rule-set + validated worked examples: `docs/superpowers/specs/2026-06-09-jamal-ob-parked-state.md`.
- Fable kill-line render this mirrors: [jamal-fable.pine:824-836](../../../jamal-fable.pine#L824).
- TV saved script "Jamal OB" id `USER;2ee1e9512ad04f5fb1aca04b07e3078d` (currently holds the scrapped pivot v0.1; overwrite on first build via the Make-a-copy-safe flow).
- Conventions: increment on-chart version tag + CHANGELOG + commit/push per increment; build one render at a time, chart-verified, via the TradingView MCP.
