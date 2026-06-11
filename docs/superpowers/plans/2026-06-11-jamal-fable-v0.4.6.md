# Jamal Fable v0.4.6 — Covariate Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emission-only release: every trade tail gains the covariates `os/osp/er/vz/dlt/swd/age_t/fr/lqb/lqs`, derivative data migrates to the official `TradingView/Request` library, and the 4-symbol basket is re-harvested + the campaign report re-rendered with the new factor tables.

**Architecture:** Zero signal-logic changes — the same ENT/SKP/CXL/ARM events must fire on the same bars (verified mechanically by a s0.4.5-vs-s0.4.6 emission diff). New factors compute in global scope (request budget + percentrank consistency), append to tails in fixed key order, and flow through the existing generic parser untouched. Harness changes: version-glob bump, new factor tables, per-trade `rt1` conditioning, liquidations conditioned *within* sweep-depth bands (pre-registered mechanical correlation).

**Tech Stack:** Pine v6 (`import TradingView/Request/3`), TradingView MCP dev loop, Python harness (no new deps), ccxt cross-checks.

**Spec authority:** `docs/superpowers/specs/2026-06-09-jamal-fable-design.md` §8 "v0.4.6 covariate enrichment" + §8 mechanical-correlation additions.

**Conventions (every task):** on-chart version bump already covered by Task 1; CHANGELOG entry + `git add … ; git commit ; git push origin main` at every commit step. TV dev loop = clipboard paste (`Set-Clipboard` → click editor → Ctrl+A, Ctrl+V) → `pine_smart_compile` → **remove + re-add the study** (layout cache) → verify on chart.

---

### Task 1: Pine v0.4.6 — knobs, Request migration, covariates, tails, Data Window

**Files:**
- Modify: `jamal-fable.pine` (header, knobs, hash, factors block, tail builders, call sites, DW plots)

- [ ] **Step 1: Header + version bump**

Replace lines 1–7:

```pine
//@version=6
indicator("Jamal Fable v0.4.6", shorttitle = "JFbl0.4.6", overlay = true,
     max_labels_count = 500, max_lines_count = 500)
import TradingView/Request/3 as r

// ════════════════ Identity (spec §9 provenance) ════════════════
SCHEMA_V = "1"
SCRIPT_V = "0.4.6"
```

(If the compiler reports a newer major of `TradingView/Request`, bump the `/3` tag — signatures are stable.)

- [ ] **Step 2: New semantic knobs (after `wick_pctile_window`, line 17)**

```pine
os_linreg_window      = input.int(50,   "Overshoot linreg window",  minval = 5)
os_pctile_window      = input.int(200,  "Overshoot pctile window")
er_window             = input.int(20,   "Efficiency ratio window",  minval = 2)
vz_window             = input.int(100,  "Volume z-score window",    minval = 10)
```

- [ ] **Step 3: Extend settings_hash (inside the `barstate.isfirst` block, after the `wick_pctile_window` mix)**

```pine
    h := f_mix(h, os_linreg_window)
    h := f_mix(h, os_pctile_window)
    h := f_mix(h, er_window)
    h := f_mix(h, vz_window)
```

cfg WILL change from 509208 — that is the point (no-pool). Record the new value from the version cell in Step 12 and in the CHANGELOG.

- [ ] **Step 4: Hoist `f_fstr` up** — move the existing one-liner `f_fstr(float x) => na(x) ? "na" : str.tostring(x, "#.########")` from line 235 to directly under `f_reg_str` (line 67). The covariate tail builder (Step 7) needs it before the T1 section. Delete the original at line 235.

- [ ] **Step 5: Replace the OI feed block (lines 171–175) with the Request library**

Delete `oi_symbol_in`, `oi_tkr`, and the `request.security(oi_tkr, …)` line. In their place:

