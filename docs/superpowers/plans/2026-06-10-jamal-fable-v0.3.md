# Jamal Fable v0.3 (Trade #2 — Flush-and-Reclaim, 2A + 2B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Project override:** NO worktrees/branches — all work inline on `main`, commit + push per task. TV via MCP loop; one `var` per line; remove+re-add only if the on-chart study fails to refresh on save (v0.2 observed in-place save refreshing correctly — verify via version cell).

**Goal:** Trade #2 detectors — 2A (flush-and-reclaim at the trend kill line) and 2B (chop-boundary sweep, fade to midpoint) — emitting ENT/SKP with §7 snapshot levels, completing the spec's two-trade taxonomy and filling the snipe slot T1's handoff CXLs reserve.

**Architecture:** Both variants are **stateless one-bar detectors** (spec §6: the sweep bar simultaneously sets up and triggers — entry = that bar's close; no pending state, no ARM/CXL). They read the same `f_engine()` outputs T1 uses. The §4 coincidence flag is captured BEFORE T1's block consumes its state.

**Tech Stack:** Pine v6 (script v0.3.0), existing harness (no new Python; handtrace gets two new episodes).

**Spec:** §6 (both variants + the only doctrine: no entry without the reclaim close), §4 (sweep definition + coincidence), §7 (snapshots: 2A shares T1's thesis line; 2B's = swept boundary as at entry), §13. State: TV script id `USER;77b6506a17b545908a3966ad81a3e7c8`, cfg 509208, entity on chart as "Jamal Fable v0.2.0".

---

## Decisions locked here (surface at the v0.3 checkpoint)
1. **1D gate on a one-bar setup = SKP `rsn=1d`**, not silence. T1 gates *arming*; 2A/2B have no arm phase, and a silent gate would erase the §8 counterfactual population. Opposing-1D sweeps are logged skips, first-class.
2. **`wick_pctile` (`wkp`) factor definition:** percentile rank (`ta.percentrank`, window = `wick_pctile_window`) of the sweep bar's *relevant* wick size in ATRs — lower wick `(min(open,close)−low)/atr` for longs, upper for shorts. Crude by design; logged, never gates.
3. **2B requires BOTH walls defined** (midpoint needs both; §3 seeding leaves the broken side undefined after a trend death). One-sided chop = no 2B on either side — the absent setups are structural, not skips.
4. **Event schema:** trade codes `2A`/`2B`; tail key order `lvl|stop|t1|rsn|reg|reg1d|age|wkp|t1co|rt1` (t1co = §4 coincidence factor, `1` when the sweep bar also satisfied T1's trigger; `0` otherwise; only meaningful for 2A).
5. **Marks:** diamonds (lime below bar = long ENT, red above bar = short ENT) — distinct from T1's triangles.

---

### Task 1: Persist the T1 backlog (carry-over from v0.2 coverage note)

- [ ] **Step 1:** Full harvest (`data_get_pine_labels`, `max_labels=500`) on BTCUSDT.P 4H → save raw to `harness/events/raw/BTCUSDT.P_240_<date>_full.json` → `parse_labels.py --symbol BTCUSDT.P`. Expected: the April–May long-side T1 events merge as new; everything else dedups.
- [ ] **Step 2:** `align_check.py` on the merged JSONL vs a fresh `fetch_bars.py` pull (`--since 2026-01-25 --until <tomorrow>`). Expected: all aligned, exit 0.
- [ ] **Step 3:** Commit: `git add harness; git commit -m "feat(fable): persist full T1 backlog (v0.2 coverage note closed)"; git push origin main`

### Task 2: 2A detector (both sides) + coincidence wiring

**Files:** Modify `jamal-fable.pine` — version → `0.3.0` (title "Jamal Fable v0.3.0", shorttitle "JFbl0.3.0", SCRIPT_V "0.3.0").

- [ ] **Step 1: Reorganize declarations, then insert the shared block.** The coincidence captures reference BOTH `t1l` and `t1s`, so first hoist ALL T1 declarations (`T1S`, `t1l`, `f_t1_reset`, `f_fstr`, `f_t1_tail`, `T1SS`, `t1s`, `f_t1s_reset`, `f_t1s_tail`) into one block ABOVE the two T1 detector if-blocks (currently `T1SS` etc. sit between them). Then insert the following BETWEEN the declarations and the T1 long if-block (it must read T1 state before T1's handoff branch resets it):

```pine
// ════════════════ Trade #2 shared (spec §6) ════════════════
// Sweep conditions (§4, one-bar definition) — evaluated once per bar.
bool swp_l = barstate.isconfirmed and regime == 1 and not na(hl_ref) and low < hl_ref and close >= hl_ref
bool swp_s = barstate.isconfirmed and regime == -1 and not na(lh_ref) and high > lh_ref and close <= lh_ref
// §4 coincidence: the sweep bar ALSO satisfied T1's trigger (captured pre-reset).
bool t2a_l_coin = swp_l and t1l.armed and not na(t1l.mlh) and close > t1l.mlh
bool t2a_s_coin = swp_s and t1s.armed and not na(t1s.mhl) and close < t1s.mhl

// Wick-size percentiles (decision #2): relevant wick in ATRs, ranked vs own history.
float wick_lo_atr = (math.min(open, close) - low) / atr
float wick_hi_atr = (high - math.max(open, close)) / atr
float wkp_lo = ta.percentrank(wick_lo_atr, wick_pctile_window)
float wkp_hi = ta.percentrank(wick_hi_atr, wick_pctile_window)

// fixed tail key order: lvl|stop|t1|rsn|reg|reg1d|age|wkp|t1co|rt1
f_t2_tail(float lvl, float stp, float t1px, string rsn, float wkp, bool t1co, float rt1) =>
    "lvl=" + f_fstr(lvl) + "|stop=" + f_fstr(stp) + "|t1=" + f_fstr(t1px) + "|rsn=" + rsn
     + "|reg=" + f_reg_str(regime) + "|reg1d=" + f_reg_str(reg_1d)
     + "|age=" + str.tostring(regime_age)
     + "|wkp=" + (na(wkp) ? "na" : str.tostring(wkp, "#.#"))
     + "|t1co=" + (t1co ? "1" : "0")
     + "|rt1=" + (na(rt1) ? "na" : str.tostring(rt1, "#.##"))
```

- [ ] **Step 2: Insert the 2A blocks AFTER the T1 short block, before Rendering:**

```pine
// ════════════════ Trade #2A: flush-and-reclaim at the kill line (spec §6A) ════════════════
// Stateless one-bar setup: the sweep bar IS the entry bar (entry = its close).
// The only doctrine: no entry without the reclaim close — swp_* encodes it.
bool t2a_ent_long = false
bool t2a_ent_short = false
if swp_l and not na(trend_high)
    if reg_1d == -1
        f_emit("2A", "SKP", "L", math.round(time / 1000), close,
             f_t2_tail(hl_ref, na, trend_high, "1d", wkp_lo, t2a_l_coin, na))
    else
        float stp = low - stop_buffer_atr * atr
        float rt1 = close > stp ? (trend_high - close) / (close - stp) : na
        if na(rt1) or rt1 < rr_min
            f_emit("2A", "SKP", "L", math.round(time / 1000), close,
                 f_t2_tail(hl_ref, stp, trend_high, "rr", wkp_lo, t2a_l_coin, rt1))
        else
            f_emit("2A", "ENT", "L", math.round(time / 1000), close,
                 f_t2_tail(hl_ref, stp, trend_high, "na", wkp_lo, t2a_l_coin, rt1))
            t2a_ent_long := true
if swp_s and not na(trend_low)
    if reg_1d == 1
        f_emit("2A", "SKP", "S", math.round(time / 1000), close,
             f_t2_tail(lh_ref, na, trend_low, "1d", wkp_hi, t2a_s_coin, na))
    else
        float stp = high + stop_buffer_atr * atr
        float rt1 = stp > close ? (close - trend_low) / (stp - close) : na
        if na(rt1) or rt1 < rr_min
            f_emit("2A", "SKP", "S", math.round(time / 1000), close,
                 f_t2_tail(lh_ref, stp, trend_low, "rr", wkp_hi, t2a_s_coin, rt1))
        else
            f_emit("2A", "ENT", "S", math.round(time / 1000), close,
                 f_t2_tail(lh_ref, stp, trend_low, "na", wkp_hi, t2a_s_coin, rt1))
            t2a_ent_short := true
```

- [ ] **Step 3:** Rendering adds: `plotshape(t2a_ent_long, "2A long", shape.diamond, location.belowbar, color.new(color.lime, 0), size = size.small)` and the red `abovebar` mirror for `t2a_ent_short`.
- [ ] **Step 4:** Compile via MCP; verify version cell reads v0.3.0 (else remove+re-add). Smoke: harvest probe shows `2A|ENT/SKP` strings; the May 27 handoff bar (1779796800) must now show **both** the T1 `CXL rsn=handoff` AND a 2A event with `t1co=1` (the §4 contract end-to-end).
- [ ] **Step 5:** Commit + push: `feat(fable): v0.3.0 Trade 2A flush-and-reclaim (both sides) + coincidence factor`.

### Task 3: 2B detector (chop boundaries, both directions)

- [ ] **Step 1: Insert after the 2A block:**

```pine
// ════════════════ Trade #2B: chop-boundary sweep → fade to midpoint (spec §6B) ════════════════
// Requires BOTH walls (midpoint undefined otherwise — §3 seeding leaves the
// broken side na after a trend death; absent setups there are structural).
bool t2b_ent_long = false
bool t2b_ent_short = false
if barstate.isconfirmed and regime == 0 and not na(range_hi) and not na(range_lo)
    float mid = (range_hi + range_lo) / 2.0
    if low < range_lo and close >= range_lo         // §4 SWEEP of the low wall
        if reg_1d == -1
            f_emit("2B", "SKP", "L", math.round(time / 1000), close,
                 f_t2_tail(range_lo, na, mid, "1d", wkp_lo, false, na))
        else
            float stp = low - stop_buffer_atr * atr
            float rt1 = close > stp ? (mid - close) / (close - stp) : na
            if na(rt1) or rt1 < rr_min               // the R gate IS the width gate (§3/§6B)
                f_emit("2B", "SKP", "L", math.round(time / 1000), close,
                     f_t2_tail(range_lo, stp, mid, "rr", wkp_lo, false, rt1))
            else
                f_emit("2B", "ENT", "L", math.round(time / 1000), close,
                     f_t2_tail(range_lo, stp, mid, "na", wkp_lo, false, rt1))
                t2b_ent_long := true
    if high > range_hi and close <= range_hi        // §4 SWEEP of the high wall
        if reg_1d == 1
            f_emit("2B", "SKP", "S", math.round(time / 1000), close,
                 f_t2_tail(range_hi, na, mid, "1d", wkp_hi, false, na))
        else
            float stp = high + stop_buffer_atr * atr
            float rt1 = stp > close ? (close - mid) / (stp - close) : na
            if na(rt1) or rt1 < rr_min
                f_emit("2B", "SKP", "S", math.round(time / 1000), close,
                     f_t2_tail(range_hi, stp, mid, "rr", wkp_hi, false, rt1))
            else
                f_emit("2B", "ENT", "S", math.round(time / 1000), close,
                     f_t2_tail(range_hi, stp, mid, "na", wkp_hi, false, rt1))
                t2b_ent_short := true
```

- [ ] **Step 2:** Rendering: 2B reuses the diamond marks via `or` (`plotshape(t2a_ent_long or t2b_ent_long, …)`) — trade identity lives in the event log; the chart only needs "an entry happened here."
- [ ] **Step 3:** Compile; smoke on a chop-heavy window (early-May BTC, or NEAR 4H). **Stale-wall watch-item review (spec follow-up):** screenshot a long chop and judge whether monotone walls leave 2B sweeping absurdly distant boundaries — record verdict in CHANGELOG.
- [ ] **Step 4:** Commit + push: `feat(fable): v0.3.0 Trade 2B chop-boundary fade (both directions)`.

### Task 4: Harvest + hand-trace 2 episodes

- [ ] **Step 1:** Full harvest → parse → align (all classes; 2A/2B px = close).
- [ ] **Step 2:** Extend `handtrace_v02.py` (new file `handtrace_v03.py`): verify one 2A episode and one 2B episode to the tick — px==bar close; stop reconciles with the sweep bar's wick extreme ± 0.5·ATR(14); rt1 recomputes; lvl equals the engine line (2A: hl_ref/lh_ref; 2B: the wall); 2B's t1 equals the wall midpoint. If a class produced no event on BTC, switch symbol (NEAR 4H is chop-rich) — chunk windows as needed.
- [ ] **Step 3:** Run; commit raw + script + results.

### Task 5: CHANGELOG + BLOCKING user checkpoint

- [ ] **Step 1:** CHANGELOG v0.3.0 entry: decisions #1–5, coincidence end-to-end evidence, hand-trace table, stale-wall verdict, event counts by class.
- [ ] **Step 2:** Commit + push.
- [ ] **Step 3:** **USER CHECKPOINT (blocking):** diamonds on chart across BTC + NEAR (+1 more perp) — does 2A snipe where Jamal would snipe, and does 2B fade boundaries he'd fade? **Do not start the v0.4 (derivatives factors) plan until approved.**

---

## Roadmap after this plan
- **v0.4:** derivatives factors (`oi_delta_setup`, `oi_trigger_dir`, `quadrant`, `funding_pctile`), null-safe, into every event tail.
- **Backfill campaign:** 4-symbol basket, evaluator episode simulation (outcomes/exit codes/counterfactuals — the §10 rules waiting in harness/README), factor-conditioned report. Only then: any talk of promoting factors or tuning `rr_min` (the 1.27–1.5 near-miss band is already logged for exactly that question).
- **Stage 2:** webhook listener (`src=L`) once the rule-set freezes.
```
