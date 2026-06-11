# Jamal Fable v0.6.0 — Unified Structural Targets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every trade targets the nearest overhead structure (midpoint / opposing kill line / trend extreme / prev D-W extremes / weekly VWAP / opposite FVG) with the gate at ≥1.0R and `tgt_src` logged; OS sweeps prev-day/week levels only; OS loses the thesis exit; stretch becomes pure instrumentation with a once-per-episode `SYS|STR` marker.

**Architecture:** Entry CONDITIONS are untouched for all four trades — only target geometry, the gate level, and OS's level set change. The candidate-bar set (ENT∪SKP-rr per trade/dir) is therefore the v0.5→v0.6 diff invariant. New Pine machinery: weekly VWAP accumulator, unfilled-FVG arrays, a nearest-target selector, the STR episode latch. Evaluator: OS thesis-exit off, gate v3, tgt_src tables, rr-pseudo artifact fix, per-symbol lq percentile. New cfg → full deep re-harvest (Jan 1→today, ≤6-week chunks ALWAYS) → campaign 3.

**Spec authority:** spec §14 "v0.6 DESIGN" block (rulings ①–⑥).

**Conventions:** version bump on chart + CHANGELOG + commit/push main every task; TV loop = clipboard paste → smart compile → remove/re-add study.

---

### Task 1: Pine v0.6.0

**Files:** Modify `jamal-fable.pine`

- [ ] **Step 1: Version + knobs + hash.** Header → `"Jamal Fable v0.6.0"` / `"JFbl0.6.0"`; `SCRIPT_V = "0.6.0"`. Change `rr_min` DEFAULT to 1.0 (knob already hashed). After `use_1d_gate` add:

```pine
os_use_piv      = input.bool(false, "OS: sweep last-N pivots (campaign-2: 23%/-0.07R)")
os_use_roll     = input.bool(false, "OS: sweep rolling extreme (campaign-2: 22%/-0.10R)")
str_episode_atr = input.float(2.5, "Stretch episode threshold (ATR)", step = 0.1)
str_reset_atr   = input.float(1.0, "Stretch episode reset (ATR)",     step = 0.1)
```

Hash block additions (after the `use_1d_gate` mix):

```pine
    h := f_mix(h, os_use_piv ? 1 : 0)
    h := f_mix(h, os_use_roll ? 1 : 0)
    h := f_mix(h, math.round(str_episode_atr * 1000))
    h := f_mix(h, math.round(str_reset_atr * 1000))
```

- [ ] **Step 2: Weekly VWAP (global scope, after the covariates block).** Confirmed-bar accumulation (no realtime repaint; backfill is all-confirmed):

```pine
// ════════════════ v0.6 weekly VWAP (target candidate; confirmed bars only) ════════════════
var float wv_pv = 0.0
var float wv_v  = 0.0
if barstate.isconfirmed
    if ta.change(time("W")) != 0
        wv_pv := 0.0
        wv_v  := 0.0
    wv_pv += hlc3 * volume
    wv_v  += volume
float wvwap = wv_v == 0 ? na : wv_pv / wv_v
```

(NOTE: `ta.change(time("W"))` must be called unconditionally if the compiler warns — extract `float wk_chg = ta.change(time("W"))` above the `if`.)

- [ ] **Step 3: Unfilled-FVG tracking (global scope, after Step 2).** Bearish FVG (overhead, long-target): bar[2].low > bar[0].high → zone (bottom = high, top = low[2]). Bullish mirror below. Near-edge targets; removed when fully traded through; capped at 20 per side:

