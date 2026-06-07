# Jamal Context — Discretionary Regime + Pullback + Flow Indicator (Pine v6)

**Date:** 2026-06-06 · **Status:** design approved, pre-implementation
**File to build:** `jamal-context.pine` (new, separate — do NOT touch the research scripts)
**Source of reuse:** `overshoot-regime-os-core-v1.pine` (regime engine, overshoot engine, carry, state panel) + `jamal-phase2.pine` / `jamal-phase3.pine` (TradingView/Request flow imports)

---

## 1. Purpose & scope

A **discretionary context tool**: a Pine v6 study that paints current market *state* so a human can trade by eye. It **displays conditions; the trader decides.**

It is **NOT** a strategy, NOT a backtest, NOT a validated edge. No `strategy()`, no win-rate, no score, no BUY/SELL/edge language. The header comment must state: *discretionary context, unvalidated, not a backtested edge.*

`overlay=true` (everything lives on the price chart: regime tint via `bgcolor`, one anchor line, taxonomy marks via `plotshape`, one flow panel via `table`). No oscillator pane — this is the minimal-ink context tool, not the Phase 1 research oscillator. *Note:* the brief mentions `force_overlay` for price-pane marks "like the existing script," but that was needed because Phase 1 was `overlay=false`; with `overlay=true` here, marks render on price directly and `force_overlay` is unnecessary.

**Terminology — two distinct "flush" concepts (do not conflate):** (1) **Flush regime** = the structural cascade state from Mechanism A (`|regime|`==2: ER + vol-hot + volume surge); (2) **liq-flush flag** = the liquidation-magnitude spike from Mechanism C. They are computed independently and can occur apart.

## 2. Three mechanisms (the spine)

The indicator is organised as three independent, well-bounded mechanism modules feeding one composition/render layer. Each mechanism is **lifted from existing, validated code** — no new detection logic is invented.

> **Composition principle (advisor):** overshoot = the **trigger** (whether/where a mark appears), regime = the **type** (what it means), flow = the **conviction** (how strong).

### Mechanism A — Structure / Regime *(reuse Phase 1 verbatim)*
ER Schmitt trigger (enter `er_trend`=0.30 / exit `er_exit`=0.18, `regime_min_dwell`=3) + signed linreg slope with ATR deadband (`slope_dead_atr`=0.05) + cascade (`er_cascade`=0.45 AND vol-hot `atr_pct`≥`vol_hi`=80 AND volume surge) → signed state machine `regime ∈ {0 Range, ±1 Trend, ±2 Cascade}`.
**Output:** background tint + one glanceable label → **Trend-up / Trend-down / Range / Flush** (Flush = cascade, `|regime|`==2).

