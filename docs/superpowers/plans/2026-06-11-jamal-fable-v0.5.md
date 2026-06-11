# Jamal Fable v0.5.0 — Generalized Sweep Engine (OS) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One new trade code `OS` — sweep-and-reclaim of a generalized level set (last-N pivots, prior day/week extremes, rolling k-bar extreme with a stretch gate) in ALL regimes — plus the 1D gate demoted to a tracked knob (default OFF, user ruling) and thesis-exit counterfactual accounting v2.

**Architecture:** T1/2A/2B emissions stay structurally identical (2A=kill, 2B=wall — history continuity); the only behavior change to them is the 1D gate knob default. OS is stateless one-bar like 2A: one event per bar per direction at the DEEPEST swept level (`n_lvls` counts the stack), entry=close, stop=wick±0.5·ATR, target=entry-snapshotted linreg anchor, rr_min 1.5 applies, `lvl_src`/`align`/`oco` logged. Evaluator: new cfg + `s0.5.0` glob (no pooling), OS factor tables, standing "would-have-been-blocked by the old 1D gate" cohort table, thesis-exit net-R-saved table.

**Tech Stack:** Pine v6 (existing imports suffice), TradingView MCP loop, Python harness.

**Spec authority:** spec §14 v0.5 paragraph incl. the 2026-06-11 checkpoint rulings (commit de8818e).

**Pre-registered (carry into the report):** `rt1`≈`os` for OS roll-class by construction; OS-in-'A' alignment is the Phase-1-killed bare fade ONLY if the reclaim trigger is ignored — judge W/A/N separately; deeper sweeps mechanically liquidate more (lq within swd).

---

### Task 1: Pine v0.5.0 — OS detector + 1D gate knob

**Files:**
- Modify: `jamal-fable.pine`

- [ ] **Step 1: Version + knobs + hash**

Header → `"Jamal Fable v0.5.0"` / `"JFbl0.5.0"`; `SCRIPT_V = "0.5.0"`. After `vz_window` add:

```pine
piv_n       = input.int(5,    "OS: last-N pivots per side",        minval = 1)
roll_k      = input.int(20,   "OS: rolling extreme window",        minval = 5)
os_m        = input.int(5,    "OS: stretch lookback (bars)",       minval = 1)
os_gate_atr = input.float(1.5, "OS: roll-class stretch gate (ATR)", step = 0.1)
use_1d_gate = input.bool(false, "Use 1D regime gate (campaign-era behavior)")
```

Extend the hash block (after the `vz_window` mix):

```pine
    h := f_mix(h, piv_n)
    h := f_mix(h, roll_k)
    h := f_mix(h, os_m)
    h := f_mix(h, math.round(os_gate_atr * 1000))
    h := f_mix(h, use_1d_gate ? 1 : 0)
```

Record the new cfg from the version cell at Step 8.

- [ ] **Step 2: Level machinery (global scope, after the covariates block)**

```pine
// ════════════════ v0.5 OS level set (spec §14) ════════════════
var array<float> piv_lows  = array.new<float>()
var array<float> piv_highs = array.new<float>()
if pl_new
    array.push(piv_lows, pl_val)
    if array.size(piv_lows) > piv_n
        array.shift(piv_lows)
if ph_new
    array.push(piv_highs, ph_val)
    if array.size(piv_highs) > piv_n
        array.shift(piv_highs)
// Prior day/week extremes: [1] + lookahead_on = last CLOSED candle (zero lag, non-repainting)
float pdl = request.security(syminfo.tickerid, "D", low[1],  lookahead = barmerge.lookahead_on)
float pdh = request.security(syminfo.tickerid, "D", high[1], lookahead = barmerge.lookahead_on)
float pwl = request.security(syminfo.tickerid, "W", low[1],  lookahead = barmerge.lookahead_on)
float pwh = request.security(syminfo.tickerid, "W", high[1], lookahead = barmerge.lookahead_on)
float roll_lo = ta.lowest(low, roll_k)[1]      // as of PRIOR bar — excludes current
float roll_hi = ta.highest(high, roll_k)[1]
float os_min_m = ta.lowest(os_raw, os_m)        // stretch extreme within last m bars
float os_max_m = ta.highest(os_raw, os_m)
int age_roll_lo = ta.barssince(roll_lo != roll_lo[1])
int age_roll_hi = ta.barssince(roll_hi != roll_hi[1])
int age_pdl = ta.barssince(pdl != pdl[1])
int age_pdh = ta.barssince(pdh != pdh[1])
```