```pine
// ════════════════ v0.6 opposite-FVG target candidates (near edge; v1 rules: no age limit) ════════════════
var array<float> fvg_bear_bot = array.new<float>()   // overhead zones: bottom edges (long targets)
var array<float> fvg_bear_top = array.new<float>()
var array<float> fvg_bull_top = array.new<float>()   // underfoot zones: top edges (short targets)
var array<float> fvg_bull_bot = array.new<float>()
if barstate.isconfirmed
    if low[2] > high                                  // new bearish FVG
        array.push(fvg_bear_bot, high)
        array.push(fvg_bear_top, low[2])
        if array.size(fvg_bear_bot) > 20
            array.shift(fvg_bear_bot)
            array.shift(fvg_bear_top)
    if high[2] < low                                  // new bullish FVG
        array.push(fvg_bull_top, low)
        array.push(fvg_bull_bot, high[2])
        if array.size(fvg_bull_top) > 20
            array.shift(fvg_bull_top)
            array.shift(fvg_bull_bot)
    // retire fully-filled zones (price traded through the FAR edge)
    if array.size(fvg_bear_top) > 0
        for i = array.size(fvg_bear_top) - 1 to 0
            if high >= array.get(fvg_bear_top, i)
                array.remove(fvg_bear_top, i)
                array.remove(fvg_bear_bot, i)
    if array.size(fvg_bull_bot) > 0
        for i = array.size(fvg_bull_bot) - 1 to 0
            if low <= array.get(fvg_bull_bot, i)
                array.remove(fvg_bull_bot, i)
                array.remove(fvg_bull_top, i)
```

- [ ] **Step 4: Nearest-target selector (after Step 3; uses regime/levels → must sit after the engine instance — it does).** Returns price + source tag; candidates strictly on the profit side of the entry close:

```pine
// ════════════════ v0.6 unified structural targets (spec §14 ②): nearest overhead/underfoot ════════════════
f_nearest_target(bool is_long) =>
    float best = na
    string src = "na"
    f_cand(float px2, string tag, float b, string s) =>
        bool better = not na(px2) and (is_long ? px2 > close : px2 < close)
             and (na(b) or (is_long ? px2 < b : px2 > b))
        [better ? px2 : b, better ? tag : s]
    if regime == 0 and not na(range_hi) and not na(range_lo)
        [b1, s1] = f_cand((range_hi + range_lo) / 2.0, "mid", best, src)
        best := b1
        src := s1
    if regime == 1
        [b2, s2] = f_cand(trend_high, "tex", best, src)
        best := b2
        src := s2
        [b3, s3] = f_cand(hl_ref, "kil", best, src)     // shorts in UP aim down at the kill line
        best := b3
        src := s3
    if regime == -1
        [b4, s4] = f_cand(trend_low, "tex", best, src)
        best := b4
        src := s4
        [b5, s5] = f_cand(lh_ref, "kil", best, src)     // longs in DOWN aim up at the kill line
        best := b5
        src := s5
    [b6, s6] = f_cand(pdh, "pdh", best, src)
    best := b6
    src := s6
    [b7, s7] = f_cand(pdl, "pdl", best, src)
    best := b7
    src := s7
    [b8, s8] = f_cand(pwh, "pwh", best, src)
    best := b8
    src := s8
    [b9, s9] = f_cand(pwl, "pwl", best, src)
    best := b9
    src := s9
    [b10, s10] = f_cand(wvwap, "wvw", best, src)
    best := b10
    src := s10
    if is_long and array.size(fvg_bear_bot) > 0
        for i = 0 to array.size(fvg_bear_bot) - 1
            [bf, sf] = f_cand(array.get(fvg_bear_bot, i), "fvg", best, src)
            best := bf
            src := sf
    if not is_long and array.size(fvg_bull_top) > 0
        for i = 0 to array.size(fvg_bull_top) - 1
            [bf2, sf2] = f_cand(array.get(fvg_bull_top, i), "fvg", best, src)
            best := bf2
            src := sf2
    [best, src]
```

(If nested function defs are rejected, inline `f_cand` as repeated if-blocks — the compiler decides; same logic.)