```pine
// ════════════════ Derivatives via official TradingView/Request library (v0.4.6) ════════════════
// Perpetuals only — spot symbols return na everywhere; let na propagate.
// NEVER nz() raw OI: nz(oi[1]) fabricates a 0 prior → spurious giant bar-1 delta.
[_oo, _oh, _ol, oi_close, _orising] = r.openInterestCrypto(symbol = syminfo.tickerid, timeframe = timeframe.period)
float oi = oi_close
float fr  = r.cryptoDerivativeMetric(metricName = "Funding Rate",      symbol = syminfo.tickerid, timeframe = timeframe.period)
float lqb = r.cryptoDerivativeMetric(metricName = "Liquidations Buy",  symbol = syminfo.tickerid, timeframe = timeframe.period)  // SHORTS force-closed
float lqs = r.cryptoDerivativeMetric(metricName = "Liquidations Sell", symbol = syminfo.tickerid, timeframe = timeframe.period)  // LONGS force-closed
```

Keep the `_PREMIUM`/spot-fallback `fp` block unchanged (`fp` stays; `fr` is additive). The deleted `input.symbol` also deletes the garbage-override study-kill hazard — note it in the CHANGELOG.

- [ ] **Step 6: New covariate computations (directly after the `f_gvb` helper, line 198)**

```pine
// ════════════════ v0.4.6 covariates (spec §8; logged, never gate) ════════════════
// Overshoot: linreg anchor on [1] so the signal bar never drags the fit.
// os is SIGNED (above/below anchor); osp ranks |os| (stretch magnitude).
float lr_anchor = ta.linreg(close, os_linreg_window, 0)[1]
float os_raw  = na(lr_anchor) or na(atr) or atr == 0 ? na : (close - lr_anchor) / atr
float os_rank = ta.percentrank(math.abs(os_raw), os_pctile_window)   // unconditional (consistency)

// Kaufman efficiency ratio
float er_num = math.abs(close - close[er_window])
float er_den = math.sum(math.abs(close - close[1]), er_window)
float er = na(er_den) or er_den == 0 ? na : er_num / er_den

// Volume z-score on the signal bar
float v_std = ta.stdev(volume, vz_window)
float vz = na(v_std) or v_std == 0 ? na : (volume - ta.sma(volume, vz_window)) / v_std

// CVD: this bar's net volume delta from 60-min intrabars (na where unavailable).
// COMPILE-GATED: if the signature is rejected, read pine_get_errors and adapt;
// if the data is unavailable for the plan/symbol, set dlt = na and proceed.
[dlt_o, dlt_max, dlt_min, dlt_c] = ta.requestVolumeDelta("60")
float dlt = na(dlt_c) or na(dlt_o) ? na : dlt_c - dlt_o

// Level ages (bars since each structural level last changed) — na-safe: an
// na != na comparison is na → false inside barssince, yielding na early-history.
int age_hl  = ta.barssince(hl_ref   != hl_ref[1])
int age_lh  = ta.barssince(lh_ref   != lh_ref[1])
int age_rlo = ta.barssince(range_lo != range_lo[1])
int age_rhi = ta.barssince(range_hi != range_hi[1])

// Shared covariate tail suffix — appended to EVERY trade tail (fixed key order:
// os|osp|er|vz|dlt|fr|lqb|lqs). Append-only per §9 schema discipline.
f_cov_tail() =>
    "os=" + (na(os_raw) ? "na" : str.tostring(os_raw, "#.##"))
     + "|osp=" + (na(os_raw) or na(os_rank) ? "na" : str.tostring(os_rank, "#.#"))
     + "|er=" + (na(er) ? "na" : str.tostring(er, "#.##"))
     + "|vz=" + (na(vz) ? "na" : str.tostring(vz, "#.##"))
     + "|dlt=" + f_fstr(dlt)
     + "|fr=" + (na(fr) ? "na" : str.tostring(fr, "#.######"))
     + "|lqb=" + f_fstr(lqb) + "|lqs=" + f_fstr(lqs)
```

- [ ] **Step 7: Append the suffix to both T1 tail builders**

In `f_t1_tail` AND `f_t1s_tail`, the final string expression currently ends with:

```pine
     + "|gvb=" + (na(g) ? "na" : str.tostring(g, "#.##"))
```

change that last line (in both functions) to:

```pine
     + "|gvb=" + (na(g) ? "na" : str.tostring(g, "#.##"))
     + "|" + f_cov_tail()
```

- [ ] **Step 8: Extend `f_t2_tail` with `swd` + `age_t` params and the suffix**

Replace the whole `f_t2_tail` function:

```pine
// fixed tail key order: lvl|stop|t1|rsn|reg|reg1d|age|wkp|t1co|rt1|oi_d|q|fp|gvb|swd|age_t|<cov>
f_t2_tail(float lvl, float stp, float t1px, string rsn, float wkp, bool t1co, float rt1, float swd, int aget) =>
    float g = f_gvb(lvl)
    "lvl=" + f_fstr(lvl) + "|stop=" + f_fstr(stp) + "|t1=" + f_fstr(t1px) + "|rsn=" + rsn
     + "|reg=" + f_reg_str(regime) + "|reg1d=" + f_reg_str(reg_1d)
     + "|age=" + str.tostring(regime_age)
     + "|wkp=" + (na(wkp) ? "na" : str.tostring(wkp, "#.#"))
     + "|t1co=" + (t1co ? "1" : "0")
     + "|rt1=" + (na(rt1) ? "na" : str.tostring(rt1, "#.##"))
     + "|oi_d=" + (na(oi_chg) ? "na" : str.tostring(oi_chg, "#.##"))
     + "|q=" + quad + "|fp=" + (na(fp) ? "na" : str.tostring(fp, "#.#"))
     + "|gvb=" + (na(g) ? "na" : str.tostring(g, "#.##"))
     + "|swd=" + (na(swd) ? "na" : str.tostring(swd, "#.##"))
     + "|age_t=" + (na(aget) ? "na" : str.tostring(aget))
     + "|" + f_cov_tail()
```

- [ ] **Step 9: Update the eight `f_t2_tail` call sites with sweep depth + level age**

Sweep depth = wick penetration past the swept level in ATRs. The extra args per site (all six existing args stay identical):

| Site | append `swd` | append `age_t` |
|---|---|---|
| 2A long (3 calls: 1d/rr/ENT) | `(hl_ref - low) / atr` | `age_hl` |
| 2A short (3 calls) | `(high - lh_ref) / atr` | `age_lh` |
| 2B long (3 calls) | `(range_lo - low) / atr` | `age_rlo` |
| 2B short (3 calls) | `(range_hi + 0) / na → use (high - range_hi) / atr` | `age_rhi` |

Concretely, e.g. the 2A long ENT line becomes:

```pine
            string a_ent = f_t2_tail(hl_ref, stp, trend_high, "na", wkp_lo, t2a_l_coin, rt1, (hl_ref - low) / atr, age_hl)
```

and the 2B short ENT line:

```pine
                string b_ent_s = f_t2_tail(range_hi, stp, mid, "na", wkp_hi, false, rt1, (high - range_hi) / atr, age_rhi)
```

Apply the same two extra args to all 12 calls (2A-L ×3, 2A-S ×3, 2B-L ×3, 2B-S ×3).

- [ ] **Step 10: Data Window additions (after the existing DW plots)**

```pine
plot(os_raw, "DW overshoot (ATR, signed)",  display = display.data_window)
plot(er,     "DW efficiency ratio",          display = display.data_window)
plot(vz,     "DW volume z-score",            display = display.data_window)
plot(dlt,    "DW volume delta (60m CVD)",    display = display.data_window)
plot(fr,     "DW funding rate",              display = display.data_window)
plot(lqb,    "DW liq buy (shorts closed)",   display = display.data_window)
plot(lqs,    "DW liq sell (longs closed)",   display = display.data_window)
```

- [ ] **Step 11: Compile via MCP**

`Set-Clipboard` the full file → click editor → Ctrl+A, Ctrl+V → `pine_smart_compile`. Expected: clean (warnings ≤ existing). If `ta.requestVolumeDelta` signature errors: `pine_get_errors`, adapt per the documented tuple form; if the function/data is flatly unavailable, replace the call with `float dlt = na` and note it in the CHANGELOG.

- [ ] **Step 12: Live verify**