- [ ] **Step 3: OS scan — deepest-level dedup (global scope, AFTER the Trade #2 shared block so `swp_l`/`swp_s` exist)**

```pine
// ════════════════ Trade OS: generalized sweep-reclaim scan (spec §14 v0.5) ════════════════
// One event per bar per direction at the DEEPEST swept-and-reclaimed level.
// Sweep grammar: low < lvl and close > lvl (strict reclaim; level as of prior bar).
// Roll class additionally requires the stretch gate (event-volume control, NOT a tuned edge).
float os_l_lvl = na
string os_l_src = "na"
int os_l_n = 0
float os_s_lvl = na
string os_s_src = "na"
int os_s_n = 0
if barstate.isconfirmed
    if array.size(piv_lows) > 0
        for i = 0 to array.size(piv_lows) - 1
            float lv = array.get(piv_lows, i)
            if low < lv and close > lv
                os_l_n += 1
                if na(os_l_lvl) or lv < os_l_lvl
                    os_l_lvl := lv
                    os_l_src := "piv"
    if not na(pdl) and low < pdl and close > pdl
        os_l_n += 1
        if na(os_l_lvl) or pdl < os_l_lvl
            os_l_lvl := pdl
            os_l_src := "pdl"
    if not na(pwl) and low < pwl and close > pwl
        os_l_n += 1
        if na(os_l_lvl) or pwl < os_l_lvl
            os_l_lvl := pwl
            os_l_src := "pwl"
    if not na(roll_lo) and low < roll_lo and close > roll_lo and not na(os_min_m) and os_min_m <= -os_gate_atr
        os_l_n += 1
        if na(os_l_lvl) or roll_lo < os_l_lvl
            os_l_lvl := roll_lo
            os_l_src := "roll"
    if array.size(piv_highs) > 0
        for i = 0 to array.size(piv_highs) - 1
            float lv = array.get(piv_highs, i)
            if high > lv and close < lv
                os_s_n += 1
                if na(os_s_lvl) or lv > os_s_lvl
                    os_s_lvl := lv
                    os_s_src := "piv"
    if not na(pdh) and high > pdh and close < pdh
        os_s_n += 1
        if na(os_s_lvl) or pdh > os_s_lvl
            os_s_lvl := pdh
            os_s_src := "pdh"
    if not na(pwh) and high > pwh and close < pwh
        os_s_n += 1
        if na(os_s_lvl) or pwh > os_s_lvl
            os_s_lvl := pwh
            os_s_src := "pwh"
    if not na(roll_hi) and high > roll_hi and close < roll_hi and not na(os_max_m) and os_max_m >= os_gate_atr
        os_s_n += 1
        if na(os_s_lvl) or roll_hi > os_s_lvl
            os_s_lvl := roll_hi
            os_s_src := "roll"
```

- [ ] **Step 4: OS tail builder + alignment chip (after `f_t2_tail`)**

```pine
// fixed tail key order: lvl|stop|t1|rsn|lvl_src|n_lvls|align|oco|reg|reg1d|age|swd|age_t|rt1|<cov>
f_os_tail(float lvl, float stp, float t1px, string rsn, string src, int nlv, string align, bool oco, float swd, int aget, float rt1) =>
    "lvl=" + f_fstr(lvl) + "|stop=" + f_fstr(stp) + "|t1=" + f_fstr(t1px) + "|rsn=" + rsn
     + "|lvl_src=" + src + "|n_lvls=" + str.tostring(nlv) + "|align=" + align
     + "|oco=" + (oco ? "1" : "0")
     + "|reg=" + f_reg_str(regime) + "|reg1d=" + f_reg_str(reg_1d)
     + "|age=" + str.tostring(regime_age)
     + "|swd=" + (na(swd) ? "na" : str.tostring(swd, "#.##"))
     + "|age_t=" + (na(aget) ? "na" : str.tostring(aget))
     + "|rt1=" + (na(rt1) ? "na" : str.tostring(rt1, "#.##"))
     + "|" + f_cov_tail()

// OS chips: color by ALIGNMENT (green=with-regime, red=against, gray=chop) — spec §14
f_mark_os(string dir, float px, string tail, string align) =>
    if in_window and barstate.isconfirmed
        color bg = align == "W" ? color.new(color.lime, 0) : align == "A" ? color.new(color.red, 0) : color.new(color.gray, 0)
        string card = "OS " + (dir == "L" ? "LONG @ " : "SHORT @ ") + str.tostring(px, "#.########")
             + "\n" + str.replace_all(tail, "|", "\n")
        if dir == "L"
            label.new(bar_index, low, "OS", style = label.style_label_up, color = bg,
                 textcolor = align == "N" ? color.white : color.black, size = size.small, tooltip = card)
        else
            label.new(bar_index, high, "OS", style = label.style_label_down, color = bg,
                 textcolor = align == "N" ? color.white : color.black, size = size.small, tooltip = card)
```

- [ ] **Step 5: OS emission (after the 2B block, so 2A/2B own their bars first)**

```pine
// ════════════════ Trade OS emission (spec §14 v0.5) ════════════════
// Same-bar coincidence with the kill-line sweep: emit BOTH, cross-flag oco=1 (dedup offline).
// 1D opposition = logged SKP only when use_1d_gate (default off — 2026-06-11 ruling, reg1d always stamped).
if not na(os_l_lvl)
    string al = regime == 1 ? "W" : regime == -1 ? "A" : "N"
    int aget = os_l_src == "roll" ? age_roll_lo : os_l_src == "pdl" ? age_pdl : na
    float stp = low - stop_buffer_atr * atr
    float t1px = lr_anchor                       // entry-snapshotted fair-value anchor (§14 doctrine exception)
    float swd = (os_l_lvl - low) / atr
    float rt1 = close > stp and not na(t1px) and t1px > close ? (t1px - close) / (close - stp) : na
    if use_1d_gate and reg_1d == -1
        f_emit("OS", "SKP", "L", math.round(time / 1000), close,
             f_os_tail(os_l_lvl, stp, t1px, "1d", os_l_src, os_l_n, al, swp_l, swd, aget, rt1))
    else if na(rt1) or rt1 < rr_min
        f_emit("OS", "SKP", "L", math.round(time / 1000), close,
             f_os_tail(os_l_lvl, stp, t1px, "rr", os_l_src, os_l_n, al, swp_l, swd, aget, rt1))
    else
        string os_ent = f_os_tail(os_l_lvl, stp, t1px, "na", os_l_src, os_l_n, al, swp_l, swd, aget, rt1)
        f_emit("OS", "ENT", "L", math.round(time / 1000), close, os_ent)
        f_mark_os("L", close, os_ent, al)
if not na(os_s_lvl)
    string al = regime == -1 ? "W" : regime == 1 ? "A" : "N"
    int aget = os_s_src == "roll" ? age_roll_hi : os_s_src == "pdh" ? age_pdh : na
    float stp = high + stop_buffer_atr * atr
    float t1px = lr_anchor
    float swd = (high - os_s_lvl) / atr
    float rt1 = stp > close and not na(t1px) and t1px < close ? (close - t1px) / (stp - close) : na
    if use_1d_gate and reg_1d == 1
        f_emit("OS", "SKP", "S", math.round(time / 1000), close,
             f_os_tail(os_s_lvl, stp, t1px, "1d", os_s_src, os_s_n, al, swp_s, swd, aget, rt1))
    else if na(rt1) or rt1 < rr_min
        f_emit("OS", "SKP", "S", math.round(time / 1000), close,
             f_os_tail(os_s_lvl, stp, t1px, "rr", os_s_src, os_s_n, al, swp_s, swd, aget, rt1))
    else
        string os_ent_s = f_os_tail(os_s_lvl, stp, t1px, "na", os_s_src, os_s_n, al, swp_s, swd, aget, rt1)
        f_emit("OS", "ENT", "S", math.round(time / 1000), close, os_ent_s)
        f_mark_os("S", close, os_ent_s, al)
```

- [ ] **Step 6: 1D gate → knob on T1/2A/2B**

Six edits, mechanical:
- 2A long: `if reg_1d == -1` → `if use_1d_gate and reg_1d == -1`
- 2A short: `if reg_1d == 1` → `if use_1d_gate and reg_1d == 1`
- 2B long / 2B short: same two substitutions.
- T1 long arming: `if reg_1d != -1` → `if not use_1d_gate or reg_1d != -1`
- T1 short arming: `if reg_1d != 1` → `if not use_1d_gate or reg_1d != 1`

The `blk`/`ARM rsn=1d` branches become unreachable with the knob off — leave them in place (they reactivate with the knob; zero cost).

- [ ] **Step 7: Compile** — clipboard paste → `pine_smart_compile`. Expect clean. Watch for: loop-in-global warnings (fine), `array<float>` syntax, security-call budget (now 8 security-class calls — well under 40).

- [ ] **Step 8: Live verify** — remove + re-add study on BTC 4H. Verify: version cell `v0.5.0` + NEW cfg (record it — needed by Task 3/4); OS chips visible (green/red/gray); hover one OS chip — `lvl_src`/`n_lvls`/`align`/`oco` present; existing T1/2A/2B chips unchanged on their historical bars.

- [ ] **Step 9: CHANGELOG + commit + push** (entry: OS detector, taxonomy, 1D knob default-off ruling, new cfg).

---

### Task 2: Hand-traces (chart quiz — the v0.2/v0.3 discipline)

- [ ] **Step 1:** Pick from the live chart: (a) one OS ENT with `lvl_src=piv`, (b) one with `lvl_src=roll` (verify the stretch gate: `os` within last `os_m` bars ≤ −1.5 for a long), (c) one bar where `n_lvls ≥ 2` (verify the EMITTED level is the deepest of the stack), (d) one `oco=1` bar (2A and OS both emitted, same bar).
- [ ] **Step 2:** For each: hand-compute entry/stop/t1/rt1 from the bar's OHLC + ATR + linreg anchor read off the Data Window — must match the tail to the tick (same tolerance as v0.3: exact at display precision).
- [ ] **Step 3:** Screenshot the verified bars; note results in CHANGELOG; commit.

STOP if any trace disagrees — that's a detector bug, not noise.

---

### Task 3: Evaluator — thesis-exit v2, 1D cohort, OS tables (TDD)

**Files:**
- Modify: `harness/evaluator/episodes.py`, `harness/evaluator/report.py`, `harness/evaluator/sanity_gate.py`
- Test: `harness/tests/test_v05_eval.py`

- [ ] **Step 1: Failing tests**

```python
"""v0.5 evaluator: thesis-exit R-delta, 1D-cohort split, OS glob."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.episodes import walk_episode
from evaluator.report import EVENT_GLOB, oneD_blocked


def _ent(lvl, stop, t1, ts=1000):
    return {"symbol": "X", "trade": "2A", "event": "ENT", "dir": "L", "bar_ts": ts,
            "px": 100.0, "factors": {"lvl": str(lvl), "stop": str(stop), "t1": str(t1),
                                     "rt1": "2.0", "reg1d": "D"}}


def test_thesis_exit_carries_rule_delta_r():
    # entry 100, stop 95, t1 110; bar2 closes below lvl 98 (thesis exit at 97),
    # then price recovers to t1 -> cf=recovered, cf_r=+2.0
    bars = [(1000, 100, 101, 99, 100), (2000, 99, 99.5, 96.5, 97),
            (3000, 97, 111, 96.9, 110)]
    ep = walk_episode(_ent(98, 95, 110), bars)
    assert ep["exit_code"] == "thesis_exit" and ep["counterfactual"] == "recovered"
    assert ep["cf_r"] == 2.0
    assert abs(ep["rule_delta_r"] - (ep["r"] - 2.0)) < 1e-9


def test_oneD_blocked_cohort_rule():
    assert oneD_blocked({"dir": "L", "factors": {"reg1d": "D"}})
    assert not oneD_blocked({"dir": "L", "factors": {"reg1d": "U"}})
    assert oneD_blocked({"dir": "S", "factors": {"reg1d": "U"}})


def test_event_glob_is_s050():
    assert "s0.5.0" in EVENT_GLOB
```

- [ ] **Step 2:** Run `py -m pytest harness/tests/test_v05_eval.py -v` — expect ImportError/AssertionError failures.

- [ ] **Step 3: `episodes.py`** — in the thesis-exit branch of `walk_episode` (where `counterfactual` is set), add:

```python
        ep["cf_r"] = rt1_val if ep["counterfactual"] == "recovered" else (-1.0 if ep["counterfactual"] == "stopped" else None)
        ep["rule_delta_r"] = (ep["r"] - ep["cf_r"]) if (ep.get("r") is not None and ep["cf_r"] is not None) else None
```

where `rt1_val = float(ev["factors"]["rt1"])` (already parsed for `r` on t1_hit — reuse the same variable; read the function first and match its local names). Non-thesis episodes get `cf_r = rule_delta_r = None` (set defaults at episode init).

- [ ] **Step 4: `report.py`** —
(a) `EVENT_GLOB = "*_s0.5.0_*.jsonl"`.
(b) Cohort rule + standing table:

```python
def oneD_blocked(e):
    """Would the campaign-era 1D gate have blocked this? (dir vs 1D regime opposition)"""
    r1d = (e.get("factors") or {}).get("reg1d")
    return (e["dir"] == "L" and r1d == "D") or (e["dir"] == "S" and r1d == "U")
```

In `render_report`, after the headline:

```python
    L.append("\n## Standing ruling-watch: 1D gate OFF (2026-06-11 user ruling, against n=9 evidence)\n")
    blocked = [e for e in eps_all if oneD_blocked(e)]
    passed = [e for e in eps_all if not oneD_blocked(e)]
    rows = []
    for lab, grp in (("would-have-been-BLOCKED", blocked), ("would-have-passed", passed)):
        s = stats_row(grp)
        rows.append([lab, s["n"], s["closed"], fmt(s["win%"], 0), fmt(s["avg_r"]), fmt(s["med_mfe"])])
    L.append(table(["cohort", "n", "closed", "win%", "avg R", "med MFE"], rows))
    L.append("\n_If the blocked cohort bleeds as n grows, flip `use_1d_gate` back on._\n")
```

(c) Thesis-exit v2 table (replaces the bare counterfactual count table):

```python
    L.append("\n### (c) thesis-exit v2 — net R saved by the third exit (per trade type)\n")
    tx = [e for e in eps_all if e["exit_code"] == "thesis_exit"]
    rows = []
    for tr, grp in sorted(group_by(tx, lambda e: e["trade"]).items()):
        deltas = [e["rule_delta_r"] for e in grp if e.get("rule_delta_r") is not None]
        rec = sum(1 for e in grp if e["counterfactual"] == "recovered")
        stp = sum(1 for e in grp if e["counterfactual"] == "stopped")
        rows.append([tr, len(grp), rec, stp, fmt(sum(deltas)) if deltas else "—"])
    rows.append(["ALL", len(tx), sum(1 for e in tx if e["counterfactual"] == "recovered"),
                 sum(1 for e in tx if e["counterfactual"] == "stopped"),
                 fmt(sum(e["rule_delta_r"] for e in tx if e.get("rule_delta_r") is not None))])
    L.append(table(["trade", "n", "recovered (exit cost us)", "stopped (exit saved us)", "NET R saved by rule"], rows))
```

(d) OS sections (after the per-trade rt1 block):

```python
    os_eps = [e for e in eps_all if e["trade"] == "OS"]
    if os_eps:
        L.append("\n## OS — generalized sweeps (NEW population, judge separately)\n")
        for key in ("lvl_src", "align"):
            L.append(f"\n### OS by `{key}`\n")
            L.append(table(FACTOR_HEADER, cat_rows(os_eps, key)))
        L.append("\n### OS by `osp` (rt1~os is MECHANICAL for roll class — pre-registered)\n")
        L.append(table(FACTOR_HEADER, bucket_rows(os_eps, "osp", [(None, 50), (50, 85), (85, None)], ["<50", "50-85", ">85"])))
        L.append("\n### OS by `vz` (the v0.4.6 quiet-bar lead, tested out-of-population)\n")
        L.append(table(FACTOR_HEADER, bucket_rows(os_eps, "vz", [(None, 0), (0, 1.5), (1.5, None)], ["<0", "0-1.5", ">1.5"])))
```

(e) PREREG: add `- OS roll-class rt1 correlates with os by construction (target = stretch anchor).` and `- The 1D gate is OFF by user ruling (2026-06-11) — the blocked-cohort table is the ruling's scoreboard.`

- [ ] **Step 4b: Direction-oriented conditioning (s046 external review — the direction-blind bucketing flaw).** Add to `report.py`:

```python
def oriented(e, key):
    """Signed covariate oriented to trade direction: positive = supportive of the trade.
    os: stretched-down supports a long -> orient = -os for L, +os for S.
    fr/fp: crowded-long (positive funding / high pctile) supports a SHORT fade -> +for S, -for L
           (fp is centered at 50 before orienting).
    """
    v = fnum(e["factors"], key)
    if v is None:
        return None
    if key == "fp":
        v = v - 50.0
    return -v if e["dir"] == "L" else v


def oriented_q(e):
    """Quadrant with the price leg made trade-relative: PW=price moved WITH trade dir pre-entry."""
    q = e["factors"].get("q", "na")
    if q == "na" or "." not in q:
        return "na"
    px, oi = q.split(".")
    with_trade = (px == "PU") == (e["dir"] == "L")
    return ("PW" if with_trade else "PA") + "." + oi
```

And render (after the existing factor tables):

```python
    L.append("\n## Direction-ORIENTED conditioning (supportive = positive; fixes the pooled-signed-factor wash-out)\n")
    for key in ("os", "fr", "fp"):
        L.append(f"\n### by oriented `{key}`\n")
        rows = []
        for lab, lo, hi in (("against (<0)", None, 0.0), ("supportive (>=0)", 0.0, None)):
            sub = [e for e in eps_all if (w := oriented(e, key)) is not None
                   and (lo is None or w >= lo) and (hi is None or w < hi)]
            s = stats_row(sub)
            rows.append([lab, s["n"], fmt(s["win%"], 0), fmt(s["avg_r"]), fmt(s["med_mfe"])])
        L.append(table(FACTOR_HEADER, rows))
    L.append("\n### by oriented `q` (PW=price moved with trade pre-entry, PA=against)\n")
    groups = defaultdict(list)
    for e in eps_all:
        groups[oriented_q(e)].append(e)
    rows = [[k, stats_row(g)["n"], fmt(stats_row(g)["win%"], 0), fmt(stats_row(g)["avg_r"]), fmt(stats_row(g)["med_mfe"])] for k, g in sorted(groups.items())]
    L.append(table(FACTOR_HEADER, rows))
```

Test (add to `test_v05_eval.py`):

```python
def test_oriented_flips_sign_for_longs():
    from evaluator.report import oriented
    e = {"dir": "L", "factors": {"os": "-2.0"}}
    assert oriented(e, "os") == 2.0           # stretched-down long = supportive
    e2 = {"dir": "S", "factors": {"os": "-2.0"}}
    assert oriented(e2, "os") == -2.0
```

- [ ] **Step 4c: Two sensitivity appendices.** (a) rr_min=2.0 counterfactual: render the headline `stats_row` twice — all episodes vs episodes with `fnum(factors, "rt1") >= 2.0` — labeled "book as-is (rr 1.5)" / "book if rr_min were 2.0 (offline counterfactual, no knob change)". (b) skip_overlap sensitivity: walk EVERY ENT independently (`walk_episode` directly, no sequential rule), render the same stats line labeled "all entries walked independently (sequential rule OFF)" with the episode count — shows whether dropping 13/43 candidates shapes the story. (c) PREREG additions: the campaign-2 hypothesis line ("quiet, shallow sweeps revert, violent ones don't — conditional on chop; pre-registered 2026-06-11 BEFORE s0.5.0 data"), the multiple-comparisons line ("~15 tables at n≈30 guarantee chance splits; vz≈p0.1 unadjusted"), and the er-window line ("er>0.45 had zero events in campaign 1 — the violence prior is untested in trends").

- [ ] **Step 5:** `sanity_gate.py`: filename → `s0.5.0_c<new cfg>`; expectations unchanged (the 11 audited entries predate any 1D-gate effect — they were taken entries).

- [ ] **Step 6:** Full suite: `py -m pytest harness/tests/ -v` → all pass. Commit + push.

---

### Task 4: Re-harvest (DEEP window: Jan 1 → today) + diff + volume management

The window extends to 2026-01-01 (s046 review action: the er>0.45 bucket had ZERO events — trending months must enter the sample). Deep history harvests under the v0.5 cfg in one pass — never harvested twice across cfgs.

- [ ] **Step 1:** Refresh bars per symbol with `--since 2025-12-25 --until <tomorrow>` (since ≥ pivot_right bars before the window start), same `--out` filenames.
- [ ] **Step 2:** Per symbol, harvest in EMIT-WINDOW CHUNKS (the deep window certainly exceeds 500 labels): set `emit_from`/`emit_to` via the indicator settings dialog (input indices shifted — do NOT trust old `in_N` positions) to successive chunks, e.g. Jan 1–Feb 15, Feb 15–Apr 1, Apr 1–May 15, May 15–tomorrow. For each chunk: `data_get_pine_labels study_filter="Jamal Fable" max_labels=500 verbose=true` (forces disk-save) → copy to `harness/events/raw/<SYM>_s050_<chunk>.json` → parse (merge is idempotent by dedup key) → if any chunk reports exactly 500 labels, split that chunk and re-pull. Then `align_check` on the merged file. Census check: confirm the `er` distribution now has events at er>0.45 (the point of the depth); if Jan–Mar was also chop, note it — the hypothesis stays untested, not failed.
- [ ] **Step 3:** Emission-diff vs s0.4.6 — extend `compare_emissions.py` with a `--baseline s0.4.6 --target s0.5.0` mode and v0.5 tolerances: (a) `trade=OS` keys are all-new — ignore; (b) an old `SKP` with `rsn=1d` may become `ENT` same bar/trade/dir — count as EXPECTED SWAP, list them; (c) T1 streams may diverge after a previously-blocked ARM (gate-off arms earlier — state evolution legitimately differs) — report T1 deltas as expected-class, but `SYS` and 2B and non-swap 2A must be IDENTICAL. Any 2A/2B/SYS surprise = STOP.
- [ ] **Step 4:** `coverage_check.py` on s0.5.0 + a quick OS census: events by `lvl_src` × ENT/SKP per symbol (sanity: roll-class volume reasonable, stretch gate doing its scope job; if OS events alone exceed ~150/symbol, note for the os_gate_atr discussion — do NOT retune mid-harvest).
- [ ] **Step 5:** Commit + push (events, raw, scripts).

---

### Task 5: Sanity gate + report + close-out

- [ ] **Step 1:** `py harness/evaluator/sanity_gate.py` → PASS required (the 11 entries grade identically).
- [ ] **Step 2:** `py harness/evaluator/report.py --out harness/reports/campaign_2026-06_s050.md` — verify: OS sections render; 1D ruling-watch table renders; thesis-exit v2 table renders with net-R numbers; headline for T1/2A/2B within expectations (new 1D-unblocked entries shift it — that's the ruling's visible cost/benefit, not a bug).
- [ ] **Step 3:** Read the report; sanity-scan OS population (n, win%, by lvl_src/align).
- [ ] **Step 4:** CHANGELOG close-out + memory update (`jamal-fable` state: v0.5 shipped, new cfg, OS census, ruling-watch numbers, thesis-exit net-R) + commit + push.
- [ ] **Step 5: USER CHECKPOINT (blocking)** — present: how many new diamonds/arrows and where, OS first-read by level class and alignment, what the 1D ruling cost/earned this window, thesis-exit net-R verdict so far, and the v0.6 question (which OS selectors the evidence backs).

---

## Self-review notes

- **Spec coverage:** OS single trade code + lvl_src classes (T1 §14) ✓; deepest-level dedup + n_lvls ✓; stretch gate roll-only, loose, hashed ✓; align W/A/N logged + chip colors ✓; oco cross-flag ✓; target = entry-snapshotted linreg anchor ✓ (snapshot is implicit: the tail stores the numeric `t1`); 1D knob default-off + ruling-watch table ✓; thesis-exit v2 per user request ✓; new cfg/no-pool ✓; HL_ref untouched ✓.
- **Type consistency:** `f_os_tail` signature matches both call sites; `oneD_blocked` used by test + report; `cf_r`/`rule_delta_r` set in episodes, consumed in report. ✓
- **Known risks:** `request.security` "W" weekly call adds history-depth dependence (weekly closed candle exists — fine); linreg anchor as `t1` can sit below entry for longs (logged as SKP rsn=rr with rt1=na — correct, the reversion already happened); OS event volume unknown — chunked-harvest path is the relief valve, census in Task 4 Step 4.
