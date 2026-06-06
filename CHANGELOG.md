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
**Status:** superseded by v7 (regime-mix readout).

## v7 — Regime-mix readout (label-sparsity verification)
**Date:** 2026-06-06 · **On-chart:** "Jamal Phase 1 v7" (shorttitle "Jamal P1v7")
**Code changes**
- Added `bs_reg` array — logs the current `regime` each post-cal bar, pruned with the baseline timeline.
- State panel +1 row **"Reg mix"**: % of window bars colored (regime≠0) + U/D/C breakdown + n. No engine logic touched — pure measurement.
**Rationale:** advisor verification — turn "looks sparse" into a number vs the v3 ER-only ~48% ceiling, BEFORE the Veto-dir probe. If colored% << expected → slope deadband/dwell over-trimming (a bug); if in-band → sparseness is the market, proceed.
**Tests run:** `pine_check` 0/0; pushed + remove/re-add; BTC 1h, lookback 1500.
**Results:** **Reg mix = 30% colored (13U / 15D / 2C), n=1501** (Range 70%). In the predicted 30–45% band (ER-only 48% minus the slope-deadband + dwell filters), well above the <15% over-trimming threshold. The balanced 13U/15D split = both directions label (not down-only). Scout numbers unchanged from v6 (no logic change).
**Verdict:** **labels are clean; the sparseness is the market, not a bug.** Engine verified — cleared to run the conditional probe. (Explicit single-episode up-leg concordance eyeball still pending — UI obstructed the screenshot; aggregate 13U is strong proxy.)
**Status:** superseded by v8 (conditioner reframe).