- [ ] **Step 5: Wire targets into ALL four trades.** Each detector replaces its old `t1` with the selector result computed AT THE SIGNAL BAR, and every tail gains `|tgt_src=<src>` appended after the existing trade-specific keys (before `f_cov_tail()`):
  - **T1 long trigger block:** `[t1n, tsrc] = f_nearest_target(true)`; `rt1 = close > stp and not na(t1n) ? (t1n - close) / (close - stp) : na`; pass `t1n` (not `s.th`) as the tail's `t1`; emit `tgt_src=`. The DISSOLVE logic still keys off `s.th` (trend-high anchoring is unchanged — only the target price changes). Mirror short.
  - **2A long/short, 2B long/short:** same replacement (2B's `mid` will usually be its own nearest target — when something nearer exists, nearest wins).
  - **OS long/short:** target = selector result; the linreg anchor disappears from `t1` but `os/osp` remain in the cov tail.
  - All `f_*_tail` functions gain a `string tsrc` param emitting `+ "|tgt_src=" + tsrc` as the last trade-specific key.

- [ ] **Step 6: OS level-set toggles.** Wrap the pivot-scan block in `if os_use_piv` and the roll-scan blocks in `if os_use_roll` (both sides). Daily/weekly scans unchanged.

- [ ] **Step 7: Stretch-episode marker (after the OS emission blocks):**

```pine
// ════════════════ v0.6 stretch-episode marker (SYS|STR; one per episode, hysteresis) ════════════════
var bool str_live = false
if barstate.isconfirmed and not na(os_raw)
    if not str_live and math.abs(os_raw) >= str_episode_atr
        str_live := true
        f_emit("SYS", "STR", os_raw > 0 ? "U" : "D", math.round(time / 1000), close,
             "os=" + str.tostring(os_raw, "#.##") + "|osp=" + (na(os_rank) ? "na" : str.tostring(os_rank, "#.#"))
             + "|reg=" + f_reg_str(regime) + "|reg1d=" + f_reg_str(reg_1d)
             + "|er=" + (na(er) ? "na" : str.tostring(er, "#.##"))
             + "|vz=" + (na(vz) ? "na" : str.tostring(vz, "#.##")))
    else if str_live and math.abs(os_raw) < str_reset_atr
        str_live := false
```

- [ ] **Step 8: DW additions for verification:** `plot(wvwap, "DW weekly VWAP", display = display.data_window)` and `plot(array.size(fvg_bear_bot) > 0 ? array.get(fvg_bear_bot, array.size(fvg_bear_bot) - 1) : na, "DW newest bear-FVG bottom", display = display.data_window)`.

- [ ] **Step 9: Compile** (clipboard → smart compile; expect iterations on the tuple-returning nested function — fall back to inline if-blocks per Step 4 note). **Step 10: Live verify** — remove/re-add; record NEW cfg from the version cell; hover chips: `tgt_src` present; DW wvwap sane vs chart VWAP study. **Step 11: CHANGELOG + commit + push.**

---

### Task 2: Hand-traces (chart quiz)

- [ ] From the fresh chart, trace to the tick from ccxt bars (script `handtrace_v06.py`, pattern of `handtrace_v05.py`): (a) one entry whose `tgt_src=pdh/pdl` — recompute prior-day extreme from D-bars; (b) one `tgt_src=mid` — recompute walls/midpoint via the pivot engine; (c) one `tgt_src=kil` counter-trend entry; (d) one `tgt_src=fvg` — recompute the FVG zone from raw bars and verify near-edge + not-yet-filled; (e) one `tgt_src=wvw` — verify against the DW value (volume column needed; if the bars CSV lacks volume, verify on-chart via Data Window instead and say so); (f) one dust-target SKP (nearest structure < 1R → rsn=rr); (g) one STR episode — verify the latch fired once and only re-armed after |os| < 1.0.
- [ ] STOP on any mismatch. Commit evidence.

---

### Task 3: Evaluator (TDD)

**Files:** Modify `episodes.py`, `report.py`, `sanity_gate.py`; Test `harness/tests/test_v06_eval.py`

- [ ] **Step 1: Failing tests:** (a) `walk_episode` on a `trade="OS"` event ignores closes through `lvl` (no thesis_exit; runs to stop/target) while `trade="2A"` still thesis-exits; (b) `EVENT_GLOB` contains `s0.6.0`; (c) rr-pseudo bucketing helper excludes `rt1=na` events; (d) per-symbol `lq_pct` rank: two symbols with different lq scales rank independently.
- [ ] **Step 2: `episodes.py`:** in `walk_episode`, compute `apply_thesis = ev["trade"] != "OS"` and guard the `thesis_dead` branch with it (spec §14 ④ — campaign-2: −4.78R net on OS).
- [ ] **Step 3: `report.py`:** glob → `*_s0.6.0_*.jsonl`; synthesize `lq_pct` at load (percentrank of `lq_tot` WITHIN symbol); the lq-within-swd nested table switches to `lq_pct` with a 50 split; rr-pseudo table filters `fnum(rt1) is not None`; new `### by tgt_src` cat table (all episodes + OS-only); STR events excluded from episode walking (SYS already is); PREREG adds: "targets are nearest-structure as of v0.6 — rt1 distributions are NOT comparable to campaigns 1–2" and "tgt_src hit-rates condition the target doctrine, not the entries".
- [ ] **Step 4: `sanity_gate.py` → gate v3:** filename `s0.6.0_c<new cfg>`; acceptance per audited bar = episode grades (t1_hit OR thesis_exit+recovered) OR skip_overlap OR **the bar exists as `SKP rsn=rr` under the new geometry** (nearest-target rt1 < 1.0 is a legitimate re-gate, not a missing event). A bar absent in ALL three forms = FAIL.
- [ ] **Step 5:** full suite green; commit + push.

---

### Task 4: Deep re-harvest + invariant diff + census

- [ ] Bars refresh (4 symbols, `--since 2025-12-25 --until <tomorrow>`).
- [ ] Harvest 4 symbols × 4 chunks (Jan1–Feb15, Feb15–Apr1, Apr1–May15, May15–tomorrow) via `indicator_set_inputs` on the emit-window inputs (RECOUNT input indices — 4 new knobs shifted them again; verify by setting a window and checking the label range before trusting). Parse-merge + align per symbol; any chunk reporting exactly 500 labels → split it.
- [ ] **Invariant diff** (`compare_s050_s060.py`): per symbol vs s0.5.0 — (i) SYS PIV/PING identical (engine untouched); (ii) the candidate-bar set {(ts,trade,dir) : event ∈ ENT∪SKP-rr} for 2A/2B must be IDENTICAL, and for OS must equal the s0.5.0 pdl/pdh/pwl/pwh-subset (piv/roll toggled off); T1 candidate set identical; (iii) ENT↔SKP designation flips and all t1/rt1/tgt_src values are EXPECTED diffs (the release is target-geometry-only); (iv) STR is new — count only. Any (i)/(ii) violation = STOP.
- [ ] Census: ENT counts per trade (expect OS sharply down from 414), `tgt_src` distribution, STR episode count per symbol, dust-target SKP count. Commit.

---

### Task 5: Campaign 3 + close-out

- [ ] Sanity gate v3 → PASS required.
- [ ] `report.py --out harness/reports/campaign_2026-06_s060.md` — verify tgt_src tables, lq_pct table, rr-pseudo without the na artifact, OS rows without thesis_exit.
- [ ] Read it: headline vs campaign 2 (the question: did nearest-structure targets + 1.0R gate turn the breakeven book positive?); tgt_src hit-rates; STR join left for offline analysis.
- [ ] CHANGELOG + memory update + commit + push.
- [ ] **USER CHECKPOINT (blocking):** chips count change, campaign-3 headline, tgt_src verdicts, 1D ruling-watch update, whether any selector now clears §8's promotion bar.

---

## Self-review notes
- Spec §14 ①–⑥ all mapped: ① Task 1 Step 6 · ② Steps 4–5 + Task 3 tgt_src tables · ③ Step 1 (rr_min default) · ④ Task 3 Step 2 · ⑤ Step 7 · ⑥ Task 3 Step 3. Entry-conditions-unchanged invariant enforced by Task 4's diff.
- Known risks: Pine tuple-returning nested helper may need inlining (declared fallback); FVG v1 rules are deliberately minimal (near edge, full-fill retirement, cap 20, no age limit) — judged by tgt_src=fvg hit-rates, not pre-tuned; weekly VWAP needs volume — hand-trace fallback to Data Window if bars CSV lacks it.
- Comparability: rt1 distributions reset at v0.6 (different geometry) — pre-registered in the report.
