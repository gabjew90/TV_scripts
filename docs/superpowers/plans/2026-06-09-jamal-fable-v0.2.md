# Jamal Fable v0.2 (Trade #1 Detector + Pivot Parity) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Project override:** NO worktrees/branches — all work inline on `main`, commit + push to `origin main` at the end of every task. TV work via the MCP loop; remove+re-add the study after every compile; one `var` per line.

**Goal:** Trade #1 (pullback-continuation) detector emitting `ARM`/`ENT`/`SKP`/`CXL` events with §7 snapshot levels and the factor vector, plus the Python pivot-parity check that licenses the evaluator's pivot reimplementation.

**Architecture:** First refactor the v0.1.2 engine into a pure function `f_engine()` (var-local state, zero emission side-effects) so `request.security` can run it on 1D without phantom labels — gated by an event-core regression diff. Then parity, then the 1D filter, then the detector (long, then short mirror), then repo-side hand-trace validation.

**Tech Stack:** Pine v6, Python 3.10 (existing `harness/`), TradingView MCP.

**Spec:** `docs/superpowers/specs/2026-06-09-jamal-fable-design.md` — §5 (Trade #1 rules), §7 (snapshot semantics), §4 (coincidence rule), §9 (event schema), §10 (parity license). State as of v0.1.2: cfg `509208`, TV script id `USER;77b6506a17b545908a3966ad81a3e7c8`, entity re-added after each compile.

---

## File structure

```
jamal-fable.pine                       # Modify: engine→f_engine(), +reg_1d, +T1 detector, v0.2.0
harness/evaluator/pivots.py            # Create: pivot detection (TV ta.pivothigh/low semantics)
harness/evaluator/parity_check.py      # Create: SYS|PIV vs Python detector, bit-exact
harness/evaluator/diff_events.py       # Create: event-core diff (regression gate for the refactor)
harness/tests/test_pivots.py           # Create
CHANGELOG.md                           # Modify: v0.2.0 entry
```

**Implementation decisions locked here (surface at the v0.2 checkpoint):**
1. **1D gate blocks ARMING only** (S1 is a context-to-watch gate). If 1D flips mid-pullback, the ENT still fires; `reg1d` is in the vector so backfill can judge whether arming-time vs entry-time 1D matters. No double-gating.
2. **After a SKP, the chain resets but the pullback continues** — a deeper retrace can re-arm and re-trigger with better R. (`pb_low` survives; `micro_LH`/armed reset.)
3. **A new trend high while armed = setup dissolved** → `CXL` with `rsn=newhigh` (distinct from `choch` and `handoff`), full vector — these are the V-shape/no-trigger population the spec pre-registers.
4. **Event tail key order is fixed** (schema stability): `lvl|stop|t1|rsn|reg|reg1d|age|d_atr|d_pct|bz|mlh|rt1`. Keys with no value emit `na` — null in the vector, never omitted.

---

### Task 1: Engine → `f_engine()` refactor (pure function) + regression gate

**Files:** Modify `jamal-fable.pine` (engine section). Version → `0.2.0` ("Jamal Fable v0.2.0", shorttitle "JFbl0.2.0").

**Why:** `request.security` re-executes its expression's dependency graph in the 1D context. If the engine's code path contains `label.new`, behavior is undefined-to-hazardous (phantom/hidden labels). A pure function with **var-local state** gets an independent state copy per calling context — exactly what we need, with emission staying in the chart context.

- [ ] **Step 1: Replace the engine section** (everything from `// ════ Pivots ════` through the FSM block) with:

```pine
// ════════════════ Engine as a pure function (no emission side-effects) ════════════════
// var locals = one independent state copy PER CALLING CONTEXT (chart, 1D security).
// Returns everything the chart context needs to emit events + render.
f_engine() =>
    var int   regime     = 0      // 0=CHOP, 1=UP, -1=DOWN
    var int   regime_age = 0
    var float hl_ref     = na
    var float lh_ref     = na
    var float trend_high = na
    var float trend_low  = na
    var float range_hi   = na
    var float range_lo   = na
    var float bos_level  = na
    var float last_ph    = na
    var float last_pl    = na
    float ph = ta.pivothigh(high, pivot_left, pivot_right)
    float pl = ta.pivotlow(low,  pivot_left, pivot_right)
    bool ph_new = not na(ph) and barstate.isconfirmed
    bool pl_new = not na(pl) and barstate.isconfirmed
    // Pivot bookkeeping BEFORE FSM (engine detail #6); confirmed-gated (detail #7)
    if ph_new
        last_ph := ph
        if regime == 1
            trend_high := ph
        else if regime == -1
            lh_ref := ph
        else
            range_hi := na(range_hi) ? ph : math.max(range_hi, ph)
    if pl_new
        last_pl := pl
        if regime == -1
            trend_low := pl
        else if regime == 1
            hl_ref := pl
        else
            range_lo := na(range_lo) ? pl : math.min(range_lo, pl)
    int prev_regime = regime
    if barstate.isconfirmed
        if regime == 0
            if not na(range_hi) and close > range_hi
                regime     := 1
                bos_level  := range_hi
                hl_ref     := last_pl
                trend_high := range_hi
            else if not na(range_lo) and close < range_lo
                regime    := -1
                bos_level := range_lo
                lh_ref    := last_ph
                trend_low := range_lo
        else if regime == 1
            if not na(hl_ref) and close < hl_ref
                regime   := 0
                range_hi := trend_high
                range_lo := na
            else if not na(trend_high) and close > trend_high
                bos_level := trend_high
        else
            if not na(lh_ref) and close > lh_ref
                regime   := 0
                range_lo := trend_low
                range_hi := na
            else if not na(trend_low) and close < trend_low
                bos_level := trend_low
        if regime != prev_regime
            regime_age := 0
        else
            regime_age += 1
    bool reg_changed = barstate.isconfirmed and regime != prev_regime
    [regime, regime_age, hl_ref, lh_ref, trend_high, trend_low, range_hi, range_lo, bos_level, ph_new, ph, pl_new, pl, reg_changed]

// Chart-context engine instance + emission (unchanged event strings)
[regime, regime_age, hl_ref, lh_ref, trend_high, trend_low, range_hi, range_lo, bos_level, ph_new, ph_val, pl_new, pl_val, reg_changed] = f_engine()

if ph_new
    f_emit("SYS", "PIV", "N", math.round(time[pivot_right] / 1000), ph_val, "typ=H")
if pl_new
    f_emit("SYS", "PIV", "N", math.round(time[pivot_right] / 1000), pl_val, "typ=L")
if reg_changed
    f_emit("SYS", "PING", "N", math.round(time / 1000), close,
         "reg=" + f_reg_str(regime) + "|age=0")
```

(Keep `f_emit`/`f_reg_str` above this block; delete the old global engine vars and FSM. Rendering/table sections consume the tuple names unchanged. SCRIPT_V := "0.2.0", title/shorttitle bumped.)

- [ ] **Step 2: Compile via MCP** (`pine_set_source` full file → `pine_smart_compile` → fix until clean; keep disk file identical).
- [ ] **Step 3: Remove + re-add the study**; screenshot: render identical to v0.1.2 (continuous lines, tint, version cell v0.2.0 cfg 509208).
- [ ] **Step 4: Regression gate — event cores must be IDENTICAL.** Write `harness/evaluator/diff_events.py`:

```python
"""Compare two event JSONL files ignoring provenance (script_v) - the
refactor regression gate: same bars in, same events out."""
import json
import sys


def core(path):
    out = set()
    for line in open(path):
        e = json.loads(line)
        out.add((e["bar_ts"], e["trade"], e["event"], e["dir"], e["px"],
                 tuple(sorted(e["factors"].items()))))
    return out


a, b = core(sys.argv[1]), core(sys.argv[2])
only_a, only_b = a - b, b - a
print(f"A: {len(a)} events, B: {len(b)} events, common: {len(a & b)}")
for x in sorted(only_a)[:10]:
    print("  only A:", x)
for x in sorted(only_b)[:10]:
    print("  only B:", x)
raise SystemExit(0 if not only_a and not only_b else 1)
```

Then: harvest BTC 4H (default Apr→now window) → save raw → `parse_labels.py --symbol BTCUSDT.P` (new file `..._s0.2.0_...jsonl`) → `py -3 harness/evaluator/diff_events.py harness/events/BTCUSDT.P_240_v1_s0.1_c509208_B.jsonl harness/events/BTCUSDT.P_240_v1_s0.2.0_c509208_B.jsonl`.
Expected: only-A/only-B differences are events newer than the v0.1 harvest (bars that closed since); zero differences in the overlapping window. If any overlapping-window diff appears, the refactor changed semantics — STOP and fix.
- [ ] **Step 5: Commit** `git add jamal-fable.pine harness; git commit -m "feat(fable): v0.2.0 engine-as-pure-function refactor, event-core regression identical"; git push origin main`

### Task 2: Python pivot detector + parity check (TDD)

**Files:** Create `harness/evaluator/pivots.py`, `harness/evaluator/parity_check.py`; Test `harness/tests/test_pivots.py`.

- [ ] **Step 1: Failing test** (`harness/tests/test_pivots.py`):

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.pivots import pivot_points


def test_simple_pivot_high_and_low():
    highs = [1, 2, 3, 9, 3, 2, 1, 2, 3]
    lows  = [1, 2, 3, 8, 3, 2, 0.5, 2, 3]
    ts    = list(range(100, 109))
    pivots = pivot_points(ts, highs, lows, left=3, right=3)
    assert (103, "H", 9) in pivots          # bar 3 high=9 > 3 left & 3 right
    assert (106, "L", 0.5) in pivots        # bar 6 low
    assert all(t in (103, 106) for t, _, _ in pivots)


def test_tie_does_not_make_pivot():
    highs = [1, 2, 9, 3, 9, 2, 1]           # equal high 2 bars apart
    lows  = [0, 0, 0, 0, 0, 0, 0]
    pivots = pivot_points(list(range(7)), highs, lows, left=2, right=2)
    assert (2, "H", 9) not in pivots        # right side contains an equal value
```

- [ ] **Step 2: Run** `py -3 -m pytest harness/tests/test_pivots.py -v` → FAIL (module missing).
- [ ] **Step 3: Implement** `harness/evaluator/pivots.py`:

```python
"""Pivot detection mirroring Pine ta.pivothigh/ta.pivotlow (L/R bars).

PARITY LICENSE (spec section 10): this module exists only because trail
simulation needs post-entry pivots. It must reproduce Pine's SYS|PIV events
bit-exact (parity_check.py); if TV's tie semantics differ from the initial
strict-inequality assumption, fix THIS module to match Pine, never vice versa.
Initial semantics: a pivot high at i requires high[i] strictly greater than
every high in [i-L, i) and (i, i+R]. Mirror for lows.
"""


def pivot_points(ts, highs, lows, left, right):
    out = []
    n = len(ts)
    for i in range(left, n - right):
        win_h = highs[i - left:i] + highs[i + 1:i + 1 + right]
        if all(highs[i] > h for h in win_h):
            out.append((ts[i], "H", highs[i]))
        win_l = lows[i - left:i] + lows[i + 1:i + 1 + right]
        if all(lows[i] < l for l in win_l):
            out.append((ts[i], "L", lows[i]))
    return out
```

- [ ] **Step 4: Run** → 2 passed.
- [ ] **Step 5: Implement** `harness/evaluator/parity_check.py`:

```python
"""Pivot-parity check (spec section 10) - gates v0.2 acceptance.

Compares Pine SYS|PIV events against the Python detector run on fetched bars,
over the events' own time range. Bit-exact required: same (ts, typ, price).
"""
import argparse
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.pivots import pivot_points


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events_jsonl")
    ap.add_argument("bars_csv")
    ap.add_argument("--left", type=int, default=3)
    ap.add_argument("--right", type=int, default=3)
    args = ap.parse_args()
    events = [json.loads(l) for l in Path(args.events_jsonl).read_text().splitlines() if l.strip()]
    piv_events = {(e["bar_ts"], e["factors"]["typ"], e["px"])
                  for e in events if e["event"] == "PIV"}
    if not piv_events:
        print("no PIV events in input")
        raise SystemExit(1)
    lo_ts = min(t for t, _, _ in piv_events)
    hi_ts = max(t for t, _, _ in piv_events)
    rows = list(csv.DictReader(Path(args.bars_csv).open()))
    ts = [int(r["ts_sec"]) for r in rows]
    highs = [float(r["high"]) for r in rows]
    lows = [float(r["low"]) for r in rows]
    py = {(t, k, p) for (t, k, p) in pivot_points(ts, highs, lows, args.left, args.right)
          if lo_ts <= t <= hi_ts}
    # Pine only emits PIV when the CONFIRMATION bar is inside the emit window;
    # pivots whose confirmation falls outside produce no event. So Python may
    # find a superset at the range edges - compare Pine⊆Python strictly, and
    # report Python-only pivots for manual edge classification.
    pine_only = piv_events - py
    py_only = py - piv_events
    print(f"pine: {len(piv_events)}  python: {len(py)}  matched: {len(piv_events & py)}")
    for x in sorted(pine_only)[:10]:
        print("  PINE-ONLY (parity FAILURE):", x)
    for x in sorted(py_only)[:10]:
        print("  python-only (edge? verify confirmation-bar window):", x)
    raise SystemExit(1 if pine_only else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run parity on real data:** `py -3 harness/evaluator/parity_check.py harness/events/BTCUSDT.P_240_v1_s0.2.0_c509208_B.jsonl harness/bars/binanceusdm_BTCUSDT_4h.csv`
Expected: `PINE-ONLY` empty (parity holds); `python-only` entries only at window edges (pivot confirmed outside emit window) — classify each by hand before accepting. If PINE-ONLY is non-empty → TV tie semantics differ → adjust `pivots.py` comparisons (`>` vs `>=` patterns) until bit-exact, document the discovered semantics in the module docstring.
- [ ] **Step 7: Commit** `git add harness; git commit -m "feat(fable): python pivot detector + parity check vs Pine SYS|PIV (bit-exact)"; git push origin main`

### Task 3: 1D regime filter (`reg_1d`)

**Files:** Modify `jamal-fable.pine`.

- [ ] **Step 1: Add after the chart-context engine call:**

```pine
// ════════════════ 1D regime filter (last CONFIRMED 1D bar; non-repainting) ════════════════
f_engine_reg() =>
    [r, _a, _hl, _lh, _th, _tl, _rh, _rl, _bl, _pn, _pv, _qn, _qv, _rc] = f_engine()
    r

int reg_1d = request.security(syminfo.tickerid, "D", f_engine_reg()[1],
     lookahead = barmerge.lookahead_on)
```

(`[1]` + `lookahead_on` = the classic non-repaint pattern: always the last *closed* D bar's regime. The security call gets its OWN `f_engine` state copy — chart events cannot change.)
- [ ] **Step 2: Surface it:** version cell text gains `· 1D ` + `f_reg_str(reg_1d)`; PING tail gains `|reg1d=` + `f_reg_str(reg_1d)`.
- [ ] **Step 3: Compile, remove+re-add, verify:** version cell shows a sane 1D state (cross-check by switching the chart to D and eyeballing the tint of the last closed bar); re-harvest a few PINGs and confirm `reg1d` parses.
- [ ] **Step 4: Commit** `git add jamal-fable.pine; git commit -m "feat(fable): non-repainting 1D regime filter via security on pure engine"; git push origin main`

### Task 4: Trade #1 LONG detector

**Files:** Modify `jamal-fable.pine` (new section between engine call and rendering).

- [ ] **Step 1: Add the detector** (long side; spec §5 — every rule cited inline):

**Pine constraint that shapes this code:** functions CANNOT reassign global `var`s — detector state lives in a UDT object (field mutation through a reference is allowed).

```pine
// ════════════════ Trade #1: pullback-continuation — LONG (spec §5) ════════════════
type T1S
    bool  armed = false
    float mlh   = na      // micro lower-high (chain tip; S3)
    int   mlhn  = 0       // chain length
    float pblow = na      // running pullback low (S2; survives SKP)
    float th    = na      // trend high this pullback keyed off (dissolve detector)

var T1S t1l = T1S.new()

f_t1_reset(T1S s, bool full) =>
    s.armed := false
    s.mlh   := na
    s.mlhn  := 0
    if full
        s.pblow := na
        s.th    := na

// fixed tail key order (schema stability): lvl|stop|t1|rsn|reg|reg1d|age|d_atr|d_pct|bz|mlh|rt1
f_t1_tail(T1S s, float lvl, float stp, float t1, string rsn, float rt1) =>
    float d_atr = na(s.pblow) or na(s.th) ? na : (s.th - s.pblow) / atr
    float d_pct = na(s.pblow) or na(s.th) or na(lvl) or s.th == lvl ? na :
         100.0 * (s.th - s.pblow) / (s.th - lvl)
    string bz = na(bos_level) or na(s.pblow) ? "na" : s.pblow <= bos_level ? "1" : "0"
    "lvl=" + str.tostring(lvl, "#.########") + "|stop=" + str.tostring(stp, "#.########")
     + "|t1=" + str.tostring(t1, "#.########") + "|rsn=" + rsn
     + "|reg=" + f_reg_str(regime) + "|reg1d=" + f_reg_str(reg_1d)
     + "|age=" + str.tostring(regime_age) + "|d_atr=" + str.tostring(d_atr, "#.##")
     + "|d_pct=" + str.tostring(d_pct, "#.#") + "|bz=" + bz
     + "|mlh=" + str.tostring(s.mlhn) + "|rt1=" + str.tostring(rt1, "#.##")

bool t1l_ent_mark = false
if barstate.isconfirmed and regime == 1 and not na(hl_ref) and not na(trend_high)
    // dissolve: a NEW trend high while armed = pullback over without trigger (decision #3)
    if not na(t1l.th) and trend_high > t1l.th
        if t1l.armed
            f_emit("T1", "CXL", "L", math.round(time / 1000), close,
                 f_t1_tail(t1l, hl_ref, na, t1l.th, "newhigh", na))
        f_t1_reset(t1l, true)
    t1l.th    := na(t1l.th) ? trend_high : t1l.th
    t1l.pblow := na(t1l.pblow) ? low : math.min(t1l.pblow, low)
    // chain growth (S3): a lower low vs prior bar makes prior bar's high the micro-LH
    if low < low[1]
        t1l.mlh  := high[1]
        t1l.mlhn += 1
        if not t1l.armed and reg_1d != -1          // S1: 1D gate blocks ARMING only (decision #1)
            t1l.armed := true
            f_emit("T1", "ARM", "L", math.round(time / 1000), close,
                 f_t1_tail(t1l, hl_ref, na, t1l.th, "na", na))
    if t1l.armed
        if close < hl_ref                           // S4 pre-entry thesis death
            f_emit("T1", "CXL", "L", math.round(time / 1000), close,
                 f_t1_tail(t1l, hl_ref, na, t1l.th, "choch", na))
            f_t1_reset(t1l, true)
        else if close > t1l.mlh                     // S3 trigger: body close above micro-LH
            if low < hl_ref and close >= hl_ref     // §4 coincidence: SWEEP bar → 2A owns
                f_emit("T1", "CXL", "L", math.round(time / 1000), close,
                     f_t1_tail(t1l, hl_ref, na, t1l.th, "handoff", na))
                f_t1_reset(t1l, false)
            else
                float stp = t1l.pblow - stop_buffer_atr * atr
                float rt1 = close > stp ? (t1l.th - close) / (close - stp) : na
                if na(rt1) or rt1 < rr_min          // S5 skip gate
                    f_emit("T1", "SKP", "L", math.round(time / 1000), close,
                         f_t1_tail(t1l, hl_ref, stp, t1l.th, "rr", rt1))
                else
                    f_emit("T1", "ENT", "L", math.round(time / 1000), close,
                         f_t1_tail(t1l, hl_ref, stp, t1l.th, "na", rt1))
                    t1l_ent_mark := true
                f_t1_reset(t1l, false)              // chain resets, pullback continues (decision #2)
if barstate.isconfirmed and regime != 1
    f_t1_reset(t1l, true)

plotshape(t1l_ent_mark, "T1 long entry", shape.triangleup, location.belowbar,
     color.new(color.lime, 0), size = size.small)
```

(Task 5's short mirror reuses `T1S`, `f_t1_reset`, and `f_t1_tail` — a second instance `var T1S t1s = T1S.new()`, with the tail's `d_atr/d_pct` computed from `s.pbhigh`-equivalents via the mirrored fields; if field semantics diverge, add a parallel `T1SS` type rather than overloading meanings.)

- [ ] **Step 2: Compile, remove+re-add, smoke-test on BTC 4H:** lime triangles only under green-tint regions, after visible pullbacks. `data_get_pine_labels` shows `T1|ARM/ENT/SKP/CXL` strings with the full tail.
- [ ] **Step 3: Commit** `git add jamal-fable.pine; git commit -m "feat(fable): Trade #1 long detector - ARM/ENT/SKP/CXL, snapshot levels, factor vector"; git push origin main`

### Task 5: Trade #1 SHORT mirror

- [ ] **Step 1: Add the mirrored block** — `t1s_*` vars; context `regime == -1`, refs `lh_ref`/`trend_low`; chain grows on `high > high[1]` with micro higher-low `low[1]`; trigger = `close < t1s_mhl`; thesis death = `close > lh_ref`; coincidence = `high > lh_ref and close <= lh_ref`; stop = `pb_high + stop_buffer_atr*atr`; `rt1 = (close - trend_low_snapshot) / (stp - close)`; dir `"S"`; ARM gate `reg_1d != 1`; red `shape.triangledown, location.abovebar`. Same tail builder mirrored (`d_atr/d_pct` from `pb_high` vs `t1s_tl`/`lh_ref`). Write it as the exact mirror of Task 4's block — every comparison flipped, every `hl_ref→lh_ref`, `trend_high→trend_low`, `low→high` swap.
- [ ] **Step 2: Compile, remove+re-add, smoke on the June BTC downtrend:** red triangles above bars in red-tint regions.
- [ ] **Step 3: Commit** `git add jamal-fable.pine; git commit -m "feat(fable): Trade #1 short mirror"; git push origin main`

### Task 6: Repo-side hand-trace validation + full harvest

- [ ] **Step 1: Harvest the full default window** (BTC 4H) → parse → `align_check` (must stay green including T1 events — they align vs `close`).
- [ ] **Step 2: Hand-trace three episodes from `harness/bars/binanceusdm_BTCUSDT_4h.csv`** (pick from what the chart shows): one `ENT`, one `SKP` (rr), one `CXL` (choch). For each: walk the bars by hand (pivot confirmations → regime → chain → trigger), write the expected event (ts, px, lvl/stop/t1, rt1) in a scratch table, then grep the events JSONL for the actual — **must match to the tick**. Any mismatch = detector bug; fix before proceeding (this is the Jamal-OB quiz loop, run against data instead of memory).
- [ ] **Step 3: Run parity again** (Task 2 command) — still bit-exact with the detector code present.
- [ ] **Step 4: Commit** raw + events: `git commit -m "feat(fable): v0.2 harvest + 3 hand-traced episodes verified to the tick"; git push origin main`

### Task 7: CHANGELOG + USER CHECKPOINT (blocking)

- [ ] **Step 1: CHANGELOG** v0.2.0 entry: refactor regression result, parity result (counts + any tie-semantics discovery), detector decisions #1–4, hand-trace table, screenshots refs.
- [ ] **Step 2: Commit + push.**
- [ ] **Step 3: USER CHECKPOINT (blocking):** triangles on chart across 2–3 symbols — do the entries land where Jamal would take the pullback? Surface decisions #1–4 explicitly. **Do not start v0.3 (Trade #2) until approved.**

---

## Roadmap after this plan
- **v0.3:** Trade #2 (2A flush at HL_ref + 2B chop boundary), coincidence end-to-end, stale-wall watch-item review.
- **v0.4:** derivatives factors (`oi_delta_setup`, `oi_trigger_dir`, `quadrant`, `funding_pctile`), null-safe.
- **Then:** first backfill campaign (4-symbol basket) + episode simulation/evaluator report.
```