Remove + re-add the study (BTCUSDT.P 4H). Verify: (1) version cell reads `v0.4.6` + NEW cfg — record it; (2) chips render identically to v0.4.5 (same bars — eyeball vs the prior screenshot); (3) `data_get_study_values` shows non-na `DW funding rate`, `DW liq buy/sell`, `DW volume z-score`, `DW open interest` on the live bar; (4) hover one entry chip — card shows the new keys.

- [ ] **Step 13: Save `.pine` to repo, CHANGELOG, commit**

Update the repo copy of `jamal-fable.pine` to exactly what compiled. CHANGELOG entry: v0.4.6 — covariates list, Request-library migration, OI-override input deleted (hazard gone), new cfg value, dlt fallback status.

```powershell
git add jamal-fable.pine CHANGELOG.md; git commit -m "feat(fable): v0.4.6 covariate emission release - os/osp/er/vz/dlt/swd/age_t/fr/lqb/lqs; derivative data via TradingView/Request/3 (OI 5-tuple, funding, liquidations); OI-override input deleted"; git push origin main
```

---

### Task 2: Feed verification — ccxt cross-checks + history coverage

**Files:**
- Create: `harness/evaluator/feed_check_v046.py`

- [ ] **Step 1: Write the cross-check script**

```python
"""v0.4.6 feed verification: library OI vs ccxt; funding sign vs ccxt.
Reads the LIVE values printed by the chart Data Window (passed on the CLI,
harvested via data_get_study_values) and compares against Binance via ccxt.
Usage: python feed_check_v046.py BTC/USDT:USDT --oi 78123.4 --fr 0.0001
"""
import argparse
import ccxt

ap = argparse.ArgumentParser()
ap.add_argument("market")            # e.g. BTC/USDT:USDT
ap.add_argument("--oi", type=float, required=True)   # DW open interest
ap.add_argument("--fr", type=float, required=True)   # DW funding rate
args = ap.parse_args()

ex = ccxt.binanceusdm()
oi = ex.fetch_open_interest(args.market)
fr = ex.fetch_funding_rate(args.market)
oi_ex = float(oi["openInterestAmount"])
fr_ex = float(fr["fundingRate"])
oi_ok = abs(args.oi - oi_ex) / oi_ex < 0.05          # 5% slack: feed sampling lag
fr_ok = (args.fr >= 0) == (fr_ex >= 0)               # sign agreement
print(f"OI  chart={args.oi:.1f} ccxt={oi_ex:.1f} -> {'OK' if oi_ok else 'MISMATCH'}")
print(f"FR  chart={args.fr:.6g} ccxt={fr_ex:.6g} -> {'OK (sign)' if fr_ok else 'SIGN MISMATCH'}")
raise SystemExit(0 if (oi_ok and fr_ok) else 1)
```

- [ ] **Step 2: Run it** — pull the live `DW open interest` / `DW funding rate` values from `data_get_study_values` on BTCUSDT.P, then:

Run: `python harness/evaluator/feed_check_v046.py "BTC/USDT:USDT" --oi <DW value> --fr <DW value>`
Expected: both `OK`. A MISMATCH on OI = the library feed differs from the old `_OI` ticker → STOP and investigate scale before harvesting.

- [ ] **Step 3: Repeat for NEARUSDT.P** (`"NEAR/USDT:USDT"`) — the small-cap feed is where coverage gaps would show.

- [ ] **Step 4: Commit**

```powershell
git add harness/evaluator/feed_check_v046.py; git commit -m "test(fable): v0.4.6 feed cross-check - library OI + funding vs ccxt"; git push origin main
```

(History coverage for `fr`/`lqb`/`lqs`/`dlt` back to April is checked from the harvested events in Task 4 Step 5 — not from the chart.)

---

### Task 3: Harness — report v0.4.6 tables (TDD)

**Files:**
- Modify: `harness/evaluator/report.py`
- Modify: `harness/evaluator/sanity_gate.py`
- Create: `harness/tests/test_report_v046.py`

- [ ] **Step 1: Write the failing tests**

