# Jamal Fable v0.4 (Derivatives Factors + gvb) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Project override:** NO worktrees/branches — inline on `main`, commit + push per task. TV via MCP loop.

**Goal:** Wire the §8 derivatives factors — `oi_d` (OI delta over the setup window), `oi_t` (OI direction on the trigger bar), `q` (price×OI quadrant), `fp` (funding/premium percentile) — plus the new `gvb` (giveback-from-level in ATRs, the measurable form of the v0.3 eye-test) into every T1/2A/2B event tail. **Null-safe everywhere:** a missing feed is `na` in the vector, never a kill (§8 reason 3). This is the LAST spec layer before the backfill campaign.

**Architecture:** All factors are additive tail keys (appended at the END — existing key order untouched, schema_v stays 1). OI via `request.security(<ticker>_OI, …, ignore_invalid_symbol=true)`; funding via the spot-premium proxy (always computable; spec §8 explicitly allows "funding/premium percentile"). T1's setup-window OI snapshot lives in a new UDT field.

**Spec:** §8 (factor table + never-gates doctrine), §12 (knobs `quadrant_window`/`funding_pctile_window` already exist). Version → 0.4.0.

---

## Decisions locked here
1. **Funding = spot-premium proxy in v1:** `prem = (perp_close − spot_close)/spot_close`, `fp = percentrank(prem, funding_pctile_window)`. Direct funding-rate feeds vary by exchange/plan; the premium is the funding driver and always derivable from `<ticker without .P>`. If Task 1 discovery finds a working `_FR`/funding ticker, prefer it and record which source `fp` uses in the CHANGELOG (provenance: source switch = note, not schema change).
2. **OI ticker = auto `<prefix>:<ticker>_OI` with an `input.symbol` override knob** (override is data-plumbing, EXCLUDED from settings_hash like the transport inputs — it selects a feed for the same semantic factor).
3. **`oi_d` semantics:** T1 = % change from the pullback's start (new UDT field `oi0`, snapshotted when `th`/`tl` seeds) to the event bar; 2A/2B = the sweep bar's own % change (`oi_chg`). `oi_t` (trigger-bar OI direction up/dn/na) is T1-only — for 2A/2B the trigger bar IS the setup bar, `oi_d` already covers it.
4. **`gvb` = |close − lvl| / ATR(14)** at ENT/SKP, all three trades — uniform definition; captures "how far from the level did the fill land."
5. **Tail extensions (append-only):** T1 → `…|rt1=|oi_d=|oi_t=|q=|fp=|gvb=`; T2 → `…|rt1=|oi_d=|q=|fp=|gvb=`. SYS events unchanged.

---

