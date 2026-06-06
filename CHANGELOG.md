# Jamal Phase 1 — Changelog & Test Log

Indicator: **Jamal Phase 1** (Pine v6, `overlay=false`). Canonical source in this repo: [overshoot-regime-os-core-v1.pine](overshoot-regime-os-core-v1.pine). Saved TradingView script name: "Jamal's Mean Reversion".

**Hypothesis under test (Phase 1, veto-only):** does conditioning fades on regime remove losing fades? A veto-only gate can't make a bad fader good — it can only stop it bleeding in trends. Headline metric: Taken-vs-Vetoed gap per side in the scout. **Gate-0 precondition:** Taken must beat baseline at all.

**Conventions**
- On-chart `indicator()` title carries a version tag (`v2`, `v3`, …), bumped on every substantive push so a recompile is visually confirmable. `shorttitle` ≤ 10 chars.
- Dev loop: edit local .pine → `pine_check` (server compile) → `pine_set_source` + `pine_smart_compile` on live TradingView Desktop → verify. **Legend cache busts only on remove + re-add of the study**, not in-place recompile.
- Input IDs are positional (`in_0`, `in_1`, … in declaration order) — used when setting inputs via MCP.
- This log records, per version: **Code changes / Rationale / Tests run / Results / Status.**

---

## v1 — "Jamal Phase 1" (initial)
**Date:** 2026-06-05 · **On-chart:** "Jamal Phase 1"
**Code changes**
- First build. Overshoot engine (decontaminated regression/SMA/EMA anchor, lagged-ATR normalization, dual-gate extremity = percentile tail AND absolute ATR floor, arm/fire reversion latch).
- Regime classifier (veto-only): persistence axis = ER `AND` lag-1 autocorrelation (`ac1`, Pearson) `AND` variance ratio (`vr`); direction = projected linreg slope w/ ATR deadband (`slope_dead_atr` default 0.02); vol state = ATR percentile + volume surge → cascade. Inputs incl. `use_vr`, `ac_min`.
- `regime` assigned by plain if/else each bar (no persistence/dwell).
- Scout: Taken vs Vetoed (single Vetoed bucket/side), arrays for MFE/MAE/ret + baseline; dashboard cols MFE/MAE/Edge/Path/n; helpers `f_mean`, `f_edge_val`, `f_net_edge_val`, `f_num_col`.
**Rationale:** establish the veto-only baseline.
**Tests run:** `pine_check` server compile; placed on BINANCE:BTCUSDT.P 1h; `data_get_study_values` sanity.
**Results:** Compiles 0 errors / 0 warnings. All series compute. **Issue:** regime segments extremely short/sparse.
**Status:** superseded by v2.

## v2 — Regime engine rework (drift-blindness fix)
**Date:** 2026-06-05 · **On-chart:** "Jamal Phase 1 v2" (shorttitle "Jamal P1v2")
**Code changes**
- **Removed `ac1` + `vr` from the trend gate.** Deleted inputs `use_vr` and `ac_min`. `ac1`/`vr` retained as Data-Window READOUT plots only.
- Added input `er_exit` (`in_3`) and `regime_min_dwell` (`in_4`, default 3). Re-indexed downstream input IDs.
- Trend strength now an **ER Schmitt trigger**: `var bool trend_on`, enter `er_trend` / exit `er_exit` (clamped `er_exit_use = min(er_exit, er_trend)`).
- New `int desired` (instantaneous label) + **signed-regime state machine**: `var int regime`, `var int regime_dwell`; cascade = priority interrupt (instant, resets dwell); all other transitions wait `regime_min_dwell`.
- `slope_dead_atr` default **0.02 → 0.05** (now the binding directional gate).
**Rationale:** `ac1` (Pearson) and `vr` are mean-centered → blind to drift; a clean drift trend has `ac1`≈0, `vr`≈1, so the AND-confirmers failed in exactly the directional moves the veto targets and flickered around thresholds → fragmented regime.
**Tests run:** `pine_check`; pushed + `pine_smart_compile`.
**Results:** Compiles 0/0. (Default thresholds still gave sparse shading → v3.)
**Status:** superseded by v3 (thresholds).