### Mechanism B — Overshoot *(reuse Phase 1 verbatim)*
Decontaminated trend anchor (Regression/SMA/EMA, `reg_len`=50, `k_decontam`=3) + lagged-ATR-normalised `os = (close − anchor)/atr_os` + extremity = percentile-tail (`pct_thresh`=90 over `pct_len`=250) **AND** ATR-floor (`os_min_atr`=1.0) → `os_ext_up` / `os_ext_dn`.
**Output:** an overshoot event + its side (up/down) + depth `|os|` in ATR. **One detector, one anchor.** Anchor type/length remain inputs (the trader's "fast vs slow dip" dial).

### Mechanism C — Derivative flow *(reuse Phase 2/3 imports)*
`import TradingView/Request/3 as r`. Binance-only (logged); non-repainting (values read lagged / on confirmed bars).
- **Funding:** `fz = (funding − SMA(funding,N)) / STDEV(funding,N)`, N = 14 days in bars (a-priori, not swept). Bands: *not extreme* = `|fz| < 1.5`; *extreme* = `|fz| ≥ 1.5`.
- **OI:** level + **build-vs-cover** = `sign(ΔOI) × price-direction` → "fresh leverage" (OI rising into the move) vs "covering / hollow" (OI falling). ΔOI over a short a-priori window (12 bars).
- **Liquidations:** `liqMag = LiqBuy + LiqSell`; **flush flag** when `liqMag ≥ p90` over a trailing a-priori window (reuse `p2_liq_gate` logic).
**Output:** three panel readouts + a liq-flush boolean.

## 3. Composition / render layer (the only place mechanisms combine)

### 3.1 Taxonomy — overshoot × regime (mutually exclusive; exactly one active per bar)

| regime | overshoot side | type | glyph (price pane) | directional? |
|---|---|---|---|---|
| Trend-up (+1) | up (`os_ext_up`) | **Blowoff** (with-trend climax) | amber **diamond** above bar | no |
| Trend-up (+1) | down (`os_ext_dn`) | **Pullback** (counter-trend dip) | green **triangle-up** below bar | **yes** (with trend) |
| Trend-down (−1) | down (`os_ext_dn`) | **Blowoff** | amber **diamond** below bar | no |
| Trend-down (−1) | up (`os_ext_up`) | **Pullback** | red **triangle-down** above bar | **yes** (with trend) |
| Range (0) | either | **Spike** (range extreme) | gray **dot** at the extreme | no |
| Flush (±2) | either | — | no price mark; "Flush" flag in panel | no |

**Hard rule:** only **Pullback** is a directional entry arrow. Spike and Blowoff are non-directional caution marks — **never a fade arrow** (range-fading is what Phase 1 killed; Blowoff is the worst-measured-asymmetry zone — v8's C1 came back *inverted*, counter-trend extremes/climaxes are violent both ways). Blowoff flag text: *"counter-trend extreme / possible exhaustion — elevated reversion risk both directions."* On-chart framing for Pullback: *"with-trend pullback condition,"* never "signal" / "entry" / "reversal."

### 3.2 Conviction — flow sets brightness (co-occurrence COUNT, never a weighted score)
Each mark has a base level (overshoot+regime alone = faintest) and brightens by **+1 per aligned flow ingredient** → 3 transparency levels. The intensity reflects *how many ingredients co-occur* — there are no tuned weights.
- **Pullback** (re-entry): +1 if **OI building** (ΔOI>0) · +1 if **funding not extreme** (`|fz|<1.5`).
- **Blowoff** (exhaustion caution): +1 if **funding extreme** (`|fz|≥1.5`) · +1 if **liq-flush present**.
- **Spike**: +1 if **funding extreme** · +1 if **OI extreme** (|ΔOI| in its tail).

### 3.3 Non-repaint
Confirmed-bar marks render **solid**; forming-bar marks render **greyed** (provisional dominates over intensity), so the historical chart never shows a mark that wasn't there at close. Same `barstate.isconfirmed` pattern as Phase 1. Panel flags forming vs confirmed state.

### 3.4 Depth
Pullback depth = `|os|` in ATR, shown live in the state panel; plus a faint label on the **most recent confirmed pullback only** (minimal ink — not every bar).

## 4. Flow panel + anchor line
Extend the existing top-right state panel (Regime / ER / Vol-pct / Overshoot / Extremity already present) with three flow rows: **Funding** (`fz`), **OI** (level + build/cover), **Liq** (flush flag). Draw **one** anchor line on price = the overshoot anchor. No extra plots. Header logs Binance-only + non-repaint.

## 5. Guardrails (non-negotiable)
- State, not commands. Directional Pullback arrows allowed as condition-markers; no BUY/SELL text, no backtest stats, no win-rate, no edge language anywhere.
- Confluence = co-occurrence, not a score.
- Non-repainting / confirmed-bar display; provisional clearly greyed.
- Minimal ink: tint + one anchor line + taxonomy marks + one flow panel. Nothing more.
- No `strategy()` / backtester. No alerts framed as signals (condition-present `alertcondition` is fine). No parameter sweeping/optimization.
- Header comment states: discretionary context, unvalidated, not a backtested edge.

## 6. Inputs (grouped)
**Regime:** er_len, er_trend, er_exit, regime_min_dwell, vol_pct_len, vol_hi, er_cascade, vsma_len, vsurge_mult, slope_dead_atr. **Overshoot/Anchor:** os_anchor, reg_len, atr_len, pct_len, pct_thresh, os_min_atr, k_decontam. **Flow:** funding_z_days(14), oi_chg_bars(12), liq_pct_len, liq_pct(90), fund_extreme_z(1.5). **Display:** show tint / marks / provisional / panel / anchor line; venue note.

## 7. Versioning & CHANGELOG discipline
On-chart `indicator()` title carries a version that **bumps every increment** (so a recompile is visually confirmable); `shorttitle` = "JmlCtx" (≤10). Each increment: **CHANGELOG.md** entry (code change / rationale / what was tested / result) + **commit & push**. Dev loop per increment: edit local .pine → `pine_check`/compile → push → **remove + re-add** the study (legend cache) → screenshot + read panel/values → verify the acceptance test.

## 8. Incremental build roadmap (each gated by a chart test)

1. **v0.1 — Regime + tint + label** (Mech A only). *Acceptance:* regime state matches Phase 1 on BTC 1h & 4h; Trend-up/down/Range/Flush label + tint correct; Flush lights on cascade bars.
2. **v0.2 — Overshoot + taxonomy marks** (Mech B + classify; flat intensity). *Acceptance:* Pullback arrows on counter-trend dips, Blowoff diamonds on with-trend climaxes, Spike dots in range, suppressed in Flush — verified **bull & bear**; non-repaint (provisional grey / confirmed solid).
3. **v0.3 — Flow panel + anchor line** (Mech C; readouts only, not yet wired to marks). *Acceptance:* funding-z / OI build-cover / liq-flush sane & non-repainting on BTC; anchor line drawn; Binance caveat logged.
4. **v0.4 — Conviction wiring** (flow → mark brightness). *Acceptance:* brightness = co-occurrence count per type, verified on sample bars; confirm it is not a score.
5. **v1.0 — Guardrails + polish** (header disclaimer, minimal-ink audit, input grouping, version tag, final CHANGELOG). *Acceptance:* full visual review screenshot; no edge/score/strategy language.

**Gate:** do not start an increment until the previous one passes its chart test.

## 9. Explicitly dropped (do not port)
All research machinery: conditioner scout, winsorized-correlation harness, MFE/MAE excursion, block bootstrap, tercile dashboard, net-edge/cost model, fade arrows, fade-framed alerts, the `os` oscillator plot. This tool renders state only.

## 10. Open defaults / notes
- Flow a-priori windows (funding 14d z, OI 12-bar Δ, liq p90) are fixed, not swept — consistent with the project's anti-overfitting stance, though this is a display tool not a validated signal.
- Anchor default Regression/50; the trader speeds it up for shallower, more frequent pullback marks.
- "Flush" regime suppresses directional arrows (too violent for a re-entry read); it surfaces only as a panel flag + tint.
