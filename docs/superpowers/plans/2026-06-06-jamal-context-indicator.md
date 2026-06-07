# Jamal Context Indicator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `jamal-context.pine` — a Pine v6 discretionary context tool that paints regime + pullback/overstretch taxonomy + derivative-flow state, reusing validated engines from the killed research scripts.

**Architecture:** Three mechanism modules in one `overlay=true` study — Structure/Regime (trigger's context), Overshoot (the trigger), Derivative flow (conviction) — feeding one composition/render layer (taxonomy marks + tint + flow panel). Built in 5 chart-test-gated increments (v0.1→v1.0); no research machinery ported.

**Tech Stack:** Pine Script v6; `TradingView/Request/3` library (OI/funding/liquidations); TradingView MCP for compile/deploy/verify (`pine_set_source`, `pine_smart_compile`, `chart_manage_indicator`, `data_get_pine_tables`, `data_get_study_values`, `capture_screenshot`).

**Spec:** `docs/superpowers/specs/2026-06-06-jamal-context-indicator-design.md`
**Source files to lift from (do NOT modify them):** `overshoot-regime-os-core-v1.pine` (regime+overshoot+panel), `jamal-phase2.pine`/`jamal-phase3.pine` (flow imports), `p2_liq_gate.pine` (liq-flush + staleness logic).

---

## Dev-loop convention (every task uses this — the "test" for Pine)

There is no unit-test runner. Each task's verification IS the chart-acceptance gate:
1. Write the full source locally to `jamal-context.pine` (Write/Edit).
2. Inject + compile: `mcp__tradingview__pine_set_source` then `mcp__tradingview__pine_smart_compile`. **Expect:** `has_errors: false`. If errors, read `pine_get_errors`, fix, recompile.
3. Deploy fresh (legend cache busts only on remove+re-add): `mcp__tradingview__chart_get_state` → if a prior "Jamal Context" study is present, `chart_manage_indicator` action=remove with its entity_id → click "Add to chart" (`ui_find_element` query "Add to chart" → `ui_mouse_click` at the button center, ~x1134,y79) → confirm via `chart_get_state`.
4. Verify the acceptance observations (per task) with `data_get_pine_tables` / `data_get_study_values` + `capture_screenshot`.
5. CHANGELOG.md entry (code change / rationale / tested / result) + bump the on-chart `indicator()` title version + `git add … && git commit && git push` (Co-Authored-By trailer, branch = main per repo convention).

**Standing rule (do NOT violate):** no `strategy()`, no score, no BUY/SELL/win-rate/edge text; condition-present `alertcondition` only; only **Pullback** is a directional arrow.

---

## File Structure

- **Create:** `jamal-context.pine` — the entire indicator (single file, grows per increment). One responsibility: render market-state context. Sections in declaration order: header comment → `indicator()` → inputs (grouped) → Mechanism A (regime) → Mechanism B (overshoot) → Mechanism C (flow) → composition (classify) → render (tint, marks, anchor, panel).
- **Modify:** `CHANGELOG.md` — append a versioned entry per increment.
- **Modify:** `docs/superpowers/plans/2026-06-06-jamal-context-indicator.md` — tick checkboxes as tasks complete.

---

## Task 1 — v0.1: Regime + tint + label (Mechanism A)

> **REVISED to v0.1.1 (slope-led) after empirical review.** Mechanism A is a **fork + modify** of Phase 1, NOT a verbatim port: trend = persistent signed 50-bar slope (signed Schmitt enter ±0.05 / hold ±0.02 + dwell 3); **ER demoted to cascade-filter only**. ER-gated trend under-shaded real rallies (flickered on pullbacks → would suppress with-trend Pullback arrows). The authoritative engine is in `jamal-context.pine` and §2A of the spec; the code block below is the original ER-gated draft, kept for history. Acceptance now: rally holds solid green + chop stays gray + reversal still flips (all PASS on BTC 4h Feb–Jun).

**Files:** Create `jamal-context.pine`; Modify `CHANGELOG.md`.

- [ ] **Step 1: Write the full v0.1 source** to `jamal-context.pine`:

```pine
//@version=6
// JAMAL CONTEXT — discretionary regime + pullback + flow context tool.
// DISCRETIONARY CONTEXT, UNVALIDATED, NOT A BACKTESTED EDGE. Displays market STATE; the trader decides.
// Brightness (later increments) = untuned co-occurrence COUNT, never a score; more aligned != higher odds.
// v0.1 = Mechanism A only: Structure/Regime (tint + glanceable label). Regime engine reused verbatim
// from overshoot-regime-os-core-v1.pine (ER Schmitt + signed-slope ATR deadband + cascade + dwell).
indicator("Jamal Context v0.1 (regime)", "JmlCtx", overlay=false)  // own pane (regime ribbon); price-pane marks/anchor via force_overlay in later increments

// ===== Inputs =====
er_len           = input.int(20,    "Efficiency Ratio length", minval=5, group="Regime")
er_trend         = input.float(0.30, "ER trend ENTER", minval=0.05, maxval=0.95, step=0.01, group="Regime")
er_exit          = input.float(0.18, "ER trend EXIT",  minval=0.01, maxval=0.95, step=0.01, group="Regime")
regime_min_dwell = input.int(3,     "Regime min dwell (bars)", minval=1, group="Regime")
vol_pct_len      = input.int(250,   "Vol percentile lookback", minval=50, group="Regime")
vol_hi           = input.float(80,  "Vol-hot percentile (cascade)", minval=50, maxval=99, step=1, group="Regime")
er_cascade       = input.float(0.45, "ER cascade threshold", minval=0.3, maxval=0.99, step=0.01, group="Regime")
vsma_len         = input.int(20,    "Volume MA length (surge)", minval=5, group="Regime")
vsurge_mult      = input.float(1.8, "Volume surge multiple", minval=1.0, step=0.1, group="Regime")
slope_dead_atr   = input.float(0.05, "Trend slope deadband (ATR/bar)", minval=0.0, step=0.01, group="Regime")
reg_len          = input.int(50,    "Anchor length (slope)", minval=5, group="Regime")
k_decontam       = input.int(3,     "Decontaminate recent (bars)", minval=0, group="Regime")
atr_len          = input.int(20,    "ATR length", minval=2, group="Regime")
show_tint        = input.bool(true, "Tint background by regime", group="Display")
show_panel       = input.bool(true, "Show state panel", group="Display")

// ===== Mechanism A: Structure / Regime =====
atr      = ta.atr(atr_len)
safe_atr = atr > 0 ? atr : na
atr_os   = safe_atr[k_decontam]

reg_lr_end  = ta.linreg(close[k_decontam], reg_len, 0)
reg_lr_prev = ta.linreg(close[k_decontam], reg_len, 1)
slope_pb    = reg_lr_end - reg_lr_prev
slope_atr   = (na(atr_os) or atr_os == 0) ? na : slope_pb / atr_os
dir_up      = not na(slope_atr) and slope_atr >  slope_dead_atr
dir_dn      = not na(slope_atr) and slope_atr < -slope_dead_atr

er_den = math.sum(math.abs(close - close[1]), er_len)
er     = er_den > 0 ? math.abs(close - close[er_len]) / er_den : na

atr_pct   = ta.percentrank(atr, vol_pct_len)
vol_ma    = ta.sma(volume, vsma_len)
vol_surge = not na(vol_ma) and vol_ma > 0 and volume > vol_ma * vsurge_mult

float er_exit_use = math.min(er_exit, er_trend)
var bool trend_on = false
trend_on := na(er) ? trend_on : (trend_on ? er >= er_exit_use : er >= er_trend)

cascade = not na(er) and er >= er_cascade and not na(atr_pct) and atr_pct >= vol_hi and vol_surge
int desired = cascade ? (dir_dn ? -2 : 2) : (trend_on and dir_up) ? 1 : (trend_on and dir_dn) ? -1 : 0

var int regime = 0
var int regime_dwell = 0
regime_dwell += 1
if cascade
    regime := desired
    regime_dwell := 0
else if desired != regime and regime_dwell >= regime_min_dwell
    regime := desired
    regime_dwell := 0

// ===== Render: own-pane regime ribbon (tint + state line) + label =====
color reg_col = regime == 1 ? #00C853 : regime == -1 ? #FF1744 : math.abs(regime) == 2 ? #FF6D00 : color.gray
color reg_bg = na
if show_tint
    reg_bg := regime == 1 ? color.new(#00C853, 86) : regime == -1 ? color.new(#FF1744, 86) : (math.abs(regime) == 2 ? color.new(#FF6D00, 78) : color.new(color.gray, 92))
bgcolor(reg_bg, title="Regime tint")
plot(regime, "Regime state", color=reg_col, style=plot.style_stepline, linewidth=2)
hline(0,  "0",  color=color.new(color.gray, 70))
hline(2,  "Flush+",  color=color.new(color.gray, 85))
hline(-2, "Flush-",  color=color.new(color.gray, 85))

string reg_label = regime == 1 ? "Trend-up" : regime == -1 ? "Trend-down" : math.abs(regime) == 2 ? "Flush" : "Range"
color  reg_bgc   = regime == 1 ? color.new(#00C853, 0) : regime == -1 ? color.new(#FF1744, 0) : math.abs(regime) == 2 ? color.new(#FF6D00, 0) : color.new(color.gray, 40)

var table panel = table.new(position.top_right, 2, 3, border_color=color.new(color.gray,50), border_width=1, frame_color=color.new(color.gray,50), frame_width=1)
if show_panel and barstate.islast
    string forming = barstate.isconfirmed ? " (confirmed)" : " (forming)"
    table.cell(panel, 0, 0, "Regime", text_color=color.silver, text_size=size.tiny)
    table.cell(panel, 1, 0, reg_label + forming, text_color=color.white, bgcolor=reg_bgc, text_size=size.tiny)
    table.cell(panel, 0, 1, "ER", text_color=color.silver, text_size=size.tiny)
    table.cell(panel, 1, 1, str.tostring(er, "#.00"), text_color=color.white, text_size=size.tiny)
    table.cell(panel, 0, 2, "Vol pctile", text_color=color.silver, text_size=size.tiny)
    table.cell(panel, 1, 2, str.tostring(atr_pct, "#.0") + " %", text_color=color.white, text_size=size.tiny)

// data-window readouts for cross-check vs Phase 1
plot(er,      "ER",      display=display.data_window)
plot(atr_pct, "atr_pct", display=display.data_window)
```
**Note:** `overlay=false` → own pane. Keep `force_overlay=true` on the v0.2 marks and the v0.3 anchor `plot` so they land on the price candles; everything else (regime ribbon, tint, panel) stays in the indicator's own pane.

- [ ] **Step 2: Compile.** `pine_set_source` (paste the above) → `pine_smart_compile`. **Expect:** `has_errors: false`. On error, `pine_get_errors` → fix → recompile.

- [ ] **Step 3: Deploy on BTC 1h.** `chart_set_symbol` BINANCE:BTCUSDT.P, `chart_set_timeframe` 60. Remove any prior "Jamal Context" study, then Add to chart. Confirm via `chart_get_state` that "Jamal Context v0.1 (regime)" is present.

- [ ] **Step 4: Verify acceptance — regime matches Phase 1 + label/tint correct.** `data_get_study_values` for the v0.1 study (regime/ER/atr_pct). Cross-check the live `regime` value and tint against the known Phase 1 engine behavior on the same bars (same inputs → identical regime; the engine code is copied verbatim). `capture_screenshot` region "chart". **Expect:** tint green in up-trends, red in down-trends, gray in range, orange on cascade; panel label reads Trend-up/Trend-down/Range/**Flush** accordingly. Switch `chart_set_timeframe` 240 and re-check. **Expect:** Flush ("orange") appears on at least one historical violent bar.

- [ ] **Step 5: CHANGELOG + commit.** Append to `CHANGELOG.md` a "Jamal Context v0.1" entry (code: regime engine port + tint + label; rationale: Mechanism A foundation; tested: BTC 1h/4h regime matches Phase 1, label/tint correct, Flush on cascade; result: PASS). Then:

```bash
git add jamal-context.pine CHANGELOG.md docs/superpowers/plans/2026-06-06-jamal-context-indicator.md
git commit -m "Jamal Context v0.1: regime engine + tint + label (Mechanism A)"
git push
```

---

## Task 2 — v0.2: Overshoot + taxonomy marks + liq-flush suppression (Mechanism B + classify + liq slice of C)

**Files:** Modify `jamal-context.pine`; Modify `CHANGELOG.md`.

Bump title to `indicator("Jamal Context v0.2 (taxonomy)", "JmlCtx", overlay=true)`. Add `import TradingView/Request/3 as r` directly under the `indicator()` line.

- [ ] **Step 1: Add Overshoot inputs** to the Inputs section (after the Regime group):

```pine
os_anchor  = input.string("Regression", "Overshoot anchor", options=["Regression","SMA","EMA"], group="Overshoot")
os_reg_len = input.int(50,  "Overshoot anchor length", minval=5, group="Overshoot")
pct_len    = input.int(250, "Overshoot percentile lookback", minval=30, group="Overshoot")
pct_thresh = input.float(90,"Overshoot percentile threshold (%)", minval=50, maxval=99.9, step=0.5, group="Overshoot")
os_min_atr = input.float(1.0,"Min overshoot (ATR)", minval=0.0, step=0.1, group="Overshoot")
liq_pct_len = input.int(250,"Liq-flush percentile lookback", minval=30, group="Flow")
liq_pct     = input.float(90,"Liq-flush percentile (%)", minval=50, maxval=99.9, step=0.5, group="Flow")
show_marks  = input.bool(true,"Show taxonomy marks", group="Display")
show_prov   = input.bool(true,"Show provisional (forming-bar) marks", group="Display")
```

- [ ] **Step 2: Add Mechanism B (overshoot engine)** after the regime section. Pooled-percentile basis (drop Phase 1's by-direction mode — unneeded for a context tool):

```pine
// ===== Mechanism B: Overshoot =====
f_decon(b, k) =>
    e = b[k]
    p = b[k + 1]
    e + (e - p) * k
reg_sma = f_decon(ta.sma(close, os_reg_len), k_decontam)
reg_ema = f_decon(ta.ema(close, os_reg_len), k_decontam)
reg_lr2 = ta.linreg(close[k_decontam], os_reg_len, 0) + (ta.linreg(close[k_decontam], os_reg_len, 0) - ta.linreg(close[k_decontam], os_reg_len, 1)) * k_decontam
anchor  = os_anchor == "SMA" ? reg_sma : os_anchor == "EMA" ? reg_ema : reg_lr2
os = (na(atr_os) or na(anchor)) ? na : (close - anchor) / atr_os
os_p_hi = ta.percentile_linear_interpolation(os, pct_len, pct_thresh)[k_decontam]
os_p_lo = ta.percentile_linear_interpolation(os, pct_len, 100 - pct_thresh)[k_decontam]
trig_up = math.max(os_min_atr,  nz(os_p_hi,  os_min_atr))
trig_dn = math.min(-os_min_atr, nz(os_p_lo, -os_min_atr))
os_ext_up = not na(os) and os >= trig_up
os_ext_dn = not na(os) and os <= trig_dn
```

- [ ] **Step 3: Add the liq-flush slice of Mechanism C** (only the flush flag is needed now; full panel later):

```pine
// ===== Mechanism C (slice): liquidation flush flag =====
liq_buy  = r.cryptoDerivativeMetric(metricName="Liquidations Buy",  symbol=syminfo.tickerid, timeframe=timeframe.period)
liq_sell = r.cryptoDerivativeMetric(metricName="Liquidations Sell", symbol=syminfo.tickerid, timeframe=timeframe.period)
liq_mag  = (na(liq_buy)?0.0:liq_buy) + (na(liq_sell)?0.0:liq_sell)
liq_p    = ta.percentile_linear_interpolation(liq_mag, liq_pct_len, liq_pct)
liq_flush = liq_mag > 0 and not na(liq_p) and liq_mag >= liq_p
```

- [ ] **Step 4: Add the composition/classify layer** (overshoot × regime × violence → exactly one type):

```pine
// ===== Composition: classify the overshoot event =====
in_trend = math.abs(regime) == 1
with_trend = (regime == 1 and os_ext_up) or (regime == -1 and os_ext_dn)
ctr_trend  = (regime == 1 and os_ext_dn) or (regime == -1 and os_ext_up)
violent    = liq_flush or math.abs(regime) == 2   // liq-flush is the binding V-flush detector (ER-cascade is blind)
is_blowoff = in_trend and with_trend
is_pullbk  = in_trend and ctr_trend and not violent
is_capit   = in_trend and ctr_trend and violent
is_spike   = regime == 0 and (os_ext_up or os_ext_dn)
// Pullback direction = WITH the trend: long in up-trend, short in down-trend
pull_long  = is_pullbk and regime == 1
pull_short = is_pullbk and regime == -1
committed  = barstate.isconfirmed
```

- [ ] **Step 5: Add the mark render layer** (only Pullback is directional; flat intensity for now; provisional greyed):

```pine
// ===== Render: taxonomy marks (only Pullback is directional; Blowoff/Capitulation/Spike are caution) =====
c_grey = color.new(color.gray, 55)
c_pull = color.new(#00C853, 0)
c_pulS = color.new(#FF1744, 0)
c_blow = color.new(#FFB300, 0)
c_capit= color.new(#D500F9, 0)
c_spike= color.new(color.gray, 20)
mk(cond, prov_ok) => show_marks and (committed ? cond : (show_prov and prov_ok and cond))
col(cond, base) => committed ? base : c_grey
// Pullback (directional)
plotshape(mk(pull_long, true)  ? low  : na, "Pullback long",  shape.triangleup,   location.belowbar, color=col(pull_long, c_pull),  size=size.small, force_overlay=true)
plotshape(mk(pull_short, true) ? high : na, "Pullback short", shape.triangledown, location.abovebar, color=col(pull_short, c_pulS), size=size.small, force_overlay=true)
// Blowoff (with-trend climax caution diamond)
plotshape(mk(is_blowoff and regime == 1, true)  ? high : na, "Blowoff up",   shape.diamond, location.abovebar, color=col(is_blowoff, c_blow), size=size.tiny, force_overlay=true)
plotshape(mk(is_blowoff and regime == -1, true) ? low  : na, "Blowoff down", shape.diamond, location.belowbar, color=col(is_blowoff, c_blow), size=size.tiny, force_overlay=true)
// Capitulation (violent counter-trend caution diamond)
plotshape(mk(is_capit and regime == 1, true)  ? low  : na, "Capitulation up-trend",   shape.diamond, location.belowbar, color=col(is_capit, c_capit), size=size.tiny, force_overlay=true)
plotshape(mk(is_capit and regime == -1, true) ? high : na, "Capitulation down-trend", shape.diamond, location.abovebar, color=col(is_capit, c_capit), size=size.tiny, force_overlay=true)
// Spike (range extreme dot)
plotshape(mk(is_spike and os_ext_up, true) ? high : na, "Spike up", shape.circle, location.abovebar, color=col(is_spike, c_spike), size=size.tiny, force_overlay=true)
plotshape(mk(is_spike and os_ext_dn, true) ? low  : na, "Spike down", shape.circle, location.belowbar, color=col(is_spike, c_spike), size=size.tiny, force_overlay=true)
// Pullback DEPTH (|os| ATR) — faint label on the MOST RECENT confirmed pullback only (minimal ink)
var label pull_lbl = na
if committed and (pull_long or pull_short)
    label.delete(pull_lbl)
    pull_lbl := label.new(bar_index, pull_long ? low : high, "PB " + str.tostring(math.abs(os), "#.0") + " ATR", style=pull_long ? label.style_label_up : label.style_label_down, color=color.new(color.gray, 70), textcolor=color.white, size=size.tiny, force_overlay=true)
// readouts
plot(os, "os", display=display.data_window)
plot(liq_flush ? 1 : 0, "liq_flush", display=display.data_window)
```

- [ ] **Step 6: Compile.** `pine_set_source` (full file) → `pine_smart_compile`. **Expect:** `has_errors: false`. Common gotcha: declare each `var` on its own line (Pine multi-declare bug). On error → `pine_get_errors` → fix.

- [ ] **Step 7: Deploy + verify taxonomy (bull & bear).** Remove old study, Add to chart. On BTC 1h: `capture_screenshot` "chart". **Expect:** green triangle-up below bar on counter-trend dips inside an up-trend; red triangle-down above bar on counter-trend rallies in a down-trend; amber diamonds on with-trend climaxes; gray dots at range extremes; no marks in Flush regime. Scroll to an up-trend and a down-trend stretch (`chart_scroll_to_date`) to confirm both.

- [ ] **Step 8: Verify the flush-suppression gate (the money case).** Find a known liquidation-flush bar (large down-flush in an up-trend). `data_get_study_values` to confirm `liq_flush==1` on that bar; `capture_screenshot`. **Expect:** that bar shows a **fuchsia Capitulation diamond, NOT a green Pullback arrow** — in both a bull example and a bear example. This is the acceptance gate; if a Pullback arrow appears on a `liq_flush==1` counter-trend bar, the `violent` gate is wrong — fix before proceeding.

- [ ] **Step 9: Verify non-repaint.** Confirm forming-bar marks render grey and confirmed marks render in color (inspect the last, still-forming bar vs history in the screenshot). **Expect:** no historical bar shows a colored mark that depends on future bars.

- [ ] **Step 10: CHANGELOG + commit.** Append "Jamal Context v0.2" entry (code: overshoot engine + liq-flush + classify + marks; rationale: taxonomy with the §3.1 violence gate so the directional arrow never fires into a flush; tested: bull&bear taxonomy + known liq-flush bar shows Capitulation not Pullback + non-repaint; result: PASS).

```bash
git add jamal-context.pine CHANGELOG.md docs/superpowers/plans/2026-06-06-jamal-context-indicator.md
git commit -m "Jamal Context v0.2: overshoot taxonomy marks + liq-flush suppression"
git push
```

---

## Task 3 — v0.3: Flow panel + anchor line + OI continuity (rest of Mechanism C)

**Files:** Modify `jamal-context.pine`; Modify `CHANGELOG.md`. Bump title to `v0.3 (flow)`.

- [ ] **Step 1: Add Flow inputs** to the Flow group:

```pine
funding_z_days = input.float(14, "Funding z-score window (DAYS, a-priori)", minval=1, group="Flow")
oi_chg_bars    = input.int(12,  "OI change window (bars)", minval=2, group="Flow")
oi_stale_run   = input.int(5,   "OI stale: max identical-OI bars before suppress", minval=2, group="Flow")
fund_extreme_z = input.float(1.5,"Funding 'extreme' |z| band", minval=0.1, step=0.1, group="Flow")
show_anchor    = input.bool(true,"Draw overshoot anchor line", group="Display")
```

- [ ] **Step 2: Add funding z + OI build/cover with continuity gate** (after the liq slice):

```pine
// ===== Mechanism C: funding z + OI build/cover (with continuity gate) =====
funding = r.cryptoDerivativeMetric(metricName="Funding Rate", symbol=syminfo.tickerid, timeframe=timeframe.period)
fz_len  = math.max(2, math.round(funding_z_days * 86400 / timeframe.in_seconds()))
f_mean  = ta.sma(funding, fz_len)
f_sd    = ta.stdev(funding, fz_len)
fz      = (not na(funding) and not na(f_sd) and f_sd > 0) ? (funding - f_mean) / f_sd : na
[oio, oih, oil, oi_close, oirise] = r.openInterestCrypto(symbol=syminfo.tickerid, timeframe=timeframe.period)
// OI continuity: count run of identical OI -> stale (forward-filled)
var int oi_run = 0
oi_run := (not na(oi_close) and oi_close == oi_close[1]) ? oi_run + 1 : 0
oi_stale = oi_run >= oi_stale_run
oi_chg   = (not na(oi_close) and not na(oi_close[oi_chg_bars]) and oi_close[oi_chg_bars] > 0) ? oi_close/oi_close[oi_chg_bars] - 1.0 : na
price_dir = math.sign(close - close[oi_chg_bars])
oi_building = not oi_stale and not na(oi_chg) and oi_chg > 0
// build/cover read (suppressed when stale): fresh leverage = OI rising into the move
string oi_read = oi_stale ? "stale" : na(oi_chg) ? "n/a" : (oi_chg > 0 ? (price_dir != 0 ? "fresh lev" : "build") : "cover/hollow")
```

- [ ] **Step 3: Draw the anchor line + extend the panel** with the flow + depth rows. Change `table.new(... 2, 3 ...)` to `2, 7` and append rows; add an anchor `plot`:

```pine
plot(show_anchor ? anchor : na, "Anchor", color=color.new(#BB86FC, 0), linewidth=1, force_overlay=true)
```
Add inside `if show_panel and barstate.islast` after the existing 3 rows (and change the table to 7 rows):
```pine
    table.cell(panel, 0, 3, "Funding z", text_color=color.silver, text_size=size.tiny)
    table.cell(panel, 1, 3, na(fz) ? "n/a" : str.tostring(fz, "#.00") + (math.abs(fz) >= fund_extreme_z ? " EXT" : ""), text_color=color.white, text_size=size.tiny)
    table.cell(panel, 0, 4, "OI", text_color=color.silver, text_size=size.tiny)
    table.cell(panel, 1, 4, oi_read, text_color=color.white, text_size=size.tiny)
    table.cell(panel, 0, 5, "Liq flush", text_color=color.silver, text_size=size.tiny)
    table.cell(panel, 1, 5, liq_flush ? "FLUSH" : "-", text_color=color.white, bgcolor=liq_flush ? color.new(#D500F9, 0) : color.new(color.gray, 40), text_size=size.tiny)
    table.cell(panel, 0, 6, "Pullback depth", text_color=color.silver, text_size=size.tiny)
    table.cell(panel, 1, 6, is_pullbk ? str.tostring(math.abs(os), "#.0") + " ATR" : "-", text_color=color.white, text_size=size.tiny)
```
Also update the header comment to log: "Flow: Binance-only (venue caveat); non-repainting."

- [ ] **Step 4: Compile.** `pine_set_source` → `pine_smart_compile`. **Expect:** `has_errors: false`.

- [ ] **Step 5: Deploy + verify flow readouts.** Remove/re-add on BTC 1h. `data_get_pine_tables` study_filter "Jamal Context". **Expect:** Funding z a small number (≈ −3..+3) with "EXT" only when |z|≥1.5; OI row reads "fresh lev"/"cover/hollow"/"stale"/"n/a" sensibly; Liq flush row flips to "FLUSH" on flush bars. Anchor line visible on price. `capture_screenshot`.

- [ ] **Step 6: Verify OI continuity gate.** If BTC OI has no stale runs in-window, temporarily lower `oi_stale_run` via `indicator_set_inputs` to force a "stale" read on a flat OI stretch and confirm the OI row shows "stale" (and that `oi_building` would be false). Restore the input. **Expect:** stale OI suppresses the build/cover read.

- [ ] **Step 7: Verify non-repaint of flow.** Confirm funding/OI/liq values are lagged (sampled from confirmed bars; the library returns lagged HTF/derivative values). **Expect:** the historical panel values don't change when scrolling.

- [ ] **Step 8: CHANGELOG + commit.**

```bash
git add jamal-context.pine CHANGELOG.md docs/superpowers/plans/2026-06-06-jamal-context-indicator.md
git commit -m "Jamal Context v0.3: flow panel (funding-z/OI build-cover/liq-flush) + anchor + OI continuity gate"
git push
```

---

## Task 4 — v0.4: Conviction wiring (flow → mark brightness)

**Files:** Modify `jamal-context.pine`; Modify `CHANGELOG.md`. Bump title to `v0.4 (conviction)`.

- [ ] **Step 1: Compute per-type co-occurrence counts** (insert after the classify layer). Counts are 0..2; never weighted:

```pine
// ===== Conviction: co-occurrence COUNT (never a weighted score) =====
fund_extreme = not na(fz) and math.abs(fz) >= fund_extreme_z
fund_calm    = not na(fz) and math.abs(fz) <  fund_extreme_z
oi_extreme   = not oi_stale and not na(oi_chg) and (oi_chg >= ta.percentile_linear_interpolation(oi_chg, 250, 90) or oi_chg <= ta.percentile_linear_interpolation(oi_chg, 250, 10))
pull_conv = (oi_building ? 1 : 0) + (fund_calm ? 1 : 0)        // 0..2
blow_conv = (fund_extreme ? 1 : 0) + (liq_flush ? 1 : 0)       // 0..2
capi_conv = (fund_extreme ? 1 : 0)                             // 0..1
spik_conv = (fund_extreme ? 1 : 0) + (oi_extreme ? 1 : 0)      // 0..2
// map count -> transparency (more aligned = more opaque/brighter)
f_tr(cnt, maxc) => 70 - math.round(50.0 * cnt / maxc)          // 70%(faint)..20%(bright)
```

- [ ] **Step 2: Replace flat mark colors with brightness-by-conviction.** Change the render `col(...)` usage so confirmed marks use transparency from the count (provisional stays grey):

```pine
col2(cond, hex, cnt, maxc) => committed ? color.new(hex, f_tr(cnt, maxc)) : c_grey
```
Update each Pullback/Blowoff/Capitulation/Spike `plotshape` to use `col2` with its `*_conv` and max (Pullback max 2, Blowoff max 2, Capitulation max 1, Spike max 2), e.g.:
```pine
plotshape(mk(pull_long, true) ? low : na, "Pullback long", shape.triangleup, location.belowbar, color=col2(pull_long, #00C853, pull_conv, 2), size=size.small, force_overlay=true)
```
(Apply the analogous `col2(...)` to all eight `plotshape` mark calls; hex per type: Pullback long #00C853 / short #FF1744, Blowoff #FFB300, Capitulation #D500F9, Spike #9E9E9E.)

- [ ] **Step 3: Add conviction to the panel** (one row, transparent count, with the standing reminder as a tooltip-free label):
```pine
    table.cell(panel, 0, 7, "Conv (count)", text_color=color.silver, text_size=size.tiny)
    table.cell(panel, 1, 7, (is_pullbk ? "pull " + str.tostring(pull_conv) : is_blowoff ? "blow " + str.tostring(blow_conv) : is_capit ? "capit " + str.tostring(capi_conv) : is_spike ? "spike " + str.tostring(spik_conv) : "-"), text_color=color.white, text_size=size.tiny)
```
(Change the panel table to `2, 8`.)

- [ ] **Step 4: Compile.** `pine_set_source` → `pine_smart_compile`. **Expect:** `has_errors: false`.

- [ ] **Step 5: Deploy + verify brightness = count.** Remove/re-add. `capture_screenshot` + `data_get_pine_tables`. **Expect:** a Pullback with OI building AND funding calm renders brightest (count 2); with neither, faintest (count 0); Blowoff brightens with funding-extreme + liq-flush. Spot-check a sample bar's panel "Conv (count)" against the visible brightness. **Confirm it is a count, not a score** (no decimals, no weights; max per type as specified).

- [ ] **Step 6: CHANGELOG + commit.**

```bash
git add jamal-context.pine CHANGELOG.md docs/superpowers/plans/2026-06-06-jamal-context-indicator.md
git commit -m "Jamal Context v0.4: conviction wiring (flow co-occurrence -> mark brightness)"
git push
```

---

## Task 5 — v1.0: Guardrails + polish

**Files:** Modify `jamal-context.pine`; Modify `CHANGELOG.md`. Bump title to `v1.0`.

- [ ] **Step 1: Header disclaimer + framing audit.** Ensure the top comment states verbatim: *"Discretionary context, UNVALIDATED, not a backtested edge. Brightness = untuned co-occurrence count, not probability. Flow data Binance-only (venue caveat), non-repainting."* Grep the file for forbidden tokens: `strategy(`, `BUY`, `SELL`, `win`, `edge`, `signal`, `entry` (in user-facing strings). Reword any to state-language ("with-trend pullback condition", "caution", "context").

- [ ] **Step 2: Condition-present alerts (not signals).** Add neutral `alertcondition`s, confirmed-bar only:
```pine
alertcondition(committed and (pull_long or pull_short), "Pullback condition", "With-trend pullback condition present")
alertcondition(committed and is_capit, "Capitulation condition", "Counter-trend flush present - elevated reversion risk both directions")
```

- [ ] **Step 3: Minimal-ink audit.** Confirm only: tint + one anchor line + taxonomy marks + one panel are drawn. Remove any leftover data-window debug `plot`s except those genuinely useful (keep regime/os/liq_flush if helpful; drop the rest). No oscillator.

- [ ] **Step 4: Input grouping + version.** Confirm inputs grouped Regime / Overshoot / Flow / Display; title is `indicator("Jamal Context v1.0", "JmlCtx", overlay=true)`.

- [ ] **Step 5: Compile + full visual review.** `pine_smart_compile` (expect clean). Remove/re-add. `capture_screenshot` "chart" on BTC 1h and 4h. **Expect:** clean, legible, minimal-ink context display; taxonomy + tint + panel + anchor all correct; no edge/score/command language anywhere on screen.

- [ ] **Step 6: CHANGELOG + commit (v1.0).**

```bash
git add jamal-context.pine CHANGELOG.md docs/superpowers/plans/2026-06-06-jamal-context-indicator.md
git commit -m "Jamal Context v1.0: guardrails, disclaimer, condition-present alerts, minimal-ink polish"
git push
```

---

## Notes for the implementer
- **Legend cache:** in-place recompile does NOT refresh the on-chart study; always remove + re-add to see changes (and to bust the legend). The bumped title version is your visual confirmation the new build landed.
- **Pine `var` gotcha:** declare each persistent `var` on its own line — `var int a = 0, b = 0` only persists the first variable (silent bug).
- **Symbols for spot-checks:** BINANCE:BTCUSDT.P (and TAOUSDT.P / HYPEUSDT.P if cross-checking alts). Flow data is Binance-only by design.
- **Do NOT** touch `overshoot-regime-os-core-v1.pine`, `jamal-phase2.pine`, `jamal-phase3.pine` — they are the research record.
