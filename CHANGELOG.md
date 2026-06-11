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