### Task 1: OI/funding source discovery (TV-side, no code)
- [ ] Use `symbol_search` for "BTCUSDT.P OI", "BTCUSDT open interest", "BTCUSDT funding" — record the actual BINANCE OI ticker format (candidates: `BINANCE:BTCUSDT.P_OI`, `BINANCE:BTCUSDTPERP_OI`) and whether any funding-rate ticker exists. Verify the OI candidate renders by temporarily charting it (or rely on Task 3's harvest: `oi_d=na` everywhere = wrong ticker).
- [ ] Record findings in the CHANGELOG entry draft; pick the auto-ticker rule accordingly.

### Task 2: Pine v0.4.0 — factor plumbing
**Files:** Modify `jamal-fable.pine` (version 0.4.0, "JFbl0.4.0").

- [ ] **Step 1: Insert after the `reg_1d` block** (data layer; all `na`-guarded):

```pine
// ════════════════ Derivatives + price-context factors (spec §8; all logged, none gate) ════════════════
// Data-plumbing input — EXCLUDED from settings_hash (selects a feed, not semantics).
oi_symbol_in = input.symbol("", "OI symbol override (blank = auto <ticker>_OI)")
string oi_tkr = oi_symbol_in != "" ? oi_symbol_in : syminfo.prefix + ":" + syminfo.ticker + "_OI"
float oi = request.security(oi_tkr, timeframe.period, close, ignore_invalid_symbol = true)

// Funding proxy: perp premium vs spot (decision #1).
string spot_tkr = syminfo.prefix + ":" + str.replace(syminfo.ticker, ".P", "")
float spot_px = request.security(spot_tkr, timeframe.period, close, ignore_invalid_symbol = true)
float prem = na(spot_px) or spot_px == 0 ? na : 100.0 * (close - spot_px) / spot_px
float fp = na(prem) ? na : ta.percentrank(prem, funding_pctile_window)

// Quadrant: sign(dPrice) x sign(dOI) over quadrant_window (crude by design).
float q_dpx = close - close[quadrant_window]
float q_doi = na(oi) or na(oi[quadrant_window]) ? na : oi - oi[quadrant_window]
string quad = na(q_doi) ? "na" : (q_dpx >= 0 ? "PU" : "PD") + "." + (q_doi >= 0 ? "OU" : "OD")

// Per-bar OI change (%): the sweep-bar delta for 2A/2B and the trigger direction for T1.
float oi_chg = na(oi) or na(oi[1]) or oi[1] == 0 ? na : 100.0 * (oi - oi[1]) / oi[1]
string oi_t_dir = na(oi_chg) ? "na" : oi_chg >= 0 ? "up" : "dn"

f_oi_d_from(float oi0) => na(oi) or na(oi0) or oi0 == 0 ? na : 100.0 * (oi - oi0) / oi0
f_gvb(float lvl) => na(lvl) or na(atr) or atr == 0 ? na : math.abs(close - lvl) / atr
```

- [ ] **Step 2: UDT snapshots.** Add field `float oi0 = na` to BOTH `T1S` and `T1SS`; set `s.oi0 := oi` wherever `s.th`/`s.tl` is seeded (the `na(t1l.th) ? …` lines and the full resets clear it via `f_t1_reset`/`f_t1s_reset` — add `s.oi0 := na` to the `full` branch of both reset functions).
- [ ] **Step 3: Tail extensions (append-only, per decision #5).** `f_t1_tail`/`f_t1s_tail` gain a trailing
  `+ "|oi_d=" + (na(od)?"na":str.tostring(od,"#.##")) + "|oi_t=" + oi_t_dir + "|q=" + quad + "|fp=" + (na(fp)?"na":str.tostring(fp,"#.#")) + "|gvb=" + (na(g)?"na":str.tostring(g,"#.##"))`
  with `od = f_oi_d_from(s.oi0)` and `g = f_gvb(lvl)` computed inside the tail builders. `f_t2_tail` gains the same minus `oi_t`, with `od = oi_chg`.
- [ ] **Step 4:** Compile via MCP; verify version cell v0.4.0; commit + push.

### Task 3: Verify factors on chart + null-safety
- [ ] Harvest probe on BTCUSDT.P 4H: T1/2A/2B events show `oi_d`/`q`/`fp`/`gvb` with sane magnitudes (OI deltas single-digit %; `fp` 0–100; `gvb` matching the v0.3 graded values ~0.0–1.1). If `oi_d=na` everywhere → Task 1's ticker is wrong; fix and re-verify.
- [ ] Null-safety: probe one symbol WITHOUT an OI feed (or set the override to a garbage symbol temporarily) → events still emit, derivatives keys read `na`, nothing else changes. Restore.
- [ ] Commit + push raw probe + parsed events (s0.4.0 files).

### Task 4: External OI cross-check (sanity, not parity)
- [ ] `ccxt binanceusdm fetchOpenInterestHistory(symbol, '4h', limit≈50)` → compare 3 bars' OI % deltas vs Pine's `oi_d`/`oi_chg` values from the harvest. Expect approximate agreement (feeds sample OI differently) — record the comparison in the CHANGELOG; investigate only if signs disagree systematically. (This is a sanity check; OI never gates, so feed noise is tolerable and *measured*.)
- [ ] Commit the check script as `harness/evaluator/oi_crosscheck.py` + results.

### Task 5: Spec amendment + CHANGELOG + USER CHECKPOINT
- [ ] Spec §8: add `gvb` row ("giveback from level in ATRs at fill — the measurable eye-test from v0.3; logged, never gates") and a note on `fp`'s premium-proxy source + `oi_d` per-trade semantics (decision #3). Spec §12: note the OI-override input as hash-excluded plumbing.
- [ ] CHANGELOG v0.4.0 entry: discovery results, factor samples, null-safety proof, cross-check table.
- [ ] **USER CHECKPOINT (blocking):** factor values eyeballed sane on 2–3 symbols. **This checkpoint gates the backfill-campaign plan** (4-symbol basket, evaluator episode simulation with exit codes + counterfactuals, factor-conditioned report — the §10 rules already written in harness/README.md).
```
