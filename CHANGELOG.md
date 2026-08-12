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

## v10 — H3 OI instrument (file `jamal-phase2.pine`)
**Date:** 2026-06-06
**Build:** import `TradingView/Request/3` → `r.openInterestCrypto`. Conditioner = **z-scored formation-window ΔOI**: `oichg = oi/oi[form_bars] − 1`, `ozi = (oichg − SMA)/STDEV` over a-priori 14-day window (fix A, not swept). Per the advisor's required fix, ΔOI is **NOT direction-fixed** (unlike funding in v9) — it is encoded as an **interaction with the continuation direction**: at each post-cal bar `sgn = sign(formation move)`, outcome **O1 = sgn × forward return** (continuation return), **O2 = sgn × signed peak-excursion** (continuation-peak safeguard). Both predicted **POSITIVE** (price↑ + OI↑ = fresh leverage → continuation carries). Continuation-only; hollow/short-cover leg parked. Same block-bootstrap 95% CI gate + ≥5/6 locked replication bar + min_eff floor. Binance-only venue caveat.
**Hygiene/continuity gate (OI, before trusting any number):** 100% coverage, 0% flat bars, max flat-run 0, avg |ΔOI|/OI ≈ 0.38%/bar → genuinely live differenced series, no forward-fill / no settlement backfill. STANDING GATE **PASSED.**
**Result (BTC 1h, n=2001, nEff=167):**
| outcome | r | t~ | boot CI95 | terciles lo/mid/hi |
|---|---|---|---|---|
| O2 cont-peak *(safeguard, read first)* | −0.04 | −0.5 | [−.12, +.06] | +.32 / +.32 / +.20 |
| O1 cont-return | −0.04 | −0.5 | [−.12, +.05] | +.18 / +.15 / −.05 |