## v3 — ER threshold recalibration (absolute, not percentile)
**Date:** 2026-06-05 · **On-chart:** "Jamal Phase 1 v3" (shorttitle "Jamal P1v3")
**Code changes**
- `er_trend` (`in_2`) default **0.40 → 0.30**; `er_exit` (`in_3`) **0.25 → 0.18**; `er_cascade` (`in_10`) **0.60 → 0.45**. Slope deadband unchanged (0.05).
- Tooltips/header updated to state the threshold is **ABSOLUTE by design** (ER dimensionless 0..1; percentile would pin firing rate to a constant and reintroduce distribution-shift flicker — the `atr_pct` ranking analogy does NOT transfer to ER).
**Rationale:** 0.40 ER enter miscalibrated for 1h crypto.
**Tests run:**
- Offline ER(20) distribution over 301 1h BTC bars via [er_hist.py](er_hist.py).
- Replay sanity pass (BTC 1h): down-leg, post-leg hold, consolidation, flush bar.
**Results:**
- ER histogram **unimodal** (peak 0.20–0.25, median 0.235, mean 0.263, p90 0.502, max 0.738) → no natural trend/range boundary; threshold is a judgment-set firing-rate dial.
- Schmitt `trend_on` fraction (ER gate only): old 0.40/0.25 = **31.7%** → new 0.30/0.18 = **47.7%**.
- Replay: down-leg (06-04) ER 0.4 → Regime **−1** (old gate would've failed: `vr` 0.7<1); +3 bars ER↓0.2 → Regime **held −1** (exit latch, no flicker); consolidation (05-30) ER 0.0 → **0 Range**; flush bar vol-pct 100% but ER 0.2 → cascade did NOT fire (confirmed V-flush has mediocre 20-bar ER → cascade ER-keying weak; parked).
**Status:** regime engine accepted; superseded by v4 (scout only).

## v4 — Scout hardening
**Date:** 2026-06-06 · **On-chart:** "Jamal Phase 1 v4" (shorttitle "Jamal P1v4")
**Code changes**
- `f_push` signature changed to `(bar, ret, vol, ret_v, vol_v)` — now stores **signal-time vol-percentile** per sample; MFE/MAE no longer stored.
- **Removed** helpers `f_mean`, `f_edge_val`, `f_net_edge_val`, `f_num_col` and all MFE/MAE/Path arrays.
- **Added** helpers: `f_effn` (non-overlapping count, entries ≥ `fwd_bars` apart = effective n); `f_edge_se` → `[edge, se, t, neff]` (SE from effective-n + dispersion via `array.stdev`); `f_gap` → `[gap, se, t]` (Taken−Veto, baseline cancels); `f_vol_losers` (mean signal-time vol-pct of ret<0 samples); `f_t_str`, `f_t_col` (|t|≥1.5 significance colour); `f_hdr`/`f_row`/`f_gate` (table writers).
- **Split Vetoed** into Veto-DIR (regime ±1 against side) and Veto-CSC (cascade): arrays `fl_t/fl_vd/fl_vc` and `fs_t/fs_vd/fs_vc` (each bar/ret/vol) + `bs_bar/bl_ret/bsh_ret`.
- Bucketing uses `reg_sig = regime[fwd_bars]`, `volp_sig = atr_pct[fwd_bars]`.
- Dashboard rebuilt: 7 cols `bucket | Edge | ±SE | t | n | nEff | Vol%lo`; bucket rows (Taken Edge = gate-0) + `gate Δ` rows (Taken−Veto-dir, verdict EDGE/ANTI/ns).
**Rationale:** point estimates with no dispersion over overlapping windows = reading noise. Make Taken-vs-Vetoed decision-grade; isolate cascade (expected un-validatable); tag flush pollution.
**Tests run:** `pine_check` (0/0); pushed + remove/re-add (legend cache); read scout via `data_get_pine_tables`; then full sweep.
**Results (single window, lookback 750):** nEff ≪ n confirmed (L Taken 51→11, S Taken 70→8); gate-0 not significant either side; verdict "insufficient data" → raised lookback and swept.

### Sweep (v4) — BTC / TAO / HYPE (BINANCE perps) × 1h / 4h
**Date:** 2026-06-06 · lookback set to 5000 via `in_24` → nEff ~50–70 (HYPE 4h ~24–29). Decision-grade.

GATE-0 — Taken edge vs baseline (ATR, t):
| | Long | Short |
|---|---|---|
| BTC 1h | −0.57 (−1.2) | −0.35 (−0.6) |
| BTC 4h | −0.41 (−0.8) | −0.12 (−0.2) |
| TAO 1h | +0.16 (0.3) | +0.31 (0.7) |
| TAO 4h | −0.57 (−1.1) | −0.35 (−0.7) |
| HYPE 1h | −0.39 (−0.8) | +0.07 (0.2) |
| HYPE 4h | +0.24 (0.4) | −1.23 (−1.2) |

GATE Δ — Taken − Veto-dir (ATR, t, verdict):
| | Long | Short |
|---|---|---|
| BTC 1h | −1.60 (−1.7) ANTI | −0.65 (−0.7) ns |
| BTC 4h | −1.32 (−1.1) ns | −0.45 (−0.5) ns |
| TAO 1h | −1.04 (−1.2) ns | +1.10 (1.0) ns |
| TAO 4h | −0.69 (−0.9) ns | +2.07 (1.5) EDGE |
| HYPE 1h | +0.38 (0.5) ns | −0.08 (−0.1) ns |
| HYPE 4h | −2.67 (−2.3) ANTI | −0.55 (−0.4) ns |

Vol%lo (cascade-pollution tag): Taken 35–53 (losers NOT high-vol) · Veto-CSC 90–98 (genuine flush bars) · Veto-CSC nEff 0–16.

**Verdict: Phase 1 = NO.**
1. **Gate-0 fails everywhere** (no |t|≥1.5; leans negative) — fader doesn't beat baseline in the allowed regime on any symbol/TF.
2. **Long veto is counterproductive** (5/6 negative, 2 significant ANTI) — vetoing dip-buys in downtrends removes the violent counter-trend oversold bounces (the best fade-longs).
3. **Short gate** inconsistent (one EDGE TAO 4h; negative BTC) — no robust edge.
4. **Cascade** un-validatable statistically + low-value (Taken Vol%lo 35–53 → minimal flush pollution). Correctly parked.

**Caveat that reframes the verdict (open):** gate-0 was measured on an **exit-blind fixed 24-bar horizon return**. Mean-reversion edge is front-loaded — a fixed hold captures the decayed endpoint, not the catchable bounce — so a real fader can print ~0/negative ret. Need MFE-vs-ret check + a triple-barrier first-touch metric before concluding no edge. See "Next".
**Status:** superseded by v5 (outcome metric).

## v5 — Triple-barrier outcome (regime = conditioner, not veto)
**Date:** 2026-06-06 · **On-chart:** "Jamal Phase 1 v5" (shorttitle "Jamal P1v5")
**Code changes**
- **Bounded to TradingView** — Python/CPCV plan dropped (user directive). Robustness via sweep + effective-n/SE + perturbation only.
- `regime_filter` now gates **live arrows/alerts only**; scout buckets are regime-conditioned regardless (conditioner, not veto verdict).
- **New Scout inputs:** `bar_target_atr` (`in_23`, default 1.0), `bar_stop_atr` (`in_24`, default 1.5), `bar_tcap` (`in_25`, default 12). ⚠ **Input IDs shifted** — current Scout map: `fwd_bars`=in_22, `bar_target_atr`=in_23, `bar_stop_atr`=in_24, `bar_tcap`=in_25, `min_samples`=in_26, **`lookback_bars`=in_27**, `cal_len`=in_28.
- **New `f_barrier(is_long, entry, atr_sig)` → `[outcome_ATR, hit(0 timeout/1 target/2 stop), mfe_ATR]`**: forward first-touch scan of +target·ATR / −stop·ATR / time cap; conservative stop-first on same-bar ambiguity.
- `f_push` now stores `(bar, out, mfe, hit)`. Removed the vol arrays + `f_vol_losers`. Added `f_rate` (first-touch %), `f_mean_min`, `f_pct_str`.
- Buckets store outcome/MFE/hit per Taken / Veto-DIR / Veto-CSC; baseline = barrier outcome on every bar, both sides (random-entry expectancy, same bracket).
- Dashboard cols: `bucket | Exp(ATR) | t | tH% | sH% | MFE | nEff`. Exp = bucket − baseline expectancy with effective-n SE/t; Taken row = gate-0; "gate d" rows = Taken − Veto-DIR.
**Rationale:** the exit-blind 24-bar horizon return measured the decayed endpoint of a front-loaded reversion. Triple-barrier first-touch captures sequence + tradeable expectancy + the ex-ante bounce-vs-knife split (tH vs sH).
**Tests run:** `pine_check` 0/0; pushed + remove/re-add; BTC 1h, lookback 1500, bracket +1.0/−1.5/12b.
**Bug (mine, fixed):** set inputs via `in_24` assuming it was lookback, but IDs had shifted → accidentally set `bar_stop_atr`=1500 (sH% = 0% everywhere, Bracket panel showed −1500). Corrected: `in_24`=1.5, `in_27`=1500.
**Results (BTC 1h, lookback 1500, bracket 1.0/1.5/12):**
| bucket | Exp | t | tH% | sH% | MFE | nEff |
|---|---|---|---|---|---|---|
| L Taken | −0.10 | −0.3 | 50% | 43% | +0.99 | 22 |
| L Veto-dir | −0.20 | −0.4 | 45% | 50% | +0.81 | 6 |
| S Taken | −0.25 | −0.8 | 48% | 48% | +0.96 | 17 |
| S Veto-dir | +0.20 | +0.4 | 68% | 32% | +1.08 | 7 |
| L gate Δ | +0.10 | +0.2 ns | | | | |
| S gate Δ | −0.45 | −0.9 ns | | | | |

**Finding:** **MFE ≈ +1.0 ATR while Exp ≈ 0** on the Taken buckets → looked like the front-loaded favorable excursion exists but the bracket hands it back. ⚠ **Partly an artifact** — MFE here was bracket-TRUNCATED (loop broke on first touch), so MFE was capped near the target. v6's bracket-free MFE corrects this (see below). Signed-regime gate Δ inconclusive at lookback 1500 (nEff 6–22; thin).
**Status:** superseded by v6 (advisor hardening).

## v6 — Scout hardening (advisor review)
**Date:** 2026-06-06 · **On-chart:** "Jamal Phase 1 v6" (shorttitle "Jamal P1v6")
**Code changes**
- **`f_effn` spacing `fwd_bars` → `min(bar_tcap, fwd_bars)` (cap):** outcomes resolve within the cap, so cap-spaced entries are independent. Recovered ~+27% effective-n here. Caveat in comment: fixes window overlap only, not vol/regime clustering → corrected nEff still slightly overstates independence.
- **Bracket-free MFE/MAE:** `f_barrier` no longer `break`s on first touch — it records the first-touch outcome but scans the full cap to accumulate max favorable / max adverse. De-circularizes the envelope (used to choose a target) from the bracket being tuned. Returns `[out, hit, mfe, mae]`.
- `f_push` stores `mae`; added `fl_*_mae` / `fs_*_mae` arrays.
- **`min_eff` input (`in_37`, default 8):** `f_edge_se` / `f_gap` return n/a unless effective-n ≥ min_eff (nEff still displayed). Pre-committed power floor. **Appended last so existing input IDs stay stable (lookback remains `in_27`).**
- Dashboard → 8 cols: `bucket | Exp | t | tH% | sH% | MFE | MAE | nEff`.
- Context comments only: stop-first pessimizes a fader → Exp = conservative FLOOR; cost-blind → haircut before believing a cell.
**Rationale:** advisor code review — recover power, de-circularize MFE, enforce a power floor.
**Tests run:** `pine_check` 0/0; pushed + remove/re-add; BTC 1h, lookback 1500, bracket 1.0/−1.5/12.
**Results (BTC 1h):**
| bucket | Exp | t | tH% | sH% | MFE | MAE | nEff |
|---|---|---|---|---|---|---|---|
| L Taken | −0.10 | −0.4 | 50% | 43% | +1.94 | +1.88 | 28 |
| S Taken | −0.25 | −0.9 | 48% | 48% | +2.17 | +2.07 | 22 |
| Veto-dir/csc | n/a | | | | | | 6–7 |

**Finding:** effN fix lifted Taken nEff +27% (22→28, 17→22); min_eff correctly n/a's the thin veto buckets. **The bracket-free envelope is ~SYMMETRIC: MFE ≈ MAE ≈ 2 ATR, tH ≈ sH ≈ 50%** → no bracket-only edge on BTC 1h Range/Taken; the v5 "edge handed back" was a bracket-truncation artifact. Gate-0 negative on the fixed bracket, and the symmetric envelope says that's not a tuning problem — the *unconditional* fade looks edgeless. The surviving (conditional) hypothesis — counter-trend Veto-dir bounces with MFE>MAE — is exactly the bucket below the min_eff floor (nEff 6–7) and unreadable at lookback 1500.
**Status:** current on chart.

---

## Decisions / direction
- **Do NOT proceed to v2 continuation.** Gate-0 precondition unmet on the exit-blind metric.
- **Pivot: regime-as-conditioner, not veto.** The fade edge may be *largest* counter-trend inside trends (one-sided positioning → sharp squeezes); the catch is continuation risk → needs an exit model (tight target + time-stop counter-trend; wider/longer in range).
- **Re-home the research:** triple-barrier expectancy + signed-regime test across symbols/TFs with CPCV is a **Python pipeline** job; Pine scout demoted to live monitoring. (No existing CPCV/pipeline found in this workspace as of 2026-06-06.)

## Next (planned, not yet done)
1. **Unconditional fade looks edgeless** (BTC 1h Range/Taken: symmetric MFE≈MAE≈2 ATR, tH≈sH≈50%, gate-0 negative). The bracket is NOT the lever after all — symmetric excursion means no target/stop sizing creates edge.
2. **Open decision (advisor):** strict "pooled gate-0 first" → fade is dead, stop. OR read gate-0 **per regime slice** — the conditional (counter-trend Veto-dir) hypothesis from v4 — which needs the Veto-dir buckets over min_eff. Lean: raise lookback (`in_27`) to ~3000 ONCE to see if the Veto-dir envelope is asymmetric (MFE>MAE); watch stationarity (~4 months on 1h). If it's also symmetric, the fade is dead.
3. If pursued: sequence/front-loading evidence beyond tH/sH (e.g. bars-to-MFE vs bars-to-MAE) only if the conditional envelope looks asymmetric.

## Open items / parked
- **Cascade ingredients redesign** (range-expansion + volume surge + single large-range bar vs 20-bar ER). Parked — measured low-value via Vol%lo. Documented as NOTE on `er_cascade`.
- **nEff display cosmetic:** sub-`min_samples` buckets show nEff 0 (computed inside the edge gate). Cells are n/a anyway; fix on next push.
- **lookback default:** code default 750 (`in_24`); on-chart instance set to 5000 via inputs for the sweep.