## v8 — Conditioner-discovery instrument (advisor reframe)
**Date:** 2026-06-06 · **On-chart:** "Jamal Phase 1 v8" (shorttitle "Jamal P1v8")
**Code changes**
- **REFRAME:** stop asserting the regime gate; measure per overshoot signal the forward asymmetry **A = MFE − MAE** (bracket-free, full window) vs pre-committed candidate conditioners, and let outcome-separation define the regime. Label = discovered output, not defended input.
- **Stripped** the stratified Taken/Veto bucket scout, the bracket inputs (bar_target/stop/tcap), and the barrier outcome tables. Regime engine kept for tint/context only (C1 uses ER+slope directly, not the discrete label).
- **New inputs (Scout):** `fwd_bars` repurposed as "Excursion window" (default 12); `vel_len` (3); lookback default → 1500. `min_eff` kept (last). ⚠ Input IDs shifted: **lookback_bars = `in_25`** now (fwd_bars in_22, vel_len in_23, min_samples in_24, cal_len in_26, min_eff in_38).
- **New helpers:** `f_excursion` (bracket-free MFE/MAE), `f_clip`, `f_wins_corr` (winsorized-5/95 Pearson — fat-tail robust, O(n), avoids O(n²) ranking), `f_corr_t` (t from effective-n), `f_bins` (tercile mean-A), `f_cpush`. Removed the barrier/bucket helpers. (Fixed a vestigial extra param in f_cpush on first compile.)
- **4 pre-committed conditioners:** C1 = `er*sign(os)*sign(slope)` (counter-trend-in-strong-trend); C2 = `|os|`; C3 = `|os−os[vel_len]|`; C4 = `|tc|`.
- **Dashboard:** `feat | r | t | A.lo | A.mid | A.hi | nEff`; r coloured at |t|≥2; tercile bins = shape check.
**Rationale:** advisor reframe — discover the conditioner that carves the outcome. Correlation over all signals (sample-efficient) not buckets (which shred nEff); winsorized (one liquidation candle can't manufacture it); built-in KILL TEST.
**Tests run:** compile 0/0 (after the f_cpush fix); BTC 1h, lookback 1500, **n=302 signals, nEff=54**.
**Results (BTC 1h):**
| Conditioner | r | t | A.lo | A.mid | A.hi |
|---|---|---|---|---|---|
| C1 SignEff | −.10 | −0.7 | +.07 | +.66 | −.64 |
| C2 \|OS\| | −.12 | −0.9 | +.18 | −.01 | −.08 |
| C3 Veloc | −.01 | −0.1 | +.02 | +.19 | −.13 |
| C4 \|Carry\| | +.20 | 1.5 | −1.00 | +.75 | +.33 |

**Finding: none passes (|t|≥2 + monotone + correct sign).**
- **C1 (the v4 counter-trend lead) is DEAD as a continuous conditioner** — ns, non-monotone (inverted-U), and inverted: counter-trend extremes (hi C1) show the *lowest* asymmetry (−.64). Mechanistically confirms v6 (counter-trend bounces are violent both ways: big MFE AND big MAE → net asymmetry unfavorable). The v4 "lead" was the exit-blind artifact.
- C2 weakly wrong-signed + ns; C3 dead.
- **C4 |carry|** is the only correctly-signed, near-significant thread (r+.20, t1.5) but bins not cleanly monotone — suggestive, not passing.
**Verdict:** BTC 1h near-kill — no conditioner cleanly carves the fade. C4 the sole candidate → ran the pre-committed cross-symbol replication (below).

### v8 — C4 |carry| cross-symbol replication (kill-confirmation, bar locked before looking)
**Pass bar (pre-committed):** C4 passes only if in **≥4 of 6 cells** it shows (a) r>0, (b) t≥1.5, (c) roughly monotone lo<mid≤hi. Testing **C4 only** (C2/C3 lighting up elsewhere is NOT a pass — dead + not pre-registered = HARK). Lookback 1500.
| cell | r | t | bins lo/mid/hi | result |
|---|---|---|---|---|
| BTC 1h | +.20 | 1.5 | −1.00/+.75/+.33 | FAIL (c) |
| BTC 4h | +.01 | 0.1 | −.76/−.65/−.55 | FAIL (b) |
| TAO 1h | +.05 | 0.3 | −.33/−.31/−.38 | FAIL (b,c) |
| TAO 4h | +.21 | 1.5 | −.73/−.75/+.39 | FAIL (c) |
| HYPE 1h | −.15 | −1.0 | −.12/−.56/−1.05 | FAIL (a, sign flip) |
| HYPE 4h | +.13 | 1.1 | −.04/−.08/+.52 | FAIL (b,c) |

**Result: 0 of 6 pass.** r ∈ [−.15, +.21], sign unstable, never clears t≥1.5 with monotonicity — best-of-4 noise survivor at nEff≈50, not a mechanism. (Aside, NOT counted: C2 lit up on TAO 4h r+.30 t2.3 but is dead/not-pre-registered, and its sign was opposite on BTC 1h — counting it would be HARK.)

## PHASE 1 CONCLUSION — KILL (2026-06-06)
The overshoot mean-reversion fade is **descriptively dead** on BINANCE BTC/TAO/HYPE perps × 1h/4h. Evidence chain: regime veto failed (v4); unconditional forward envelope is symmetric (v6: MFE≈MAE≈2 ATR, tH≈sH≈50% — no bracket creates edge); the original counter-trend thesis inverted (v8 C1); and no pre-registered conditioner (C1–C4) carves the fade asymmetry, C4's replication 0/6. A=MFE−MAE is a generous necessary-not-sufficient screen, and it fails everywhere. This is a **successful kill test**, not a failed project. Per charter: no C5/C6, no Python/CPCV, no perturbing a corpse. Any future work starts from a *new* signal hypothesis, not a rescue of this fader.
**Status:** v8 instrument current on chart (BTC 1h).

---

# ========================= PHASE 2 — DERIVATIVES-FLOW CONDITIONERS (OPEN) =========================
**Premise (2026-06-06):** funding / OI / liquidations are direct reads of price-insensitive *forced* flow — where a moat can live and what price-only (Phase 1) couldn't see. Discipline identical to Phase 1; three rich series = data-mining minefield, so guards are stricter.

**Keep** the v8 harness (winsorized corr(C, A) + tercile shape + effective-n + min_eff floor + locked-bar replication). **Strip** the overshoot-fade strategy framing. Phase 2 = feed the validated instrument *better, mechanism-gated* conditioners.

**Mechanism gate** — no conditioner enters without a one-line "why it exists and persists." Pre-committed hypotheses (cap 3, locked before looking):
- **H1 funding → counter-positioning reversion:** signed funding predicts *negative* signed forward return (extreme funding = crowded leveraged side paying carry → reversion against the crowd). Continuous, best history → **build first.**
- **H2 liquidation magnitude → fade the flush:** side set by which side was liquidated; conditioner = liquidation-spike *magnitude percentile* (continuous, NOT a binary bucket); predicts favorable post-flush A.
- **H3 ΔOI → continuation vs hollow:** sign of OI change interacts with forward continuation (price↑ + OI↑ = new leverage/fragile; price↑ + OI↓ = short-cover/hollow).

**Required harness tweak:** A=MFE−MAE is direction-agnostic; H1/H3 are *directional* → add a **signed forward-outcome mode** (signed fwd return / signed first-touch) with a signed conditioner, so "+funding → down" reads as negative r. H2 stays on A (liq event defines the side).

**Sequence (gated):** (a) **DATA-AVAILABILITY SPIKE first** — load the series via `request.security`, plot BTC 1h/4h, report history depth, NaN/gaps, funding step cadence, bar-close repaint; confirmed values sampled LAGGED. (b) wire H1, BTC 1h. (c) if it carves → locked-bar replication ×6 (≥4/6, correct sign, t≥1.5, monotone). (d) then H2, then H3.

**Guardrails:** one pre-committed conditioner at a time (a non-registered series lighting up ≠ pass — the v8 HARK trap); a passer is necessary-not-sufficient (still needs a sequence/exit test); cost-blind / descriptive / overlapping. **nEff is the binding limit** — derivatives history is shorter and liquidation cascades are rare (H2 may be power-starved); protect nEff via event + window definition; don't over-read thin cells.

**DATA-AVAILABILITY SPIKE — RESULT (2026-06-06, probe `p2_data_probe.pine`, BTC 1h, 21309 bars loaded ≈ 2.4y):**
| series | ticker | non-NA / span | verdict |
|---|---|---|---|
| price (control) | BINANCE:BTCUSDT.P | 21309 / 21309 | ✓ |
| **Open Interest** | **BINANCE:BTCUSDT.P_OI** | **21309 / 21309** | ✓ full, gapless, native Binance (the `_OI` suffix works) |
| Funding | SGX:BTFR | 3325 / 3325 | ⚠ proxy venue (SGX, not Binance), only ~4.5mo |
| Funding (Binance) | `_FUNDING` / `_FUNDING`/`FUNDINGRATE` forms | 0 | ✗ invalid — no Binance funding in Pine |
| Liquidations | `_LIQUIDATIONS` / `_LIQ` forms | 0 | ✗ **unavailable in TradingView Pine** |
| OI/Funding/Liq via IntoTheBlock | ITB:BTC_* | 0 (on 1h) | ✗ |

**Implications (reorders the pre-committed plan):**
- **OI has the best data, not funding** — full 2.4y gapless native Binance. → **build H3 (OI) first**, contra the original "funding first."
- **H1 funding compromised:** SGX proxy only, ~4.5mo → nEff-limited + venue mismatch. Decision pending: accept proxy (caveated) or defer.
- **H2 liquidations DEAD on data** (not in TV Pine). Bounded-to-TV ⇒ only a price/volume flush *proxy* is possible, which discards the "direct forced-flow" rationale. Decision pending: drop vs proxy.
- Cadence/repaint: funding is a step series (8h); all confirmed values sampled LAGGED in the harness (same as price excursion). OI is per-bar.

**SPIKE CORRECTION (2026-06-06) — use the official `TradingView/Request` library, not raw `request.security` suffixes.** `import TradingView/Request/3 as r` exposes: `r.openInterestCrypto(symbol, timeframe)` → `[o,h,l,close,rising]`; `r.cryptoDerivativeMetric(metricName, symbol, timeframe)` with metricName ∈ {"Funding Rate","Liquidations Buy","Liquidations Sell", …}. Re-probed BTC 1h (`p2_data_probe.pine`), all gapless over the full 21311-bar (~2.4y) window:
| series | non-NA / span | last |
|---|---|---|
| OI close (`openInterestCrypto`) | 21311 / 21311 | 101831.97 |
| Funding ("Funding Rate") | 21311 / 21311 | −0.001012 |
| Liquidations Buy | 21311 / 21311 | 9.43 |
| Liquidations Sell | 21311 / 21311 | 0.69 |

This **supersedes** the request.security-only finding above (which only saw SGX funding proxy + no liquidations). **All three Phase-2 series are fully available with deep history.** Consequences: (1) no reorder forced — the pre-committed **H1 funding-first** plan stands (full real-funding history); (2) funding proxy concern void; (3) **H2 liquidations revived** — Buy/Sell available, though liquidation *spikes* are rare so the spike-tail nEff (not history) is the binding limit. Funding is a step series (8h) — sample LAGGED. Units of funding/liq TBD from lib docs; sign/percentile is what the hypotheses use.

**C-VERIFICATION (2026-06-06) — funding is LIVE/CONTINUOUS, not an 8h step.** Probe `P2 funding verify`: funding changes ~1.3 bars/change (≈75% of bars), at arbitrary UTC hours (1/2/3…), not 00/08/16 boundaries. So `cryptoDerivativeMetric("Funding Rate")` = Binance **live/predicted** funding (off the premium index), **single-venue** (ticker-keyed, not aggregate), known at each bar.
- Look-ahead: continuous & known-at-bar → lagged `funding[fwd_bars]` is safe (no step forward-fill look-ahead).
- Venue: BINANCE only (aggregate unavailable via ticker call); dominant-venue proxy.
- Fix-B premise shift: NOT a step → the ~8× step pseudo-replication worry is largely void; but funding LEVEL persists in multi-day regimes → **block bootstrap still the honest significance gate** (for level autocorrelation).

**v9 spec (A+B + two-outcome, pending final confirm):** event = every post-cal bar; conditioner = **z-funding** `(funding − SMA)/STDEV` over an a-priori ~weeks window (fix A, no sweep); outcomes (both signed, both predicted NEGATIVE vs z-funding) = O1 signed forward return `(close−entry)/atr` (stingy endpoint screen) + O2 signed peak-excursion (dominant of up/down excursion, signed — catches front-loaded reverted moves, so a fail isn't a false-kill); significance via **block bootstrap CI** (blocks ≥ multi-day, parametric t indicative only); pass bar **≥5/6** cells correct-signed + CI-excludes-0 + monotone-decreasing terciles.
## v9 — H1 funding instrument (file `jamal-phase2.pine`)
**Date:** 2026-06-06
**Build:** import `TradingView/Request/3`; conditioner = **z-funding** `(funding − SMA)/STDEV` over a-priori 14-day window (fix A, not swept); event = every post-cal bar; outcomes O1 signed return + O2 signed peak-excursion (both predicted NEGATIVE); significance = **block-bootstrap 95% CI** of winsorized corr (fix B; multi-day blocks; parametric t indicative). LCG RNG (function-local var — Pine forbids modifying a global var in a function). Lean build, fade engine stripped.
**Leak gate #1 (rigorous, before trusting any number):** forward-settle test over 2663 boundaries — interval FIRST bar == its settlement only **19%**, any-early **22.9%**, avg |first−settle| **0.0031** → mid-interval live ≠ next settled ⇒ **no backfill leak; series genuinely live.** (Earlier flat-backfill check + this forward test = #1 PASSED.)
**Result (BTC 1h, n=2001, nEff=167):**
| outcome | r | t~ | boot CI95 | terciles lo/mid/hi |
|---|---|---|---|---|
| O1 signed-return | +0.13 | 1.7 | [+.01, +.22] | −.46 / −.12 / +.18 |
| O2 signed-peak | +0.15 | 1.9 | [+.02, +.23] | −.72 / −.22 / +.31 |

**H1 VERDICT: KILLED (wrong-signed).** Predicted negative (reversion); got **significant POSITIVE** — bootstrap CI entirely above 0 on *both* outcomes, terciles **monotone increasing** (high z-funding → continuation UP, not reversion). The O2 excursion safeguard did not rescue it (also positive) → not an exit-blind false-kill; the favorable excursion runs *with* funding. z-score (fix A) did not flip it, and leak #1 is clean → the positive sign is real. **No BTC-4h cell** (pre-reg replicates only IF it carves; it didn't — a 4h cell would only probe the *momentum* finding, a different hypothesis). Verdict scoped: "H1 on **Binance** funding"; aggregate not a rescue.
**PARKED NOTE (not an open thread):** funding extremity → short-horizon *continuation/momentum* (the mirror of H1). Only marginally significant (boot floor +.01/+.02, t<2) and its credibility was itself hostage to #1. If ever pursued, it requires a **cold separate pre-registration** that opens by killing the leak question — NOT a pivot off this run (that would be HARK).

## STANDING GATE — data-layer integrity (all of Phase 2)
Every derivative series must pass a check-#1-equivalent (no settlement/lookahead backfill) BEFORE its hypothesis is trusted. A leak contaminates the whole layer. Reusable tool: `p2_leak_check.pine`. **Next: H3 (OI) — run the OI leak check first, then wire ΔOI.**

---

## Decisions / direction
- **Do NOT proceed to v2 continuation.** Gate-0 precondition unmet on the exit-blind metric.
- **Pivot: regime-as-conditioner, not veto.** The fade edge may be *largest* counter-trend inside trends (one-sided positioning → sharp squeezes); the catch is continuation risk → needs an exit model (tight target + time-stop counter-trend; wider/longer in range).
- **Bounded to TradingView (standing, per v5 directive): no Python/CPCV.** Robustness comes from in-Pine multi-symbol × multi-TF replication + effective-n/SE + parameter perturbation. (Searched 2026-06-06: no CPCV/pipeline exists in the workspace anyway.)

## Next
- **Phase 1 is concluded: KILL** (see above). No further work on the overshoot fader — no C5/C6, no perturbation, no Python/CPCV.
- The v8 conditioner instrument is reusable infrastructure: any *new* signal hypothesis can be screened through the same corr(C, A) + tercile + replication discipline. Don't reopen this one.

## Open items / parked
- **Cascade ingredients redesign** (range-expansion + volume surge + single large-range bar vs 20-bar ER). Parked — measured low-value via Vol%lo. Documented as NOTE on `er_cascade`.
- **lookback default:** code default **1500** (`in_25` in v8). NB `in_24` is now `min_samples`. (The v6 nEff-display cosmetic is obsolete — the bucket scout it referred to was removed in v8.)