**H3 VERDICT: KILLED (flat).** Predicted positive; got **r≈0 on both outcomes, bootstrap CI spans 0**, terciles flat-to-mildly-*decreasing* (high-ΔOI tercile is the lowest continuation, the opposite of predicted, though not itself significant). The O2 excursion safeguard was read first per the kill rule and is **also flat** → not an exit-blind false-null; the favorable continuation excursion does not run with fresh OI. nEff=167 (well above the min_eff floor) → this is a **well-powered null**, not a power failure. The hygiene gate is clean, so the flat is real, not a data artifact. **No replication ×6** — a decisive fail on the anchor cell does not move the locked bar (same precedent as H1's BTC-1h kill). Verdict scoped: "H3 on **Binance** OI, continuation encoding." Hollow/short-cover leg stays parked (would need its own cold pre-registration; pivoting to it off this null would be HARK).

## v11 — H2 liquidations instrument (file `jamal-phase2.pine`)
**Date:** 2026-06-06
**Build:** import `TradingView/Request/3` → `r.cryptoDerivativeMetric` "Liquidations Buy"/"Liquidations Sell". The liquidation **imbalance defines the side** (no signed conditioner): `netliq = LiqSell − LiqBuy` (>0 = sell-liqs dominant = forced selling = price pushed DOWN → fade is UP); `fsign = sign(formation-window netliq)`, sampled at entry. Conditioner = **flush MAGNITUDE percentile** `magpct = percentrank(Σ(LiqBuy+LiqSell, form_bars), pctlen)`, a-priori 14-day window (not swept) — tests flush SIZE, not imbalance. Outcomes measured in the **fade frame**, both predicted **POSITIVE**: **O1 = fsign × (MFE − MAE)** = `fsign·(upx − dnx)` (the *pre-registered* `A` pass metric, fade path quality); **O2 = fsign × forward return** (corroborating, held-to-horizon). Conditioner/fsign sampled at `[fwd_bars]`; formation window sits entirely before entry, forward window entirely after → no overlap, no leak. Same block-bootstrap 95% CI + ≥5/6 locked bar + min_eff floor. Also fixed: restored the missing `indicator()` declaration (the v10 on-disk file had diverged from the editor and would not compile standalone).
**Data-integrity / distribution gate (`p2_liq_gate.pine`, BTC 1h):** 100% coverage Buy/Sell/mag; `sign(netliq)`~same-bar concord **72.7%** (healthy mechanism, not leak-grade ~100%); fat tail p50/p90/p99 = 11/192.5/860.2, max 1923; top-decile **nEff = 841** (power abundant). **One** stale stretch (81 identical bars) exists but ended **8166 bars ago**, the only run >5 in 21312 bars, **0 stale bars in the recent 2250-bar H2 window** → STANDING GATE **PASSED** for the H2 sample. CAVEAT logged: if lookback ever extends past ~8k bars, exclude that ancient forward-filled stretch.
**Result (BTC 1h, n=2001, nEff=167):**
| outcome | r | t~ | boot CI95 | terciles lo/mid/hi |
|---|---|---|---|---|
| O1 A=MFE−MAE *(pre-registered)* | −0.01 | −0.1 | [−.11, +.10] | −.41 / −.27 / −.50 |
| O2 fadeRet *(corroborating)* | 0.00 | 0.0 | [−.11, +.08] | −.17 / −.09 / −.24 |

**H2 VERDICT: KILLED (flat conditioner; base rate is continuation).** Fails two ways: (1) **no carve** — r≈0, bootstrap CI spans 0 on the pre-registered metric *and* the corroborator → flush magnitude does not predict fade success. (2) **base rate against the fade** — every tercile is **negative** (fading a flush loses on average: adverse excursion > favorable, endpoint return < 0), and *most* negative in the **top flush tercile** (−.50), i.e. bigger flushes → *more* continuation, the opposite of the premise; terciles non-monotone, wrong-way at the extreme. Well-powered (nEff=167), gate-clean, no leak (windows non-overlapping). **No ×6 replication** — decisive anchor fail, locked bar doesn't move. Scoped to Binance liquidations.

## STANDING GATE — data-layer integrity (all of Phase 2)
Every derivative series must pass a check-#1-equivalent (no settlement/lookahead backfill) BEFORE its hypothesis is trusted. A leak contaminates the whole layer. Reusable tools: `p2_leak_check.pine` (signed-series forward-settle test, used for funding) and `p2_liq_gate.pine` (unsigned-series coverage/staleness/tail+nEff localizer, used for liquidations). Funding, OI, and liquidations all PASSED their respective gates.

## PHASE 2 SCORECARD (pre-committed cap = 3 — EXHAUSTED)
- **H1 funding → reversion:** KILLED (significant *continuation*, wrong-signed; v9).
- **H3 ΔOI → continuation:** KILLED (flat / well-powered null; v10).
- **H2 liquidations → fade-flush:** KILLED (flat conditioner; base rate = continuation; v11).

## PHASE 2 CONCLUSION — KILL (derivatives-flow conditioners find no reversion edge)
All three pre-committed mechanism-gated conditioners are dead on the BTC-1h anchor, each gate-clean and well-powered (nEff≈167, no leak/staleness in-window). **The cap of 3 is exhausted; no 4th conditioner without a fresh COLD pre-registration** (adding one now off these nulls = HARK). **Consistent cross-hypothesis theme:** every *directional* signal points to **continuation/momentum, never reversion** — H1 funding-extremity → continuation (significant), H2 large-flush → continuation base rate (the top tercile most negative for the fade), and the v9 parked funding-momentum residual. The reversion thesis that motivated Jamal (Phase 1 overshoot fade + Phase 2 derivatives reversion) is descriptively unsupported on BTC 1h across price, funding, OI, and liquidations. The *only* recurring positive signal is momentum — but pursuing it requires its own cold pre-registration (predicted sign flipped, leak question re-opened first), NOT a pivot off this layer.

# ========================= PHASE 3 — MOMENTUM (COLD PRE-REGISTRATION) =========================
**LOCKED 2026-06-06, before any run (cold). Advisor-reviewed; two pass-bar adjustments folded in.**

**Why momentum, why now:** Phase 1 (reversion of overshoots) and Phase 2 (derivatives→reversion) are both KILL. The one signal that kept recurring — as the *wrong-signed* shadow of three reversion hypotheses — is continuation. This is a fresh, cold test of it: predicted sign committed POSITIVE a-priori, not inferred from the prior nulls.

**M1 — price-momentum continuation (precondition GATE, not a destination):**
- **Hypothesis:** on 1h/4h crypto perps, the sign AND magnitude of the recent move positively predict the next move (momentum), not reversion.
- **Conditioner (single, a-priori, NOT swept):** `mom = (entry − close[entry+form_bars]) / atr_entry` — signed normalized formation move. `form_bars=12`, `atr_len=20`, sampled at entry (lagged).
- **Outcomes (both predicted POSITIVE corr):** O1 = signed forward return `(close−entry)/atr_entry` over `fwd_bars=12` (pass metric); O2 = signed dominant peak excursion `upx≥dnx?upx:−dnx` (exit-blind safeguard). Terciles of `mom` must be **monotone increasing** through 0.
- **Significance:** winsorized Pearson + **block-bootstrap 95% CI, block = 4×fwd_bars = 48 bars per TF** (ADJ-2: a multiple of the horizon, not a wall-clock 2 days — 2 days was 48 bars on 1h but only 12 on 4h, dishonestly tight). Effective-n spacing + `min_eff` floor. CI must exclude 0.
- **EFFECT-SIZE FLOOR (ADJ-1 — the real gate; significance is near-free at n≈2000 on the most-arbitraged signal in crypto):** committed cost model, round-trip bps of notional = taker 9 + slippage 5 + funding-carry 4 = **18 bp BTC / 28 bp TAO·HYPE** (+10 bp thinner books). Converted to ATR per cell via that cell's realized `mean(ATR/price)` (one added readout, no P&L engine). Pass requires **net_spread = (O1.hi − O1.lo) − 2·c_ATR ≥ +0.15 ATR** (long-short, both legs costed; +0.15 a real tradeable floor, not breakeven) — read off the tercile cells already computed.
- **Integrity / "leak gate":** OHLC-only → no settlement/backfill vector; the sole leak path (formation/forward overlap) is eliminated BY CONSTRUCTION (formation entirely pre-entry, forward entirely post, conditioner entry-lagged).
- **Locked pass bar:** predicted sign + CI excludes 0 + monotone-increasing terciles + **net_spread ≥ +0.15 ATR**, in **≥5 of 6** cells BTC/TAO/HYPE × 1h/4h. All six fresh for this conditioner.
- **Framing (advisor):** M1 is a *precondition* — a pass means "there is momentum to amplify," NOT "edge found"; bare signed-momentum autocorrelation has no moat (most-competed signal in existence). Do not over-spend the replication budget defending it. **Center of gravity is M2+** (does a derivatives STATE tell you *when* momentum is real). The momentum base rate ideally lives *inside* M2 as the control arm (baseline-vs-conditioned = the Phase 1 scout structure); running M1 standalone as a cheap gate is acceptable only because of the freshness argument.
- **Anti-HARK:** a-priori windows not swept; ONE conditioner; locked bar does not move; aggregate not a rescue for a near-miss; a decisive flat/wrong-signed/cost-failing anchor kills. Honesty: BTC 1h is EXPECTED to pass given the continuation theme → the anchor alone is uninformative; the hurdles are replication breadth, monotonicity, and the net-edge floor.

### v12 — M1 RESULT (file `jamal-phase3.pine`) — KILLED, 0/6
**Date:** 2026-06-06. Instrument: conditioner = signed normalized formation move, O1 = signed fwd return (pass), O2 = signed dominant peak excursion; net-edge verdict computed in-dashboard per the locked bar. Run across the full grid (BTC/TAO/HYPE × 1h/4h), cost_bps = 18 BTC / 28 alts as committed.

| cell | O1 r | O1 boot CI95 | terciles lo/mid/hi | mono | gross spread | cost 2RT | **NET** | verdict |
|---|---|---|---|---|---|---|---|---|
| BTC 1h  | +.06 | [−.05, +.15] | −.32 / +.03 / −.11 | no  | +.21 | +.59 | **−.38** | FAIL |
| BTC 4h  | +.02 | [−.12, +.09] | −.26 / −.15 / −.17 | no  | +.09 | +.28 | **−.18** | FAIL |
| TAO 1h  | +.04 | [−.10, +.14] | −.08 / −.11 / +.16 | no  | +.24 | +.35 | **−.11** | FAIL |
| TAO 4h  | +.03 | [−.12, +.12] | −.07 / +.12 / −.09 | no  | −.02 | +.17 | **−.19** | FAIL |
| HYPE 1h | +.09 | [−.03, +.17] | +.02 / +.17 / +.40 | **yes** | +.38 | +.41 | **−.03** | FAIL |
| HYPE 4h | +.04 | [−.07, +.12] | −.04 / +.06 / +.21 | **yes** | +.25 | +.17 | **+.08** | FAIL |

**M1 VERDICT: KILLED — 0/6 (need ≥5/6).** Two independent reasons, either sufficient:
1. **Significance/monotonicity alone kills it, cost-independent:** the O1 bootstrap CI **spans 0 in all six cells**, and terciles are monotone in only 2 (both HYPE). So even at *zero cost* the locked sign+CI+mono bar is met by **0/6**. The cost floor is not what's doing the killing on the significance axis — bare 12-bar momentum simply isn't there on BTC/TAO and is only borderline on HYPE.
2. **Net edge confirms why:** best net = HYPE 4h **+.08 ATR** (still < +.15 floor); every other cell net-negative; BTC 1h net −.38 (cost 0.59 ATR ≈ 3× the gross spread). Gross momentum spreads (0.1–0.4 ATR / 12 bars) are too small to clear realistic costs.

**Structure observed (descriptive, not a pass):** the *only* clean monotone-increasing momentum is **HYPE** (youngest / most-retail / highest-vol name), gross-positive but ≈breakeven after cost. BTC/TAO show no monotone 12-bar momentum. ADJ-1 validated on first contact: BTC 1h's O2 r=+.12 (CI excl 0) would have read as "momentum confirmed" on an r-only gate, while its net edge is −.38 ATR.

**Implication for the program:** M1's premise — "there is bare momentum to amplify" — is **false at the 12h/48h horizon.** This does not *logically* kill M2 (conditional momentum could exist where unconditional momentum averages to ~0), but it raises M2's bar: conditioning must now *manufacture* a tradeable-after-cost edge from a zero/negative base, not merely amplify a positive one. Per the advisor's a-priori horizon lock (1h/4h only; no horizon variants = no multiple-comparisons creep), a longer-horizon momentum test would require its own separate cold pre-registration. **Strategic fork (advisor): close the momentum program on M1's failure, or run M2 as a long-shot baseline-vs-conditioned test focused on whether a funding state carves a cost-clearing subset (HYPE-like high-vol names its best hope).**

**M2 — funding as a momentum AMPLIFIER (QUEUED, separate cold pre-reg — do NOT run with M1):** does continuation strengthen when funding confirms the move? Structured baseline-vs-conditioned (Phase 1 scout). Opens by re-running the funding leak gate. **Cell accounting caveat (lock when drafting M2):** funding on BTC 1h is already peeked by H1 → NOT a fresh confirming cell for M2.

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

# ========================= JAMAL CONTEXT — DISCRETIONARY TOOL (BUILD LOG) =========================
**New direction (2026-06-06):** after Phase 1/2/3 research all KILLED, pivot to building `jamal-context.pine`, a **discretionary context tool** (NOT a strategy/backtest/edge). Spec: `docs/superpowers/specs/2026-06-06-jamal-context-indicator-design.md`; plan: `docs/superpowers/plans/2026-06-06-jamal-context-indicator.md`. Three mechanisms — overshoot (trigger), regime (type), flow (conviction). Phased build, each increment gated by a live-chart test.

## Context v0.1 — Regime + tint + label (Mechanism A)
**Date:** 2026-06-06 · **On-chart:** "Jamal Context v0.1 (regime)" (shorttitle "JmlCtx", **`overlay=false` — own pane**)
**Code:** New file. Ported the Phase 1 regime engine **verbatim** (ER Schmitt enter 0.30/exit 0.18, dwell 3; signed linreg slope with ATR deadband 0.05; cascade = ER≥0.45 & vol-pct≥80 & volume surge; signed state machine → `regime ∈ {0 Range, ±1 Trend, ±2 Cascade}`). Render = **own-pane regime ribbon**: a regime step-line (−2…+2) coloured by state + `bgcolor` tint, with a top-right state panel (Regime label / ER / Vol pctile). Label maps cascade→**"Flush"**. ER/atr_pct data-window readouts. No overshoot/flow/marks yet.
**Render-mode correction (per user):** initial draft was `overlay=true` (on the price chart); changed to **`overlay=false`** so the tool gets its **own pane** (matches the brief's "like the existing script"); later increments push price-pane marks/anchor via `force_overlay`. **TradingView script renamed** from "Jamal's Mean Reversion" → **"Jamal Context"** (same slot id; the working tab had been the Context code all session; canonical research is in the repo .pine files + the "…EX/EX1" scripts).
**Rationale:** Mechanism A is the foundation every later mark keys off; build + verify it alone first.
**Tested (BTC 1h & 4h):** Compiles 0 errors. 1h: panel "Range (forming)", ER .07, vol 60.8% — red tint over down-legs. 4h: panel "Trend-down (forming)", ER .23, vol 95.2% — **all four tints render** (green Trend-up, red Trend-down, gray Range, orange Flush on violent bars). Regime matches Phase 1 by construction (verbatim port).
**Result:** PASS (render). **Status:** superseded by v0.1.1 (regime logic reworked before v0.2 per empirical review).

## Context v0.1.1 — Regime reworked to SLOPE-LED (Mechanism A fork)
**Date:** 2026-06-06 · **On-chart:** "Jamal Context v0.1.1 (regime - slope-led)" (shorttitle "JmlCtx", `overlay=false`)
**Why:** empirical review across a 4-month/4h window (Feb–Jun BTC) showed the ER-gated regime **under-shaded the Apr–May rally** (flickered Trend↔Range on every pullback) while painting brief mini-trends in chop. Root cause = wrong primitive: ER measures *efficiency*, not *direction-persistence*; a normal pullback tanks short-horizon ER and trips the trend-exit. For a with-trend Pullback tool this is fatal — the regime flips to Range exactly during the dip (the entry), so Pullback arrows would be suppressed when most wanted.
**Code (advisor-directed Option 2):** trend is now **slope-led** — repointed the Schmitt+dwell from ER onto the signed `slope_len`=50 linreg slope (ATR/bar): signed Schmitt (enter ±0.05, hold while ≥±0.02 EXIT) + dwell 3. **ER demoted** to cascade-filter + display only (cascade/Flush unchanged). Regime-slope horizon decoupled from the (later) overshoot anchor. Panel now shows Slope ATR/bar + ER(filter). **This FORKS Mechanism A** from the frozen ER-gated research engine — research scripts left untouched (their Phase 1–3 results stand against the ER definition). Rejected Option 1 (tuning er_exit/dwell = wrong knob, overfits one chart). Option 3 (recent-trend-memory arming) deferred — not needed if the trend holds through the dip; if added later it must be gated on not-a-flush.
**Tested (BTC 4h, same Feb–Jun view):** Compiles 0 errors. **(1)** Apr 11–May 1 rally = **solid green block** (was flickery) ✓. **(2)** Feb–Mar chop = mostly gray; red only on the real early-Feb decline ✓. **(3)** Late-May→June reversal **still flips Trend-down**, with orange Flush on the accelerating leg ✓. Caveat (accepted): ~1–2 wk reversal lag at the May top (slope-led trade-off; Blowoff/Flush are the fast warnings).
**Version-on-pane (per user):** the pane legend showed only the shorttitle (no version). Fixed: shorttitle now carries the version (`"JC v0.1.1"`, ≤10) so the legend is version-stamped, AND the state panel gained a purple title row ("Jamal Context" / "v0.1.1"). Convention going forward: bump **title + shorttitle + panel row together** each increment so a recompile is visually confirmable on the pane.
**Result:** PASS — all three advisor acceptance criteria met. **Status:** regime accepted; cleared to build v0.2 (overshoot + taxonomy marks + liq-flush suppression).

### PARKED — chandelier trend-INVALIDATION overlay (v0.1.2 candidate, gated; do NOT build yet)
**Idea (advisor):** borrow the chandelier `dir` *element* to attack v0.1.1's accepted reversal lag — but NOT as the backbone (a chandelier `dir` is binary +1/−1 with no Range state and whipsaws in chop; would destroy the ~70% Range slice the Spike taxonomy needs). Instead: **slope-led stays the entry classifier; chandelier becomes a one-way fast EXIT.** While `regime==+1`, a *confirmed close* below the long chandelier stop forces `regime→Range` one step early (bypassing the slope Schmitt dwell); mirror for −1. OR-exit (slope-decay OR chandelier-break) = faster reversal.
**Guards (non-negotiable if built):** use highest/lowest **close** + a **confirmed close** through the stop (a wick must not flip it); chandelier may **only invalidate (±1→0), never promote (0→±1)** — that firewall keeps Range ~70% and chop gray. A-priori params (no sweep): ATR(20) × **mult 3.0**, ~22-bar window. Forks Mechanism A → stays in `jamal-context` only (research scripts frozen).
**Acceptance (same Feb–Jun BTC 4h test as v0.1.1, + one):** (1) Apr–May rally still solid green; (2) Feb–Mar chop still gray; (3) May→June reversal flagged **measurably faster** than v0.1.1; (4) reg-mix Range% stays ~30% band (v7). If it can't beat #3 without breaking #1/#2/#4 → don't build; keep v0.1.1 + lean on Blowoff/Flush.
**DECISION GATE (why parked):** this is a THIRD fast-reversal mitigation (Blowoff + Flush already target the same lag) and is price-only (adds timing, not a new info axis) → scope-creep risk. Measured lag (Apr25–May31 4h): top ~May 5–6, regime holds green through ~May 12–13 (covers the top + first leg down 83k→80k), red engages ~May 16 → **~10–11 day / ~60-bar lag**. Real, not cosmetic — the green-during-topping window is where a false with-trend Pullback arrow could fire into a developing top. BUT the *cost* (an actual bad arrow) only renders once v0.2 draws marks. **Rule:** build v0.2 → re-check the May-top window with arrows+Blowoff → build the chandelier overlay ONLY IF false Pullback arrows appear there and Blowoff doesn't counter them; else keep v0.1.1.

## Context v0.1.2 — chandelier trend-invalidation overlay (BUILT; user requested, gate overridden)
**Date:** 2026-06-07 · **On-chart:** "Jamal Context v0.1.2 (regime - slope + chandelier-exit)" (shorttitle "JC v0.1.2"). User: "fix the regime shading before arrows; explore the chandelier" — so built now rather than gating on v0.2.
**Code:** slope-led backbone unchanged; added a **standard latching chandelier `dir`** (close through long/short stop; highest/lowest CLOSE; ATR(20)×3.0; 22-bar) as a one-way invalidation gate. `regime = slope_dir AND chand_dir` for the trend states; chandelier forces ±1→0 immediately (bypassing dwell), never promotes; re-validates on price RECLAIM of the opposite stop. Added reg-mix R/T/F% panel readout (acceptance #4). Chandelier stop plotted on price (force_overlay) for review. Forks Mechanism A (research scripts frozen).
**BUG found+fixed mid-build:** first cut used a hand-rolled `ce_block` latch cleared only when the *slope* left the direction. Because slope stays +1 through a whole rally, a single mid-rally chandelier break (the Apr 19–21 >3-ATR pullback) **locked out trend-up for the rest of the rally** → the Apr 13–30 rally body went fully GRAY (criterion #1 fail). Replaced with the canonical latching `chand_dir` (self-clears on reclaim) → lockout gone.
**Result (BTC 4h Feb–Jun):** #1 rally green = soft-pass (mostly green; brief gray notches at >3-ATR pullbacks, e.g. Apr 19–21); #2 chop gray = ✓; #3 faster reversal = ✓ (May-top green ends ~May 7 vs ~May 13 in v0.1.1 — the user's complaint); #4 reg-mix = **R/T/F 50/48/2** vs the ~70%-Range target — NOT met on this window, BUT this Feb–Jun sample is unusually trend-heavy (chop + big rally + big decline); the chandelier only *adds* Range so it didn't collapse it; #4 needs a longer/representative sample to judge. **Status:** superseded by v0.1.3 (user: "green appears when clearly dumping").

## Context v0.1.3 — chandelier dir = STRUCTURAL direction (new-high re-entry); kills green-in-dump
**Date:** 2026-06-07 · **On-chart:** "Jamal Context v0.1.3 (regime - slope + chandelier new-high)" (shorttitle "JC v0.1.3").
**Problem (user):** v0.1.2 showed GREEN during declines. Cause: my chand_dir re-greened on any close back above the short stop (a low bar), so a **bounce to a LOWER high during the early decline reclaimed it** while the 50-bar slope still lagged +1 → green on a downtrend bounce.
**Fix:** chand_dir is now a STRUCTURAL direction — **bullish (+1) ONLY on a fresh ce_len-bar high close**; bearish (-1) on a long-stop break OR a fresh low; else hold. Re-green therefore requires a NEW HIGH; a bounce to a lower high cannot turn it green. Rally still resumes green when it makes new highs after a pullback.
**Result (BTC 4h Feb–Jun):** the clear down-legs (May 13→end-May, and the June dump) are now **solid red — no green**. Residual: a green blip at the May 9–11 double-top (price at ATHs; the shallow May 7–9 dip to ~79k didn't break the *wide* 3-ATR chandelier, so it stayed +1) — "green at the top," not "green while dumping." Mix R/T/F = 52/45/2. **Status:** superseded by v0.1.4 (user: "the 1h timeframe doesn't make sense still").

## Context v0.1.4 — TF-normalize all regime windows to wall-clock (4h reference)
**Date:** 2026-06-07 · **On-chart:** "Jamal Context v0.1.4 (regime - tf-normalized)" (shorttitle "JC v0.1.4").
**Problem (user):** the 1h regime made no sense — it flipped GREEN on every 1–2 day bounce inside a clear downtrend (e.g. May 31–Jun 1, and "Trend-up" on the Jun 4–7 bottoming bounce). Cause: all windows are bar-counts tuned for 4h, so on 1h the 50-bar slope = ~2 days and the 22-bar chandelier high = ~1 day → a 2-day bounce IS a "trend" and any bounce makes a fresh 22-bar high → re-greens. Same code, different meaning per TF.
**Fix:** added `norm_tf` (default ON) — every window (slope, ATR, chandelier, ER, vol-pct, vol-MA, dwell, k_decontam) is a **4h-reference bar count** scaled by `tf_factor = 14400 / timeframe.in_seconds()` to its effective bar count, so the regime spans the SAME wall-clock horizon on any TF. 1h→×4 (slope 200, ce 88), 4h→×1 (50/22 unchanged), 1D→÷6 (8/4). Panel shows the effective slope/ce window. Thresholds (slope_enter/exit, ce_mult) unchanged — all windows scale together so the ATR/bar ratio stays comparable.
**Result:** **1h** (May 26–Jun 7): the whole decline is now **solid red, no bounce-green**; the Jun 4–7 bounce stays Trend-down; Mix R/T/F = **74/26/0** (now matches the v7 ~70%-Range target). **4h: provably unchanged** (factor 1.0 → Win 50/22, Mix 52/45/2, identical ribbon). The regime now reads the same multi-day trend on 1h as on 4h. **Status:** regime shading working across 1h+4h — awaiting user verdict.

# ========================= JAMAL OB — ORDER-BLOCK DETECTOR (BUILD LOG) =========================
**SCRAPPED (2026-06-08): the PIVOT-driven approach (v0.1) was deleted entirely at the user's request** — the `jamal-ob.pine` v0.1 (pivots) file, its design spec, and the on-chart study are removed (kept in git history only; the lesson about creating new TV scripts via Make-a-copy lives in memory `tv-new-script-via-copy`). **Replaced** by a different algorithm: a **sweep + walk-back + displacement/down-move-gated bullish demand-OB detector** (red down-leg → sweep of prior low → reclaim above the down-leg swing high → OB anchored at the highest-open red of the leg). New spec + step-by-step plan via the superpowers flow. TV saved-script name "Jamal OB" reused for the new code.

**PARKED (2026-06-09) at user request — full resume state saved to `docs/superpowers/specs/2026-06-09-jamal-ob-parked-state.md`.** Spec-validation phase: formation + confirmation rules LOCKED and user-validated on NEAR/BTC/ASTER daily, including two critical corrections — (1) confirm level = swing extreme over `[stop-candle…T]` *including* the walk-back stop-candle; (2) walk-back terminates only on STRUCTURE (green-that-held/doji/breakout), never on red-open monotonicity (the open-stop falsely truncated NEAR's Apr-24→May-4 leg). Scope: tag/invalidation DEFERRED; bullish+bearish coexist independently. No code written for the new algorithm yet; design doc pending. Next effort: **Jamal Fable** (separate indicator, own build log below when started).

## OB v0.1.0 — skeleton (sweep-driven two-line rebuild)
**Date:** 2026-06-27 · **On-chart:** "Jamal OB v0.1.0" (shorttitle "JOB0.1.0") · TV script "Jamal OB" (id USER;2ee1e9512ad04f5fb1aca04b07e3078d, pivot v0.1 overwritten)
**Code changes**
- New `jamal-ob.pine`: indicator decl, `SCRIPT_V`, `max_lookback` input, two `na` stepline plots (lower demand / upper supply), version table. No logic yet.
**Rationale:** verify file + TV target + render scaffold before adding sweep/walk-back logic. Note: targeting the existing "Jamal OB" TV script required opening it via the editor's script menu with a real CDP click — `pine_open` alone does NOT rebind the editor's save target (see memory `pine-editor-save-target-binding`; an earlier subagent attempt clobbered live Fable via this exact gotcha, since restored).
**Tests run:** `pine_smart_compile` on NEAR daily; clobber-check via `pine_open` line counts; `data_get_study_values`; screenshot.
**Results:** Compiles 0/0. Clobber-check: Jamal OB = 22 lines (skeleton saved correctly), Fable untouched. Version cell shows "Jamal OB v0.1.0"; both lines `na` (nothing drawn) as expected.
**Status:** scaffold for v0.1.0 bullish/bearish logic.

## OB v0.1.0 — bullish side (lower line = open_R)
**Date:** 2026-06-27 · **On-chart:** "Jamal OB v0.1.0"
**Code changes**
- `bull_sweep = close<open and low<low[1]`; `f_walkback_bull()` backward loop (structure-only termination, mid-leg green-pause skip via `low[i-1]<low[i] and high[i]<=high[i+1]`, highest-open-red R); `lower_line := open_R` on each confirmed bullish sweep.
**Rationale:** the demand line per spec §4.1; sweep-driven (moves on every new same-side sweep), self-prune achieved statelessly (each sweep re-walks from scratch).
**Tests run:** NEAR daily via replay — May-4 sweep (replay 2026-05-05) and May-16 sweep (replay 2026-05-17), read `data_get_study_values`.
**Results:** `OB lower (demand open_R)` = **1.407** (May 4, Apr-25 open) and **1.607** (May 16, May-13 open) — both EXACT vs the parked-spec oracle. Compiles 0/0; binding re-verified (nameButton "Jamal OB") before save.
**Status:** bullish side complete; bearish next.

## OB v0.1.0 — bearish side (upper line = open_R); v0.1.0 feature-complete
**Date:** 2026-06-27 · **On-chart:** "Jamal OB v0.1.0"
**Code changes**
- `bear_sweep = close>open and high>high[1]`; `f_walkback_bear()` mirror (lowest-open-green R, mid-leg red-pause skip via `high[i-1]>high[i] and low[i]>=low[i+1]`); `upper_line := open_R` on each confirmed bearish sweep.
**Rationale:** the supply line per spec §4.2; exact mirror of bullish; coexists independently with the demand line.
**Tests run:** NEAR daily via replay — May-12 green sweep; coexistence + by-hand OHLC trace.
**Results:** `OB upper (supply open_R)` = **1.547** (May 12 open) — EXACT vs oracle; lower line simultaneously = 1.596 (independent May 9–11 bullish leg, R = May-9 open), confirming coexistence. Compiles 0/0; binding re-verified before save.
**Replay-timing note (important for future MCP verification):** `replay_start(D)` makes **D−1 the *forming* (unconfirmed) bar**, so confirmed-bar-gated state reflects bars through **D−2**. First read of the bearish line at replay 2026-05-13 gave 1.261 (May-8's sweep, since May 12 was still forming) — NOT a bug. Re-read at 2026-05-14 (May 12 then confirmed) gave the correct 1.547. The bullish reads matched the oracle at D−1 only because both candidate sweep bars share the same leg/R.

## OB v0.1.0 — close-out (behavior + cross-symbol sanity)
**Date:** 2026-06-27 · **On-chart:** "Jamal OB v0.1.0"
**Tests run:** NEAR daily realtime screenshot (stepline render + self-prune behavior); BTC daily cross-symbol smoke (`data_get_study_values` + screenshot).
**Results:** Both steplines render correctly. **Self-prune confirmed visually:** during a sustained NEAR down-leg the green demand line holds flat at the leg origin (~2.392, the highest-open red at the top) rather than trailing price — each new-low sweep re-walks to the same origin, exactly the spec's "continuous descent collapses into ONE OB." Lines are independent OB anchors (no bracketing guarantee; lower>upper is valid). BTC daily: computes cleanly (lower 63,990.1 / upper 62,924.0), lines step and bracket price sensibly, no runtime errors. v0.1.0 done.
**Status:** **v0.1.0 SHIPPED.** Deferred for later versions (spec §7): confirmation + displacement/down-move gates, invalidation/kill behavior, multiplicity/fallback stack, OB boxes/tags.
**Build note:** entire v0.1.0 driven inline via the TradingView MCP after a subagent attempt clobbered live Fable through the editor save-target gotcha (restored; see memory `pine-editor-save-target-binding`). Targeting "Jamal OB" required opening it via the editor script menu with a real CDP click; every save was preceded by a nameButton binding re-check and followed by a clobber check. Spec: `docs/superpowers/specs/2026-06-26-jamal-ob-design.md`; plan: `docs/superpowers/plans/2026-06-26-jamal-ob.md`.

## OB v0.2.0 — `hold_until_swept` sticky mode (BOS-reset) + green-start walk-back
**Date:** 2026-06-27 · **On-chart:** "Jamal OB v0.2.0" (shorttitle "JOB0.2.0")
**Code changes**
- New input `hold_until_swept` (default OFF = exact v0.1). When ON, each side's line LOCKS at its current OB and relocates only when (a) its anchor low/high is wicked out (`low < bull_anchor_low` / `high > bear_anchor_high`), or (b) after a **structure break** — a close beyond the leg origin `*_bos` — the next sweep forms a fresh OB. State: `*_anchor_low/high`, `*_bos`, `*_broken`.
- Walk-back extended: `f_walkback_*(maxlb, s0)` now returns `[open_R, leg_swing]` where `leg_swing` = swing high/low over `[stop-candle..s0]` (the BOS level). **Green-start rule:** the walk-back anchor is offset `s0 = 0` when the anchor candle is the "right" colour (red for bull / green for bear), else `s0 = 1` (a green bullish anchor / red bearish anchor starts one bar earlier, so a green candle's open is never the OB level; a red sweep candle can still carry the line).
**Rationale (design iteration — two corrections found by testing):**
1. First cut (pure "hold until the anchor low is swept") was **degenerate**: the anchor only ratchets DOWNWARD, so it pinned to the lowest low of loaded history and stuck (NEAR sticky read **0.845** demand / **13.515** supply). Fix: reset the OB on an opposite-side **structure break** (close beyond the down-leg origin), so the line can relocate UP to newer OBs — killing the all-time-extreme pin.
2. Green breaking candles shouldn't seed `open_R` from their own (green) open → start the walk-back one bar earlier for them.
**Tests run:** NEAR daily via replay + realtime, `data_get_study_values`, toggling `in_1`.
**Results:** OFF = **1.596 / 1.547** at replay 2026-05-14 — byte-identical to v0.1 (regression clean). ON at the same bar = 1.596 / 1.547 (no longer 0.845/13.515 — degeneracy gone). Realtime side-by-side same bar: **OFF lower 1.867 vs ON lower 2.392** — sticky correctly HOLDS the deeper unswept demand OB while default re-anchors to a shallow recent one. Compiles 0/0; binding re-verified before save; toggle left at OFF default.
**Status:** v0.2.0 shipped. Still deferred (spec §7): confirmation gates (displacement / down-move), full invalidation/kill, multiplicity/fallback stack, OB boxes.

## OB v0.2.1 — intrabar wick-sweep relocation (sticky mode)
**Date:** 2026-06-27 · **On-chart:** "Jamal OB v0.2.1" (shorttitle "JOB0.2.1")
**Code changes**
- The sticky wick-sweep trigger (`low < bull_anchor_low` / `high > bear_anchor_high`) now fires **intrabar** — the moment the forming bar's low/high breaks the anchor, the line relocates live, instead of waiting for the bar to close. Split the old single `if barstate.isconfirmed` block into `*_wick` (every-bar, sticky only) and `*_conf` (confirmed-gated: bootstrap / post-break new sweep / default mode). Structure-break flag (`close > bull_bos`) stays confirmed.
**Rationale:** a wick sweep is inherently an intrabar event; waiting for the close just delays showing something that already happened. Colour-based triggers stay confirmed since they must know the candle is red/green.
**Repaint note:** the forming bar now repaints (line is provisional until close). **Closed-bar history is unchanged** — the wick is already in the bar's final low/high, so the committed value at close is identical to v0.2.0. Also confirmed: the sweep **counts even if the candle closes back above the anchor** (the trigger is the bar's LOW, not its close), and that relocation persists (the new anchor becomes the wicked low) — this was already true in v0.2.0; v0.2.1 just surfaces it live.
**Tests run:** NEAR daily replay, `data_get_study_values`, toggle both states.
**Results:** OFF = 1.596/1.547 and sticky ON = 1.596/1.547 at replay 2026-05-14 — both byte-identical to v0.2.0 (closed-bar regression clean). Compiles 0/0; binding re-verified; toggle left OFF.
**Status:** v0.2.1 shipped.

## OB v0.2.2 — demand-line freshness dimming (render-only)
**Date:** 2026-06-27 · **On-chart:** "Jamal OB v0.2.2" (shorttitle "JOB0.2.2")
**Code changes**
- Green line now renders BRIGHT (`color.new(green, 0)`) only once BOTH: (a) a bar **after** the one that set the line has **confirmed a close above it** (`bull_closed_above`), and (b) the level is **untouched** — no later bar's low has come back to it (`low <= lower_line` → `bull_touched`; the setting bar is excluded since its own low is below `open_R` by construction). Otherwise DULL (`color.new(green, 60)`, the fable passive-line idiom). Both flags reset on relocation, so **a fresh line always starts dull** (user-specified: on relocation, condition (a) is not yet true — even a green breaking candle closing above its own new level does not count). Touch detection is intrabar (a live wick dims immediately); the close-above arm is confirmed-bar only. Red line unchanged.
- State: `bull_touched`, `bull_closed_above` — render-only; line VALUES unchanged in both modes.
**Rationale:** brightness = "unmitigated + respected" demand (price accepted above the level and hasn't retested it); dull = untested-below, already-tagged, or not-yet-reclaimed. Visual triage without changing level logic.
**Tests run:** compile 0/0; BTC + NEAR realtime value reads (unchanged vs v0.2.1 logic); screenshots (dull segments render across BTC/NEAR downtrends; bright path = legacy full-green color); hand-trace of flag transitions on the NEAR May sequence (May-4 reloc → dull; May-6 confirmed close 1.488 > 1.407 → bright; May-13+ relocations reset).
**Results:** shipped; binding re-verified after a Pine-editor panel reopen (editor had closed mid-session — reopened via ui_open_panel, still bound to Jamal OB).
**Status:** v0.2.2 shipped. Red-line mirror of the freshness dimming NOT built (green only, as requested).

## OB v0.2.3 — freshness FIX (reclaim pass-through bug) + red mirror + DW flags
**Date:** 2026-06-27 · **On-chart:** "Jamal OB v0.2.3" (shorttitle "JOB0.2.3")
**Code changes**
- **Bug fix (user-reported "brightness isn't working"):** v0.2.2's touch check `low <= lower_line` counted the RECLAIM bar's own pass-through wick as a touch — a bar closing above the line necessarily wicks through it first (crypto perps don't gap), so `bull_touched` latched on the very bar that reclaimed, and brightness effectively NEVER fired (NEAR May-6: closed 1.488 > 1.407 but low 1.287 tripped the latch).
- **Corrected semantics: touches only count FROM ABOVE.** The touch latch is armed only while `bull_closed_above` is already true; the arming bar's own wick and all wicks from below (pre-reclaim) are ignored. Bright = reclaimed (confirmed close above on a bar after the setting bar) AND not yet retested; first low back at the line → dull until relocation (no re-arm).
- **Red mirror added** (user request): arms on a confirmed close BELOW the upper line; a later `high >= line` latches touched. Dull red = `color.new(red, 60)`.
- **DW plots** `DW lower/upper fresh (1=bright)` — freshness verifiable numerically via data_get_study_values.
**Tests run:** compile 0/0; NEAR daily replay ×3 reading DW flags.
**Results:** replay 2026-05-08 (last bar May 7): lower 1.407 fresh **1** — the previously-broken reclaim case now bright ✓. Replay 2026-05-12 (May 10 reloc): 1.596 fresh **0** ✓. Replay 2026-05-14 (May 12 armed 1.607>1.596; May 13 low 1.549 retested the line): fresh **0** — touch-from-above latch ✓ (OHLCV-verified May-13 low). All three state transitions confirmed.
**Status:** v0.2.3 shipped. (Session note: a platform permission-classifier outage paused this increment mid-flight; resumed cleanly, binding still Jamal OB.)

## OB v0.2.4 — first-touch bar stays bright (render-only)
**Date:** 2026-06-27 · **On-chart:** "Jamal OB v0.2.4" (shorttitle "JOB0.2.4")
**Code changes**
- The colour now reads the touched-state **as of the prior bar** (`*_prev_touched` snapshot taken before the freshness update): the first retest bar itself still renders BRIGHT; dimming takes effect on the NEXT bar. The latch itself is unchanged (still sets on the touch bar, still blocks re-arming, still resets on relocation). Both lines. Live nuance: a forming candle wicking into the line stays bright until that bar closes.
**Rationale:** user request — the candle that first tags the level is the retest itself; the visual downgrade belongs after it.
**Tests run:** compile 0/0; NEAR daily replay ×3 via DW fresh flags.
**Results:** replay 2026-05-14 (May-13 first-touch bar): lower fresh **1** (was 0 in v0.2.3) ✓. Replay 2026-05-15 (bar after touch): **0** ✓. Replay 2026-05-08 (reclaim regression): **1** ✓.
**Status:** v0.2.4 shipped.

## OB v0.3.0 — bright-freeze: a reclaimed line holds until retested (or BOS escape)
**Date:** 2026-07-02 · **On-chart:** "Jamal OB v0.3.0" (shorttitle "JOB0.3.0")
**Code changes**
- **Bright-freeze (both modes):** while a line is BRIGHT (reclaimed + untested), ALL relocation is suppressed — `*_reloc = (wick or conf) and not *_locked`, `*_locked = closed_beyond and not prev_touched and not broken`. Unlocks on either (1) **touch** — the retest that also starts the dulling; relocation resumes on the next sweep (the touch bar itself never relocates: lock reads prior-bar state), or (2) **escape** — a confirmed close beyond the leg-origin BOS level `*_bos` (price outran the whole leg; prevents the sticky-style staleness of a frozen line while price runs away). `*_broken` arming is no longer gated on `hold_until_swept` (needed in default mode for the escape; sticky semantics unchanged).
- Freshness state vars hoisted above the relocation blocks (lock needs them); freshness reset keyed to the gated `*_reloc`. New DW plots `DW lower/upper locked (1=frozen)`.
- **Emergent nuance:** if the reclaim close itself already clears the BOS level (strong reversal), the escape is pre-armed and the freeze never engages — behavior identical to v0.2.4. The freeze bites exactly when the reclaim close lands BETWEEN the line (open_R) and the leg origin (a tentative reclaim inside the leg's range).
**Rationale:** user request — "only reset the walk-back once the brightened OB line gets touched," with an escape hatch chosen over the literal freeze-forever variant (which reproduces the sticky staleness problem when price never retests).
**Tests run:** compile 0/0; NEAR daily replay ×4 via DW fresh/locked flags (default mode).
**Results:** 2026-05-08: 1.407 fresh 1 locked **0** (May-6 reclaim 1.488 also cleared bos 1.432 → escape pre-armed) ✓. 2026-05-12: 1.596 fresh 0 locked 0 (relocations fire when unlocked) ✓. 2026-05-14: 1.596 fresh 1 locked **1** (May-12 reclaim 1.607 < bos 1.631 → FROZEN) ✓. 2026-05-15: locked 0 (May-13 touch released it) ✓.
**Status:** v0.3.0 shipped.

## OB v0.4.0 — single mode (sticky) + bright-freeze without BOS escape
**Date:** 2026-07-02 · **On-chart:** "Jamal OB v0.4.0" (shorttitle "JOB0.4.0")
**Code changes**
- **`hold_until_swept` input REMOVED — sticky is the only mode.** The old default (re-anchor on every same-side sweep) is gone. Relocation = anchor wick-out (intrabar) or post-BOS-break sweep, bootstrap by plain sweep — the v0.2.x sticky core, now unconditional.
- **BOS escape REMOVED from the bright-freeze** (v0.3.0's unlock #2). `*_locked = closed_beyond and not prev_touched` — while bright, ALL relocation is suppressed and the ONLY unlock is a touch of the level. A never-retested bright line holds indefinitely (user-accepted, chosen against the HYPE example). `*_broken`/`*_bos` retained — they still gate the post-BOS sweep relocation path when the line is not bright. DW `locked` plots dropped (locked ≡ bright now).
**Rationale:** user expectation on HYPE weekly: the Jan-26 candle (close 30.573) brightens the 26.865 line and it must HOLD there until the Feb-23 candle touches it — v0.3.0 instead let the Feb-9 sweep relocate to 32.441 because the Jan-26 close also cleared the 28.4 leg origin (escape pre-armed). Also: one mode, not two.
**Tests run:** compile 0/0; HYPE weekly (BINANCE:HYPEUSDT.P 1W) replay ×3 via DW fresh flags.
**Results:** replay 2026-02-18 (post-Feb-9 sweep): lower **26.865 fresh 1** — freeze HELD (v0.3.0 gave 32.441) ✓. Replay 2026-03-04 (post-Feb-23 touch, low 25.613): 26.865 fresh 0 ✓. Replay 2026-04-01 (post-Mar-23 sweep, first after unlock): relocated to **38.342** ✓. Note: sticky-from-genesis changes ALL line history vs old default mode (e.g. HYPE upper now 22.193 where v0.3.0 default showed 37.399 at Feb-9) — expected, whole-mode change.
**Status:** v0.4.0 shipped.

## OB v0.4.1 — brightened lines never sweep-relocate (anchor wick-out only)
**Date:** 2026-07-02 · **On-chart:** "Jamal OB v0.4.1" (shorttitle "JOB0.4.1")
**Code changes**
- Removed the post-touch sweep relocation for lines that have EVER brightened: `*_conf` gains `and not *_closed_above/below` (the armed flag persists until relocation, so it doubles as "has brightened since set"). A brightened line: freeze while bright → touch dulls it → then it HOLDS its level; only an **anchor wick-out** (price violating the OB extreme, `low < anchor_low` / `high > anchor_high`) can relocate it. The BOS+sweep reset now applies only to never-reclaimed lines. One condition per side; everything else unchanged.
**Rationale:** user request ("remove the reset after brighten rule", clarified as the post-touch sweep relocation). A reclaimed level stays meaningful after one retest; it should only move when the OB is actually violated.
**Tests run:** compile 0/0; HYPE 1W replay + realtime via DW flags.
**Results:** replay 2026-04-01 (post-Mar-23 sweep): lower **26.865 held** (v0.4.0 relocated to 38.342) ✓. Same replay, upper 44.284 vs v0.4.0's 29.016 — the gate binds on the mirrored bear side too (bear had brightened during the earlier downtrend) ✓. Realtime: lower **26.865** — the January demand line still standing (v0.4.0: 66.936), dull (touched Feb-23, anchor 20.475 never violated); upper **59.714** — identical to v0.4.0, proving wick-out relocation still functions (the May/June highs wicked the bear anchors; histories reconverge after a shared reloc bar) ✓.
**Status:** v0.4.1 shipped.

## OB v0.5.0 — deterministic anchor-start (`State start date` input)
**Date:** 2026-07-03 · **On-chart:** "Jamal OB v0.5.0" (shorttitle "JOB0.5.0")
**Problem (user-surfaced):** the sticky state machine bootstraps on the first sweep of LOADED history and (post-v0.4.1 immortality) can pin there forever → (a) **path-dependence across devices** — user's mobile (short history) showed an Aug-12-2025 R candle on BTC daily while desktop (long history) showed a line frozen at 9,139.8 from 2020 (spot: 3,446 from 2018!); (b) unbounded staleness on long histories.
**Code changes**
- New `start_ts = input.time(timestamp("1 Jul 2025"), "State start date")`. `active = time >= start_ts` gates all relocation triggers (wick + conf, both sides), and the walk-backs take `t0` and **clamp** (`if time[i] < t0 → break`) so a leg can never reach pre-start bars. Every device computes identical lines from the same starting bar; a line can never anchor before the start date.
**Tests run:** compile 0/0; BTC.P 1D + HYPE 1W reads.
**Results:** BTC.P 1D: lower **60,224.7 BRIGHT** (June-2026 OB, standing reclaimed demand) vs v0.4.1's 9,139.8 relic; upper 108,934.6 unchanged (its lifecycle was already post-start — clamp is a no-op there, good consistency signal). HYPE 1W: 26.865/59.714 — byte-identical to v0.4.1 (regression clean; histories converge at shared reloc bars).
**Status:** v0.5.0 shipped. Mobile/desktop will now agree once mobile syncs; the start date is a per-chart input (move it forward for lower TFs if desired).

## OB v0.6.0 — walk-back pause test vs the leg's running extreme (wick-myopia fix)
**Date:** 2026-07-03 · **On-chart:** "Jamal OB v0.6.0" (shorttitle "JOB0.6.0")
**Problem (user-surfaced, BTC 1D Aug-2025):** the mid-leg pause test compared a candidate stop-candle only against the SINGLE next bar toward the anchor. Aug-11's 122,450 upper wick exceeded Aug-12's high → read as "red-that-held" → the bear walk from the Aug-13 sweep stopped immediately, R = Aug-12 (118,641.8) — even though Aug-13 itself took the wick out one bar later. User's structural read: the leg runs from the Aug-3 bottom.
**Code changes**
- Pause clause 1 now judges against the **leg's running extreme**: bear — a red "held" only if NO bar later in the leg traded above its high (`hi_seen > high[i]` where `hi_seen` = max high of bars already walked); bull mirror — a green "held" only if no later bar traded below its low (`lo_seen`). Clause 2 (break-down/out vs the earlier bar) unchanged. Strictly more permissive → walks only get longer, never shorter. Loop restructured so the BOS extreme still includes the stop-candle.
- Chosen over the fuller "swept-swing/leg-origin" redesign (which would have reached Aug-3 / 112,508.8) — that option remains open.
**Tests run:** compile 0/0; BTC.P 1D replay 2025-08-21; NEAR 1D replay 2026-05-14; HYPE 1W realtime.
**Results:** BTC Aug fixture: upper **114,069.6** (R = Aug-6; walk passes Aug-11's wick + Aug-8/9, stops at Aug-5's true breakdown vs Aug-4 low) — exactly as hand-traced ✓. HYPE 1W: 26.865/59.714 **byte-identical** (clean legs unaffected) ✓. NEAR 1D 2026-05-14: lower 1.200 (was 1.596), upper 2.625 (was 1.547) — walks now reach true leg origins; the June-2026 hand-validated oracles no longer bind (expected & warned; values anchor to deeper structure). User should eyeball NEAR/BTC dailies.
**Status:** v0.6.0 shipped.

## OB v0.7.0 — FVG identification, 4 timeframes (state only, NOT drawn)
**Date:** 2026-07-03 · **On-chart:** "Jamal OB v0.7.0" (shorttitle "JOB0.7.0")
**Code changes**
- 3-candle FVG detection on COMPLETED bars `[3][2][1]`: bull `low[1] > high[3]` → `[high[3]..low[1]]` (support below); bear `high[1] < low[3]` → `[high[1]..low[3]]` (resistance above). Leak-free/non-repaint: internal `[1..3]` offsets + `lookahead_on`; a gap is known from the open of the bar after the pattern completes.
- Four TFs: chart (local call) + D/W/M via `request.security`. **The latest-gap latch lives INSIDE `f_fvg_latest()`** — each security context keeps its own `var` state on its own series, so requesting a TF lower than the chart still returns the current latest gap. (First cut latched OUTSIDE from detection pulses; on a 1W chart the D pulses got lost to per-chart-bar sampling → stale Feb values. Caught in verification, rewritten.)
- Latest gap per TF/side only; NO mitigation tracking, size filter, or gap arrays yet (next layer, when this feeds the line logic). Nothing rendered — 16 Data-Window plots (`DW FVG {chart,D,W,M} {bull,bear} {top,bot}`).
**Tests run:** compile 0/0; HYPE 1W `data_get_study_values`.
**Results:** chart-TF values == W values on a 1W chart (built-in self-check) ✓; W bull 47.275/56.307 matches hand-scan of the weekly bars (mid-May rally gap: May-18 low > May-4 high) ✓; W bear 26.45/26.862 = the December gap (none since — uptrend) ✓; D bull 68.757/69.954 + D bear 64.30/65.202 current near spot (~65) after the in-context-latch fix ✓; M bear `na` (HYPE has never printed a monthly bear FVG) ✓.
**Status:** v0.7.0 shipped. OB line logic untouched (HYPE 1W lines 26.865/59.714 unchanged).

## OB v0.8.0 — FIRST-VIOLATION walk-back rule (unifies both user fixtures)
**Date:** 2026-07-04 · **On-chart:** "Jamal OB v0.8.0" (shorttitle "JOB0.8.0")
**Problem (user-surfaced, SOL.P 8h Jun-3-2026 5PM PST flush):** v0.6.0 walked through the Jun-3 00:00 UTC recovery green (because the flush EVENTUALLY undercut its low) → R = 81.25; the user's structural read: that green held — the next bar broke ABOVE its high (75.67 > 75.39) before anything broke below it, so the decline into the flush is a NEW leg from 75.21. This is the opposite pull from the BTC Aug-11 case (where the user wanted walk-through). One rule satisfies both:
**Code changes**
- **First-violation rule** replaces BOTH pause clauses: for a counter-leg candle, scan the bars after it chronologically (inner loop `j = i-1 .. s0`). Leg-direction break first (below a green's low / above a red's high) → PAUSE, keep walking. Counter-direction break first → the candle is the leg origin → STOP. Outside bar breaking both in one bar → pause; never violated → stop. `lo_seen`/`hi_seen` running extremes removed; O(n²) worst-case inner scan (trivial at max_lookback 200).
**Tests run:** compile 0/0; SOL.P 8h replay (Jun-4 + 1 step); BTC.P 1D replay 2025-08-21; HYPE 1W realtime.
**Results:** SOL flush candle: lower relocates to **75.21** (was 81.25) — the user's read, exact ✓. BTC Aug fixture: upper = **112,508.8** = the Aug-3 candle — the user's ORIGINAL structural instinct there, which the v0.6.0 minimal fix couldn't reach (it stopped at Aug-5 → 114,069.6); first-violation walks past Aug-11/Aug-8/9/5/2 (all overrun in leg direction first) and stops at Aug-1 (broken downward first) ✓. HYPE 1W: 26.865/59.714 byte-identical — third rule generation in a row ✓. Chart==D FVG self-check passes on the daily chart ✓.
**Status:** v0.8.0 shipped. Supersedes the v0.6.0 minimal fix (user-approved, knowing BTC moves to Aug-3).

## OB v0.9.0 — candle-anatomy stop (conviction body) + macro-extreme walk backstops + start Jan-2024
**Date:** 2026-07-04 · **On-chart:** "Jamal OB v0.9.0" (shorttitle "JOB0.9.0")
**Code changes**
- **Candle anatomy (user-chosen resolution of the Jan-30-green vs Aug-11-red contradiction):** when the first-violation scan finds the leg broke through a counter-candle in the LEG direction first, the candle still STOPS the walk if it is a CONVICTION candle — body ≥ `stop_body_frac` of its range (new input, default **0.47**; knife-edge calibration: Jan-30-2026 8h green = 0.49 → stop, Aug-8-2025 1D red = 0.45 → pause). Wick-spikes/indecision candles keep getting run through. Counter-direction-first and never-violated still stop regardless.
- **Per-side macro-extreme backstops:** walk-backs now clamp at the extreme bars since the start date — bull walks never extend past the macro-HIGH bar, bear walks never past the macro-LOW bar (`hh_time`/`ll_time`, confirmed-bar tracked). `max_lookback` default 200 → **500**.
- **Start date default → 1 Jan 2024** (input renamed "Start date"; bounds the extreme search AND the state machine).
**Tests run:** compile 0/0; BTC.P 8h replay Jan-31-2026 stepping through the 8AM-PST flush candle, at two start dates.
**Results:** **Anatomy verified:** with start Jul-2025, the flush relocation now stops at the Jan-30 16:00-UTC conviction green → lower = **84,211.4** (user's expected value; v0.8.0 gave 89,444.5) ✓. **CONFLICT FOUND:** with the shipped Jan-2024 default, NO relocation fires at that candle at all — the line sits frozen at **42,918.3** (a 2024-rally level, brightened+touched, anchor never violated since) — the v0.4.x staleness pathology re-created by the long window. The two features fight on the very fixture that motivated them; default start date needs a user decision.
**Status:** v0.9.0 shipped; anatomy ✓; default-start decision OPEN.

## OB v0.10.0 — new macro extreme RESETS that side's line (closes the v0.9.0 staleness conflict)
**Date:** 2026-07-04 · **On-chart:** "Jamal OB v0.10.0" (shorttitle "JOB0.10.0")
**Code changes**
- Per the user's clarified intent ("draw the FIRST green and red line from those extremes"): a **new macro HIGH since the start date voids the green line and resets its whole state** (`lower_line := na`, anchor/bos/broken/touched/closed_above cleared); the next bull sweep re-bootstraps, its walk-back bounded by the new top. Mirror: new macro LOW resets the red side. Old structure predating an extreme can never linger as a fossil line.
- **Bug found & fixed during verification:** the first cut reset the state but kept the old line VALUE drawn — the freshness block instantly re-armed brightness on the fossil (price far above it) and the bright-freeze then BLOCKED the re-bootstrap forever (BTC 8h showed 61,636 bright at Jan-2026). The line itself must clear on reset.
**Tests run:** compile 0/0; BTC.P 8h replay Jan-31-2026 fixture at the DEFAULT Jan-2024 start.
**Results:** lower relocates to **84,211.4** at the user's 8AM-PST flush candle — the anatomy stop at the Jan-30 conviction green — **at the Jan-2024 default** (v0.9.0 froze at 42,918.3 there). The Oct-2025 ATH reset wiped the 2024 fossil state; the v0.9.0 OPEN default-start decision is closed: extreme-resets make long windows safe.
**Status:** v0.10.0 shipped.

## OB — REVERT to v0.8.0 (v0.9.0 + v0.10.0 rolled back)
**Date:** 2026-07-04 · **On-chart:** "Jamal OB v0.8.0" (shorttitle "JOB0.8.0")
**Change:** user-requested revert. `jamal-ob.pine` restored verbatim from commit d016e21. Dropped: candle-anatomy conviction stop (`stop_body_frac`), macro-extreme walk backstops, extreme-reset line voiding, Jan-2024 start default, max_lookback 500. Back to: first-violation walk rule, start date Jul-1-2025, max_lookback 200. v0.9/v0.10 remain in git history (177e45c, abf849a) if wanted later.
**Tests run:** compile 0/0; BTC.P 8h replay Jan-31-2026 fixture.
**Results:** lower relocates to **89,444.5** at the 8AM-PST flush — exact v0.8.0 behavior restored ✓.
**Status:** live version = v0.8.0.

## OB v0.13.0 — SWEEP-REVERSAL walk-back stop (v0.12.0 mirror-bug fix; real-candle calibrated)
**Date:** 2026-07-07 · **On-chart:** "Jamal OB v0.13.0" (shorttitle "JOB0.13")
**Calibration (real candles, not synthetic):** re-calibrated the walk-back stop on REAL candle sequences via interactive tap-picker artifacts (user on mobile), after synthetic shapes (v0.12.0) regressed real fixtures. Two rounds of ground-truth picks:
- **Round 1 (SOL 8h, BTC 1D) SPLIT the field:** SOL demand → **75.21** (v0.8.0's value); BTC supply → **118,641.8 / Aug-12** (v0.12.0's shallow "stop at the wick-spike" read). This is the OPPOSITE of the Aug-3/112,508.8 the v0.8.0 log had recorded as the user's BTC instinct — the real-candle tap corrected that record (and matches the user's earlier "Aug 12 R candle" note). Neither single shipped rule reproduced both picks.
- **Round 2 (SOL 8h, BTC 1D, SOL 1W) confirmed 3/3,** incl. the SOL 1W Apr-2025 rally — a leg where the corrected rule and v0.8.0 DISAGREE (v0.8.0 first-violation walks past Mar-24 since Mar-31 broke below it first; corrected rule stops at Mar-24). The user's eye picked the corrected rule.
**Root cause:** v0.12.0 had the right idea (stop at a counter that swept the prior bar's extreme) but tested the HIGH on BOTH sides — a copy-paste mirror error. The demand side must test the LOW; that one flip is why v0.12.0 walked SOL 8h past its reversal green to 81.25 instead of stopping at 75.21.
**Code changes**
- **Sweep-reversal stop** replaces the v0.8.0 first-violation inner scan on BOTH sides. Bull demand: a GREEN counter STOPS the walk iff `low[i] < low[i+1]` (swept the prior/older bar's low → bullish reversal = leg origin); else PAUSE. Bear supply: a RED counter STOPS iff `high[i] > high[i+1]` (swept the prior high → bearish reversal); else PAUSE. Dojis stop; reds/greens in-leg still drive the running max/min of opens. The O(n²) `j`-scan is gone → single-neighbour O(n) compare.
**Tests run:** compile 0/0; SOL.P 8h replay 2026-06-05 (Jun-3 flush); BTC.P 1D replay 2025-08-21; ETH.P 1D replay 2026-06-28 (demand pause-branch); HYPE 1W realtime (regression guard). SOL 1W Apr-2025 leg is pre-start (Jul-2025) so not drawn on-chart — validated by the round-2 tap only.
**Results (on-chart, replay):** SOL 8h → lower **75.21** ✓ (user pick; also = v0.8.0); BTC 1D → upper **118,641.8** ✓ (user pick; v0.8.0 gave 112,508.8 — the corrected record); ETH 1D → lower **2,116.82** ✓ — the May–Jun flush demand line, whose walk PASSED THROUGH three green pauses (Jun-2/4/9 bounces, none made a new low) and stopped at the May-23 swept-low green: on-chart proof of the demand-side PAUSE branch. The later Jun-23/26 flush correctly did NOT relocate it (1510.87 never undercut the 1503.6 anchor, no BOS). HYPE 1W → upper **59.714** byte-identical; lower **26.865 → 24.455** (the demand leg is one where sweep-reversal and first-violation stops differ; expected, not a target). SOL 1W Apr-rally hand+tap → **105.84**.
**Status:** v0.13.0 shipped. Saved to TV script "Jamal OB" (bind-checked; Fable untouched). Supersedes v0.8.0 (which mis-stopped the BTC Aug leg at Aug-3) and the reverted v0.12.0 (bull/bear mirror bug). Calibration artifacts: real-candle tap-pickers (scratchpad `ob-real-calib.html`, `ob-real-calib2.html`).

## OB v0.14.0 — INSIDE-BAR series stop (the walk ends at any prior-extreme sweep, not only the reversal side)
**Date:** 2026-07-07 · **On-chart:** "Jamal OB v0.14.0" (shorttitle "JOB0.14")
**Problem (user, VVVUSDT.P 1D Nov-3/4-2025):** the green line leaked. Nov-4 swept the **Oct-10 swing low** (1.237 < 1.246) — a prior sweep — which should re-anchor demand at the **start of the down-series = Nov-3 open (1.642)**. Instead v0.13.0 walked back through the whole Oct-27→Nov-2 consolidation to Oct-27's higher open (**1.761**). Cause: v0.13.0's demand stop tested only whether a green swept the prior **LOW**; Nov-2 swept the prior **HIGH** (1.647 > 1.624 — a bear-side sweep = the swing high), so the walk ignored it and kept going. Both v0.13.0 AND v0.8.0 gave 1.761 here (genuinely new case).
**Insight (user):** no pivot detection needed — the swing highs/lows ARE sweeps (Oct-10 and Nov-2 are both sweep candles already). The down series ends at the first candle that takes out a prior extreme; only a bar fully inside the prior bar's range is a pause.
**Code changes**
- **Inside-bar stop, symmetric both sides.** A counter candle now ENDS the series (→ STOP, leg origin) UNLESS it is an INSIDE BAR of the prior (older) bar — `high[i] <= high[i+1] and low[i] >= low[i+1]` (swept neither extreme) → PAUSE. Any counter taking out a prior HIGH or LOW is a swing/sweep → the series is over → STOP. (v0.13.0 checked only the reversal-side extreme: bull the low, bear the high.)
**Tests run:** compile 0/0; VVV.P 1D replay Nov-5-2025; SOL.P 8h replay Jun-5-2026; BTC.P 1D replay 2025-08-21. SOL 1W hand-verified (pre-Jul-2025 start, not drawn on-chart).
**Results (on-chart replay):** VVV 1D → lower **1.642** ✓ (was 1.761 — the fix); SOL 8h → **75.21** ✓ unchanged; BTC 1D → upper **118,641.8** ✓ unchanged (lower 107,087.3 unchanged); SOL 1W Apr rally → **105.84** ✓ (Apr-28 is an inside bar → walked through; Mar-31 swept the prior low → stop). Shifts ETH's demand line shallower vs v0.13.0 (an on-chart-only value, never a validated target) — one of its walk-through greens made a new high.
**Status:** v0.14.0 shipped. Saved to TV "Jamal OB" (bind-checked; Fable v0.7.2 untouched). Supersedes v0.13.0 (reversal-side-only stop that leaked past pure swing highs like VVV Nov-2).

## OB v0.15.0 — 3-candle green-line stop (16-permutation calibrated); BULL side only
**Date:** 2026-07-07 · **On-chart:** "Jamal OB v0.15.0" (shorttitle "JOB0.15")
**Problem (user, SOL.P 1W Jun-1-2026):** the green line stopped at May-18 (a green that dipped below May-11's low) → **85.22**, instead of walking through to May-11's open (**96.42**). v0.14.0's inside-bar stop fired because May-18 swept the prior LOW — but here that low-sweep is a mid-leg bounce, not the origin.
**Method:** instead of guessing again, enumerated ALL 16 permutations of the tested green G's high/low vs its immediate LEFT (older, L) and RIGHT (newer, R) neighbours in a tap-picker artifact (`scratchpad/ob-green-perms.html`); user marked the landing for each. Truth table → a clean rule.
**Rule (bull/green ONLY):** at a green counter G, STOP iff `G.high > L.high` OR `R is entirely above G` (R.high > G.high AND R.low > G.low); else PAUSE (keep walking). Boolean `stop = a ∨ (¬b ∧ ¬d)` with a=hi>L, b=hi>R, d=lo>R. **`G.low vs L.low` is IRRELEVANT** — 8/8 permutation pairs differing only there were identical (a genuine asymmetry: the rule reads L's high but R's high+low). Code: green pause = `high[i] <= high[i+1] and (high[i] > high[i-1] or low[i] > low[i-1])` (i+1 = older L, i-1 = newer R).
**Bear side UNCHANGED** (still v0.14.0 inside-bar) pending the user's RED-line permutation table — keeps BTC Aug at 118,641.8. The bull rule mirrored would regress BTC (Aug-11 is the mirror-image of SOL-1W's May-18 but with the opposite user intent — STOP vs walk-through — so the red side needs its own table, not a flip).
**Tests run:** compile 0/0; SOL.P 1W replay Jun-8-2026; VVV.P 1D replay Nov-5-2025; SOL.P 8h replay Jun-5-2026; BTC.P 1D replay 2025-08-21.
**Results (on-chart):** SOL 1W → lower **96.42** ✓ (was 85.22 — the fix: walks through May-18 to May-11, stops at the May-4 green); VVV → **1.642** ✓ unchanged; SOL 8h → **75.21** ✓ unchanged; BTC → supply **118,641.8** ✓ + demand **107,087.3** unchanged. Fable v0.7.2 untouched.
**Status:** v0.15.0 shipped (BULL green rule). Red-line permutation table pending before mirroring.

## OB v0.16.0 — mirror the 3-candle rule onto the bear/red side (user: "just mirror it")
**Date:** 2026-07-07 · **On-chart:** "Jamal OB v0.16.0" (shorttitle "JOB0.16")
**Change:** the bear/red walk-back is now the EXACT MIRROR of the bull v0.15.0 3-candle rule (high↔low). At a RED counter, STOP iff `RED.low < L.low` OR `R is entirely below the red` (R.low<RED.low AND R.high<RED.high); else PAUSE. Code: red pause = `low[i] >= low[i+1] and (low[i] < low[i-1] or high[i] < high[i-1])`. (Was v0.14.0 inside-bar.) I flagged that mirroring is NOT a strict reflection of the user's intent (BTC Aug-11 is the mirror-shape of SOL-1W May-18 with the opposite call), but the user chose to mirror anyway.
**Prediction error (logged for honesty):** I told the user mirroring would drop BTC Aug supply to Aug-3 / **112,508.8**. WRONG — the mirror walks past Aug-11 but then STOPS at **Aug-5** (Aug-5.low 112,582.4 < Aug-4.low 114,053.8 = the mirror's "local bottom" stop), so the lowest green open in the walked leg is **Aug-6's open = 114,069.6** (coincidentally the old v0.6.0 value). Corrected the code comment + told the user the real value. Lesson: trace the full walk before quoting a resulting level — an intermediate stop was skipped.
**Tests run:** compile 0/0; BTC.P 1D replay 2025-08-21.
**Results (on-chart):** BTC → supply **114,069.6** (Aug-6 open; was 118,641.8 under v0.15.0), demand **107,087.3** unchanged. Green fixtures unaffected (bull rule untouched): SOL 1W 96.42, VVV 1.642, SOL 8h 75.21 all hold. Fable v0.7.2 untouched.
**Status:** v0.16.0 shipped. Both sides now the symmetric 3-candle rule.

## OB v0.17.0 — inside-candle edge-case fix (re-introduces G.low-vs-L); both sides
**Date:** 2026-07-07 · **On-chart:** "Jamal OB v0.17.0" (shorttitle "JOB0.17")
**Change:** ran a 6-case inside-candle tap-picker (`scratchpad/ob-green-inside.html`); the user's answers FLIPPED two of the original-16 permutations — **#13** (R engulfs G): continue→**STOP**; **#14** (R merely above G): stop→**continue**. This proves **`G.low vs L.low` (c) is NOT irrelevant** — the original 16-perm picker drew L and R the same size, hiding the inside-bar nature. (Corrects the v0.15.0 "c is irrelevant" claim.)
**Corrected bull rule:** STOP iff `G.high > L.high` OR ( `R.high > G.high` AND `G.low is NOT between L.low and R.low` ). Boolean `stop = a ∨ (¬b ∧ (c==d))` (a=hi>L, b=hi>R, c=lo>L, d=lo>R). Inside-bar reading: an inside candle walks through UNLESS the newer R engulfs it (bigger both sides). Bear = exact mirror. Code: pause = `not a and (b or (c != d))` with local bools (bull a_hi/b_hi/c_lo/d_lo; bear a_lo/b_lo/c_hi/d_hi). Fits all 22 data points (16-perm + 6 inside).
**Tests run:** compile 0/0; BTC.P 1D 2025-08-21; SOL.P 1W Jun-8-2026; VVV.P 1D Nov-5-2025; SOL.P 8h Jun-5-2026.
**Results (on-chart):** demand/green fixtures UNCHANGED — SOL 1W **96.42**, VVV **1.642**, SOL 8h **75.21**; BTC supply **114,069.6** + demand **107,087.3** unchanged (the change only touches inside-bar shapes, which the fixtures don't hit). Non-target SUPPLY lines shifted from the bear-side refinement: SOL 1W supply 200.57→**161.85**, SOL 8h supply 244.65→**233.79** (no locked target). Fable untouched.
**Status:** v0.17.0 shipped. Both sides on the symmetric 3-candle rule + inside-candle correction.

## OB v0.18.0 — TRAIL: reclaimed line leapfrogs to newest reclaimed OB (never fossilises on a runaway) — BUILT, SUPERSEDED
**Date:** 2026-07-07 · **On-chart:** "Jamal OB v0.18.0" (shorttitle "JOB0.18") · **never committed** (interim; folded into the v0.19/v0.20 commit).
**Problem (user):** "a bright green line that never gets touched because price ran away." A reclaimed-but-untested line froze at its OB while price rallied far above it — a stale fossil. User's rule: "a bright/untouched line can only move when another bright line is formed" → "always trail to the newest reclaimed demand" (chose v2 over bright-only).
**Change:** added CANDIDATE/SWAP trail. For ANY reclaimed line (bright OR dulled — gated on `*_closed_above/below`, NOT the freeze), a later same-side sweep past it tracks a candidate OB (`*_cand_line/anchor/bos`); when price RECLAIMS the candidate (`bull_swap`: close > cand; `bear_swap`: close < cand) the line LEAPFROGS to it and re-brightens. Touch no longer stops relocation — it only affects colour. Down direction unchanged (anchor-wick relocates). v1 (gate on `*_locked`) was insufficient — the line trailed up then a TOUCH dulled it and it stalled (dulled lines didn't trail); v2 fixed it by gating on reclaim.
**Tests run:** VVV.P 1D (the user's runaway example).
**Results:** green line climbed the whole rally instead of freezing — **1.161 → 19.1** at the top, **13.4** after pullback (vs. frozen 1.161 or dulled-stall 6.44 pre-trail). Both sides mirrored.
**Status:** SUPERSEDED. The trail solved the up-runaway but the user then pivoted the relocation model entirely (v0.19.0 FVG). Trail retired on green in v0.19.0, on red in v0.20.0.

## OB v0.19.0 — GREEN line = FVG relocation model; draw last-5 FVG zones (green/red) that vanish on touch
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.19.0" (shorttitle "JOB0.19")
**Change (user spec):** "the only way the green line moves now is if (1) a new anchor low happens, or (2) an FVG is formed and price enters it, triggering a new anchor + walk-back." Rewired the BULL line: relocate iff `bull_wick` (low < `bull_anchor_low`, intrabar) OR `bull_fvg_touched` (price re-entered a chart-TF bull FVG, confirmed-bar). Walk-back runs from the current bar (or the bar before if wrong colour to seed); moves the line ONLY if it returns a real level (`not na(oRb)` — "an eligible down-series behind the entry"). REMOVED on green: bright-freeze, post-BOS sweep, and the v0.18.0 trail. Brightness is colour-only now.
**Also (user):** draw the last 5 FVGs per side as light shaded zones that disappear on touch. Added `array<box>` pools (`bull_fvg_boxes`/`bear_fvg_boxes`, cap 5 each via push+shift), `box.new(..., extend.right)` green (support gap `[high[3]..low[1]]`) / red (resistance gap `[high[1]..low[3]]`); mitigate + delete on touch (bull: `low ≤ box top`; bear: `high ≥ box bottom`), descending-index remove loop (safe). `max_boxes_count = 50`. Bull FVG-touch feeds trigger (2). Red side left on the v0.18.0 trail (interim asymmetry, flagged).
**Tests run:** compile 0/0, saved; VVV.P 1D; bind-check (Fable v0.7.2 v28 untouched).
**Results:** demand **13.422** (dull), 3 untouched zones on chart (bull 9.77–10.10 & 7.26–7.41, bear 12.36–13.06 — the rest deleted on touch, confirming mitigation). Green ratcheted UP the rally via bull-FVG re-entries, stepped down to 13.422 on the pullback. Known accepted tradeoff: in a contiguous one-way drop the walk-back returns the leg origin, so the line parks above price until a FRESHER lower FVG is entered.
**Status:** superseded by v0.20.0 (red mirror + opacity + dead-code cleanup).

## OB v0.20.0 — MIRROR the FVG model onto red (symmetric); FVG fill opacity bump; trail fully retired
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.20.0" (shorttitle "JOB0.20")
**Change (user: "yes and yes"):** (1) mirrored the v0.19.0 FVG model onto the BEAR line — relocate iff `bear_wick` (high > `bear_anchor_high`) OR `bear_fvg_touched`, walk-back with `not na(oRs)` eligibility, freshness on `bear_did_reloc`. Removed the entire v0.18.0 red trail (`bear_swap`/`bear_cand_*`, `bear_locked`, `bear_conf`, `bear_broken`) and now-dead bull trail vars (`bull_broken`, `bull_cand_*`) + `bull_sweep`/`bear_sweep`. Both lines now follow ONE symmetric rule (high↔low mirror). (2) FVG fill opacity **90 → 82 transparency** (10% → 18%; borders 65 → 60) so the zones read on mobile without being heavy.
**Rationale:** finish the symmetric model the user asked for; retire the trail entirely (superseded by FVG relocation on both sides); make the "light shaded" zones actually visible on a phone.
**Tests run:** compile 0/0, saved; VVV.P 1D; grep-verified zero dangling refs to removed vars; bind-check (Fable v0.7.2 v28 untouched).
**Results:** demand **13.422** / supply **12.237** (both dull) — same current levels as v0.19.0 (deterministic; the bear path differs mid-history but converges at the last bar), 3 zones unchanged. Borders (40% opacity) carry the zones; fills lightly visible. Version cell "Jamal OB v0.20.0".
**Status:** shipped. Symmetric FVG relocation model on both sides; trail + bright-freeze + BOS-sweep all removed. Committed + pushed.

## OB v0.20.1 — FVG zones: shaded fill only, no border (cosmetic)
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.20.1" (shorttitle "JOB0.20.1")
**Change (user):** "you don't need to color the borders of the FVG, just shade." Both `box.new` calls: dropped `border_color`, set `border_width = 0`; bumped fill 82 → **78 transparency** (18% → 22% opacity) to compensate for the removed border so the shade still reads. Logic/relocation/mitigation unchanged — pure render.
**Tests run:** compile 0/0, saved; VVV.P 1D screenshot (bear FVG 12.36–13.06 renders as a soft-edged filled band, no border edge); bind-check (Fable v0.7.2 v28 untouched).
**Note:** the crisp rectangle-ish outlines still on chart are the demand/supply STEPLINES (staircase of OB levels), not the FVG boxes.
**Status:** shipped. Committed + pushed.

## OB v0.20.2 — mitigated FVGs KEPT and capped at the mitigating candle (no longer deleted)
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.20.2" (shorttitle "JOB0.20.2")
**Change (user):** "show the last 5 FVG; if mitigated, don't delete them, just cut them off from extending past the candle that mitigated it." The pool is now the last 5 FORMED per side (mitigated ones still count toward the 5). On first touch, instead of `box.delete` + `array.remove`, the box is CAPPED: `box.set_right(b, bar_index)` + `box.set_extend(b, extend.none)` so it stops at the mitigating candle and no longer trails right. Added a parallel `array<bool>` (`bull_fvg_mit`/`bear_fvg_mit`, index-aligned, push/shift in lockstep with the box arrays) to track per-box mitigation → the `*_fvg_touched` relocation trigger still fires exactly ONCE (on first touch). Mitigation loop now iterates ASCENDING (no in-loop deletion) behind the existing `size > 0` guard (which also avoids Pine's `for 0 to -1` descending-iteration foot-gun). Line-relocation logic unchanged.
**Tests run:** compile 0/0, saved; VVV.P 1D — box count 3 → **10** (5 bull + 5 bear, mitigated retained); screenshot shows short capped shaded rectangles ending at their touch candle; bind-check (Fable v0.7.2 v28 untouched).
**Status:** shipped. Committed + pushed.

## OB v0.21.0 — explicit START condition for the green line (swing-low sweep bootstrap)
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.21.0" (shorttitle "JOB0.21")
**Problem (user):** "we need to define a start condition when there is no green line yet at the beginning or the start date or the green line has just had a reset triggered." Under v0.19/v0.20 the only bootstrap was implicit — the first bull-FVG entry — leaving a warm-up gap with no line (visible on VVV.P 1D: no green line for the first stretch after listing) and no defined re-appear path after a future reset.
**Spec (user, AskUserQuestion-confirmed):** the first anchor candle = the first RED candle that takes out a previous SWING low. Swing low = **3-candle local low** (low below both neighbours; confirms one bar later). Take-out = **wick below** (`low <` the swing low; candle must be red). Line placement = the normal walk-back from that anchor (line logic unchanged).
**Change:** added `var float bull_swing_low` (most recent confirmed 3-candle swing low; the swing bar must be ≥ start date) and trigger `bull_boot = active and barstate.isconfirmed and na(bull_anchor_low) and close < open and not na(bull_swing_low) and low < bull_swing_low`; `bull_reloc` = wick OR fvg OR boot. Ordering subtlety: `bull_boot` is computed BEFORE the swing-low update on the same bar, so a bar that takes out the OLD swing while confirming a NEW lower one still fires against the old swing. `bull_boot` requires `na(bull_anchor_low)` → it is dormant while a line exists and is automatically the re-appear path after any future reset (reset trigger itself still undefined — next design step, along with the user's planned condition-2 modification). RED side unchanged (still FVG-entry bootstrap) until the user says mirror.
**Tests run:** compile 0/0, saved; VVV.P 1D listing bars (Sep-2025); BTC.P 1D sanity; bind-check (Fable v0.7.2 v28 untouched).
**Results:** VVV — green line now starts at the first red candle to wick below the first confirmed swing low (~bar 6 of the listing), level = highest red open of that first leg; previously no line existed until the first bull-FVG tap. Current values converge unchanged (13.422 / 12.237). BTC 1D — lines live and relocating through the 2026 decline; demand 60,224.7 (bright) / supply 58,605.4.
**Status:** shipped. Committed + pushed. OPEN: green-line RESET trigger undefined; condition-2 (FVG re-entry) modification pending — user's next topic.

## OB v0.22.0 — green-line RESET: bright line + new bull FVG above it → re-arm the start search
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.22.0" (shorttitle "JOB0.22")
**Spec (user):** "if the line is bright and a confirmed fvg forms above it, reset the green line logic as if it's at start date (don't move it immediately, but start looking for the new place to move it)."
**Change:** RESET trigger (confirmed-bar): line established (`not na(bull_anchor_low)`) AND bright coming into the bar (`bull_closed_above and not bull_touched`) AND a new bull FVG confirms this bar with its gap ENTIRELY above the line (`high[3] > lower_line`; exposed from the FVG block as `bull_new_fvg`/`bull_new_fvg_bot`). On reset: the LINE KEEPS DRAWING at its level (colour logic keeps running — it can still dull on a touch), but `bull_anchor_low := na` (condition 1 dormant; also what makes the v0.21.0 bootstrap re-arm), `bull_swing_low := na`, and a new **search epoch** `bull_seek_from := time` — swing lows only count from the reset bar and subsequent bull walk-backs clamp at the epoch instead of the start date ("as if at start date"). The search ends on the bootstrap sweep OR a bull-FVG entry, whichever fires first — the reset-causing FVG itself is a natural landing: price retracing into it fires condition 2 and relocates the line to the new demand. Reset requires an established line, so it can't re-fire while already searching. Interpretation choices (flagged to user): "fvg" = BULL FVG; "above it" = gap bottom above the line. New DW diagnostics: `DW lower searching (1=post-reset)` and `DW lower resets (lifetime)`. Bear side untouched.
**Tests run:** compile 0/0, saved ×2 (second pass added the reset counter); VVV.P 1D; bind-check (Fable v0.7.2 v28 untouched).
**Results:** VVV 1D — **8 lifetime resets** fired across the listing history (bright-line + FVG-above happened repeatedly in the Oct–Jun rally), line currently ESTABLISHED (searching=0) and converges to the same levels (demand 13.422 dull / supply 12.237 dull). Full-history screenshot: green line still ratchets the entire rally.
**Status:** shipped. Committed + pushed. OPEN: condition-2 (FVG re-entry) modification still pending — the user's original ask before the start/reset detour; red-side mirror of start+reset when requested.

## OB v0.23.0 — reset bright-gate removed + FULL bear mirror (symmetric lifecycle both sides)
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.23.0" (shorttitle "JOB0.23")
**Change (user: "you can remove the bright line as a precondition. also mirror the bear side"):**
1. **Reset precondition loosened:** the v0.22.0 reset no longer requires the line to be BRIGHT — ANY established demand line resets (goes into search, holds its level) when a new bull FVG confirms entirely above it. Dropped `bull_is_bright` from `bull_reset`.
2. **Bear side fully mirrored (high↔low):** START = the first GREEN candle whose high takes out the most recent CONFIRMED 3-candle swing high (`bear_swing_high`, swing bar ≥ epoch; wick take-out; confirmed-bar; boot check before the same-bar swing update). RESET = a new confirmed bear FVG forming ENTIRELY BELOW an established supply line (`low[3] < upper_line`; exposed as `bear_new_fvg`/`bear_new_fvg_top`) → anchor/swing cleared, epoch `bear_seek_from := time`, line keeps drawing. Bear walk-backs + swing tracker clamp at the bear epoch. New DW diagnostics: `DW upper searching`, `DW upper resets (lifetime)`. Both sides now run the identical START → RELOCATE (anchor-wick / FVG-entry) → RESET lifecycle with independent per-side epochs.
**Tests run:** compile 0/0, saved; VVV.P 1D; bind-check (Fable v0.7.2 v28 untouched).
**Results:** VVV 1D — bull lifetime resets **8 → 11** (the bright gate had been suppressing 3), bear lifetime resets **7** (mirror live). Both lines currently ESTABLISHED (searching=0/0) and converge to the same levels (demand 13.422 / supply 12.237, both dull). Full-history screenshot: both lines step-climb the entire rally.
**Status:** shipped. Committed + pushed. Repo .pine and TV source now byte-identical (injected the local file verbatim). OPEN: condition-2 modification (user's original pending topic).

## OB v0.24.0 — bright-touch RESET (both sides)
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.24.0" (shorttitle "JOB0.24")
**Spec (user):** "actually a touch of a bright green line also triggers reset." Mirrored to red per the v0.23.0 symmetry.
**Change:** added reset trigger (b): the FIRST TOUCH of a BRIGHT line — the same armed-first-touch event that dulls the colour (`bull_closed_above and not bull_touched and low <= lower_line`; bear mirror `high >= upper_line`) — also fires the reset (anchor/swing clear, epoch bump, line keeps drawing). NOT confirmed-gated (fires intrabar like the freshness latch; rolls back per Pine realtime semantics and commits at bar close; historical bars evaluate once). Reset per side = (a) new FVG entirely beyond the line (confirmed) OR (b) bright-touch. **Behavioral consequence: a BRIGHT line can never wick-relocate** — price must cross the line (→ touch-reset clears the anchor) before it can reach the anchor extreme; DULL lines wick-relocate exactly as before. Touch during search does nothing extra (reset requires an established line).
**Tests run:** compile 0/0, saved; VVV.P 1D; bind-check (Fable v0.7.2 v28 untouched).
**Results:** VVV 1D — bull lifetime resets **11 → 20**, bear **7 → 15** (the bright-touch events across history). Path changed on the supply side: upper now **13.221** and currently IN SEARCH (DW upper searching = 1 — a fresh reset waiting for its bootstrap/FVG landing); demand unchanged at **13.422** (established). Full-history: both lines still step-climb the rally.
**Status:** shipped. Committed + pushed. OPEN: condition-2 modification (user's original pending topic).

## OB v0.25.0 — condition-2 restructure: FVG entry moves from MOVE to START (both sides)
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.25.0" (shorttitle "JOB0.25")
**Spec (user):** "under MOVE, remove the bull fvg trigger. under START, add bull fvg trigger." (This is the condition-2 modification they'd been planning since before the start/reset detour.) Mirrored to red per standing symmetry.
**Change:** while a line is ESTABLISHED, the ONLY relocation trigger is now the anchor-extreme wick (`bull_wick`/`bear_wick`, intrabar). FVG entry (`*_fvg_touched`) is now purely a SEARCH-ENDING trigger: `bull_start_fvg = na(bull_anchor_low) and bull_fvg_touched` (bear mirror) joins the swing-sweep bootstrap as START (b) — whichever fires first ends the search and anchors the walk-back. Net flow: FVG-driven moves now happen ONLY after a reset (or at initial bootstrap) — an FVG forms beyond the line → reset → price retraces into a gap → line lands there. Gaps getting filled below/through an ESTABLISHED line no longer move it.
**Full v0.25.0 lifecycle (per side, symmetric):** START (no line): (a) counter-colour candle sweeps a post-epoch confirmed 3-candle swing, or (b) FVG entry. MOVE (established): anchor-extreme wick ONLY. RESET (established): (a) FVG confirms entirely beyond the line, or (b) first touch of a bright line — line holds its level, search re-arms, epoch bumps.
**Tests run:** compile 0/0, saved; VVV.P 1D; bind-check (Fable v0.7.2 v28 untouched).
**Results:** VVV 1D — demand **13.422** (established, dull), supply **12.936** (in search); resets 19/14 (paths differ from v0.24.0's 20/15 since FVG-relocations no longer occur mid-line). Full-history: lines step the rally with visibly FEWER mid-trend jumps (each step now = a reset→land cycle or a wick-out, not any passing gap-fill).
**Status:** shipped. Committed + pushed. The condition-2 modification is COMPLETE — no open design items on Jamal OB.

## OB v0.26.0 — bright-touch RESET removed (both sides); touch is colour-only again
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.26.0" (shorttitle "JOB0.26")
**Context:** on GRASSUSDT.P 1W the v0.24.0 bright-touch reset put the line into an 8-week search (Mar-16 bright-touch → nothing until the May-11 FVG entry), whose landing (the May-11 weekly's own open, a one-candle leg) prompted a full replay trace. After seeing the mechanism, the user removed the trigger: "remove b from RESET."
**Change:** deleted `bull_touch_reset`/`bear_touch_reset`; RESET per side is again ONLY a new confirmed FVG forming entirely beyond the line (bull above / bear below). A touch of a bright line is back to COLOUR-ONLY (dulls it, nothing else). **Consequence: bright lines can wick-relocate again** (v0.24.0 had made that impossible since the touch cleared the anchor before price could reach the anchor extreme).
**Lifecycle now (per side, symmetric):** START (no line): (a) counter-colour candle sweeps a post-epoch confirmed 3-candle swing, or (b) FVG entry. MOVE (established): anchor-extreme wick ONLY. RESET (established): FVG confirms entirely beyond the line — line holds its level, search re-arms, epoch bumps.
**Tests run:** compile 0/0, saved; GRASS.P 1W + VVV.P 1D; bind-check (Fable v0.7.2 v28 untouched).
**Results:** GRASS 1W — resets 3→**1** bull / 2→**1** bear (touch-resets gone); demand 0.4893 now ESTABLISHED + BRIGHT (was in-search under v0.25.0). VVV 1D — resets 19→**10** bull / 14→**8** bear; demand 13.422 established, supply 14.316 in search.
**Status:** shipped. Committed + pushed.

## OB v0.27.0 — full-leg walk-backs (no epoch clamp) + any-part-beyond reset geometry
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.27.0" (shorttitle "JOB0.27")
**Context (two user-caught cases, both replay-traced):**
1. **HYPE.P 1D May-26-2026:** a bull FVG [59.887..60.752] formed above the bright line (58.587) AND was entered on the same bar → reset + instant re-place, but the walk-back was EPOCH-CLAMPED at the reset bar, so it couldn't include May-25's red (open 62.79) — the line landed at May-26's own open 61.145. User: the walk should see the full leg.
2. **HYPE.P 1W Feb-9-2026:** the weekly gap [24.456..29.5] STRADDLED the line at 26.848 (bottom below, top above) → under "entirely above" no reset fired, though visually the gap sat above the line. User: any part above should count.
**Change (user: "1. full leg / 2. any part above"):**
1. Walk-backs are clamped at the START DATE only — `f_walkback_*` call sites pass `start_ts` again; the reset epoch (`*_seek_from`) now gates ONLY the swing tracker (post-reset swings).
2. Reset geometry: bull fires when the new gap's TOP > line (was: bottom > line); bear mirror fires when the gap's BOTTOM < line. Captured values swapped accordingly (`bull_new_fvg_top = low[1]`, `bear_new_fvg_bot = high[1]`).
**Tests run:** compile 0/0, saved; both fixtures replay-verified; bind-check (Fable v0.7.2 v28 untouched).
**Results:** HYPE 1D — after May-26 confirms, demand = **62.790** (May-25's open) ✓. HYPE 1W — the Feb-9 straddling gap now RESETS (bull resets 0→2 by mid-Feb) and same-bar form+enter chains reset→start → line re-places at 32.422 (Feb-9's own open — the one-candle-leg pattern again; open question stands). Reset counts rise overall under the looser geometry (by design).
**Status:** shipped. Committed + pushed. OPEN: one-candle-leg landings (parked).

## OB v0.27.1 — default start date → 1 Jul 2023 (~3 years back)
**Date:** 2026-07-08 · **On-chart:** "Jamal OB v0.27.1" (shorttitle "JOB0.27.1")
**Change (user):** default `State start date` moved 1 Jul 2025 → **1 Jul 2023** (~3 years back from today). The "as far back as it can go" case is inherent: symbols younger than the start date simply begin at their first bar (`active = time >= start_ts` is true from bar 0). Tooltip updated, including the determinism caveat.
**Caveat (flagged to user):** the start date originally existed for cross-device determinism (v0.5.0 — mobile loads less history than desktop). With a 3-year window, devices that can't load back to mid-2023 on older symbols may show different lines than desktop; the input can be tightened per-chart if that matters.
**Tests run:** compile 0/0, saved; HYPE.P 1D; bind-check (Fable v0.7.2 v28 untouched).
**Results:** HYPE 1D now computes from its listing (~Dec 2024, younger than the default): demand 70.729 / supply 53.289, resets 20/13 over the longer history. All prior current-value fixtures quoted under the Jul-2025 start are superseded by design (longer history = different paths); the RULES are unchanged from v0.27.0.
**Status:** shipped. Committed + pushed.

## OB v0.28.0 — a zone cannot be swept by its own creation candle (mitigation before detection)
**Date:** 2026-07-09 · **On-chart:** "Jamal OB v0.28.0" (shorttitle "JOB0.28")
**Problem (user, NEAR.P 1h Jul-8-2026, replay-traced):** at the close of the Jul-8-00:00-UTC bar a bull FVG [1.878..1.885] confirmed above the line (1.876) → reset fired correctly — but the gap's top is the PREVIOUS candle's low, and the forming candle's own low (1.884) was already 0.001 inside it. The engine counted that birth overlap as the FVG sweep: the once-per-box trigger fired on a GREEN candle whose walk-back found NO down-series (doji behind it, then a green local-top stop) → per the v0.19 eligibility rule the line held — and the zone was SPENT. When a red candle properly swept the zone 2 hours later with a real down-series behind it, nothing fired. User confirmed the intended model: "after a reset, it's just normal walk back logic starting from either a pivot sweep or a fvg sweep" — the divergence was WHICH candle counts as the fvg sweep.
**Change:** reordered the FVG block — MITIGATION RUNS BEFORE DETECTION. A box pushed this bar is not seen by the mitigation loop until the next bar, so a newborn zone survives its creation candle; the FVG sweep is the first LATER candle to enter the zone. Both sides (the block is shared). No other logic touched.
**Tests run:** compile 0/0, saved; NEAR.P 1h replay; bind-check (Fable v0.7.2 v28 untouched).
**Results:** NEAR 1h — reset still fires at the gap's confirmation (line 1.876 → search); the zone survives birth; the NEXT candle (red, low 1.88, real down-series behind it) sweeps it → line moves to **1.891** (that candle's open; walk: red seed 1.891 → green pause → doji stop). Later path re-converges: current line 1.930 unchanged. Lifetime reset counts shift across history (sweep timing changed everywhere) — expected.
**Status:** shipped. Committed + pushed. OPEN: one-candle-leg landings (parked).

## OB v0.29.0 — flat dojis follow the counter-candle 3-candle rule (calibrated); one-candle legs CONFIRMED as-is
**Date:** 2026-07-11 · **On-chart:** "Jamal OB v0.29.0" (shorttitle "JOB0.29")
**Calibration (two tap-picker rounds, artifact 77329157 / `scratchpad/ob-doji-oneleg.html`):**
1. **One-candle legs — RESOLVED, KEEP, no code change.** B1: a giant flush's OWN OPEN is valid demand (the GRASS-1W May-11 / HYPE-1W 32.422 landings were correct). B3: even with reds behind the green local top, still the flush's own open — **the walk never jumps a local top** (leg contiguity sacred). B4: 1-red legs fine.
2. **Doji rule — 12-case colour×sweep quiz** (doji colour red/green/flat × swept older red's high/low/both/nothing; newer neighbour held fixed): RED-body dojis → walk through ALL 4 (= reds, in-leg; engine already does this). GREEN-body dojis → stop iff swept the HIGH (= exactly the existing green 3-candle rule; engine already does this). FLAT dojis (close==open) → same pattern as greens → **should follow the green rule, not auto-stop**.
**Change:** the walk-back pause conditions widen by one character per side — bull `close[i] > open[i]` → `close[i] >= open[i]`, bear `close[i] < open[i]` → `close[i] <= open[i]` — so an exact open==close candle takes the calibrated counter-candle 3-candle path (stop = a ∨ (¬b∧(c==d))) instead of unconditionally breaking the walk. The in-leg branches stay strict (a flat doji contributes no open). Note: the quiz held the newer neighbour fixed with b true, so the flat-doji answers pin the a-branch; the ¬b∧(c==d) branch is inherited from the green table.
**Non-regression:** all 22 green-rule calibration points used strictly green G candles — unaffected. The v0.28.0 NEAR fixture re-derived by hand: the t23 flat doji STILL stops that walk under the full rule (¬a, ¬b, c==d → stop) → 1.891 landing unchanged.
**Tests run:** compile 0/0, saved; NEAR.P 1h sane (demand 1.899 / supply 1.881 after two more days of bars); bind-check (Fable v0.7.2 v28 untouched). (pine_open initially failed — the Pine Editor PANEL was closed after idle days; `ui_open_panel(pine-editor, open)` then rebind fixed it.)
**Status:** shipped. Committed + pushed. Walk-back calibration data now totals 34 points (16 perms + 6 inside + 12 doji).

## OB v0.30.0 — reset geometry test REMOVED: any new same-side FVG resets an established line
**Date:** 2026-07-12 · **On-chart:** "Jamal OB v0.30.0" (shorttitle "JOB0.30")
**Problem (user: "why is the red line stuck", ZEC.P 1W):** the supply line sat at **40.38** (the Sep-1-2025 weekly open = the origin of the 40→775 vertical) with price at ~545 and **ZERO lifetime resets** — even below the demand line (inverted). Root cause: (1) each rally high wick-fired a relocation but the contiguous green leg re-walked to the SAME origin every time; after the 775 top no high exceeded the anchor → MOVE dead. (2) The reset needed a bear FVG with any part BELOW 40.38 — every bear gap since formed at price, far ABOVE the line → RESET unreachable forever. Structural asymmetry: the any-part-beyond geometry assumes the line is on the price side it normally lives on; a monster one-way move strands the opposite line with all gaps forming on the wrong side. User confirmed the intended model on the Dec-8-2025 weekly: "dec 8 hits an fvg, wouldn't that reset? and walk back into its own open of that candle."
**Change:** dropped the position test from the reset — `bull_reset`/`bear_reset` now fire on ANY new same-side FVG confirming while the line is established (`*_new_fvg` alone; the `*_new_fvg_top/bot` captures deleted). The gap forming IS the fresh-structure signal; the search + sweep discipline decides where the line re-lands. Supersedes v0.27.0's any-part-beyond, which superseded v0.22.0's entirely-beyond.
**Tests run:** compile 0/0, saved; ZEC.P 1W replay of the user's exact fixture; bind-check (Fable v0.7.2 v28 untouched).
**Results:** ZEC 1W — supply un-stuck: 40.38 → **214.92** current (8 lifetime resets vs 0), demand 662.68 (10 resets). Replay: at the Dec-8-2025 close the bear gap [430.30–470] confirms → RESET fires (searching=1, line holds 40.38); Dec-15 (first later candle into the gap, high 457.78) sweeps it → walk-back (Dec-15 seeds 404.05 → Dec-8 green in-leg 342.67 → Dec-1 red local-bottom stop) → line = **342.67 = Dec-8's own open**, exactly the user's predicted landing. Reset frequency rises across all charts (every same-side gap now resets) — by design; the lifecycle is now: gap prints → search → next sweep re-lands.
**Status:** shipped. Committed + pushed.

## OB v0.31.0 — BRIGHT MEMORY (green side) — BUILT, REVERTED same day
**Date:** 2026-07-12 · **Commits:** a07f160 (build) → reverted; live = v0.30.0 again.
**What it was (user spec):** the drawn green line = the most recently ACTIVATED bright demand level; untouched brights remembered (stack, activation order, cap 20); a touch consumed the active bright and FELL BACK to the previous untouched one (chaining through several on a deep flush); memory empty → dull hold at the last consumed level; the v0.30 engine ran underneath as the candidate layer (activation = the reclaim arming edge). The v0.18.0 trail reborn + touch-fallback. Verified on VVV.P 1D: drawn 9.531 BRIGHT, memory depth 5, under price ~11.15.
**Why reverted:** the user said "revert" on seeing it — most likely the tall vertical FALLBACKS (a touch near the top of the rally dropped the drawn line to a much older, far deeper bright, producing large whipsaw steps). The concept may return with different fallback ordering (e.g., nearest-untouched-below instead of most-recent-by-time); the full implementation lives in git history at a07f160.
**Status:** REVERTED — jamal-ob.pine restored verbatim to v0.30.0 (on-chart tag "Jamal OB v0.30.0" re-injected).

## OB v0.32.0 — FVG detection at the pattern's own completing close (one bar earlier)
**Date:** 2026-07-13 · **On-chart:** "Jamal OB v0.32.0" (shorttitle "JOB0.32"; v0.31 skipped — burned by the revert)
**Problem (user, VVV.P 1D):** "on yesterday's daily candle close, I see it should've formed an fvg — why didn't it form?" The Jul-11 close completed a bear gap (Jul-11 high 10.945 < Jul-9 low 11.065), but the box didn't print. Root cause: the v0.7.0 detection offsets read the pattern as bars `[3][2][1]` and confirm at the close of the bar AFTER the third candle — a one-bar lag inherited from the un-gated DW latch (where `[1]/[3]` prevents intrabar repaint). The box/event pipeline is close-gated, so the lag was never necessary there.
**Change:** the drawn-box/event detection now fires at the PATTERN'S OWN COMPLETING CLOSE — the confirmed bar itself is the third candle: bull `low > high[2]` (gap `[high[2] .. low]`), bear `high < low[2]` (gap `[high .. low[2]]`). Same gap, same boundaries, one bar earlier, still zero-repaint. Boxes now span `[bar_index-1 .. bar_index]` at birth (displacement candle → completing candle; the old span included the unrelated detection bar). Downstream shifts one bar earlier with it: `*_new_fvg` resets, and the v0.28 birth rule now protects the completing candle (the NEXT bar is the first eligible sweeper). The 4-TF DW latch keeps the old `[1]/[3]` offsets (un-gated, would repaint intrabar; display-only) — the DW readout now LAGS the drawn boxes by one bar.
**Tests run:** compile 0/0, saved; VVV.P 1D; bind-check (Fable v0.7.2 v28 untouched).
**Results:** VVV 1D — the [10.945–11.065] bear zone now DRAWN (visible in the box list as {11.07, 10.95}), dated to Jul-11's close as the user expected. All FVG timing across charts shifts one bar earlier (resets/sweeps included) — paths re-shuffle accordingly (VVV resets now 29/37).
**Status:** shipped. Committed + pushed.

## OB v0.33.0 — STATELESS TRIGGER MODEL: resets/search deleted; three always-armed Triggers; series-bottom guard; vocabulary rename
**Date:** 2026-07-23 · **On-chart:** "Jamal OB v0.33.0" (shorttitle "JOB0.33")
**How it happened:** the user formalized vocabulary (ORIGIN = starts the down series, its open = the line; TRIGGER = fires a walk-back; BOTTOM/End = the series' lowest low), then dissolved the reset concept with one question — "what does kill mean? the line just sits there; the only way it moves is if a new trigger candle starts a new walk back." Exposed truth: resets never did anything visible — the established/search state's ONLY function was gating which events were allowed to be Triggers. So the gate is gone.
**Change:**
1. **Deleted the entire reset/search machinery** — reset conditions, lifetime counters, search epochs, searching flags, `*_new_fvg` capture flags. No states remain.
2. **Three Triggers, always armed (per side):** (1) BOTTOM sweep — price trades below the current series' lowest low (intrabar chain); (2) PIVOT sweep — a red candle takes out the most recent confirmed 3-candle swing low (one-shot per swing; the swing is consumed only when a placement actually succeeds off it — the v0.28 lesson); (3) FVG sweep — first later candle into a gap (one-shot per zone, unchanged). Any Trigger → walk-back → line = the Origin's open, with the eligibility rule unchanged. Bear = exact mirror.
3. **Placement guard = the series BOTTOM** (user-approved): walk-backs now return the leg's lowest low (bull) / highest high (bear); the guard := min(Trigger candle's low, leg low). Kills hollow re-Triggers off the old Trigger's wick; "you only become a new Trigger by sweeping the actual bottom." (`bull_anchor_low`→`bull_guard_lo`, `bear_anchor_high`→`bear_guard_hi`; `*_bos` info values dropped.)
4. Vocabulary rename throughout comments + DW: new plots `DW lower guard (series bottom)` / `DW upper guard (series top)`; searching/reset DW plots removed. Script shrank ~100 lines.
**Tests run:** compile 0/0, saved; ETH.P 1D replay of the June-dump fossil case; bind-check (Fable v0.7.2 v28 untouched).
**Results:** ETH 1D replay — mid-dump the line sits at **2021.59** (guard = flush bottom 1503.60 ✓ new guard plot); the Jun-7 close prints the [1600.56–1643.65] bull gap; **Jun-8 sweeps it → line steps to 1689.66** at that close — three days after the bottom, with zero reset machinery. Guard after placement = **1563.00** (the walked leg's bottom, deeper than the sweeping candle's own 1613.1 wick — placement guard verified). Current ETH: demand 1933.31 / supply 1841.08, both tight to price (~1907). The RESET calibration quiz (artifact ad2c2fce) is moot — superseded by this model; re-run a calibration only if real-chart eyeballing finds bad placements.
**Status:** shipped. Committed + pushed. Lifecycle is now two sentences: "A line is the walk-back of the most recent Trigger. A candle becomes the Trigger by sweeping the series bottom, a confirmed swing, or a gap."

## OB v0.33.1 — fix: guard poisoned to na when a walk-back runs off loaded chart history
**Date:** 2026-08-03 · **On-chart:** "Jamal OB v0.33.1" (shorttitle "JOB0.33")
**Problem (found in the v0.33 end-to-end code review):** the walk-back loop's history clamp was `if time[i] < t0 → break` — but one offset past the chart's first loaded bar, `time[i]` is `na`, `na < t0` is falsy, and the loop took ONE extra iteration before the na-candle's falsy branch broke it. That extra step ran `leg_lo := math.min(leg_lo, na)` → **na poisons the leg extreme** → `guard := math.min(low, na)` = **na** → Trigger 1 (BOTTOM sweep, `low < bull_guard_lo`) silently dead until a pivot/FVG sweep re-places the line and writes a fresh guard. The LINE itself was never wrong (`best_open` only accumulates from real red bars, and the loop's na-break predates v0.33) — pre-v0.33 the leg extreme was an unused info value, so the same latent flaw was harmless; v0.33 promoted it to the guard. Only bites when a walk reaches the chart's first bar without a normal stop: young listings (VVV's first weeks) or the first placements after the start date on short-history charts.
**Change:** both walk-back clamps become `if na(time[i]) or time[i] < t0 → break` — the edge check now runs BEFORE the leg-extreme update, so the na bar never contaminates it. Two one-line edits; behavior on long-history charts is byte-identical.
**Tests run:** compile 0/0, saved; ETH.P 1D values unchanged (demand 1917.31 / supply 1844.17, guards 1820.61 / 1898.50 — all real numbers); VVV.P 1D (the young-listing case) both lines + both guards real numbers (guards 11.492 / 14.844); bind-check (opened "Jamal OB" USER;2ee1e951… before injecting — Fable untouched).
**Status:** shipped. Committed + pushed.

## OB v0.34.0 — pivot-sweep and FVG-sweep triggers become toggles, DEFAULT OFF: by default the line moves only on new lows/highs
**Date:** 2026-08-03 · **On-chart:** "Jamal OB v0.34.0" (shorttitle "JOB0.34")
**Change (user request: "default without the swing low and fvg triggers and make them toggles, so the only way the green line moves by default is new lows"):** two new `input.bool` toggles, both default OFF — "Pivot-sweep trigger" (`use_pivot`) and "FVG-sweep trigger" (`use_fvg`). Gating: `bull_pivot` gains `(use_pivot or na(bull_guard_lo))`, `bull_reloc` uses `(use_fvg and bull_fvg_touched)`; bear mirror. With both ON the conditions reduce exactly to v0.33.1. FVG boxes still DRAW regardless (display unaffected); only the trigger is gated.
**Bootstrap exception:** with all guards `na` at chart start, the BOTTOM sweep can never fire (nothing to be below) — so the pivot sweep is ALWAYS allowed when that side has no guard yet (`na(guard)`), i.e. it retains its original v0.21 job of placing the FIRST line, then goes dormant if toggled off. Without this the indicator would be permanently blank at defaults.
**Accepted default trade-off (surfaced to the user):** in a long one-way move the opposite-side line freezes at the old extreme — ETH.P 1D at defaults: supply parked at 4,073.93 (guard 4,957.67 = the cycle top) with price ~1,856; demand 1,904.21 (guard 1,384.00 = the cycle-low chain). This is the v0.30-era "stuck line" pathology, now BY CHOICE at defaults; the toggles bring back the v0.33 step-toward-price behavior.
**Tests run:** compile 0/0, saved; ETH.P 1D defaults (values above — both lines = pure new-low/new-high chains ✓); VVV.P 1D defaults (bootstrap exception: first placement fires, then chains — demand 1.160 bright / guard 0.912 ≈ listing ATL, supply 18.479 / guard 21.562 ≈ ATH ✓); bind-check (same editor binding as v0.33.1 — Fable untouched). `indicator_set_inputs` could NOT flip the bool toggles (returns empty updated_inputs — MCP limitation with checkbox inputs); toggles-on equivalence to v0.33.1 verified by inspection (pure boolean reduction), not on-chart.
**Status:** shipped. Committed + pushed.

## OB v0.35.0 — self-bootstrapping chain: guard seeds from the first bar; pivot loses its bootstrap role; start date default ~4 years
**Date:** 2026-08-04 · **On-chart:** "Jamal OB v0.35.0" (shorttitle "JOB0.35")
**Change (user spec: "first green line should just take the lowest low back to the start date (default 4 years) and walk back from it"; implemented as the equivalent simplification):** the guard now SEEDS from the first active bar (`if active and na(bull_guard_lo): bull_guard_lo := low`; bear mirror with high), placed BEFORE the wick-trigger computation so the seed bar itself can't trigger. Every later record low is an ordinary BOTTOM sweep → walk-back → placement, so at any bar the line is BY CONSTRUCTION the walk-back of the lowest low since the start date (red: highest high) — exactly the user's rule, with no separate "find the minimum" step. The v0.34 pivot bootstrap exception (`or na(guard)`) is DELETED — pivot sweep is now purely toggled (dead code once seeding exists). Start date default 1 Jul 2023 → **1 Aug 2022** (~4 years; static date, not a moving "today−4y" — a creeping cutoff would let old extremes silently fall out of the window and shift lines overnight; explained to user). Failed early walks (record low with no red series behind) just retry on the next record low — existing semantics.
**Tests run:** compile 0/0, saved; ETH.P 1D defaults: demand **1,644.08** / bottom **1,071.14** = the walk-back of the Nov-2022 (FTX-crash) record low — the lowest low since Aug-2022, frozen since, exactly the rule's prediction (was 1,904.21/1,384.00 under the 2023 start); supply 4,073.93 / top 4,957.67 unchanged (same post-2022 ATH). VVV.P 1D defaults: **identical to v0.34** (demand 1.160 bright / 0.912 ATL, supply 18.479 / 21.562 ATH) — seeded chain converges to what the pivot bootstrap produced, good consistency signal. Bind-check (pine_open "Jamal OB" USER;2ee1e951… before inject — Fable untouched).
**Status:** shipped. Committed + pushed. Default lifecycle is now ONE sentence per side: "the green line is the walk-back of the lowest low since the start date; the red line is the walk-back of the highest high."

## OB v0.36.0 — gap+pivot COMBO trigger (single toggle, default OFF), quiz-calibrated; replaces the separate pivot/FVG toggles
**Date:** 2026-08-06 · **On-chart:** "Jamal OB v0.36.0" (shorttitle "JOB0.36")
**How the rule was derived:** three rounds of BTC-1D tap quizzes (artifact 9ae0f664; real candles Oct-2022→Jan-2024, drawn given-line premises computed by the real walk-back). Round 1 (5 cases): marks Mar-27 / Jun-30 / Sep-24-2023; C1 NEVER across the whole Jan-2023 breakout; C5 none (the Jan-3-2024 flush sweeps pivots but no gap, and stops 105 pts above the Bottom). Round 2 (zoom tie-breakers): Sep-24 re-confirmed with the decisive note "Fvg taken earlier and then this candle takes the last pivot that formed" (a SEQUENCE, not a same-candle AND); Oct-11 added (a Round-1 omission at small scale); Jun-30 (green close) confirmed. Round 3 (April discriminator): Apr-24 marked, Apr-21 not — the swept swing must have FORMED at/after the gap dip (Apr-21's swing predates the Apr-17 dip; Apr-24 sweeps the Apr-21 swing born after it).
**THE RULE (bull side; bear = exact mirror):** a candle that takes out the most recent CONFIRMED 3-candle swing low is a Trigger only if a bull gap is involved — (a) SAME CANDLE: it is also the first candle to dip into a gap, or (b) SEQUENCE: a gap was dipped earlier since the last placement (the ARM) and the swept swing formed at or after that dip. Candle colour irrelevant (the old pivot trigger's red-close requirement is gone). Swing take without gap: nothing. Gap dip without swing take: nothing by itself, but sets the arm. Any successful placement clears the arm. One-shot per swing (consumed only on successful placement — v0.28 lesson) and per zone (first touch caps the box, as always).
**Code:** `use_pivot`/`use_fvg` inputs removed; single `use_combo` (default OFF). New state per side: `*_swing_bar` (bar_index of the swing candle) and `*_arm_bar` (bar_index of the first gap dip since the last placement, na = unarmed). Trigger: `sweep and (fvg_touched or (not na(arm_bar) and swing_bar >= arm_bar))`. Arm set in the trigger block right after the FVG block (same-bar dips can both arm and fire via the `fvg_touched` branch). With `use_combo` false, `*_reloc` reduces exactly to the v0.35 chain.
**Tests run (temp builds with combo ON + shifted start dates, BTC.P 1D replay):** start Sep-1-2023 — line 26,240.7/Bottom 24,888 through Sep-23 (the Sep-21 gap dip arms but does NOT move ✓), **27,195.9** after Sep-24 ✓, **27,943.0**/Bottom 26,525 after Oct-11 ✓ — all three exactly the quiz-predicted walk-backs. Start Jun-1-2023 — **30,683.2**/Bottom 29,500 the day Jun-30 closes (same-candle path, green candle ✓). Late-July follow-up moves (31,4xx→30,070.9, Bottom 28,830) traced to the ALWAYS-ON new-low chain after Jun-30 reset the Bottom to 29,500 — correct default behavior, not the combo. Final build (defaults: combo OFF, start 1 Aug 2022) compiled 0/0; BTC defaults sane (16,693.0/15,443.2 demand off the Nov-2022 bottom; 108,934.6/126,208.5 supply); single study instance on chart; user's QQQ chart restored; bind-check (pine_open "Jamal OB" USER;2ee1e951… before every inject — Fable untouched).
**Status:** shipped. Committed + pushed. Start-date/first-line rule remains deferred per the user.

## OB v0.37.0 — combo gated to the catch-up direction: green combo only while price is above the green line (bear mirror)
**Date:** 2026-08-06 · **On-chart:** "Jamal OB v0.37.0" (shorttitle "JOB0.37")
**Change (user intent: "this logic is intended to keep the green line from being left behind... when toggled on, the logic should only work when price is above the green line, and dormant when price is below"):** new per-side gate on the combo — bull: `bull_px_above = not na(lower_line) and close[1] > lower_line`; bear mirror `close[1] < upper_line`. The gate wraps BOTH arming and firing (fully dormant below the line). It reads the PREVIOUS confirmed close, not the trigger candle's own position, because the fixtures demand it: Sep-24-2023 closed 8 pts below the line and Oct-11 closed 331 pts below it, yet both must fire — what matters is that price was living above the line coming into the candle. With no line yet (na), the combo is dormant and the chain bootstraps as usual. Chain (Trigger 1) unaffected.
**Tests run:** compile 0/0, saved; temp build (combo ON, start 1 Sep 2023), BTC.P 1D replay: 27,195.9 after Sep-24 ✓ and 27,943.0 after Oct-11 ✓ — the gate blocks neither fixture (gate values coming in: 26,563 > 26,240.7 and 27,381.2 > 27,195.9). Dormancy is a plain boolean cut on the same verified path. Final build defaults unchanged (combo OFF, start 1 Aug 2022); version tag v0.37.0 confirmed on chart; user's QQQ chart restored; bind-check held (same Jamal OB editor binding).
**Status:** shipped. Committed + pushed.

## OB v0.38.0 — gap CLOSE-FILL trigger (sandbox-calibrated), replaces the v0.36/v0.37 gap+pivot combo entirely
**Date:** 2026-08-06 · **On-chart:** "Jamal OB v0.38.0" (shorttitle "JOB0.38")
**How the rule was derived:** the walk-back sandbox (artifact b790385f — tap a candle → it becomes a Trigger, walk-back plots live) with the exhaustive-tap protocol: the user tapped EVERY candle where the green line should move across Oct-2022→Jan-2024 BTC 1D (21 taps, 1 wrong-flag), so non-taps are deliberate negatives. Node analysis (scratchpad ob-sandbox-analysis.js / ob-sandbox-sim.js / ob-final-model.js) profiled every tap and simulated candidate engines. All 21 taps are red candles taking the previous low; the set decomposes exactly into (a) chain new-lows (already the default trigger) and (b) the user's note "Note the candles closing completely the fvg" → CLOSE-FILL: the first candle to CLOSE below a bull gap's bottom. Close-fill separates every previously-confusing pair (Sep-21 closes 62 pts through its zone = trigger; Oct-3 dips but closes above = nothing). Follow-up answers: Dec-19-2022 flag = the walk should stop BEFORE the previous Trigger (16,768 = Dec-18's open, not 17,804) → close-fill walks CLAMP exclusively at the last line-moving Trigger (chain walks stay unclamped — Nov-9-2022's idempotent full-leg walk must stay silent); Jan-18-2023 = mis-tap (dropped — it was the only non-chain non-fill tap); marginal fills COUNT (any margin below the bottom; Feb-4/Sep-6-2023 were user omissions).
**Change:** `use_combo` + ALL pivot/swing machinery deleted (`*_swing_low/bar/swept`, `*_arm_bar`, the swing tracker, the v0.37 gate). New `use_fill` toggle (default OFF). New per-side state: `*_fill_bot/top` + `*_fill_done` float/bool arrays (close-fill bookkeeping SEPARATE from the visual boxes — a zone stays fill-armed after the first-touch cap; capped at 30 zones; the Aug-17 fixture filled two-month-old June zones) and `*_move_bar` (bar_index of the last level-changing placement = the fill-walk clamp). Walk-backs gain a `stop_bar` param (exclusive clamp). Fill fires on confirmed close beyond the zone (bull: below bottom; bear mirror: above top), one-shot per zone, both directions, no price-side gate.
**Tests run:** compile 0/0, saved; temp build (fill ON, start 1 Oct 2022) on BTC.P 1D replay vs the simulated path: after Dec-19-2022 → **16,768.1**/Bottom 16,210 (the clamped landing the user chose) ✓; after Nov-14-2023 → **37,330.3** ✓; after Jan-3-2024 → **44,979.7**/Bottom 40,333 ✓. The full simulated path matches all 20 valid taps' levels. Disclosed deviations (engine fires the user did not tap, all rule-consistent): early same-leg fills land the same level a few bars sooner (Mar-7 vs Mar-10, Aug-15 vs Aug-17); the user-endorsed marginal fills add moves they had missed (Feb-4 → 23,730, Sep-6 → 25,962, Nov-28-2022 → 16,596); crash stair-steps (Mar-8/9, Apr-21, Aug-17 → 29,189) where a clamped fill steps down and a later unclamped chain walk can step back up. Final build (fill OFF, start 1 Aug 2022) compiled 0/0, tag verified, QQQ restored, bind-check held.
**Status:** shipped. Committed + pushed. With the toggle OFF, behavior is byte-identical to v0.35 defaults.

## OB v0.38.2 — walk-back restored to the original, unmodified rule (v0.38.0 clamp + v0.38.1 threshold both reverted; v0.38.1 never shipped)
**Date:** 2026-08-07 · **On-chart:** "Jamal OB v0.38.2" (shorttitle "JOB0.38")
**What happened:** the user, testing v0.38.0 with the fill toggle on ETH.P 1D, asked why the May-16→17-2026 walk-back "did not go all the way." Diagnosis: May-17 close-filled a 3.4-pt bull gap born Apr-8 ([2,174.41..2,177.77] — its DRAWN box was capped at first touch Apr-10 and long rotated out of the last-5 visuals, but the fill bookkeeping kept it armed); the fill walk then hit the v0.38.0 clamp because May-12's fill had "moved" the line 2,368.32 → 2,370.21 — a $1.89 technicality — truncating the walk at May-13 and stepping the line down to 2,282.06 instead of the full-leg 2,370.21. A v0.38.1 fix (clamp anchor only on moves > 0.5% of price) was built and replay-verified (ETH held 2,370.21; BTC Dec-19 still 16,768.1) but the user rejected the whole approach mid-ship: "the walk back logic should never have changed."
**Change:** BOTH the v0.38.0 previous-Trigger clamp and the v0.38.1 0.5% threshold are deleted — `stop_bar` param removed from both walk-backs, `*_move_bar` state removed. The walk-back is the original v0.17/v0.29 rule, identical for every trigger, full leg, no exceptions. LESSON (recorded in memory): the walk-back is settled 34-point-calibrated logic — never modify it to satisfy a single fixture; the Dec-19 answer defined a LANDING preference, not a licence to restructure the walk.
**Known consequence (disclosed):** the Dec-19-2022 fixture's fill now walks to 17,804 — the level already in force — so the line does not move there (the user's chosen 16,768 landing is no longer produced). If that case still matters, it needs its own rule derived from more examples.
**Tests run:** compile 0/0, saved; temp build (fill ON): BTC.P 1D replay Dec-21-2022 → line **17,804.0** (full walk confirmed, clamp gone); ETH.P 1D replay May-19-2026 → line **2,370.21**/Bottom 2,074.26 (the user's complaint case: line holds through May 16-17, no step-down). Final build (fill OFF default) compiled 0/0; QQQ restored; bind-check held.
**Status:** shipped. Committed + pushed.

## OB v0.39.0 — RED-BRIGHT trigger (third Trigger on the green line; single toggle, default OFF)
**Date:** 2026-08-10 · **On-chart:** "Jamal OB v0.39.0" (shorttitle "JOB0.39")
**How it came up:** the user sent a phone screenshot of BINANCE:HYPEUSDT.P 1D asking what moved the green line around Feb 21-22 2026. Desktop (toggle OFF) read 25.418 flat across Feb 20/21/22 while the phone showed 28.107 — I wrongly attributed the gap first to loaded-history divergence, then to a different indicator owning the label. Both were wrong: the phone simply had `use_fill` ON. Replay with the fill toggle on reproduced the screenshot exactly (28.107 green / 27.280 red at the Mar-3 bar, volume 14.71 M matching). The two labels decode as Origin opens: 28.107 = Feb-27's open (red candle), 27.280 = Feb-28's open (green candle). The actual Feb move: a bull FVG spanning Feb-19 high 29.410 → Feb-21 low 29.524 (width 0.114, **0.39%** of price) was close-filled by Feb-22's close at 29.015; the walk-back ran Feb-22 → Feb-21 → stopped at Feb-20 (green, high 30.43 > Feb-19's 29.41), landing the line on Feb-21's open **30.364** — a 0.39% gap relocating the level by 31%. LESSON: check the study's input state before theorising about data divergence.
**Change:** new `use_redlit` input (`in_2`, default OFF; `start_ts` re-indexed to `in_3`). New `bear_lit_evt` flag raised on the arming edge inside the bear freshness block. New `bull_redlit` Trigger 3 OR'd into the existing bull relocation condition — **the walk-back, the guard update, and the hold-on-na rule are untouched and shared with Triggers 1 and 2** (user directive: it is an additional entry point, nothing more). One-shot per red-line placement by construction, since `bear_closed_below` latches until the next bear relocation. **Evaluation order swapped:** the bear side now runs relocation AND freshness before the bull side, because the trigger is produced by bear freshness and consumed by bull relocation on the same bar; the two sides read none of each other's state, so the swap is order-neutral. New DW diagnostics: `red-lit trigger` (per-bar), `red-lit count (cumulative)`, `red-lit relocations` (redlit as sole cause) — the gap between the last two is the na-rate.
**Tests run:** compile 0/0, saved, tag v0.39.0 confirmed on chart. **Regression (`use_redlit` OFF, `use_fill` ON), HYPE.P 1D:** live bar 55.840 / 52.201, guards 51.107 / 57.999 — identical to v0.38.2; Feb-23 replay bar 30.364 / 28.843, guards 25.613 / 32.344 — identical to v0.38.2. **Toggle ON, same symbol (~300 bars):** `red-lit count` **51**, `red-lit relocations` **19** — the trigger fires roughly every 6 bars and is the sole cause of 19 relocations that would not otherwise happen. Endpoint converges: live values with the toggle ON are identical to OFF (55.840 / 51.107), i.e. the 19 extra relocations wash out of the chain by the last bar on this symbol. Bind-check held (`ui_open_panel pine-editor open` → `pine_open "Jamal OB"` USER;2ee1e951… before every inject — Fable untouched).
**Open / not done:** no mirror (green-bright → red relocation) — deliberately out of scope, it is a different signal needing its own calibration. The 51-vs-19 split is not yet decomposed into "walk returned na" vs "a sweep or fill co-fired on the same bar"; both are folded into the 32. No multi-symbol sweep yet — every number above is HYPE.P 1D only.
**Status:** shipped, default OFF. Behaviour with the toggle off is v0.38.2 exactly.

## OB v0.40.0 — BRIGHT-LINE trigger mirrored (green-bright → red walk-back); three-stage bar evaluation
**Date:** 2026-08-10 · **On-chart:** "Jamal OB v0.40.0" (shorttitle "JOB0.40")
**Change:** `use_redlit` **renamed to `use_lit`** ("Bright-line trigger", still `in_2`, still default OFF) and now covers BOTH directions, matching the `use_fill` precedent of one toggle per feature. Red bright → `f_walkback_bull` → green line moves (v0.39.0 behaviour, unchanged). **New mirror:** green bright (first confirmed close above the lower line since its last relocation) → `f_walkback_bear` → red line moves. Both walk-backs, both guard updates and the hold-on-na rule are untouched and shared with Triggers 1-2.
**Why the restructure:** the two bright triggers are **mutually recursive** — red-bright feeds the bull walk, green-bright feeds the bear walk, and each side's lit edge is itself gated on whether that side relocated this bar. No single top-to-bottom pass resolves that. The bar is now evaluated in three stages: **PASS 1** both sides relocate on Triggers 1-2 only (sweep, close-fill); **LIT** both freshness blocks run, each gated on its own side's pass-1 relocation exactly as before, raising `bear_lit_evt` / `bull_lit_evt`; **PASS 2** the cross triggers fire, each skipped if that side already relocated in pass 1, each doing its own freshness reset on landing. The pass-2 skip is free: a walk-back's result depends only on its anchor bar (this bar or the one before, by candle colour), so a second walk on the same bar returns an identical level — which is why this is behaviourally identical to v0.39.0 for red→green. **Tie-break:** if both lines go bright on one bar, red→green resolves first and cancels the green's own lit event, since the level it lit against has just been replaced.
**Tests run:** compile 0/0, saved, tag v0.40.0 confirmed. **Regression (`use_lit` OFF), HYPE.P 1D live bar:** 55.840 / 52.201, guards 51.107 / 57.999 — identical to v0.38.2 and to v0.39.0-OFF. Strong equivalence signal: with the toggle OFF the **red-lit count is 51**, exactly matching v0.39.0's count, confirming the three-stage restructure preserved the lit-edge semantics bar-for-bar. **Toggle ON (~300 bars):** red-lit 58 / relocations 25; green-lit 80 / relocations 27 — 52 bright-triggered relocations total. Note the counts themselves shift once the mirror is on (red 51→58, green 89→80) because the two sides now feed each other, which is the feature working, not drift.
**Disclosed:** the live endpoint is **identical with the toggle ON and OFF** (55.840 / 51.107) despite 52 extra relocations across history — the chain re-converges by the last bar on this symbol, exactly as v0.39.0 did. The toggle changes the *path*, not the current read, at least on HYPE.P 1D. Whether that holds elsewhere is untested.
**Open / not done:** still HYPE.P 1D only — no multi-symbol sweep. The `*_n` vs `*_reloc_n` gap is still not decomposed into "walk returned na" vs "that side already relocated on a sweep/fill". No fixture-level verification of an individual green-bright relocation (the counters prove it fires; no single case has been hand-walked the way the Feb-22 close-fill was). The feedback loop the mirror creates (green lights → red moves → red can light → green moves → green re-arms) is bounded by requiring a real confirmed close beyond a line each step, but has not been stress-checked on a chop-heavy symbol.
**Status:** shipped, default OFF. Behaviour with the toggle off is v0.38.2 exactly.

## OB v0.40.1 — BUGFIX: the bright-line trigger was never one-shot (missing rising-edge guard)
**Date:** 2026-08-11 · **On-chart:** "Jamal OB v0.40.1" (shorttitle "JOB0.40")
**How it surfaced:** the user reported "I'm seeing green line move a lot" with the bright-line toggle on, and sent SOLUSDT.P 1W around Jan 2023. Their red line read 40.60 while my desktop read 9.98 — an input mismatch again (their config: `use_fill` **OFF**, `use_lit` **ON**; setting `in_1` false reproduced 40.60 exactly). Replaying week by week found the move: **Jan 30 2023 week** (O 26.09 H 26.334 L 22.45 C 23.464, red candle) fired the red-bright trigger; the walk anchored on that bar, seeded with its own open, and stopped immediately at Jan 23 (high 26.869 > Jan 16's 26.687) → green **32.92 → 26.09**, guard **7.78 → 22.11**. The next week (Feb 6, low 19.66) then swept that freshly-raised guard, re-running the walk via Trigger 1 — the guard-ratchet cascade, caught live.
**The defect:** the reclaim-latch branch in the LIT stage is a LEVEL test, not an edge test — `else if not bear_touched and barstate.isconfirmed and close < upper_line` has no `not bear_closed_below`. It re-fires on EVERY confirmed bar closing beyond the line for as long as the line is not retested. This was harmless in v0.38.2 and earlier, where the latch drove only colour and re-setting an already-true bool was a no-op; **v0.39.0 hung a Trigger on it** and I asserted "one-shot per line placement by construction" in the tooltip, the vocabulary, the changelog and in conversation, without ever verifying it. On SOL 1W the red line sits at 40.60 while price trades 20-26, so `high >= upper_line` never latches `bear_touched` and the trigger fired **every single week** — 26 times by Feb 2023. LESSON: a cumulative counter read only at the endpoint hides per-bar misbehaviour; read it across bars, or it proves nothing.
**Change:** added the rising-edge guard to both freshness branches — `not bear_closed_below and ...` and the mirror `not bull_closed_above and ...`. Nothing else. Because the branch previously only re-assigned an already-true latch, **colour behaviour and every `use_lit` OFF path are bit-identical**; only the `*_lit_evt` flags, the counters, and therefore Trigger 3 change.
**Tests run:** compile 0/0, saved, tag v0.40.1 confirmed. **SOL.P 1W, Feb-13-2023 week, `use_lit` ON, `use_fill` OFF —** before: red-lit **26**, relocations **15**, green **26.09**, guard **19.66**. After: red-lit **2**, relocations **0**, green **32.92**, guard **7.78** — the green line now holds the Nov-2022 crash Origin with the guard on the Dec-2022 structural low, instead of trailing price. **Regression (`use_lit` OFF, same bar):** green 32.92 / red 40.60, guards 7.78 / 48.38 — identical to the v0.40.0 OFF reading. Bind-check held.
**Open / not done:** the v0.39.0 and v0.40.0 calibration numbers (HYPE.P 1D: red-lit 51/58, green-lit 80/89, 52 relocations) were all measured against the buggy trigger and are **void** — they counted level hits, not edges. Nothing has been re-measured on HYPE since the fix. The guard-ratchet interaction is real and unchanged: a bright trigger still writes `bull_guard_lo` from a possibly-shallow leg, which can unlock extra sweeps; it simply fires far less often now. Still single-symbol verification only.
**Status:** shipped, default OFF.

## OB v0.41.0 — close-fill becomes a QUEUE: only the newest unmitigated zone is armed ("reading A")
**Date:** 2026-08-11 · **On-chart:** "Jamal OB v0.41.0" (shorttitle "JOB0.41")
**User spec:** "track fvgs that get closed through (mitigated) and only trigger a walk back if the most recent unmitigated fvg gets closed through." Two readings were offered. The user chose **reading A (queue)**: all zones are retained, but only the newest not-yet-closed-through zone is armed; firing it arms the next-newest on the FOLLOWING bar. Reading B (discard older zones outright) was not taken.
**Change:** the close-fill check no longer loops over every zone. It scans from the newest end for the first zone with `fill_done == false`, and only that zone can fire this bar. Previously every unmitigated zone was armed at once, so a single bar closing through several stacked zones set one shared event; now that same bar fires only the newest, and the rest are walked one per bar. Bear side mirrors exactly. Nothing else changed: the walk-back, the guard update, the 30-zone memory and the separation from the 5-box visual cap are untouched. New DW diagnostics: `bull/bear close-fill count` and `close-fill relocations` (fill as sole cause).
**Known consequence, stated up front and inherent to reading A:** a zone price never closes back through sits at the head of the queue forever and blocks every older zone behind it. This is not a bug in the implementation, it follows from "only the newest unmitigated is armed."
**Tests run:** compile 0/0, saved, tag confirmed. **BTC.P 1D, `use_fill` ON, `use_lit` OFF, start set to 1 Oct 2022 to match the original v0.38.0 fixture conditions:** at the **Nov-14-2023** bar the green line reads **27,943.0** (still the Oct-11 level) where the documented v0.38.0 fixture is **37,330.3**. At **Nov-21-2023** it reads **37,330.3**. Between those bars exactly ONE bull fill fired (count 21→22, relocations 13→14). At Dec-11-2023 it is still 37,330.3. **So the queue does not change WHERE the line lands, it changes WHEN: the same Origin, roughly one week (5-7 daily bars) later.** Live BTC.P 1D at defaults with both toggles on: bull close-fill 116 events / 64 relocations, bear 122 / 66.
**Caveat on that comparison (important):** 37,330.3 is a **v0.38.0** number, and v0.38.0 had the walk clamp that v0.38.2 deleted. I did not run the pre-queue v0.40.1 build side by side at the same bar, so "one week late" is measured against a documented figure from an older engine, not a direct A/B. The level matching exactly at the later date is strong evidence the same Origin is found and only trigger timing moved, but it is evidence, not proof.
**Judgement the user should make:** the delay works directly against the stated purpose of this trigger. From the v0.37.0 entry: "the combo exists to keep the line from being left behind." During a rally, bull gaps form continuously and are not closed through, so the newest one sits just under price and holds the queue shut. That is precisely when catch-up is wanted. Reading B would make this worse, not better.
**Open / not done:** no direct A/B against v0.40.1. The other documented catch-up fixtures (Sep-21, Oct-11, Dec-11-2023) were not individually re-timed, only Nov-14. Aug-17-2023 (the two-month-old June zone fill that motivated the 30-zone memory) was not re-checked at all and is the fixture most likely to be broken by a queue. Single symbol.
**Status:** shipped, `use_fill` still default OFF.

## OB v0.42.0 — close-fill gains an OPPOSITE-LINE GATE (each pathway armed only past the other line)
**Date:** 2026-08-11 · **On-chart:** "Jamal OB v0.42.0" (shorttitle "JOB0.42")
**Spec history (worth recording, the first two attempts were wrong):** the user first asked for "if price is below green line, trigger fvg logic on the red line (price closing above green fvgs)", then restated it as green-gap-filled moving the red line, describing it as "the existing fvg logic but an additional condition of price relative to the line". Both rest on a mistaken recollection that a green gap fill already moves the red line. It never has: `bull_fill_evt` (green gap closed below its bottom) feeds `bull_fill`, which feeds the block that writes `lower_line`, the GREEN line. Confirmed three ways: the code path, the v0.38.0 entry ("relocates the green line"), and the HYPE Feb-22-2026 trace done earlier the same day where a green gap fill moved the green line 23.203 → 30.364. Shown to the user, who then restated correctly: **"when price is below green line, and a red fvg gets filled, move the red line. and mirror."** An earlier partial build of the wrong (crossed) version was reverted with `git checkout` before anything was pushed to TradingView.
**Change (small, and it is the third attempt that is correct):** each close-fill pathway keeps its own-colour target and gains a price gate on the OTHER line.
  green gap filled (close below its bottom) → GREEN line, armed only while `close > upper_line`
  red gap filled (close above its top)      → RED line,   armed only while `close < lower_line`
Read as a commitment filter: demand re-anchors only after supply has been overcome, supply only after demand has failed. Fills while price sits between the two lines do nothing. **A zone is NOT consumed when the gate fails** (unarmed is not spent), so it stays at the head of the v0.41.0 queue and can still fire later once price is in the right regime and still closed through the zone. Both gates are evaluated in the FVG block, BEFORE pass 1, so they always read the line values coming into the bar and there is no dependence on which side relocates first — the v0.37.0 convention, revived.
**Tests run:** compile 0/0, saved, tag confirmed. **Both toggles OFF, BTC.P 1D live:** 16,693.0 / 108,934.6, guards 15,443.2 / 126,208.5 — the documented v0.36.0 defaults, exact. Gated counters read 31 bull / 4 bear there, consistent with the gate: with the lines parked at 16.7k and 108.9k, price is rarely outside the band. **Both toggles ON, same bar:** lines and guards unchanged from v0.41.0 (64,750.0 / 63,497.1, guards 62,228.8 / 65,482.7 — the endpoint converges yet again, so this bar cannot discriminate). Close-fill counters, v0.41.0 → v0.42.0: **bull 116 events / 64 relocations → 88 / 71**; **bear 122 / 66 → 118 / 92**. Fewer events, MORE relocations. Hit rate rises from 55% to 81% (bull) and 54% to 78% (bear).
**Why relocations went up while events went down:** two effects. The gate removes fills that fired in mid-range and often produced no move, and because an ungated fill no longer consumes its zone, that zone survives and can fire later in a regime where the walk succeeds. Net: the trigger fires less and accomplishes more.
**Open / not done:** no per-bar verification that a specific mid-range fill was correctly suppressed; the counters are consistent with it but a replay fixture would be stronger. The v0.38.0 sandbox fixtures (Sep-21, Oct-11, Nov-14, Dec-11-2023) are NOT re-checked — they were already shifted by the v0.41.0 queue and are now additionally gated, so that calibration surface is two changes stale. Single symbol. The v0.41.0 queue-blocking property is unchanged and now interacts with the gate: a zone at the queue head that is closed through only while ungated stays there.
**Status:** shipped, `use_fill` still default OFF.

## OB v0.43.0 — MONOLITHIC GROUPING: an alternative walk-back behind `use_mono` (default OFF)
**Date:** 2026-08-11 · **On-chart:** "Jamal OB v0.43.0" (shorttitle "JOB0.43")
**How it was derived (two calibration rounds, both artifacts published):** Round A (artifact b4a3e09f) = 12-case tap-picker, "tap the candle whose open should be the green line", uniform 23-bar windows so framing leaked nothing, engine answer never shown, 2 controls mixed in. User answered 7, skipped 5. **4 agreed, 3 disagreed, and the disagreements went in BOTH directions** (cases 3 and 7 wanted a shorter walk, case 6 a longer one). Exhaustive search over all 65,536 boolean rules on the four comparisons the v0.17 walk can see returned **ZERO fits** — three geometry classes required opposite verdicts for identical candle shapes. Round B (artifact de818bf4) = "why does the fall start there", every green in four walks marked individually, tap-any-candle-to-draw-its-OHLC so sweeps are checkable by eye, trigger cause stated per card. That produced 13 per-green marks and, critically, the user's own restatement of the rule.
**What the marks revealed:** case 7's round-A answer was **noise** — the user's per-green marks for that walk reproduce the CURRENT engine exactly, so that disagreement was never real. Case 1 was **revised** to 63,842.4 (the user's original instinct, retracted after my explanation, then reinstated). Adding features (next-bar-is-red, closed-above-previous-open) still left 2 hard contradictions: BTC-2024-04-08 (start) vs BTC-2022-09-17 (walk) identical on all six features, and ETH-2022-09-14 (start) vs BTC-2024-04-16 (walk) likewise.
**The user's rule (verbatim intent):** group consecutive same-colour candles into ONE monolithic candle (open = the run's first bar's open, close = its last bar's close, extremes = the run's). The series then alternates red mono / green mono. Each GREEN mono is judged against the RED mono behind it (P): **inside P → keep walking; took P's low AND high → the fall starts here; took P's low only → the fall starts here ONLY if the very next BAR takes out the green's high, otherwise keep walking; closed above P's open → the fall starts here.** Origin = highest red-mono open reached. Bear side = exact high/low mirror. **Both hard contradictions dissolve:** ETH-09-17 is an inside candle; BTC-09-16+09-17 MERGE and the merged candle meets no condition. Strong corroboration that the mental model is monos, not bars: the user's 29-Apr explanation cited **27 April**, and the merged 26–28 Apr red mono's low IS 27 April's low — a reference the bar-by-bar rule could never produce.
**One correction to the proposal, needed to make it fit:** "the next candle" must stay a **SINGLE BAR**. Merging the newer reds too inflates the high-taken test (Sep-19's high survives Sep-20 alone at 19,625 but not the merged Sep-20..21 at 20,154.1) and drops the fit from 7/8 to 5/8.
**Fit:** **7 of 8** user-marked cases vs **4 of 8** for the v0.17 walk. Every case the old rule got right, the new one also gets right.
**Change:** new `use_mono` input (`in_3`, default OFF; `start_ts` re-indexed to `in_4`). Two new functions `f_walkback_bull_mono` / `f_walkback_bear_mono` returning the same `[open, leg extreme]` pair so the guard is unchanged, plus selectors `f_wb_bull` / `f_wb_bear` that all FOUR call sites (pass-1 bull, pass-1 bear, pass-2 bull, pass-2 bear) now route through. The v0.17 walks are untouched and still run when the toggle is off, honouring the v0.38.2 standing rule.
**BUG FOUND AND FIXED DURING THE BUILD:** the first Pine version folded the red mono's open into `best_open` BEFORE testing the buffered green against it. When the green ends the walk, that mono is not part of the leg, so the origin came back one mono too far (64,478.8 = the 26–28 Apr mono's open instead of 63,842.4). Caught because the on-chart value disagreed with the JS model. Fix = test first, contribute after, on both sides.
**Tests run:** compile 0/0, saved, tag confirmed. **Toggle OFF, BTC.P 1D replay 2024-05-01 bar:** green 66,777.9, guard 59,150 — identical to v0.42.0. **Toggle ON, same bar:** green **63,842.4** (matches the model and the user's revised case-1 answer). **Toggle ON, BTC.P 1D replay 2022-09-22 bar:** green **22,386.0** (case 6; the old walk gave 20,102). Engine replica used for all offline work was itself validated against 5 on-chart readings to the decimal before being trusted.
**Blast radius (measured, full history, close-fill on):** BTC 78 of 244 bull placements change (32%), SOL 94/249 (38%), ETH 70/190 (37%); average gap when they differ 6.3–11.8%. **About a third of all levels move.** This is a different walk, not a refinement — which is exactly why it is behind a toggle.
**Open / not done:** (1) **Case 7 / BTC-2024-04-16 is unresolved** — the user's own rule says STOP there (took 15-Apr's low, next bar took its high), their card marking says keep walking. It is structurally identical to ETH-2022-09-14, which they marked STOP. (2) **"Closes above previous red candle" is untested** — no case in the set reaches that condition, so whether it means above the mono's open, the last red's open, or its high is undetermined. (3) The **34-point v0.15/v0.17/v0.29 corpus has NOT been re-checked** against monos; those rounds judged isolated three-candle shapes and monos may contradict some. (4) Repo `.pine` currently carries a fuller comment/vocabulary block than the TradingView copy — code identical, comments diverged during the push; sync on the next edit.
**Status:** shipped, default OFF. With the toggle off, behaviour is v0.42.0 exactly.

## OB v0.44.0 — mono INSIDE rule: an inside green can end the walk if the next RED MONO takes its high
**Date:** 2026-08-11 · **On-chart:** "Jamal OB v0.44.0" (shorttitle "JOB0.44")
**User spec:** "the green (or mono green) can be an inside candle (as compared to the previous mono red) and still stop the walk back if it's high gets taken out by the next mono red." Previously (v0.43.0) an inside green ALWAYS kept walking, unconditionally.
**Measured before building, and the cost was disclosed and accepted:** three variants tested against the 8 marked cases — inside never stops (v0.43.0) **7/8**; inside stops if the SINGLE NEXT BAR takes its high **7/8** (identical, because no inside green in the set has its high taken by the next bar, so that variant would ship untested); inside stops if the NEXT RED MONO takes its high **4/8**. The user chose the third knowing it costs cases 2, 4 and 5.
**Why the mono variant fires so readily (structural, not incidental):** the red mono after an inside green runs all the way to the TRIGGER bar, and the trigger bar by definition just made a new extreme. On the way it very often prints a high above a modest inside candle. Measured on the four inside greens in the set — BTC 2023-09-22 (green high 26,737.7; next bar 26,620.6 ✗; next red mono 26,739.9 ✓ **by 2.2 points**), ETH 2023-04-22 (1,886.5; 1,882.11 ✗; 1,891.3 ✓), SOL 2025-12-13 (134.2; 133.58 ✗; 135.4 ✓), ETH 2022-09-17 (1,475.15; 1,469 ✗; 1,469 ✗). Three of four flip.
**Levels that moved as a result (all previously user-marked):** BTC 2023-09-24 **27,195.9 → 26,566.7**; ETH 2023-04-24 **2,103.29 → 1,873.4**; SOL 2025-12-15 **136.36 → 133.04**. Note BTC 2023-09-24 is the SECOND time that level has moved — it was also endorsed during the v0.36 round at 27,195.9, and the round-A quiz re-confirmed it, so the mono inside rule now contradicts two separate confirmations of the same level.
**Change:** both mono walks gain `g_rhi` / `r_glo` (the newer red/green mono's extreme, captured when the counter mono is buffered) and `last_red_hi` / `last_grn_lo` (set when each mono completes). The inside branch becomes `insStop = inside and not na(g_rhi) and g_rhi > g_hi`, OR'd ahead of the existing non-inside conditions. Bear side is the exact mirror (inside red mono stops if the newer GREEN mono takes its low). The v0.17 walks and the `use_mono` OFF path are untouched.
**Tests run:** compile 0/0, saved, tag v0.44.0 confirmed. **`use_mono` ON, `use_fill` ON, `use_lit` OFF, BTC.P 1D:** 2023-09-25 replay bar → green **26,566.7** (was 27,195.9 under v0.43.0 — the intended change landed); 2024-05-01 replay bar → green **63,842.4**, guard 59,150 (unchanged from v0.43.0, confirming the inside rule did not leak into non-inside walks).
**Open / not done:** fit against the marked set is now **4/8**, down from 7/8. The three regressions are accepted by explicit user direction, not resolved. BTC-2024-04-16 (case 7) remains unresolved from v0.43.0. The "closes above previous red candle" reference is still untested. The 34-point v0.15/v0.17/v0.29 corpus still has not been re-checked against monos. Repo `.pine` carries a fuller comment block than the TradingView copy; code identical.
**Status:** shipped, `use_mono` still default OFF.

## OB v0.44.1 — mono: the ANCHOR'S OWN mono is in-leg and never judged
**Date:** 2026-08-12 · **On-chart:** "Jamal OB v0.44.1" (shorttitle "JOB0.44")
**Bug, user-surfaced on NEAR.P 1D:** with `use_mono` + `use_lit` on, 11 Aug 2026 took out the guard (low 1.536 vs guard 1.569) but the green line stayed at 1.837 and, more tellingly, **the guard did not move either**. Cause: 11 Aug closed green so the walk anchored on 10 Aug, which is also green. The mono walk then judged the anchor's OWN green mono against the red mono behind it (9 Aug): it took 9 Aug's low (1.588 < 1.592) AND its high (1.669 > 1.648), which is rule 1, so the walk ended on step one having collected no red mono at all. `best_open` came back na, the hold-on-na rule left the line where it was, and because the guard is only written on a successful placement it stayed at 1.569 — so the 11 Aug low was never absorbed and the trigger would re-fire on any later low under 1.569.
**Root cause is an asymmetry with the default walk:** `f_walkback_bull` NEVER tests the anchor bar — its loop starts at `s0 + 1` and the anchor only ever contributes its open. The mono walk buffered and tested the anchor's mono like any other, so an anchor sitting inside a green mono could kill the walk before it began.
**Change:** `first_run` flag in both mono walks. The first run to complete (the one containing the anchor) is never buffered for judgement; it is in-leg by definition. Two lines per side. Nothing else touched.
**Tests run:** compile 0/0, saved, tag v0.44.1 confirmed. **Offline against the 8 marked cases: identical on 8/8 with the exemption on or off** — in every marked case the anchor's mono was red or the exemption did not bind, so this is a free fix. **NEAR.P 1D, mono + bright on, fill off:** green **1.837 → 1.611** (the 9 Aug red mono's open, which is what the user predicted) and guard **1.569 → 1.536**, so the 11 Aug low is now absorbed. Walk trace: `10 Aug anchor mono -> skipped; 08 Aug STOP inside 04-07 Aug but next red mono took its high` → origin = the 9 Aug red mono.
**Process note:** this session I quoted an entire 8-combination comparison table taken from a chart that was silently on the 1-HOUR timeframe after a TradingView restart, and built three wrong theories on it (input-order corruption, stale mobile cache, exchange divergence) before the user spotted it. Verified once at launch, never re-checked after two symbol changes. **Check symbol AND resolution together via `chart_get_state` before quoting any value.**
**Open / not done:** unchanged from v0.44.0 — BTC-2024-04-16 still conflicts with the user's own mark, the "closes above previous red candle" branch is still untested by any case, and the 34-point v0.15/v0.17/v0.29 corpus still has not been re-checked against monos.
**Status:** shipped, `use_mono` still default OFF.

## OB v0.44.1 — repo/TradingView desync correction (2026-08-12, same day)
**What was wrong:** the entry above says the `first_run` exemption is "two lines per side". It was two lines on the BEAR side only. The repo copy of `f_walkback_bull_mono` declared `bool first_run = true` and then never read it and never set it to false, so the bull green-mono buffer was unguarded. The TradingView copy was correct — that is what produced the NEAR 1.611 reading recorded above — so the divergence was repo-only and no tested result changes. Found while reassembling the file to undo the clobber below.
**Change:** `if not first_run` around the bull side's green-mono buffer, plus `first_run := false` after the branch, matching the bear side exactly.
**Tests run:** re-injected the full file, compile 0/0, saved as script version 79. **NEAR.P 1D, mono + bright on, fill off:** green **1.611**, guard **1.536**, red **1.783** — identical to the pre-clobber reading the user confirmed on their phone, so the bull exemption is confirmed present and the file now matches what ships.
**Process note — script clobber.** Creating "Jamal Mono" started with `pine_new`, whose blank template I verified in the editor before injecting. That verification was worthless: `pine_new` does not persist a new script (already recorded in memory as `tv-new-script-via-copy`), so the save went to whatever the editor was last BOUND to, which was Jamal OB. It saved as Jamal OB version 78 with the title "Jamal Mono v0.1.0", and TradingView reset the on-chart study's positional input array to defaults, silently turning the user's bright and mono toggles OFF. Restored from the repo copy. **Verifying the editor's CONTENTS does not verify its save TARGET. Before any save, confirm the bound script name, not the buffer.** The working route is the one in memory: editor script menu → Make a copy… → name it → then inject.
**Status:** repo and TradingView now byte-equivalent on code; the repo keeps a fuller comment block.

# ========================= JAMAL MONO — MONOLITHIC CANDLE PANE =========================
**What it is (2026-08-12):** a standalone read-only indicator, `jamal-mono.pine`, that draws the monolithic grouping as actual candles in a separate pane under the price chart. Same grouping rule the `use_mono` walk-back runs on, so what the walk sees can be read directly off the screen instead of inferred from where the lines land. Saved TradingView script name: "Jamal Mono".

## Mono v0.1.0 — first build
**Date:** 2026-08-12 · **On-chart:** "Jamal Mono v0.1.0" (shorttitle "JMono0.1")
**Code changes**
- `indicator(..., overlay = false)` → separate pane. `max_labels_count = 500`.
- Grouping state: `m_init` / `m_red` / `m_o` / `m_h` / `m_l` / `m_len` / `m_count`. A new run starts when `close < open` flips; otherwise the run's high/low extend and `m_len` increments. Open is the run's oldest bar's open; close is plotted as the live `close`, which IS the run's newest close by construction.
- `plotcandle(m_o, m_h, m_l, close, ...)` — the mono is drawn on EVERY bar of its run, growing as the run extends. The rightmost bar of a run therefore shows the completed mono and the bars before it show it part-formed. Nothing draws retroactively and nothing looks ahead.
- `label.new` prints the bar count under each completed run of 2+ (`show_len`); single-bar monos stay unlabelled so the pane is readable. A `plotchar` tick marks each run start (`show_split`). Both toggleable, plus three colour inputs.
- Data-window plots: mono OHLC, bars in the current run, red flag, cumulative mono count.
**Rationale:** every mono question so far (NEAR 11 Aug, BTC 30 Apr 2024, the two calibration quizzes) was answered by hand-building the grouping offline in JS and rendering it to an HTML artifact. This puts the same picture on the live chart at zero cost, on any symbol and timeframe.
**Colour convention:** RED is `close < open`, so a FLAT DOJI counts as GREEN — matched deliberately to `f_walkback_bull_mono`, which uses the same test. A pane that disagreed with the walk on dojis would be worse than no pane.
**Compile fix:** `var bool m_red = na` fails with *Cannot assign a value of the "simple na" type... declared with the "const bool" type* — Pine will not seed a bool with na. Replaced the na-means-uninitialized idiom with an explicit `var bool m_init = false` companion flag.
**Tests run:** compile 0/0, saved, added to chart. **NEAR.P 1D, 2026-08-12:** renders in its own pane below price; data window reads a 3-bar GREEN run, open 1.598 / high 1.683 / low 1.536 / close 1.634, 1,085 monos since the chart's first loaded bar. That low of 1.536 is the same value Jamal OB reports as its lower guard, an independent cross-check that the run boundaries agree. Most recent multi-bar label is a **4**, the 4–7 Aug run identified in the v0.44.1 investigation; the current 3-bar run is correctly unlabelled because labels print on the bar a run ENDS.
**Known / by design:** the stair effect. A 4-bar run occupies 4 slots with a progressively taller candle rather than one wide candle, because Pine cannot draw a single candle spanning several bars. Readable, but the pane has roughly the same bar count as price, not the compressed count. If one-candle-per-mono is wanted it needs boxes/lines rather than `plotcandle`, and the last mono would then only appear once its run closes.
**Status:** superseded by v0.2.0 (the stair is now a toggle, off by default).

## Mono v0.2.0 — one candle per mono (`one_candle`, default ON)
**Date:** 2026-08-12 · **On-chart:** "Jamal Mono v0.2.0" (shorttitle "JMono0.2")
**User request:** "I see that Jamal mono repeats consecutive candles. can you add a toggle, where instead of repeating they actually form a monolithic candle (make sure spacing still aligns x axis with the main price pane)."
**Code changes**
- New input `one_candle` (default ON, first in the list). ON = box/line renderer; OFF = the v0.1.0 `plotcandle` stair.
- `plotcandle` is now fed `na` for all four series when `one_candle` is on, which draws nothing. Pine has no way to disable a plot call, so this is the idiom.
- New renderer: `box.new` for the body (top/bottom = max/min of the mono's open and close) and `line.new` for the wick (high to low at the run's centre), both `xloc.bar_time`. Created on `new_run`, then updated in place each bar of the run via `box.set_right` / `set_top` / `set_bottom` and `line.set_xy1/2`, so the live mono grows rather than being redrawn.
- Track `m_start` (bar_index) and `m_t0` (time) at each run start — the box needs the run's left edge, which the v0.1.0 state did not keep.
- `max_boxes_count = 500`, `max_lines_count = 500` added to `indicator()`.
- Run-length labels are centred under the mono's box in one-candle mode (`(m_start[1] + bar_index - 1) / 2`) instead of sitting on the run's last bar. The run-start tick is suppressed in one-candle mode — the box edges already mark every boundary.
**Why boxes and not plotcandle:** `plotcandle` is strictly one value per bar and cannot span bars, which is what produced the stair in v0.1.0. Boxes and lines take x-coordinates and can span any distance, so they are the only way to draw one candle across a multi-bar run.
**X-axis alignment.** Edges are placed with `xloc.bar_time` at `±(timeframe.in_seconds() * 380)` ms around the run's first and last bar times, i.e. 0.38 of a bar either side, giving a body 76% of the bar span — the same body-to-gap ratio TradingView's own candles use. `xloc.bar_index` was rejected: it puts edges on bar CENTRES, which would make every mono half a bar narrow and collapse single-bar monos (42% of all monos on BTC daily) to zero width and therefore invisible.
**Tests run:** compile 0/0, saved, study auto-updated to v0.2.0 on chart. **NEAR.P 1D zoomed to 4–12 Aug 2026:** run structure reads RED 4 bars (4–7 Aug, labelled "4"), GREEN 1 (8 Aug), RED 1 (9 Aug), GREEN 3 (10–12 Aug, live and unlabelled) — exactly the grouping in the v0.44.1 walk trace above, independently reproduced. Data window agrees: 3 bars in the current run, low 1.536, matching Jamal OB's lower guard.
**How interpolation was confirmed:** whether `xloc.bar_time` interpolates between bars or snaps to whole ones decides if sub-bar offsets do anything at all, and it cannot be read off a single screenshot. Test: render at offset 500 (half a bar) and at 380, and compare. At 500 the monos tiled edge to edge with no gaps; at 380 visible gaps appeared. A snapping renderer would have produced identical output. Interpolation confirmed, so the offsets land where intended. Recorded because eyeballing pixel positions in a screenshot was tried first and was not reliable enough to settle it.
**Known limits:** (1) the 500-box cap means one-candle mode shows only the most recent ~500 monos — NEAR daily has ~1,085, so early history renders empty; switch the toggle off to see all of it. (2) The half-bar offset assumes evenly spaced bars. True on 24/7 crypto; on a session-gapped symbol (equities, futures) the edges drift across weekend and holiday gaps. (3) A doji mono (open == close) is a zero-height box, which still renders as a hairline via the border — the correct look, but it is a border artifact rather than an explicit case.
**Status:** shipped, `one_candle` default ON.

## Mono v0.3.0 — inside-bar merging (`merge_inside`, default OFF)
**Date:** 2026-08-12 · **On-chart:** "Jamal Mono v0.3.0" (shorttitle "JMono0.3")
**User request:** "can you add a toggle that includes inside candles as part of the consecutive candles regardless of color."
**Change:** one clause added to the run test. A bar whose colour differs from the run's is still absorbed if it is INSIDE the run's range so far (`high <= m_h and low >= m_l`). Only a bar that flips colour AND breaks the run's high or low starts a new mono. Plainly: a bar that makes neither a new high nor a new low for the run does not break the run, whatever colour it is.
**The definitional fork, and which side was taken.** "Inside" can mean inside the previous BAR (the textbook inside bar) or inside the RUN so far. Taken: **inside the run**, because the mono is the unit here and it matches how `use_mono`'s own inside rule compares a whole green mono against the whole red mono behind it. Note the containment: any bar inside the previous bar is necessarily inside the run, so previous-bar is a strict SUBSET and would merge less.
**Also added:** `m_ins` counter (opposite-colour bars absorbed into the current run), surfaced in the data window and as a trailing `*` on the run-length label, so merged monos are identifiable at a glance. `m_start`/`m_t0` unchanged.
**Tests run:** compile 0/0, saved as script version 5. **NEAR.P 1D, crosshair parked on the last bar:** toggle OFF gives **1,085 monos**, byte-identical to the v0.1.0 and v0.2.0 baseline, so the default path is provably untouched. Toggle ON gives **301 monos** — a 72% reduction.
**Result that needs a decision (not resolved).** The run-based definition is very permissive in practice. Once a run has accumulated a wide range from same-colour bars, most later bars fall inside it and get swallowed, so runs get long: NEAR daily produces monos of **27, 26 and 15 bars**. The earlier reasoning that "merging cannot cascade" is true but weaker than it sounds — absorbing an inside bar cannot WIDEN the mono, so one absorption does not make the next more likely; but a run that is already wide absorbs almost everything regardless. If these lengths are wrong for the intended reading, the fix is the strict definition (inside the PREVIOUS BAR, `high <= high[1] and low >= low[1]`), which is a one-line change and merges far less. Flagged to the user with both numbers.
**Not done:** the strict variant is not implemented; no calibration case has been checked against merged monos; `use_mono` in jamal-ob is NOT affected and still groups on colour flips only. **With this toggle ON the pane deliberately stops mirroring the walk-back** — it is a what-if view. The tooltip says so.
**Status:** superseded by v0.4.0 the same day — the run-based "inside" test was the wrong reading.

## Mono v0.4.0 — inside judged against a single NEIGHBOUR bar, plus the next-bar clause
**Date:** 2026-08-12 · **On-chart:** "Jamal Mono v0.4.0" (shorttitle "JMono0.4")
**User request:** "if an opposite color candle is 'inside' compared to the previous candle, absorb it in previous mono candle. logic already captures this right? / if opposite color candle is 'inside' compared to the next candle, then the next mono candle should absorb it."
**Answer to the first half: no, v0.3.0 did not capture it.** v0.3.0 tested against the whole accumulated RUN, not the previous CANDLE. That is why it produced 27-, 26- and 15-bar monos and cut NEAR daily from 1,085 monos to 301: once a run was wide, nearly every later bar fell inside it. The user's wording settles the fork that v0.3.0 flagged as open — it is the previous BAR.
**Rules now,** for an opposite-colour bar X with previous bar P and next bar N:
- X inside P (`X.high <= P.high and X.low >= P.low`) → X joins the PREVIOUS mono.
- X inside N → X joins the NEXT mono, becoming its FIRST bar. That mono therefore opens at X's open and takes **N's** colour, not X's.
- Neither → X starts its own mono, as before.
- PRECEDENCE: previous wins when X is inside both, matching the order the rules were given in.
**ONE-BAR LAG (the structural consequence).** The next-bar clause cannot be resolved until the next bar exists, so with merging on the state machine classifies bar t-1 at bar t. Implemented as `int k = merge_inside ? 1 : 0` with every read `[k]`-offset (`close[k]`, `time[k]`, `bar_index - k`, P at `k+1`, N at `k-1`). This is DEFERRAL, not lookahead: nothing uses data beyond the bar being drawn. Cost is that the live bar is ungrouped until it closes, which is arguably more correct anyway since an unclosed bar's colour can still flip. With merging off `k` is 0 and the machine is bar-for-bar identical to v0.1.0-v0.3.0.
**Repeat mode is disabled while merging.** `plotcandle` has no `offset` argument, so its output cannot be shifted back onto the bar being classified; under the lag it would draw every mono one bar right of where it belongs. Rather than ship a silently misaligned renderer, `use_box = one_candle or merge_inside` forces the box renderer, which positions itself by `time[k]` and is lag-correct by construction. The `one_candle` tooltip says it is ignored while merging.
**Compile error worth recording:** `The "plotcandle" function does not have an argument with the name "offset"`. The first attempt tried `offset = -k` to shift the stair. `plot()` and `plotchar()` take `offset`; `plotcandle()` does not.
**Tests run:** compile 0/0, saved as script version 7. **NEAR.P 1D, crosshair parked on the last bar** (a `pointermove` dispatched to the chart canvas — `data_get_study_values` reads at the CROSSHAIR, and an earlier reading this session was silently taken from 12 Mar because of it):
- merging OFF → **1,085 monos, lag 0**, identical to the v0.1.0/v0.2.0/v0.3.0 baseline, so the restructure provably did not disturb the default path.
- merging ON → **781 monos, lag 1**. A 28% reduction, against v0.3.0's 72%. Visible mono lengths are now 2-8 bars where v0.3.0 showed 27, 26 and 15.
- Current mono under merging: 2 bars, open 1.598, high 1.669, low 1.536, close 1.620 — the 10-11 Aug pair, with 12 Aug correctly unclassified under the lag.
**Not done:** no calibration case checked against the new grouping; the precedence choice (previous over next) is asserted, not tested against a case where it matters; `use_mono` in jamal-ob is still colour-flip-only and unaffected.
**Status:** superseded by v0.5.0 — the previous-side test is reverted to v0.3.0's, the next-side clause is kept.

## Mono v0.5.0 — previous side reverted to MONO-based, next-bar clause kept
**Date:** 2026-08-12 · **On-chart:** "Jamal Mono v0.5.0" (shorttitle "JMono0.5")
**User instruction:** "revert to 0.3 / inside candles get absorbed into immediately previous monolithic candles, keep this rule. / a green candle that takes out the low of the previous monolithic candles, breaks the monolithic logic, however if it is inside the next immediate candle, it should be the start of the next monolithic candle."
**Reading taken:** the two sides are measured against DIFFERENT things, on purpose. "Immediately previous monolithic candle" means the accumulated run, so the previous-side test goes back to v0.3.0's `x_hi <= m_h and x_lo >= m_l`. "Inside the next immediate candle" means a single BAR, so v0.4.0's next-side test stays as it was. v0.4.0's mistake was switching BOTH sides to single bars; only the next side should have been.
**Change:** one line. `inside_p` becomes `merge_inside and m_init and x_hi <= m_h and x_lo >= m_l`; `p_hi`/`p_lo` deleted. Everything else — the next-bar clause, the colour-adoption rule, the one-bar lag, the forced box renderer — is unchanged from v0.4.0.
**Asymmetry is not an accident and is worth restating:** the next side CANNOT be mono-based, because the next mono does not exist yet at the moment X is judged. Only its first bar is visible. So previous-side compares against a mono and next-side against a bar, necessarily.
**CAVEAT flagged to the user, not resolved.** "Not inside" is symmetric in this implementation: a bar breaks the mono by taking out EITHER its high or its low. The rule was specified with a green bar taking out the LOW as the example. If the intent is that only the low matters for a green bar (mirrored to only the high for a red bar against a green mono), that is a narrower rule and is NOT what this implements.
**Tests run:** compile 0/0, saved as script version 8. **NEAR.P 1D, crosshair on the last bar, merging ON → 280 monos, lag 1.** Sits just below v0.3.0's 301, which is the expected shape: the previous-side test is identical to v0.3.0 again, and the next-bar clause folds a further ~21 stray single-bar monos into their successors. Long monos are back by design — 27, 26 and 15 bars on NEAR daily, the same figures v0.3.0 produced. Current mono: 1 bar (11 Aug), open 1.600, high 1.621, low 1.536, close 1.620, with 12 Aug correctly unclassified under the lag.
**Merging-OFF path:** unchanged by construction — `inside_p` and `inside_n` are both gated on `merge_inside`, so with it off the machine is the plain colour-run grouping. Measured at **1,085 monos, lag 0** on the v0.4.0 build whose OFF path is byte-identical to this one.
**Comparison table, NEAR.P 1D:** off 1,085 · v0.3.0 (mono-inside only) 301 · v0.4.0 (bar-inside both sides) 781 · **v0.5.0 (mono-inside + next-bar clause) 280**.
**Not done:** no calibration case checked against this grouping; the previous-over-next precedence is still asserted rather than tested; the symmetric-vs-low-only question above is open; `use_mono` in jamal-ob remains colour-flip-only and unaffected.
**Status:** superseded by v0.6.0 — absorption now also ENDS the mono.

## Mono v0.6.0 — an absorbed inside candle also ENDS the mono
**Date:** 2026-08-12 · **On-chart:** "Jamal Mono v0.6.0" (shorttitle "JMono0.6")
**User instruction:** "I would say opposite color inside candles gets absorbed by the monolithic candle but they also end the candle."
**Change:** the inside-the-previous-mono bar still joins that mono, but it is now the mono's LAST bar. It sets the mono's close, and the bar after it is forced to start a fresh mono whatever its colour. Carried across the bar boundary by a new `var bool m_sealed`, set in the `inside_p` branch and consumed by a new first-position clause in the decision chain (`else if m_sealed -> new_run := true`), cleared whenever a new mono starts. `m_sealed` is surfaced in the data window.
**Consequence that makes this the right shape:** a mono can now hold **at most one** absorbed opposite-colour bar, always the last one. That is precisely what removes the runaway lengths of v0.3.0/v0.5.0 — under those, absorbing did not end the run, so a mono that had grown wide kept swallowing everything that fell inside it, giving 27- and 26-bar monos on NEAR daily. Those are gone; the pane now shows 2-5 bar monos throughout.
**Second consequence, expected:** the mono's close comes from an opposite-colour bar, so a green mono sealed by a red inside bar can close BELOW its own open while still being drawn green. The mono keeps the RUN's colour, which is what a run means. Not a bug.
**Interaction kept:** if the bar following a sealed mono is itself inside its own next bar, it still adopts that next bar's colour when it opens the new mono. The `m_sealed` clause only forces `new_run`; it does not suppress the colour-adoption rule.
**Tests run:** compile 0/0, saved as script version 9. **NEAR.P 1D, crosshair on the last bar, merging ON → 863 monos, lag 1.** Current mono: 3 bars, open 1.611, high 1.669, low 1.536, close 1.620, one merged bar, not sealed.
**Comparison table, NEAR.P 1D:** off 1,085 · v0.3.0 301 · v0.4.0 781 · v0.5.0 280 · **v0.6.0 863**. The jump from 280 to 863 is the whole point: sealing stops the cascade, so merging now folds roughly 222 monos into their predecessors instead of collapsing the chart into a few dozen giants.
**Reading note:** `m_ins` counts opposite-colour bars in the mono from BOTH paths — one absorbed by `inside_p`, or one that opened the mono under the `inside_n` colour-adoption rule. So `m_ins = 1` with `m_sealed = 0` is a legitimate combination (the current NEAR mono is exactly that) and does not indicate a missed seal.
**Not done:** unchanged from v0.5.0 — no calibration case checked against this grouping, the previous-over-next precedence is asserted not tested, the symmetric-vs-low-only question is still open, and `use_mono` in jamal-ob remains colour-flip-only.
**Status:** superseded by v0.7.0 — the forward-absorb clause is removed.

## Mono v0.7.0 — forward-absorb removed; lag and the renderer restriction go with it
**Date:** 2026-08-12 · **On-chart:** "Jamal Mono v0.7.0" (shorttitle "JMono0.7")
**User question, answered before the change:** "how does it handle multiple inside candles?"
- **Consecutive OPPOSITE-colour inside bars:** only the FIRST is absorbed. It seals the mono, so the second starts a new mono even though it is also inside. A mono holds at most one absorbed bar, always the last.
- **SAME-colour inside bars:** never tested for inside-ness at all. `same_col` is evaluated first in the chain, so they are ordinary run extensions and never seal. The inside rule only ever applies to bars that flip the colour.
Both behaviours are now written into the source comments so the question does not have to be re-derived.
**User instruction:** "let's remove the forward absorb logic inside candle."
**Change:** the `inside_n` clause and everything it dragged in are deleted — `n_hi`, `n_lo`, `n_red`, `take_col` and the colour-adoption rule. The grouping is now a single added clause: an opposite-colour bar inside the mono so far is absorbed and seals it; anything else starts a new mono.
**Three simplifications fall out for free, which is the real value of the removal:**
1. **The one-bar lag is gone.** It existed solely to see the next bar. `k` is deleted along with every `[k]` offset and the `ready` guard; the script reads only the bar being drawn and prior state. The live bar is grouped again in real time, and the "DW lag" plot is removed as meaningless.
2. **Repeat mode works under merging again.** It had been force-disabled because `plotcandle` takes no `offset` and would draw a bar to the right under the lag. With no lag there is nothing to correct, so `use_box` is deleted and `one_candle` is honoured in both modes.
3. **`m_ins` has one meaning again** — bars absorbed by the inside rule. Under v0.4.0-v0.6.0 it also counted the bar that opened a mono under colour-adoption, which made `m_ins = 1` with `m_sealed = 0` a legitimate but confusing combination. Renamed "DW inside bars absorbed".
**Tests run:** compile 0/0, saved as script version 10. **NEAR.P 1D, crosshair on the last bar, merging ON → 917 monos**, no lag field. Current mono: 3 bars (10-12 Aug), open 1.598, high 1.683, low 1.536, close 1.636, 0 absorbed, not sealed — open/high/low identical to the merging-OFF reading, confirming the live bar is back in the current mono now the lag is gone.
**Comparison table, NEAR.P 1D:** off 1,085 · v0.3.0 301 · v0.4.0 781 · v0.5.0 280 · v0.6.0 863 · **v0.7.0 917**. The rise from 863 is exactly the removal: bars the forward rule used to fold into the following mono now form their own again.
**Not done:** no calibration case checked against this grouping; the symmetric-vs-low-only question is still open (a bar breaks the mono by taking out either extreme, where the rule was given with the low as the example); `use_mono` in jamal-ob remains colour-flip-only and unaffected.
**Status:** superseded by v0.8.0 — absorption now runs as a group.

## Mono v0.8.0 — absorption runs as a same-colour group; visual controls
**Date:** 2026-08-12 · **On-chart:** "Jamal Mono v0.8.0" (shorttitle "JMono0.8")
**User request:** "merged candles seem really cramped can u improve the visual? also add logic that absorbs consecutive same color inside candles. so currently absorb only one inside candle. you can absorb as many consecutive candles that are inside and same color."
**Logic change.** v0.7.0 absorbed exactly one inside bar then sealed. Now the mono enters an ABSORBING state that keeps taking bars for as long as each is inside AND matches the colour of the first absorbed bar. Two new state vars, `m_absorbing` and `m_abs_red`, replace `m_sealed`; the decision chain gains an `m_absorbing` branch ahead of `same_col`. The first bar that is not inside, or is inside but a different colour, ends the mono. Note this includes a bar the same colour as the MONO — once the group has started, the mono is closing, so a returning same-colour bar does not resume the run.
**Why it cannot run away:** absorbing never widens the mono, since an inside bar sits within the existing high/low by definition. `inside_m` is therefore tested against a range that stops moving the moment absorption starts. The runaway 27- and 26-bar monos of v0.3.0/v0.5.0 came from absorption not ending the mono at all, which is a different failure.
**Answered in the source comments** (user asked): consecutive OPPOSITE-colour inside bars — under v0.7.0 only the first was absorbed; under v0.8.0 the whole same-colour group is. SAME-colour bars are never tested for inside-ness at all, because `same_col` is checked before `inside_m`.
**Visual work — what landed:** `body_pct` input (default 76%, the ratio TradingView's own candles use; 100% tiles edge to edge), `wick_w` input (default 2, was hardcoded 1), and `label_min` (default 3) so labels no longer print on every 2-bar mono and stop crowding the pane.
**Visual work — what FAILED, recorded so it is not retried blindly.** The pane leaves dead space because **boxes and lines are drawings, and drawings do not drive a pane's price scale — only plots do.** Two attempts to anchor it with hidden plots of `m_h`/`m_l`:
1. **100% transparent** — compiles and runs, but changes nothing. Measured properly by toggling the input and comparing the axis: identical 1.000-3.000 on NEAR 1D either way. TradingView drops fully transparent plots from auto-scaling.
2. **97% transparent** — put the study into a RUNTIME error and blanked the pane. Not diagnosed; the message was not reachable from the collapsed pane legend and the compile log was clean. Reverted.
Both removed along with the `fit_scale` input rather than ship a control that does nothing or breaks the render. The dead space is roughly 16% of the pane on NEAR 1D. **Pane HEIGHT, which matters more than the margin, is a chart-level setting Pine cannot touch at all** — a synthetic pointer drag on `paneSeparator` was also tried and TradingView ignored it. The user has to drag the divider.
**Tests run:** compile 0/0, saved as script version 13, error cleared and pane rendering again. **NEAR.P 1D, crosshair on the last bar, merging ON → 850 monos**, against v0.7.0's 917: the group rule folds ~67 further monos into their predecessors. Current mono: 3 bars (10-12 Aug), open 1.598, high 1.683, low 1.536, close 1.637, 0 absorbed. Labels confirmed printing only on 3+ bar monos.
**Process note:** a crosshair click earlier in the session pinned the data window to 23 Mar, and the first reading of this build (797 monos) was taken from there. Caught by cross-checking Jamal OB's lines against their known values. Synthetic `pointermove` did not clear it; a real `ui_mouse_click` on the price pane did. **`data_get_study_values` reads at the CROSSHAIR — verify position, not just symbol and resolution.**
**Not done:** no calibration case checked against this grouping; the symmetric-vs-low-only question is still open; `use_mono` in jamal-ob remains colour-flip-only and unaffected.
**Status:** superseded by v1.0.0 — grouping restated as two independent toggles.

## Mono v1.0.0 — grouping restated as TWO independent merge rules
**Date:** 2026-08-12 · **On-chart:** "Jamal Mono v1.0.0" (shorttitle "JMono1.0")
**User spec:** "two toggles: monolithic candle for consecutive colors / monolithic candle for inside candles ('inside' as seen by the most immediate candle, not monolithic) / both toggles should play nicely together."
**The whole grouping is now two rules.** A bar CONTINUES the current mono if either accepts it, and starts a new mono if neither does:
- **COLOUR** (`merge_color`, default ON) — the bar is the same colour as the mono. This is the classic rule and the one `use_mono` runs on.
- **INSIDE** (`merge_inside`, default OFF) — the bar is inside the bar IMMEDIATELY BEFORE IT (`high <= high[1] and low >= low[1]`). Colour is irrelevant to this rule.

**What changed from v0.9.0/v0.8.0.** Colour merging was previously hardcoded as the base grouping with the inside rule bolted on as a special case; it is now a peer toggle, so all four combinations are meaningful. And the absorption machinery is GONE — `m_sealed`, `m_absorbing`, `m_abs_red`, the group-colour tracking and the "an absorbed bar also ends the mono" rule from v0.6.0-v0.8.0. That rule existed only because "inside" used to be measured against the mono's whole accumulated range, so without a stop a wide mono swallowed everything (the 27- and 26-bar monos). Measuring against the previous single bar removes that failure structurally: an absorbed group is a NESTED CHAIN, each bar contained by the one before it, which shrinks and terminates on its own. A sealing rule would also not compose cleanly with two independent toggles. **Flagged to the user as a deliberate drop, since it reverses an earlier explicit instruction whose premise no longer holds.**
**No-widening still holds:** `bar[1]` is already in the mono, so the mono's range contains it, so anything inside `bar[1]` is inside the mono. An INSIDE-rule join can never extend the mono's high or low.
**Inputs cut to exactly two toggles,** per the request. `show_len` folded into `label_min` (0 = no labels) and `show_split` deleted — it only applied in repeat mode and was redundant once the box edges mark every boundary. Remaining non-toggle settings: `body_pct`, `wick_w`, `label_min`, three colours.
**Tests run:** compile 0/0, saved as script version 14. **NEAR.P 1D, crosshair on the last bar — all four combinations:**

| colour | inside | monos |
|---|---|---|
| off | off | 2,128 |
| ON | off | **1,085** |
| off | ON | 1,766 |
| ON | ON | 831 |

Three checks pass. **Colour-only reproduces 1,085 exactly**, the baseline every prior version measured, so the restructure did not disturb the classic grouping. **Both-off gives 2,128 = one mono per bar**, which independently confirms the loaded bar count and that the degenerate case behaves. And the counts are **monotonic in both toggles** — adding a merge rule can only merge more, never less — which is the property an OR of two independent rules must have and the concrete meaning of "play nicely together".
**Not done:** no calibration case checked against the inside grouping; the symmetric-vs-low-only question is still open (a bar fails the inside test by taking out either the previous bar's high or its low, where the rule was first described with the low as the example); `use_mono` in jamal-ob is unaffected and still colour-only.
**Status:** superseded by v1.1.0 — colour becomes the base case, absorption the toggle.

## Mono v1.1.0 — colour is the BASE CASE; absorption is the toggle
**Date:** 2026-08-12 · **On-chart:** "Jamal Mono v1.1.0" (shorttitle "JMono1.1")
**User spec (a clean restart):** "base case is monolithic candle formation by color. toggle will be monolithic candle formation by absorption. rules for absorption: A candle of opposite color O always starts a new monolithic candle. if O is inside the candle immediately before it P, it should get absorbed the previous monolithic candle. if O+1 is also an inside candle as seen by O, also absorb into previous monolithic candle, and so on and so forth. Otherwise O is the beginning of the next monolithic candle."
**Implemented exactly as stated.** Colour grouping is no longer a toggle, it is the always-on base. `use_absorb` (default OFF) adds:
1. opposite-colour bar O starts a new mono, **unless**
2. O is inside the bar immediately before it → absorbed, mono enters ABSORBING phase;
3. while absorbing, each following bar is absorbed if inside **its own** immediate predecessor (O+1 inside O, O+2 inside O+1, …);
4. the first bar not inside its predecessor ends the mono and starts the next.
This also reconciles with the earlier "only two toggles" request: the two bools are now **absorption** and **one-candle rendering**.
**One ambiguity resolved and flagged:** absorption is TERMINAL. A bar the same colour as the mono, arriving after absorption began and not inside its predecessor, starts a NEW mono rather than resuming the colour run. Rule 4 is stated without a colour condition, and this is the only reading under which "and so on and so forth" terminates cleanly.
**Tests run:** compile 0/0. **NEAR.P 1D:** absorption OFF → **1,085 monos**, the colour-only baseline every prior version measured, so the base case is untouched. Absorption ON → **952**. Current mono 3 bars (10-12 Aug), 0 absorbed.
**Process — a long tooling failure worth recording.** After the Pine editor was closed with its window X and reopened via `pine-dialog-button`, **`pine_set_source` kept returning `success` with a plausible `lines_set` while the editor view still showed the old source**, and compiles kept saving the OLD version. Five injection attempts, a study remove/re-add, and a `pine_open` round-trip all failed to shift it; `pine_open` reported the saved script at 204 lines (v1.0.0), confirming the save target was stale, and `tv_health_check` reported healthy throughout. Resolution: killed and relaunched TradingView. **On restart the editor restored an UNSAVED buffer that already contained v1.1.0** — so the injections had been reaching the Monaco model all along and only the rendered view and the save path were stale. Compiling after the restart produced v1.1.0 correctly. **Lesson: `pine_set_source`'s return value proves nothing. Verify the version line in `.view-lines` after injecting and before compiling; if it disagrees, restart TradingView rather than re-injecting.**
**Not done:** no calibration case checked against the absorption grouping; the symmetric-vs-low-only question is still open; `use_mono` in jamal-ob is unaffected. Repo keeps a slightly fuller comment block than the TradingView copy (code identical).
**Status:** shipped, `use_absorb` default OFF so the pane mirrors `use_mono` out of the box.

# ========================= JAMAL FABLE — TRADE-FIRST SIGNAL + HARNESS (BUILD LOG) =========================
**Charter (2026-06-09):** the v1–v9 restart, inverted — trade-first, instrument-minimal, validation-before-conviction. Two trades only (pullback-continuation; flush-and-reclaim with in-trend 2A + chop 2B variants), structural BOS/CHoCH regime engine carried from v9, derivatives factors day one, and the validation harness built BEFORE the indicator earns conviction: Pine emits decision-time events as machine labels; the repo parses, fetches exchange bars, aligns, and judges. "TV draws it, something outside TV judges it." Spec: `docs/superpowers/specs/2026-06-09-jamal-fable-design.md` (rev 2 + v0.1 amendments). Plan: `docs/superpowers/plans/2026-06-09-jamal-fable.md`.

## Fable v0.1 — "the pipe": regime engine + event schema + harvest/align harness, end-to-end
**Date:** 2026-06-09 · **On-chart:** "Jamal Fable v0.1" (shorttitle "JFable0.1", version cell "Jamal Fable v0.1 · schema 1 · cfg 509208") · TV script "Jamal Fable" (id USER;77b6506a17b545908a3966ad81a3e7c8, created via Make-a-copy) · **Commits:** 061344d, 05e8e77, e6ebc92, c9f6007, 32909e0, eff2308, 8dea7dc.
**Built:**
- **Pine (`jamal-fable.pine`):** §3 regime FSM (CHOP↔UP/DOWN, CHoCH only to CHOP, never direct flips; HL_ref/LH_ref = most recent confirmed pivot while live → honest re-anchoring; range seeding: broken side undefined until first post-death pivot). Events as compact labels `JF|schema|script|cfg|src|trade|event|dir|tf|ts|px|k=v…`: `SYS|PING` on regime transitions, `SYS|PIV` on pivot confirmations. settings_hash over the 8 semantic knobs (defaults → cfg 509208); half-open transport window `[emit_from, emit_to)` excluded from the hash. All pivot bookkeeping + FSM confirmed-bar gated (realtime pivot flicker can't corrupt `var` state). Minimal render: regime tint, HL_ref/LH_ref/range lines, version cell.
- **Harness (Python, `harness/`):** `bars/fetch_bars.py` (ccxt binanceusdm, paginated, drops in-progress candle), `harvest/parse_labels.py` (JF-string tree walk, provenance-grouped JSONL one file per (schema, script, cfg, src, tf, symbol), dedup-idempotent, malformed→quarantine), `evaluator/align_check.py` (hard precondition: every event's bar must exist with matching price — PIV-H↔high, PIV-L↔low, else close, 0.1% tol; strict PIV typ), binding `README.md` methodology (no-pool rules, pre-registered annotations, episode rules for v0.2+). 10/10 unit tests green.
**Acceptance (the three pins):**
1. **Alignment:** BTCUSDT.P 4H, Apr→Jun harvest: **91/91 events aligned** against independently-fetched Binance bars; after chunk 2 merge: **173/173**. Zero quarantines.
2. **Provenance:** every event carries schema_version/script_v/settings_hash/src; grouping enforced on disk (`BTCUSDT.P_240_v1_s0.1_c509208_B.jsonl`).
3. **Label discipline:** one machine label per event; re-harvest → `new events: 0` (idempotent); chunked path exercised via the emit window (chunk 2 = Feb→Apr, 82 events, merged into the SAME cfg file — transport window excluded from hash by design).
**FSM eyeball (BTC 4H, Apr 30–Jun 10):** UP segment early-May with stepped HL_ref; CHOP gaps with orange range lines; DOWN through the June waterfall with LH_ref re-anchoring at each confirmed pivot high; PING sequence U→C→U→C→D→C→U→C→D→C→D→C→D — never a direct U↔D.
**Engine details surfaced for checkpoint:** (a) regime-entry seeding (hl_ref←last pivot low; trend_high←broken boundary); (b) within-bar ordering (pivots before FSM — parity-relevant); (c) confirmed-bar gating everywhere. Spec amended (§3/§9/§12).
**Status:** v0.1 pins ALL GREEN — **awaiting user checkpoint on regime behavior** before the v0.2 (Trade #1 detector) plan is written. Known cosmetic: 91 gray machine labels clutter the chart; a display toggle is a v0.2 candidate if wanted.

## Fable v0.1.1 — hide the machine labels (display toggle); spec/plan re-review
**Date:** 2026-06-09 · **On-chart:** "Jamal Fable v0.1.1" (shorttitle "JFbl0.1.1") · entity re-added (remove+re-add after compile).
**Problem (user):** the chart was covered in gray boxes — those are the event labels (the machine transport the MCP harvests), never meant for human eyes.
**Fix:** `show_labels` input (default OFF) renders labels **fully transparent instead of suppressing creation** — label objects still exist, so harvest is unchanged. Verified both halves: clean screenshot (no gray boxes) AND `data_get_pine_labels` still returns all events (98 on NEAR 4H, script_v stamped 0.1.1). cfg unchanged (509208) — the toggle is display-layer, excluded from settings_hash like the emit window. Spec §9/§12 amended.
**Re-review findings (spec + plan, fresh pass after v0.1):**
1. (fixed) **Bar-fetch range foot-guns** documented in harness/README: `--until` is 00:00 UTC of that date → pass tomorrow's date to cover today's events; `--since` must extend ≥ pivot_right bars before the emit window (PIV bar_ts = pivot bar, precedes its confirmation bar). Task-6 run was correct by luck of timing; now it's a written rule.
2. (verified in real data) same-bar PIV H+L occurs (3×on BTC 4H); dedup key's `typ` component handles it — the rev-2 fix was load-bearing, not theoretical.
3. (verified, self-healing) blowoff-top edge: if CHoCH fires before the top pivot confirms, range_hi seeds low but the late-confirming pivot extends it in CHOP (monotone max) — corrects with honest lag.
4. (noted, accepted) settings_hash is mod-1e6 — a hash collision pooling two configs is ~1-in-a-million; accepted residual risk.
5. (watch-item for v0.3) range boundaries only EXPAND during chop — a long chop can leave a stale far boundary for 2B targets/sweeps; spec'd intentionally, must be eyeballed in v0.3 chart validation.
6. (edge, documented) at the very first CHOP→UP of a chart, `hl_ref` seeds from the last confirmed pivot low — if none exists yet, UP has no CHoCH line until the first pivot low confirms (guarded by `not na`).
**Status:** chart now clean (tint + structural lines only). Checkpoint on regime behavior still open.

## Fable v0.1.2 — continuous structure lines (visual continuity)
**Date:** 2026-06-09 · **On-chart:** "Jamal Fable v0.1.2" (shorttitle "JFbl0.1.2").
**Problem (user):** the regime lines looked like disconnected floating segments (each regime's line appeared/vanished with `style_linebr` + per-regime `na`).
**Fix:** two ALWAYS-ON structure lines exploiting the FSM's seeded continuity (UP→CHOP hands `trend_high`→`range_hi`; CHOP→UP hands `range_hi`→`trend_high`; mirrors for DOWN): `upper_lvl` = trend_high (UP, faded teal = passive/T1 ref) / lh_ref (DOWN, opaque red = kill line) / range_hi (CHOP, orange); `lower_lvl` = hl_ref (UP, opaque green = kill line) / trend_low (DOWN, faded teal) / range_lo (CHOP, orange). Opaque = the body-close-beyond-it-changes-the-regime line; faded = context. Lines break only where a level is genuinely undefined (fresh-chop broken side). Verified on NEAR 4H: both lines flow unbroken across all regime transitions. Render-only → cfg unchanged (509208).
**Checkpoint result:** user APPROVED the regime engine ("then approve", conditional on continuity — delivered). v0.1 checkpoint CLOSED → v0.2 (Trade #1 detector) plan unblocked.

## Fable v0.2.0 — Trade #1 detector (both sides) + pivot parity + 1D filter
**Date:** 2026-06-09/10 · **On-chart:** "Jamal Fable v0.2.0" (shorttitle "JFbl0.2.0", version cell adds "· 1D <reg>") · **Plan:** `docs/superpowers/plans/2026-06-09-jamal-fable-v0.2.md` · **Commits:** f857e6b, 870341f, 9f1d8ab, ad8d0d2, dcd0d93 + this one.
**Built (in order, each gated):**
1. **Engine→pure-function refactor (`f_engine()`, var-local state)** so `request.security` can run it on 1D with an independent state copy and zero label side-effects. **Regression gate:** re-harvest reproduced all 91 in-window events **bit-exact** (diff_events.py; only-diff = the out-of-window chunk-2 events, as expected).
2. **Python pivot detector + parity check:** strict-inequality semantics matched Pine first try — **78/78 PIV events bit-exact** (parity_check.py gates the evaluator's §10 reimplementation license). Still 78/78 with the detector live.
3. **1D regime filter:** `request.security(…, "D", f_engine_reg()[1], lookahead_on)` = last CLOSED 1D bar, non-repainting; `reg1d` added to PING tail + version cell (additive factor).
4. **Trade #1 LONG detector** (UDT state — Pine can't reassign globals from functions): ARM (chain forms; 1D gate blocks arming only) / ENT (close > micro_LH, §7 snapshot levels lvl/stop/t1 embedded, full vector) / SKP rsn=rr (≥1.5R gate) / CXL rsn=newhigh|handoff|choch. Fixed tail key order `lvl|stop|t1|rsn|reg|reg1d|age|d_atr|d_pct|bz|mlh|rt1`; nulls emit `na`. Lime triangle on ENT.
5. **SHORT mirror** (separate T1SS type; rsn=newlow for the mirrored dissolve; red triangle).
**Bug found & fixed by event review:** `CXL rsn=choch` was never emitted — the FSM flips regime INSIDE f_engine before the detector runs, so the armed setup died in the silent regime-exit reset. Fix: thesis-death CXL emitted from the regime-exit path (the only way a trend dies is CHoCH, so the reason is exact); the in-regime branch was provably unreachable and removed. Verified live: CXL choch at 1779321600 (the exact D→C PING bar).
**Validation:**
- **Hand-trace (handtrace_v02.py): 3 episodes verified to the tick** vs independently-fetched bars — ENT L @1776600000 (rt1 1.73), SKP L @1776816000 (rt1 0.18), ENT S @1780963200 (rt1 1.91, live June downtrend). Implied pullback extremes land EXACTLY on real bar extremes (E2→73669.0 = the pivot low; E3→64250.0 = the PIV-H price).
- **Alignment: 128/128** events (all classes) vs Binance bars; **parity 78/78**; idempotent merge (probe re-parse added 37 new, deduped 23).
- **Every event class observed in real data:** ARM, ENT L+S, SKP rr, CXL choch/newhigh/newlow/**handoff** (a real LH_ref sweep while armed → correctly surrendered to future-2A per §4).
**Render:** structure lines switched to `style_stepline` (square steps, no diagonal connectors).
**Known coverage note (pre-registered):** canonical JSONL currently persists all SYS events + the recent-window T1 events (probe); April–May long-side T1 backlog merges on the next full harvest — dedup makes this safe by construction.
**Status:** v0.2.0 acceptance evidence complete — **awaiting user checkpoint on the entry triangles** before the v0.3 (Trade #2) plan.
**Checkpoint result:** APPROVED ("the entries aren't bad… generally seem to call direction ok"; fewness explained = the 1.5R gate; "snipe" expectation = Trade #2's slot). Realized outcomes of the three T1 entries (evaluator-style bar-walk): E1 stopped (−1R), E2 hit T1 (+1.65R partial point), E3 short open — the loss→deeper-re-entry sequence is decision #2 working as designed.

## Fable v0.3.0 — Trade #2: 2A flush-and-reclaim + 2B chop-boundary fade
**Date:** 2026-06-10 · **On-chart:** "Jamal Fable v0.3.0" (shorttitle "JFbl0.3.0") · **Plan:** `docs/superpowers/plans/2026-06-10-jamal-fable-v0.3.md` · **Commits:** 736da78, b963536 + this one.
**Built:** stateless one-bar detectors (spec §6 — the sweep bar IS the entry bar, entry = its close; no ARM/CXL states): **2A** at the trend kill line (lvl=HL_ref/LH_ref, stop=wick±0.5·ATR, t1=trend extreme) and **2B** at chop walls (both walls required; t1=midpoint; the ≥1.5R gate doubling as the width gate). Decisions: 1D gate = logged `SKP rsn=1d` (no silent gating); `wkp` = percentrank of the relevant wick in ATRs (window 200); `t1co` coincidence factor; diamond marks (trade identity lives in the event log). T1 short-side declarations hoisted above the shared captures.
**Task 1 first (provenance-critical):** full T1 backlog persisted at s0.2.0 BEFORE the version bump — 85 events merged, **213/213 aligned**.
**§4 contract closed end-to-end:** the May-27 BTC bar (1779796800) now shows BOTH halves — T1 `CXL rsn=handoff` AND 2A `SKP rsn=rr` with `t1co=1`, `wkp=99.5` (the violent flush was handed off, evaluated by its owner, and declined on R: the bounce had consumed the move). One candle, one owner, judged.
**First real signals:**
- 2A shorts (BTC May downtrend): 5 ENTs at the LH_ref sweeps — rt1 1.68/4.49/1.6/2.25/1.78, wkp 66–92. Consecutive-bar sweep ENTs each re-qualify (stateless design); the evaluator's per-direction sequential rule will collapse them into one episode.
- 2B longs (NEAR post-May-26 chop): 3 ENTs fading the **May-31 range-low sweeps** at 2.245–2.276 (rt1 4.25/3.15/3.99, t1=midpoint ~2.61) — the exact zone the Jamal-OB bullish block anchored on, before the run to 3.085. Plus `SKP rsn=1d` on the **June-3 sweep of the 2.978 wall** (1D was UP) — that blocked short preceded the crash; logged, so the backfill can judge the 1D gate with evidence.
**Hand-trace (handtrace_v03.py): 3 episodes to the tick** — 2A ENT S (stop==bar_high+0.5·ATR exactly), the t1co=1 handoff bar, 2B ENT L on NEAR (incl. implied range_hi == 2.978, proving the seeded-wall geometry). Alignment: BTC s0.3.0 8/8, NEAR 6/6.
**Stale-wall watch-item verdict (spec follow-up):** no pathology observed — NEAR's chop walls tracked honestly (range_lo stepped 2.269→2.209 with the pivots; range_hi=2.978 was the dead trend's high, i.e., the real liquidity pool, and its June-3 sweep was a legitimate boundary event). Keep watching across the basket in the backfill campaign.
**Coverage note:** s0.3.0 canonical files persist the 2A/2B event classes + notable T1s (BTC 8, NEAR 6); SYS/T1 under s0.3.0 are identical to the verified s0.2.0 set modulo script_v; the full multi-symbol sweep lands with the backfill campaign.
**Status:** v0.3.0 acceptance evidence complete — **awaiting user checkpoint on the diamonds** before the v0.4 (derivatives factors) plan.
**Checkpoint result:** APPROVED after a full outcome audit prompted by the user's "some do, some don't": all **11 closed Trade-#2 entries across BTC/NEAR/SOL reached T1 before stop** (2 open). The "don't look right" diamonds decompose into three measurable shapes — high-giveback fills (entry-at-close lands 0.4–1.1 ATR off the level on violent reclaim bars), cluster stacking (consecutive re-qualifying sweeps; evaluator's one-episode rule handles accounting), and sweeps of freshly re-anchored lines (pivot-true but not eye-obvious). Resolution per architecture: no rule changes — **`gvb` (giveback in ATRs) added to the v0.4 factor list** so the campaign can judge the eye-test with evidence.
**Recall audit (user: "expected more entries"):** BTC funnel 61 ARMs → 35 SKP (only 7 near-misses 1.0–1.5R; 28 genuinely <1R) + 17 V-dissolves + 4 choch + 1 handoff → 3 ENTs. Diagnosis: R-GEOMETRY (stop at full pullback extreme + target at prior extreme), not the 1.5 threshold; plus T1's 1D-arming block was SILENT (invisible misses Apr 27–29, May 7–8); plus scope — generalized sweep simulation found **~312 sweep-reclaim bars vs the last-5 pivots where 2A considered 8** (kill line only). Resolutions: `ARM rsn=1d` (v0.4), MFE in the campaign evaluator, **"2A-general" promoted from backlog to the v0.5 slot** (spec §14), filtered by the campaign's factor report.

## Fable v0.4.0 — derivatives factors + gvb (the last spec layer before the campaign)
**Date:** 2026-06-10 · **On-chart:** "Jamal Fable v0.4.0" (shorttitle "JFbl0.4.0") · **Plan:** `docs/superpowers/plans/2026-06-10-jamal-fable-v0.4.md` · TV relaunched w/ CDP via UWP activation (memory route).
**Built:** append-only tail extensions on every T1/2A/2B event — `oi_d` (T1: setup-window OI %Δ via `oi0` UDT snapshot; 2A/2B: sweep-bar %Δ), `oi_t` (T1 trigger-bar OI direction), `q` (price×OI quadrant, 14-bar), `fp` (premium percentile — Binance `_PREMIUM` feed, spot-proxy fallback, rank-invariant), `gvb` (|close−lvl|/ATR). Plus the recall-audit fix: **T1's blocked watches now emit `ARM rsn=1d`** (was silent). All null-guarded (`na`, never a kill).
**Discovery:** no searchable Binance `_OI` ticker, but the auto `<prefix>:<ticker>_OI` RESOLVES on Binance and Bybit (empirically; `BTCUSDT.P_OI`, `BYBIT:NEARUSDT.P_OI` both live). `_PREMIUM` derivative-metrics feed found via search and preferred for `fp`. **Hazard documented:** a garbage value in the OI override `input.symbol` kills the study (TV validates before `ignore_invalid_symbol`); override must hold real symbols only.
**Verification:** live ENT S vector reads `oi_d=-4.24|oi_t=dn|q=PU.OD|fp=10.5|gvb=1.2` — OI contracting through the short-covering bounce, depressed premium: the flush thesis, measured. **ccxt cross-check (oi_crosscheck.py): sign agreement 3/3** vs Binance openInterestHistory (exchange −3.65/−4.24/−4.48% vs Pine −4.24/−4.50/−2.45%; ±2% sampling slack between feeds — tolerable for a never-gating factor). s0.4.0 probe persisted, 4/4 aligned; 12/12 tests.
**Status:** spec §8 factor set COMPLETE. **Awaiting user checkpoint on factor sanity → then the BACKFILL CAMPAIGN plan** (4-symbol basket, episode simulation with exit codes + counterfactuals + MFE, factor-conditioned report) — the first time the harness judges instead of records.

## Fable v0.4.1 / v0.4.2 — human-readable inspection layer (render iterations at the checkpoint)
**Problem (user):** "Show event labels" rendered 240 overlapping raw transport strings — un-hoverable, unreadable. v0.4.1 (tooltips on transport labels) didn't fix the overlap.
**v0.4.2 (the real fix):** transport labels demoted to a debug-only toggle ("unreadable by design"); the **entry marks became the human layer** — plotshape triangles/diamonds replaced by small labeled chips (`T1`/`2A`/`2B`, lime-below=long, red-above=short) whose hover-tooltip is the full event card (entry, lvl/stop/t1, rt1, oi_d/oi_t/q/fp/gvb). Entries are rare → no overlap; trade identity now visible at a glance. Harvest transport unchanged (machine text untouched; entry-chip labels add ~1 per ENT to the 500 budget). Also: TV studies restored from a saved layout do NOT refresh on in-place compile — remove+re-add required (bit twice this session; rule re-confirmed).
**v0.4.3:** Data Window plots (per-bar regime/age/1D/ATR/OI/OI-chg/premium/fp/wick-pctiles/quad-signs/giveback) — crosshair any bar for the live state; verified populated via data_get_study_values (OI 100.5k matches the ccxt scale — one more independent agreement).

## Fable v0.4.4 — pre-campaign emission fixes (external review, 4 findings)
**Date:** 2026-06-10 · the campaign freeze version. Nothing had been harvested for the campaign yet → no cross-version pooling exists.
1. **Blocked-ARM spam (CRITICAL):** `ARM rsn=1d` re-emitted on every chain-growth bar of a 1D-blocked pullback → at the 500-label cap Pine FIFO-evicts oldest labels SILENTLY — evicted real events vanish from the harvest and `align_check` cannot detect absence (the one tripwire-less failure). Fix: `blk` flag on both UDTs — ONE blocked-ARM per pullback cycle; full reset clears it.
2. **1d-SKPs were unwalkable:** emitted with `stop=na/rt1=na`, so the campaign's 1D-gate pseudo-episodes would have silently returned an empty set (the walker's own `no_levels` drop). Fix: stp/rt1 computed on the sweep bar and passed in ALL 1d branches (2A both sides, 2B both directions) — snapshot doctrine preserved, no repo-side reconstruction.
3. **`t1co` could disagree with the handoff:** the pre-captured coincidence checked the PREVIOUS bar's chain; T1's handoff checks after same-bar chain growth (engulfing lower-low bars diverge). Fix: `t1co` is now set by T1's own handoff branch — consistent with `CXL|handoff` by construction.
4. **(Backlogged, pre-Stage-2 gate):** `barstate.isconfirmed` semantics inside the `request.security` 1D engine copy are unverified for LIVE bars (TV's documented behavior is counterintuitive; a developing daily close could corrupt the D-copy's `var` state). Backfill immune. Robust pattern noted: gate D-copy mutations on `ta.change(time("D"))`. Spec §14 updated.
**Also recorded:** engine detail #8 (spec §3) — T1's chain grows and can trigger in the SAME bar pass; Python parity must replicate. Campaign plan corrected: harvests pool s0.4.4 ONLY (the "0.4.x render-only" claim was wrong as of this version).

## Fable v0.4.5 + BACKFILL CAMPAIGN — the first judgment pass
**Date:** 2026-06-10/11 · **Report:** `harness/reports/campaign_2026-06.md`.
**v0.4.5 (found AT harvest time):** entry chips weren't window-gated — ALL-HISTORY chips (265 on BTC) filled the label budget to exactly 500, one label from evicting in-window events. One-line fix (`in_window` on f_mark); freeze moved to s0.4.5. Also discovered: oversized MCP results auto-save to disk → harvest transport now costs ~zero context (copy file → parse), and clipboard-paste (Set-Clipboard → Ctrl+A/V in the editor) replaces full-source resends.
**Harvests:** BTC 235/235, ETH 187/187, SOL 235/235, NEAR 214/214 aligned (871 events, 4 symbols, Apr 1→Jun 11, s0.4.5 only).
**Evaluator:** episodes.py (8 tests) + report.py (smoke) + sanity_gate.py. **Gate initially FAILED 2/11** — and the investigation VALIDATED the walker: the two disagreements were §7 thesis-exits (bar closed back through the kill line before target) that the cruder v0.3 stop-vs-target audit couldn't see; both graded `cf=recovered`, exactly matching the v0.3 eventual-target observation. Gate criterion corrected to spec-equivalence → PASS.
**Headline (n=30 episodes, 27 closed — SMALL SAMPLE, directional reads only):** win 52%, avg +0.96R, med MFE 1.42R. April 64%/+1.28R; May 38%/+0.63R; June 3 open. skip_overlap collapsed 12 clustered entries.
**Gate questions answered from logged skips (the architecture's payoff):**
- (a) **rr gate KEEP at 1.5**: pseudo-episodes below the gate earn ≤+0.44R avg (1.25–1.5 band: 55%/+0.44R; <1.0: ~zero/negative) vs +0.96R for taken entries — lowering dilutes.
- (b) **1D gate KEEP**: blocked sweeps graded 33% win / −0.25R as-if-taken — the gate is net-saving (incl. the NEAR Jun-3 monster it missed; the class still loses).
- (c) thesis-exit counterfactuals 2 recovered / 2 stopped — no evidence against §7.
**Factor reads (small-n):** `rt1>3` 5/5 wins +3.84R (high-R setups carried the book); `fp<25` 80%/+1.91R (washed-out premium); **`wkp` INVERTED vs intuition** — modest wicks (<50pct) 75% beat violent flushes (>85pct, 40%); `gvb` INCONCLUSIVE (the eye-test factor shows no clean edge yet); `reg1d` aligned-with-trend 4/4 (n=4).
**Status:** report committed — **awaiting user review** (the decisions: rr gate, 1D gate, gvb, v0.5 2A-general selectors).

## Fable v0.4.6 — covariate emission release (Request-library migration)
**Date:** 2026-06-11 · **On-chart:** "Jamal Fable v0.4.6" (`JFbl0.4.6`) · **cfg 553046** (was 509208 — 4 new hashed knobs) · plan `docs/superpowers/plans/2026-06-11-jamal-fable-v0.4.6.md`.
**Code changes (EMISSION-ONLY — zero signal-logic edits, to be proven by emission-diff vs s0.4.5):**
- **Derivative data migrated to official libraries** (user-corrected: these were never raw-ticker-only): `import TradingView/Request/3 as r` — OI via `r.openInterestCrypto()` (5-tuple, never nz raw OI), funding via `r.cryptoDerivativeMetric("Funding Rate")`, liquidations via `"Liquidations Buy"` (= SHORTS force-closed) / `"Liquidations Sell"` (= LONGS force-closed). The `_OI` security feed AND the OI-override `input.symbol` (garbage-value study-kill hazard) are DELETED. `_PREMIUM`-based `fp` retained alongside the new actual `fr`.
- **CVD:** `import TradingView/ta/9 as tvta` → `tvta.requestVolumeDelta("60")`, bar delta = last−open. (Plan's `ta.requestVolumeDelta` doesn't exist as a built-in — compile-gated fallback to the ta library worked first try.)
- **New covariates, all logged never gate:** `os` (signed linreg-anchored ATR-normalized overshoot; anchor on `[1]` so the signal bar can't drag the fit) + `osp` (percentrank of |os|), `er` (Kaufman), `vz` (volume z-score), `dlt` (60m CVD bar delta), `swd` (sweep penetration in ATR, t2 tails only), `age_t` (bars since swept level set, via `ta.barssince(lvl != lvl[1])`), `fr`, `lqb`, `lqs`. Appended in fixed order via shared `f_cov_tail()`; `f_t2_tail` gains `(swd, aget)` params across all 12 call sites.
- New hashed knobs: `os_linreg_window=50`, `os_pctile_window=200`, `er_window=20`, `vz_window=100`. Renamed `f_reg_str`/`f_engine_reg` locals `r`→`rg` (library-alias collision).
- 7 new Data Window plots (os/er/vz/dlt/fr/lqb/lqs).
**Tests run:** pine_smart_compile clean (after the two expected fixes: requestVolumeDelta namespace; ta.sma extracted from ternary); study removed+re-added; version cell v0.4.6/cfg 553046; `data_get_study_values` on NEAR 4H shows ALL new DW values non-na (OI 41.79M, fr 0.010%, lqb 3, lqs 588, dlt −4.89M, vz −1.92, er 0.103, os +1.19).
**Status:** Pine live; feed cross-checks, harness report v0.4.6, basket re-harvest + emission-diff next.

## Fable v0.4.6 close-out — re-harvest, emission proof, report
**Date:** 2026-06-11 · **Report:** `harness/reports/campaign_2026-06_s046.md`.
**Feed verification:** library OI vs ccxt — BTC 102,767.6 vs 102,762.1 (0.005%), NEAR 41.79M vs 41.81M (0.05%); funding sign agreement both (chart fr is in PERCENT; ccxt decimal).
**Harvests:** BTC 235 + ETH 189 + SOL 238 + NEAR 215 = 877 events, all aligned, s0.4.6/cfg 553046 only.
**Emission-only PROOF (compare_emissions.py):** all 871 events shared with s0.4.5 are bit-identical on every pre-existing key — including `oi_d`/`q`, meaning the Request-library OI series matches the old `_OI` ticker exactly on every event bar. One false positive (NEAR PIV at 1781121600) traced to PIV backdating (§9: bar_ts = pivot bar, emission = +3 bars) — horizon rule fixed, PASS 4/4.
**Coverage (coverage_check.py):** fr/lqb/lqs/dlt **0% na back through April** — full-window history for funding, liquidations AND 60m CVD. swd/age_t na on T1 rows is structural (t2-only keys).
**Sanity gate:** PASS — the 11 v0.3-audited entries grade identically from s0.4.6 data.
**Report:** headline unchanged (n=30, 52%, +0.96R — regression-clean). New factor reads (ALL small-n):
- **`vz<0` (quiet entry bars): 77% win / +1.86R vs `vz` 0–1.5: 27% / +0.03R** — the standout; rhymes with the wkp-inverted finding (quiet sweeps beat violent ones).
- **`lq_tot` low within swd<0.3: 62% / +1.51R vs lq high: 45% / +0.89R** — same quiet-beats-loud shape in liquidation space.
- **Per-trade `rt1` (critique #5 answered): the >3 row is ENTIRELY Trade-#2 family** (2A 3/3 +3.94R, 2B 2/2 +3.69R; T1 never produces rt1>3). The "high projected R" selector is a 2A/2B property.
- `osp` FLAT (55/45/60%) — the OS stretch thesis's free first read on existing trades: neither confirmed nor refuted. `os` signed: stretched-down slightly best, but signed-os-vs-trade-direction conditioning is the v2 refinement.
- `fr>=0` 59%/+1.30R vs `<0` 40%/+0.39R (crude long/short mix; `fp<25` remains the better-formed funding read).
- LQ_SPLIT = harvested median 3834.5 — units feed-native, NOT cross-symbol comparable (per-symbol normalization = v2).
**Status:** v0.4.6 COMPLETE — awaiting user review (campaign decisions + v0.5 unified sweep engine go-ahead).

## Fable v0.5.0 — generalized sweep engine (OS) + 1D gate off + campaign 2
**Date:** 2026-06-11 · **On-chart:** "Jamal Fable v0.5.0" (`JFbl0.5.0`) · **cfg 209091** · plan `docs/superpowers/plans/2026-06-11-jamal-fable-v0.5.md` · report `harness/reports/campaign_2026-06_s050.md`.
**Code:** Trade `OS` = stateless sweep-reclaim of a generalized level set (`lvl_src=` piv last-5/pdl/pdh/pwl/pwh via D/W security closed-candle + roll k=20 stretch-gated at 1.5 ATR), deepest-level dedup + `n_lvls`, `align=W/A/N` chips (green/red/gray), `oco=1` on kill-line coincidence, target = entry-snapshotted linreg anchor; `use_1d_gate` knob DEFAULT OFF (user ruling, pre-registered against n=9). Evaluator: thesis-exit v2 (`cf_r`/`rule_delta_r`), 1D ruling-watch cohort, direction-oriented conditioning (os/fr/fp/q), rr-2.0 + skip-overlap sensitivity appendices. 29/29 tests.
**Verification:** hand-traces 4/4 to the tick from ccxt bars (linreg anchor to 8dp, stretch gate, deepest-dedup, oco co-presence); emission-diff vs s0.4.6 PASS (deltas = OS + 12 gate-swaps + 20 T1 arming-divergences ONLY); sanity gate PASS. **Ops:** NEAR's single-window pull FIFO-evicted 20 early-April labels at the 500 cap — recovered by chunked re-pull; ALWAYS harvest in ≤6-week chunks at v0.5 event density. Transient Binance 451 (geo) mid-session — cleared on retry.
**Campaign 2 (deep window Jan 1→Jun 11, 3,883 events, 515 ENTs, 258 sequential episodes):**
- **Headline: the raw expanded book is breakeven** (25% win, 0.00R) — entry expansion found volume, not edge; the selectors are the product. OS raw: ~22% win, −0.1R.
- **Thesis-exit v2 (n=93): NET −3.67R.** 73/93 exits saved a stop (+), but the 19 recoveries forfeited large +rt1 each. Per-trade: 2B +3.43 KEEP, T1 +0.36 KEEP, 2A −2.68, **OS −4.78 — the third exit HURTS the new trade**; v0.6 question: drop thesis-exit for OS (its lvl is a swept level, not a regime line).
- **1D ruling-watch: ~no cost so far** (blocked 23%/−0.06R vs passed 26%/+0.02R, n=60/198). Scoreboard standing.
- **Campaign-2 hypothesis SUPPORTED directionally on 10× the data:** er>0.45 (trends) 15%/−0.34R vs chop 29%/+0.12R — sweep-reclaims are a CHOP tool; vz<0 31%/+0.19 vs vz 0–1.5 20%/−0.15; wkp<50 50%/+1.11 vs >85 15%/−0.26. Quiet, shallow, in-chop survives; violent/trending fails.
- **OS reads:** align=W 40%/+0.14 vs A 20%/−0.23 (the against-regime fade still loses — Phase-1's ghost, now with n); lvl_src: pdl best (32%/+0.18), roll worst; **OS rt1>3 INVERTED (8%/−0.42)** vs 2A rt1>3 (57%/+2.07) — far linreg targets don't get hit, exactly the pre-registered mechanical-correlation warning.
- **Oriented conditioning resurrected funding** (supportive fp 38%/+0.52 vs against 19%/−0.16) and exposed `PA.OD` (price-against + OI-down washout) 44%/+1.01.
- rr sensitivity: rr 2.0 would WORSEN the book (−0.07R) — 1.5 stays. skip-overlap sensitivity: independent 29%/+0.12 vs sequential 25%/0.00 (mild shaping, noted).
- KNOWN ARTIFACT (fix in v0.6 report): the rr-gate pseudo table's `rt1=na` row (757 anchor-wrong-side OS skips) grades meaninglessly (target already passed at entry) — exclude from that table.
**Status:** v0.5.0 COMPLETE — awaiting user review (v0.6 directions: OS selector study (W-align + chop + quiet + pdl), OS thesis-exit reconsideration, per-symbol lq normalization).

## Fable v0.6.0 — OS levels: daily/weekly only (DESCOPED release)
**Date:** 2026-06-12 · **On-chart:** "Jamal Fable v0.6.0" (`JFbl0.6.0`) · **cfg 935851** · plan `docs/superpowers/plans/2026-06-11-jamal-fable-v0.6.md` (scope-override header).
**USER DESCOPE at plan review:** the full v0.6 design (unified nearest-structure targets + 1.0R gate, OS thesis-exit removal, SYS|STR stretch marker, wVWAP/FVG machinery) is PARKED in spec §14 + the plan. Shipped: **OS sweeps prev DAY/WEEK extremes only** — `os_use_piv`/`os_use_roll` hashed toggles, default OFF (campaign-2 verdicts: piv 23%/−0.07R, roll 22%/−0.10R; daily levels best 32%/+0.18R). rr_min STAYS 1.5; all targets unchanged (OS keeps the linreg anchor); OS keeps its thesis exit. Pivot/roll machinery retained behind the toggles (one-line re-enable; their s0.5.0 data remains minable offline). Report fix: rr-pseudo table excludes the meaningless `rt1=na` rows (anchor-wrong-side skips).
**Status:** Pine live; evaluator bump + deep re-harvest + campaign 3 next.

## Fable v0.6.0 close-out — campaign 3 (daily/weekly OS)
**Date:** 2026-06-12 · **Report:** `harness/reports/campaign_2026-06_s060.md`.
**Harvests:** BTC 738 + ETH 649 + SOL 716 + NEAR 717 = 2,820 events (Jan 1→Jun 12), all aligned, 16 chunks. **Invariant diff PASS:** 1,064 OS piv/roll events dropped, ~504 stacked bars cleanly re-selected their daily candidate (level-identity keys only), every other event bit-identical. Sanity gate PASS. One transient quarantine (post-fetch bar) cleared by bars refetch.
**Campaign 3 (158 sequential episodes):**
- **Headline improved: 28% win / +0.10R** (campaign 2: 25% / 0.00R) — the level cut removed mostly-losing volume. OS curated to 96 episodes; daily classes ~flat (pdl 29%/+0.08, pdh 29%/0.00, pwh 33%/+0.11), **pwl 0/7 (−0.66R)** — prior-week-low longs are the new worst slice.
- **1D ruling-watch FLIPPED in the user's favor:** would-have-been-blocked 32%/+0.14 vs passed 27%/+0.08 (n=34/124) — the old gate would have COST money this window. Ruling vindicated so far.
- Persistent selectors (3rd consecutive campaign): vz<0 32%/+0.27 vs 0–1.5 23%/−0.14; wkp<50 57%/+1.40; er>0.45 trends still negative (21%/−0.14); osp>85 extreme stretch still bad (16%/−0.19); OS align=W 40% > A/N.
- OS rt1>3 still inverted (7%/−0.47 — the far-anchor pathology persists while the linreg target stays, per descope); 2A/2B rt1>3 still strong (50%/+1.69, 50%/+1.50). rr 2.0 still worsens the book.
- Thesis-exit v2 (n=51): net −4.80R ALL; OS −3.38, 2A −3.22, 2B +1.44, T1 +0.36 — evidence for the parked OS/2A third-exit question keeps accumulating.
**Status:** v0.6.0 COMPLETE — parked designs (unified nearest-structure targets, OS thesis-exit removal, STR marker) remain in spec §14 + v0.6 plan, each with growing evidence.

## Fable v0.6.1 + v0.6.2 — OS chip recolor + alignment-aware targets · campaign 4
**Date:** 2026-06-12 · **Report:** `harness/reports/campaign_2026-06_s062.md` · cfg 935851 (unchanged; logic carried by script_v).
**v0.6.1 (display-only, 249b4bb):** OS chips per user scheme — with-regime long=GREEN / short=RED, against-regime=YELLOW, chop=GRAY. Sweep-side rule audited on user question: longs already sweep ONLY pdl/pwl, shorts ONLY pdh/pwh (a prior explanation misstated this; code was always correct).
**v0.6.2 (37151df, user ruling):** OS target is now ALIGNMENT-AWARE — with-regime → trend extreme (2A's target), against-regime → fair-value anchor, chop → range midpoint; `tgt=` (tex/fv/mid) logged. Re-harvest 16 chunks: same event counts (738/649/716/717), diff PASS (~380 OS retargeted, 146 ENT↔SKP gate flips, one `oi_d` feed restatement on a live-edge SOL event — known ±2% sampling slack). Sanity gate PASS.
**Campaign 4 (162 episodes): headline 29% / +0.16R** — third consecutive improvement (breakeven → +0.10 → +0.16). The W-aligned OS population TRIPLED (15→50; the trend-extreme target clears the 1.5 gate far more often than the far anchor) and is now profitable at scale (28%/+0.16); `fv` (against-regime) remains the weakest target class (26%/+0.01). osp>85 extreme stretch: 5% win / −0.54R (worst slice, 4th consecutive campaign); pwl longs now 0-for-8.
**Status:** v0.6.2 COMPLETE.

## Fable v0.7.0 — FVG sweep class · third exit removed · campaign 5
**Date:** 2026-06-12 · **Report:** `harness/reports/campaign_2026-06_s070.md` · cfg 935851 (script_v carries provenance).
**Third exit REMOVED first (39fa316, user ruling):** all trades run to stop/target; `APPLY_THESIS_EXIT=False` reversibility flag; campaign 4 re-rendered 34%/+0.13R. **pwl autopsy:** all 16 pwl longs were A/N-aligned by construction (price under last week's low cannot be with-trend) on violent bars — structural knife-catch class.
**v0.7.0 (88de9db):** FVG zones as OS sweep levels per spec §14 pinned rules — bull zone [high[2], low] / bear mirror, `lvl` = near edge, close-through-far-edge retires, cap 20/side, sweepable bar-after-formation, `fvg_sz` logged, NO size gate. **Audit (verify_os_v070.py): 1,817 OS events PASS** incl. full zone-lifecycle re-simulation from raw bars (warm-up skip: chart zones predating the bars file, empirically Jan-only; fvg_sz<0.005 ATR rounds to 0 — display precision).
**Campaign 5 (3,943 events, 233 episodes): 34% / +0.10R** — held campaign 4's level while adding 50% more trades. **FVG instantly the largest OS class (n=126): 32%/+0.01R raw — flat, neither edge nor drag.** Sharpened with n: align W 38%/+0.33 and N 43%/+0.33 vs **A 21%/−0.39 (yellow chips = the book's drag, 5 campaigns consistent)**; osp gradient cleanest yet (<50: 47%/+0.57; >85: 12%/−0.59); pwl longs now 0-for-5 at −1.00R avg.
**Demotion candidates with convergent multi-campaign evidence: align=A (yellow), osp>85, pwl-longs.**
**Status:** v0.7.0 COMPLETE — awaiting user review.

## Fable v0.7.1 — per-class OS trade codes (OSD/OSW/OSF) · yellow-chip study
**Date:** 2026-06-12 · **Report:** `harness/reports/campaign_2026-06_s071.md` · cfg 935851.
**Yellow study (user question "what separates a good yellow from a bad one", 132 independent A-aligned entries):** the separator is the LEVEL CLASS — calendar-level yellows are GOOD (pdh 50%/+0.54, pwh 42%/+0.31, pdl 39%/+0.22; pooled non-FVG ~38%/+0.18) while **FVG yellows are the poison (20%/−0.35, n=87 = 2/3 of all yellows)** — fading a gap-retest against a fresh trend fights the most crowded continuation setup. Secondary: osp>85, rt1>3, stacked-levels all degrade yellows further; only large zones (>0.8 ATR) hold up within FVG-yellow.
**v0.7.1 (eba385e):** OS split into per-class trade codes — **OSD** (prev-day), **OSW** (prev-week), **OSF** (FVG); chips show the class; deepest-dedup unchanged (one entry per bar/dir, named by winning class); generic "OS" reserved for the toggled-off piv/roll. Evaluator: OS-prefix filters; per-class rt1 tables now automatic.
**Verification:** rename-diff PASS (mapped OSD/OSW/OSF→OS: all 3,943 events bit-identical to s0.7.0); OS audit 1,817/1,817 PASS; sanity gate PASS; counts identical per symbol.
**Status:** v0.7.1 COMPLETE — open ruling: demote OSF×yellow (keep calendar yellows), osp>85, pwl-longs.

## Fable v0.7.2 — yellow-OSF suppression (first evidence-earned entry gate) · HYPE · studies · campaign 6
**Date:** 2026-06-12 · **Report:** `harness/reports/campaign_2026-06_s072.md` · **cfg 11295**.
**Studies this cycle (all committed with writeups):** waterfall-fallback (option-3 chain REJECTED: 18 unlocked trades 28%/−0.05R; blind spot is protective); single-use FVG (REJECTED: touch count = noise; REAL finding = zone-freshness gradient, registered); prev-candle-sweep requirement (REJECTED/inverted: higher-low reclaims at daily levels outperform, registered); cap-10 (immaterial: 4% of entries, flat). **HYPEUSDT.P added** (1,044 events aligned; deep bars to Jun-2025 after the audit caught months-old zones predating the file).
**v0.7.2 (de8677e):** `osf_skip_against` hashed knob default ON — OSF entries with align=A emit `SKP rsn=aln` (full levels logged) instead of trading. Evaluator: aln pseudo-episodes + standing (b2) scoreboard (CORRECTED to rt1≥1.5 would-have-been-entries only — the raw pool includes sub-gate skips that grade trivially), OSF freshness standing table (in-sample flag).
**Verification:** diff PASS (only OSF-A designation/rsn changes, 493 events across 5 symbols); OS audit 2,284 PASS; gate PASS.
**Campaign 6 (5 symbols, 254 episodes): 36% win / +0.17R — best book yet** (was 33%/+0.06 pre-suppression). Ruling-watch: suppressed cohort as-if-taken = 28%/−0.11R (n=130) — the gate removes a verified-losing population.
**Open:** osp>85 + pwl-long demotions; campaign-6 hypothesis docket (zone freshness, re-test rhythm, higher-low reclaim — in-sample until post-registration data accrues).

## Study — 1h timeframe transfer (2026-06-13)
**Report:** `harness/reports/study_2026-06_1h_timeframe.md`. `report.py --tf` param (240/60) folds timeframe into the no-pool key; 1h events live in `*_60_*` files (never pool with 4H).
**Harvest:** BTC + HYPE on 1h, Jan→Jun, 24 chunks, 7,203 events ALL aligned. **osp>85 re-validation (4H, full sample):** confirmed n=88, 20%/−0.34R, holds in every trade type EXCEPT 2B (2B fine at extreme stretch — its setup IS stretch-to-wall). pwl-longs SOFTENED on full sample (now 21 trades 19%/−0.38, 4 winners all post-HYPE) → demoted from the demotion list, hold.
**1h VERDICT — does NOT transfer:** pooled 27%/−0.13R vs 4H 36%/+0.17; BTC alone +0.05R (edge → ~zero), HYPE −0.19R. The 4H calibration catches 1h microstructure that doesn't revert. **Factor structure partially survives** (osp>85 worst on both symbols independently; W>A and quiet>violent orderings kept but compressed below breakeven) — and **er-chop INVERTS** (good on 4H, worst on 1h). **The instrument is a 4H tool; 1h needs its own recalibration + campaign (separate project).** Keeper: osp>85 loses on every TF/symbol/campaign — most validated finding in the project, cross-TF confirmation that the osp>85 demotion is real.