```python
"""v0.4.6 report helpers: per-trade rt1 conditioning + nested lq-within-swd."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.report import bucket_rows_nested, EVENT_GLOB


def _ep(trade, swd, lq, r, code="t1_hit"):
    return {"trade": trade, "exit_code": code, "r": r, "mfe_r": r,
            "ambiguous": 0, "factors": {"swd": str(swd), "lq_tot": str(lq)}}


def test_event_glob_is_s046():
    assert "s0.4.6" in EVENT_GLOB


def test_nested_buckets_split_outer_then_inner():
    eps = [_ep("2A", 0.1, 5, 1.0), _ep("2A", 0.1, 50, -1.0, "stop_out"),
           edge := _ep("2A", 0.9, 50, 2.0)]
    rows = bucket_rows_nested(eps, "swd", [(None, 0.5), (0.5, None)], ["<0.5", ">=0.5"],
                              "lq_tot", [(None, 10), (10, None)], ["<10", ">=10"])
    # 4 rows: 2 outer x 2 inner; the (<0.5, <10) row holds exactly 1 episode
    assert len(rows) == 4
    assert rows[0][0] == "<0.5 | <10" and rows[0][1] == 1
    assert rows[3][0] == ">=0.5 | >=10" and rows[3][1] == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest harness/tests/test_report_v046.py -v`
Expected: FAIL — `ImportError: cannot import name 'bucket_rows_nested'` (and `EVENT_GLOB`).

- [ ] **Step 3: Implement in `report.py`**

(a) Extract the glob into a constant and bump it — replace the line in `load_events`:

```python
EVENT_GLOB = "*_s0.4.6_*.jsonl"
```
```python
    files = sorted(glob.glob(str(HARNESS / "events" / EVENT_GLOB)))
```

(b) Add the nested bucketer (below `bucket_rows`):

```python
def bucket_rows_nested(eps, okey, oedges, olabels, ikey, iedges, ilabels):
    """Two-level conditioning: outer factor bands, inner factor bands within each."""
    rows = []
    for olab, (olo, ohi) in zip(olabels, oedges):
        outer = [e for e in eps
                 if (v := fnum(e["factors"], okey)) is not None
                 and (olo is None or v >= olo) and (ohi is None or v < ohi)]
        for ilab, (ilo, ihi) in zip(ilabels, iedges):
            sub = [e for e in outer
                   if (w := fnum(e["factors"], ikey)) is not None
                   and (ilo is None or w >= ilo) and (ihi is None or w < ihi)]
            s = stats_row(sub)
            rows.append([f"{olab} | {ilab}", s["n"], fmt(s["win%"], 0), fmt(s["avg_r"]), fmt(s["med_mfe"])])
    return rows
```

(c) Synthesize `lq_tot` at load time — in `load_events`, after `e = json.loads(line)`:

```python
            f = e.get("factors", {})
            b, s = f.get("lqb"), f.get("lqs")
            if (b not in (None, "na")) or (s not in (None, "na")):
                f["lq_tot"] = str((0 if b in (None, "na") else float(b)) +
                                  (0 if s in (None, "na") else float(s)))
```

(missing side = legitimately 0 liquidations; both-missing stays absent → `na` bucket).

(d) New factor tables in `render_report` — extend `specs` with:

```python
        ("os",  [(None, -1.0), (-1.0, 1.0), (1.0, None)], ["<-1 (stretched dn)", "-1..1", ">1 (stretched up)"]),
        ("osp", [(None, 50), (50, 85), (85, None)], ["<50", "50-85", ">85"]),
        ("er",  [(None, 0.2), (0.2, 0.45), (0.45, None)], ["<0.2 (chop)", "0.2-0.45", ">0.45 (trendy)"]),
        ("vz",  [(None, 0), (0, 1.5), (1.5, None)], ["<0", "0-1.5", ">1.5 (heavy)"]),
        ("fr",  [(None, 0), (0, None)], ["<0 (shorts pay)", ">=0 (longs pay)"]),
        ("swd", [(None, 0.3), (0.3, 0.8), (0.8, None)], ["<0.3", "0.3-0.8", ">0.8 (deep)"]),
        ("age_t", [(None, 10), (10, 40), (40, None)], ["<10", "10-40", ">40"]),
```

