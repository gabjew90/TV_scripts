# Jamal OB — Pivot-Driven Order-Block Detector (Pine v6)

**Date:** 2026-06-07 · **Status:** design approved, pre-implementation
**File to build:** `jamal-ob.pine` (NEW, standalone) · **TV saved-script name:** "Jamal OB" · **shorttitle:** "JmlOB"
**Source spec:** user-provided "Pivot-Driven Order Block Detection — Logic Specification" (`coinglass_pull/scripts/ob_v5_pivot.py` prototype, tested daily BTCUSDT).
**Independent of** the Jamal Context tool (mid-build at v0.1.4) — do NOT modify Jamal Context.

---

## 1. Purpose & scope
A faithful Pine v6 port of the pivot-driven order-block algorithm: structural pivot → liquidity sweep → reference candle → structural break (CHoCH/BOS) → OB zone, with a built-in regime tracker. **Discretionary context / detection tool — displays structure; the trader decides.** Not a strategy, not a backtest, not a validated edge (header states so). `overlay=true` (boxes + labels on price). Runs on the chart timeframe (spec tested on Daily).

## 2. Architecture (pipeline; each unit isolated)
`indicator("Jamal OB v0.1", "JmlOB", overlay=true, max_boxes_count=500, max_labels_count=500)`
1. **Pivot engine** → most-recent confirmed PH and PL (value + bar index).
2. **Setup state machine** (independent `pending_up` / `pending_dn`) → sweep → reference candle R → structural break.
3. **Regime tracker** (neutral/bull/bear) → CHoCH (flip) vs BOS (continue).
4. **Render layer** → OB boxes, CHoCH/BOS labels, regime readout, optional markers, alerts.

## 3. Algorithm (verbatim from the spec)
**Pivot detection** (`B`=3 left, `A`=3 right):
- PH at bar i: `high[i] > high[i-1..i-3]` AND `high[i] > high[i+1..i+3]`. PL mirror with lows.
- A pivot at bar i is **CONFIRMED at bar i+A** (needs A bars after). → inherent A-bar lag.

**Bullish OB** (prereq: a confirmed PL exists MORE RECENTLY than a confirmed PH — PL after PH):
1. **Sweep:** a bar with `low < pivot_low_value` (liquidity below PL taken).
2. **Reference candle R:** from the bar after the PH (ph_idx+1), walk forward to the FIRST RED candle (`close < open`), skipping greens. R = that first red.
3. **Break:** a bar with `close > high[R]`. If regime ≠ bull → **CHoCH** (flip to bull); if regime == bull → **BOS**.
4. **Zone:** top = `pivot_high_value`, bottom = `pivot_low_value` (full pivot range).
5. **Draw:** from bar R forward; invalidated when any wick enters the zone (first touch = tag).

**Bearish OB** (mirror; prereq PH after PL):
1. **Sweep:** `high > pivot_high_value`.
2. **R:** from pl_idx+1, first GREEN candle (`close > open`), skipping reds.
3. **Break:** `close < low[R]` → CHoCH (flip to bear) or BOS.
4. **Zone:** top = `pivot_high_value`, bottom = `pivot_low_value`.
5. **Draw:** from R; invalidate on wick touch.

**Regime:** starts neutral. Bull break → CHoCH if regime≠bull else BOS (regime→bull). Bear break → CHoCH if regime≠bear else BOS (regime→bear). CHoCH = first break in a new direction (reversal); BOS = continuation.

**State notes (from spec §8):** pivots confirmed with A-bar lag; sweep + R detection happen as bars complete; the structural break is the trigger; `pending_up`/`pending_dn` tracked independently; **a new sweep overwrites any existing pending setup on the same side**.

## 4. Render rules (decisions locked with user)
- **OB box** (`box.new`): left edge at bar **R**, spans `[pivot_low, pivot_high]` (FULL pivot range — confirmed per user), extends right while active. Bull = translucent green, Bear = translucent red.
- **Invalidation:** on the FIRST wick-touch of the zone, **freeze** the box right-edge at the tag bar and **fade** it to a muted "mitigated" color (kept as history, not deleted). Retain the **last `keep_n` per side** (default 10); delete oldest beyond that (stays well under the 500 cap).
- **CHoCH / BOS labels** (`label.new`) at the confirmation bar: `CHoCH▲`/`BOS▲` below bar (bull), `CHoCH▼`/`BOS▼` above bar (bear). CHoCH brighter/distinct from BOS so reversals stand out.
- **Regime readout:** small top-right `table` cell — Neutral / Bull / Bear (toggle).
- **Optional, default OFF (minimal ink):** confirmed-pivot dots (PH/PL) and sweep markers — for engine verification.
- **Alerts:** condition-present `alertcondition` (neutral wording, no buy/sell): bull CHoCH, bear CHoCH, bull BOS, bear BOS, OB tagged.

## 5. Inputs
- **Pivots:** `left_B`=3, `right_A`=3.
- **Display:** show_ob, show_breaks, show_regime, show_pivots(off), show_sweeps(off); `keep_n`=10.
- **Colors:** bull OB, bear OB, mitigated, CHoCH, BOS + transparency.

## 6. Non-repaint & conventions
- **Non-repaint:** pivots confirm A bars after forming (inherent lag); breaks are taken on **confirmed (closed) bars** only, so historical OBs/labels never repaint; the forming bar is provisional and flagged. OBs appear at the confirmation bar (R is in the past, drawn retroactively from R — standard for SMC OB tools; documented).
- **Conventions:** on-chart `indicator()` title carries a version tag, **bumped every push** (shorttitle "JmlOB" + a panel/version readout) so a recompile is visually confirmable. **CHANGELOG.md** entry per increment (code / rationale / tested / result). **commit + push to GitHub main every change** (Co-Authored-By trailer). Dev loop: edit → `pine_smart_compile` → remove/re-add (legend cache) → screenshot verify.

## 7. Incremental build roadmap (one render at a time — user-requested; each gated by a chart test)
1. **v0.1 — Pivot engine + pivot dots.** Render confirmed PH/PL as dots (show_pivots ON for this increment). *Test:* dots sit on correct swing highs/lows on daily BTC, confirmed with the A-bar lag (no repaint).
2. **v0.2 — Setup state machine + CHoCH/BOS labels.** Sweep → R → break; draw the CHoCH/BOS labels (no boxes yet). *Test:* labels fire at correct structural breaks; CHoCH vs BOS classification matches regime flips; bull & bear.
3. **v0.3 — OB boxes (active only).** Draw the full-pivot-range box from R, extending right; no invalidation yet. *Test:* boxes anchor at [PL,PH] from R, correct side/color, bull & bear.
4. **v0.4 — Invalidation (freeze + fade) + retention.** First wick-touch freezes+fades the box; keep last `keep_n` per side. *Test:* a zone that gets wicked freezes at the tag bar and fades; oldest beyond keep_n removed; no repaint.
5. **v0.5 — Regime readout + optional markers + alerts; polish.** Regime table cell; sweep/pivot toggles finalized; condition alerts; header disclaimer; minimal-ink pass. → **v1.0** when accepted.

**Gate:** do not start an increment until the previous one passes its chart test. Each increment bumps the on-chart version, logs to CHANGELOG, and is committed+pushed.

## 8. Out of scope
No auto entry/exit/target markers (spec §9 is trader guidance, not drawn signals — keep it discretionary). No multi-timeframe HTF OBs (chart-TF only) for v1. No score/edge claims.