(e) Per-trade `rt1` conditioning (critique #5 — the pooled rt1>3 row mixed trade types). After the factor-specs loop:

```python
    L.append("\n### by `rt1` PER TRADE TYPE (pooled rt1 mixes trade geometries — pre-registered)\n")
    for tr, teps in sorted(group_by(eps_all, lambda e: e["trade"]).items()):
        L.append(f"\n**{tr}:**\n")
        L.append(table(FACTOR_HEADER, bucket_rows(teps, "rt1",
                 [(None, 2.0), (2.0, 3.0), (3.0, None)], ["1.5-2", "2-3", ">3"])))
```

(f) Liquidations within sweep-depth bands (pre-registered: bigger flushes liquidate more):

```python
    L.append("\n### by `lq_tot` WITHIN `swd` bands (mechanical correlation pre-registered in §8)\n")
    L.append(table(FACTOR_HEADER, bucket_rows_nested(
        eps_all, "swd", [(None, 0.3), (0.3, 0.8), (0.8, None)], ["swd<0.3", "swd 0.3-0.8", "swd>0.8"],
        "lq_tot", [(None, 1), (1, None)], ["lq low", "lq high"])))
```

(Note: `lq_tot` units are feed-native; the 1.0 inner edge is a placeholder split — after first render, replace with the harvested median and note the value in the report commit message. T1 episodes have no `swd` → excluded by construction; that is correct, sweep depth is a sweep-trade concept.)

(g) Update the PREREG block — append two lines:

```python
- Liquidation totals correlate mechanically with sweep depth; lq is read WITHIN swd bands.
- rt1 is conditioned per trade type; the pooled rt1 table from the 2026-06 campaign mixed geometries.
```

(h) Update the report title sources line: `s0.4.5 only` → use `EVENT_GLOB` in the f-string.

- [ ] **Step 4: Run tests**

Run: `python -m pytest harness/tests/ -v`
Expected: ALL pass (new + the existing suite).

- [ ] **Step 5: Bump `sanity_gate.py`** — change the event filename pattern:

```python
    evs = [json.loads(l) for l in open(HARNESS / "events" / f"{sym}_240_v1_s0.4.6_c{CFG}_B.jsonl")]
```

with `CFG = "<new cfg from Task 1 Step 12>"` defined at top. The 11 audited expectations stay byte-identical — same outcomes from the new harvest IS the emission-only regression proof at episode level.

- [ ] **Step 6: Commit**

```powershell
git add harness/evaluator/report.py harness/evaluator/sanity_gate.py harness/tests/test_report_v046.py; git commit -m "feat(fable): report v0.4.6 - new factor tables, per-trade rt1, lq-within-swd nested conditioning, s0.4.6 glob"; git push origin main
```

---### Task 4: Re-harvest the basket + emission-only proof

**Files:**
- Create: `harness/evaluator/compare_emissions.py`
- Create: `harness/evaluator/coverage_check.py`
- Data: `harness/events/raw/`, `harness/events/*.jsonl`, `harness/bars/*.csv`

- [ ] **Step 1: Refresh bars** (extend through yesterday; `--until` = TOMORROW's date per the fetcher rule):

```powershell
python harness/bars/fetch_bars.py --symbol BTCUSDT --tf 4h --until 2026-06-12
python harness/bars/fetch_bars.py --symbol ETHUSDT --tf 4h --until 2026-06-12
python harness/bars/fetch_bars.py --symbol SOLUSDT --tf 4h --until 2026-06-12
python harness/bars/fetch_bars.py --symbol NEARUSDT --tf 4h --until 2026-06-12
```

(Use the exact existing CLI of `fetch_bars.py` — check its argparse if flags differ; `--since` must remain ≥ `pivot_right` bars before the window.)

- [ ] **Step 2: Harvest all 4 symbols** — per symbol: `chart_set_symbol` → remove + re-add Jamal Fable → `data_get_pine_labels study_filter="Jamal Fable"` (oversized result auto-saves to disk) → copy the saved file to `harness/events/raw/<SYMBOL>_s046.json` → parse:

```powershell
python harness/harvest/parse_labels.py harness/events/raw/BTCUSDT.P_s046.json --symbol BTCUSDT.P
python harness/evaluator/align_check.py   # hard precondition, every symbol
```

Expected: 0 quarantined per symbol. Repeat ×4. Files land as `*_s0.4.6_c<newcfg>_B.jsonl` automatically.

- [ ] **Step 3: Write the emission-diff script** — proves "emission-only release" mechanically:

```python
"""s0.4.5 vs s0.4.6: same events on same bars (head identity + old factor keys
equal); only script_v/cfg and the NEW keys may differ. Any delta = logic change."""
import glob
import json
import sys
from pathlib import Path

NEW_KEYS = {"os", "osp", "er", "vz", "dlt", "fr", "lqb", "lqs", "swd", "age_t"}
HARNESS = Path(__file__).resolve().parents[1]

bad = 0
for old_f in sorted(glob.glob(str(HARNESS / "events" / "*_s0.4.5_*.jsonl"))):
    sym = Path(old_f).name.split("_")[0]
    new_fs = glob.glob(str(HARNESS / "events" / f"{sym}_*_s0.4.6_*.jsonl"))
    if not new_fs:
        print(f"{sym}: NO s0.4.6 file"); bad += 1; continue
    def load(p):
        evs = {}
        for line in open(p):
            e = json.loads(line)
            k = (e["bar_ts"], e["trade"], e["event"], e["dir"], e["factors"].get("typ", ""))
            evs[k] = e
        return evs
    old, new = load(old_f), load(new_fs[0])
    only_old = set(old) - set(new)
    only_new = set(new) - set(old)
    # the new harvest may extend past the old one's last bar — tolerate strictly-later extras
    horizon = max(k[0] for k in old)
    only_new = {k for k in only_new if k[0] <= horizon}
    val_diff = 0
    for k in set(old) & set(new):
        fo, fn = old[k]["factors"], new[k]["factors"]
        for fk, fv in fo.items():
            if fk not in NEW_KEYS and fn.get(fk) != fv:
                val_diff += 1
                print(f"{sym} {k}: factor {fk} {fv} -> {fn.get(fk)}")
    status = "OK" if not (only_old or only_new or val_diff) else "DIFF"
    if status == "DIFF":
        bad += 1
        for k in sorted(only_old): print(f"{sym} MISSING in new: {k}")
        for k in sorted(only_new): print(f"{sym} EXTRA in new:   {k}")
    print(f"{sym}: {status} (shared={len(set(old) & set(new))}, old-only={len(only_old)}, new-only={len(only_new)}, value-diffs={val_diff})")
print("emission-diff:", "PASS" if bad == 0 else f"FAIL ({bad})")
raise SystemExit(1 if bad else 0)
```

- [ ] **Step 4: Run it**

Run: `python harness/evaluator/compare_emissions.py`
Expected: `PASS` all 4 symbols. Any missing/extra event or changed old-key value = an accidental logic change → STOP, diagnose in the Pine diff before proceeding. (Known tolerable case: `oi_d`/`oi_t`/`q` values may shift if the library OI series differs in sampling from the old `_OI` ticker — if ONLY oi-derived keys differ while events/levels are identical, record it as a feed-migration delta in the CHANGELOG, not a logic bug; add `oi_d`, `oi_t`, `q` to `NEW_KEYS` to re-run, and note the count.)

- [ ] **Step 5: Coverage check** — new-factor na-rates by month (catches shallow funding/liq/CVD history *from the data*):

```python
"""Per-month na-rate for the v0.4.6 factor keys, across all s0.4.6 events."""
import glob
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

KEYS = ["os", "osp", "er", "vz", "dlt", "fr", "lqb", "lqs", "swd", "age_t"]
HARNESS = Path(__file__).resolve().parents[1]
tot = defaultdict(int)
nas = defaultdict(lambda: defaultdict(int))
for f in glob.glob(str(HARNESS / "events" / "*_s0.4.6_*.jsonl")):
    for line in open(f):
        e = json.loads(line)
        if e["trade"] == "SYS":
            continue
        m = datetime.fromtimestamp(e["bar_ts"], tz=timezone.utc).strftime("%Y-%m")
        tot[m] += 1
        for k in KEYS:
            if e["factors"].get(k, "na") == "na":
                nas[m][k] += 1
print("month   n      " + "  ".join(f"{k:>6}" for k in KEYS))
for m in sorted(tot):
    print(f"{m} {tot[m]:5d}  " + "  ".join(f"{100*nas[m][k]/tot[m]:5.0f}%" for k in KEYS))
```

Run: `python harness/evaluator/coverage_check.py`
Expected: `os/osp/er/vz/swd/age_t` near 0% na (price-derived; `swd/age_t` na on T1 rows is structural — they are t2-only keys, so T1-heavy months show high %, that is fine); `fr/lqb/lqs/dlt` low na in recent months — if April is 100% na for any, the feed history is shallow: record the coverage boundary in the report commit, do NOT block.

- [ ] **Step 6: Commit**

```powershell
git add harness/evaluator/compare_emissions.py harness/evaluator/coverage_check.py harness/events/ harness/bars/; git commit -m "feat(fable): v0.4.6 basket re-harvest (4 symbols, aligned) + emission-diff PASS + factor coverage map"; git push origin main
```

---

### Task 5: Report re-render + sanity gate + close-out

- [ ] **Step 1: Sanity gate**

Run: `python harness/evaluator/sanity_gate.py`
Expected: `gate: PASS` — the 11 v0.3-audited entries grade identically from s0.4.6 data. FAIL = STOP (walker or emission regression).

- [ ] **Step 2: Render the report**

Run: `python harness/evaluator/report.py --out harness/reports/campaign_2026-06_s046.md`
Expected: episodes ≈ 30 + a few new June closes; all new factor tables render; per-trade rt1 section present; lq-within-swd table present. Replace the `lq_tot` placeholder inner edge with the harvested median and re-render.

- [ ] **Step 3: Read the report yourself** — sanity-scan: headline within noise of the s0.4.5 run (same episodes ± June additions); no factor table 100%-na that coverage_check said should have data.

- [ ] **Step 4: CHANGELOG + memory + commit**

CHANGELOG: v0.4.6 close-out — new cfg, emission-diff PASS, coverage boundaries, report path. Update the `jamal-fable` memory file state line (v0.4.6 shipped, new cfg, report regenerated, v0.5 unified-sweep-engine next).

```powershell
git add harness/reports/ CHANGELOG.md; git commit -m "docs(fable): v0.4.6 campaign report re-render + close-out"; git push origin main
```

- [ ] **Step 5: USER CHECKPOINT (blocking)** — present: emission-diff result, coverage map, the new factor tables (especially `osp` on existing trades — the free first read on the OS stretch thesis), and the v0.5 go/no-go. The campaign's four standing review decisions (rr 1.5 / 1D gate / gvb / v0.5 selectors) can be ruled on with this richer report in hand.

---

## Self-review notes

- **Spec coverage:** §8 v0.4.6 keys — `os/os_pct(→osp)/swd/er/vz/dlt/age_t/fr/lqb/lqs` all in Tasks 1; Request migration + override deletion (Task 1 Step 5); ccxt re-cross-check (Task 2); history-coverage check (Task 4 Step 5); per-trade rt1 + lq-within-swd (Task 3); no-pool via new glob + new cfg (Tasks 1/3). ✓
- **No engine/signal edits anywhere** — enforced by compare_emissions.py (Task 4) + sanity gate (Task 5). ✓
- **Known risk:** `ta.requestVolumeDelta` signature/data availability — compile-gated with explicit na fallback (Task 1 Step 6/11). Library OI sampling may differ from `_OI` ticker — explicit tolerance procedure (Task 4 Step 4).
- **Type consistency:** `f_t2_tail(..., float swd, int aget)` matches all 12 call sites (Task 1 Step 9); `bucket_rows_nested` signature matches test (Task 3). ✓
