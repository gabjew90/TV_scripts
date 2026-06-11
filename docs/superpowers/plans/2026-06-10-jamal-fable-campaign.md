# Jamal Fable Backfill Campaign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Project override:** NO worktrees/branches — inline on `main`, commit + push per task.

**Goal:** The first judgment pass — deep 4-symbol backfill, episode simulation with exit codes/counterfactuals/MFE, and the factor-conditioned report that decides: the rr-gate level, the 1D gate's worth, the `gvb` filter, and the selection criteria for v0.5's 2A-general.

**Architecture:** Pure repo-side work plus harvests. `episodes.py` walks each ENT forward through ccxt bars against its OWN snapshot levels (spec §7 — never reconstructed); `report.py` conditions outcomes on the §8 factors and *reclassifies logged skips as pseudo-episodes* to answer gate questions without touching Pine. Every §10 rule (no-pool, sequential-per-direction, pre-registered annotations) is enforced in code.

**Tech Stack:** Python (existing harness), TradingView MCP for harvests only. **No Pine changes** — the indicator is frozen at **v0.4.4** for the whole campaign (provenance hygiene; v0.4.4 = the pre-campaign emission fixes from external review: blocked-ARM once-per-pullback, walkable 1d-SKP levels, handoff-consistent t1co).

**Spec:** §7 (snapshot grading), §8 (factors + promotion path), §10 (evaluator rules), §14 (2A-general gate criteria). Pre-registered, NOT findings: depth↔R mechanical correlation; V-shape coverage hole; ambiguous-bar resolution (below).

---

## Decisions locked here (pre-registered before any data is graded)
1. **Ambiguous bar rule:** if one bar touches both stop and target, the episode grades as **stop first** (worst case), flagged `ambiguous=1` and counted in the report. Conservative by construction.
2. **R accounting v1:** `stop_out` = −1R; `t1_hit` = +rt1 (full position; partial+runner accounting is a later refinement — noted on the report); `thesis_exit` = mark-to-exit R at the confirmed close. **MFE** = max favorable excursion in R from entry to episode end (and capped `mfe30` over the first 30 bars for open episodes).
3. **Trail (post-T1 runner) is NOT simulated in v1** — exit codes are `stop_out | thesis_exit | t1_hit | open`; the trail column ships with the partial-accounting refinement. (Scope cut, stated loudly per no-silent-caps.)
4. **Pseudo-episodes:** `SKP rsn=rr` and `SKP rsn=1d` events carry full snapshot levels → they are graded exactly like entries. This answers "what would rr_min=1.0/1.25 have caught?" and "what did the 1D gate save/cost?" from data already logged — zero Pine changes.
5. **Window split:** Apr / May / Jun calendar months, reported separately + pooled-with-caveat; no significance language across windows (§10).
6. **Counterfactual on thesis_exit:** continue the walk — `recovered` (target before stop) vs `stopped`.

---

### Task 1: Episode walker (`harness/evaluator/episodes.py`) — TDD

**Files:** Create `harness/evaluator/episodes.py`; Test `harness/tests/test_episodes.py`.

- [ ] **Step 1: Failing tests** (synthetic bars; one per outcome class):

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.episodes import walk_episode, build_episodes

BARS = [  # ts, o, h, l, c — a tiny synthetic tape
    (0, 100, 101, 99, 100), (1, 100, 102, 98, 101), (2, 101, 106, 100, 105),
    (3, 105, 107, 95, 96), (4, 96, 97, 90, 91), (5, 91, 95, 90, 94),
]

def _ev(ts, dir_, ent, lvl, stop, t1):
    return {"bar_ts": ts, "dir": dir_, "px": ent, "event": "ENT", "trade": "T1",
            "factors": {"lvl": str(lvl), "stop": str(stop), "t1": str(t1), "rt1": "2.0", "rsn": "na"}}

def test_t1_hit_long():
    e = walk_episode(_ev(0, "L", 100, 97, 98, 105.5), BARS)
    assert e["exit_code"] == "t1_hit" and e["exit_ts"] == 2 and e["r"] == 2.0

def test_stop_out_long():
    e = walk_episode(_ev(0, "L", 100, 97, 99.5, 200), BARS)
    assert e["exit_code"] == "stop_out" and e["r"] == -1.0

def test_ambiguous_bar_is_stop_first():
    e = walk_episode(_ev(1, "L", 101, 95, 100.5, 105.5), BARS)  # bar 2: low 100<=100.5? no... bar 3 hits 107 AND 95
    assert e["exit_code"] in ("t1_hit", "stop_out")  # refined below in impl test

def test_thesis_exit_long_with_counterfactual():
    e = walk_episode(_ev(0, "L", 100, 99.0, 89, 200), BARS)   # bar 1 CLOSES 101 ok; bar 3 closes 96 < lvl 99 -> thesis
    assert e["exit_code"] == "thesis_exit" and e["exit_ts"] == 3
    assert e["counterfactual"] in ("recovered", "stopped", "open")

def test_sequential_per_direction():
    evs = [_ev(0, "L", 100, 97, 98, 200), _ev(1, "L", 101, 97, 98, 200)]
    eps, overlapped = build_episodes(evs, BARS)
    assert len(eps) == 1 and len(overlapped) == 1

def test_mfe_computed():
    e = walk_episode(_ev(0, "L", 100, 95, 98, 200), BARS)
    assert e["mfe_r"] >= (107 - 100) / (100 - 98) - 0.01   # ran to 107 before stopping at bar 3/4
```

- [ ] **Step 2:** Run → FAIL (module missing).
- [ ] **Step 3: Implement** — core semantics (long side; shorts mirrored):
  - Iterate bars strictly AFTER the entry bar. Per bar, in order: (a) stop touch (`low <= stop`) and target touch (`high >= t1`) — if both, **stop first** + `ambiguous=1`; (b) else stop → `stop_out`; (c) else target → `t1_hit`; (d) else confirmed close beyond `lvl` → `thesis_exit` (then continue walking for the counterfactual: target-before-stop = `recovered`).
  - Track `mfe_r` continuously (best favorable price vs entry, in R) until episode end; `mfe30_r` capped at 30 bars.
  - `build_episodes(events, bars)`: sort ENTs by ts; per (symbol, dir), an ENT whose ts falls inside an open episode → `skip_overlap` list; else walk it. Levels ALWAYS from the event's own factors (`lvl/stop/t1` strings → float; `na` → episode skipped with reason `no_levels`).
  - Pseudo-episode helper: `as_pseudo(skp_event)` — identical walk; tags `pseudo=rr|1d`.
- [ ] **Step 4:** Tests pass (tighten the ambiguous-bar test to assert the actual rule once implemented: bar with both touches → `stop_out`+`ambiguous`).
- [ ] **Step 5:** Commit + push.

### Task 2: Report generator (`harness/evaluator/report.py`)

**Files:** Create `harness/evaluator/report.py`; Test `harness/tests/test_report.py` (smoke: synthetic episodes → markdown contains the pre-registered annotations block and a gvb-band table).

- [ ] **Step 1:** Implement: loads **`harness/events/*_s0.4.4_*.jsonl` ONLY** (no-pool enforced: refuses mixed cfg/schema without `--allow-mixed`; **CORRECTION to the original draft:** 0.4.x deltas are NOT all render-only — v0.4.4 changed emission semantics (blocked-ARM dedup, 1d-SKP levels, t1co timing) precisely so the campaign could be answered; since nothing was harvested for the campaign before v0.4.4, the campaign pools nothing across script versions — earlier s0.4.0 probe files are excluded), builds episodes per symbol via `episodes.py` + that symbol's bars CSV, then writes `harness/reports/campaign_<date>.md`:
  - **Headline:** episodes by trade/dir/symbol — count, win% (t1 before stop), avg R, median MFE, ambiguous count, skip_overlap count, open count.
  - **Factor conditioning** (each: count / win% / avg R / median MFE per bucket): `gvb` (<0.3, 0.3–0.7, >0.7), `wkp` (<50, 50–85, >85), `oi_d` sign, `fp` (<25, 25–75, >75), `q`, `t1co`, `d_pct` (<60, 60–100, >100), `age` (<10, 10–50, >50).
  - **Gate questions:** (a) rr reclassification — pseudo-episodes from `SKP rsn=rr` bucketed by their rt1 (1.0–1.25, 1.25–1.5): would they have paid? (b) 1D gate — pseudo-episodes from `SKP rsn=1d` + `ARM rsn=1d` follow-throughs: what did blocking cost/save? (c) thesis-exit counterfactuals: recovered vs stopped ratio.
  - **Pre-registered annotations block** (printed verbatim at the top): depth↔R is mechanical; V-hole measured by ARM-without-ENT; ambiguous=stop-first is conservative; monthly windows are not pooled for significance.
- [ ] **Step 2:** Smoke test passes; commit + push.

### Task 3: The harvests (one symbol per step — context-heavy, deliberately serialized)

For EACH of BTCUSDT.P, ETHUSDT.P, SOLUSDT.P, NEARUSDT.P (4H, default emit window Apr 1 → now):
- [ ] `chart_set_symbol` → `data_get_pine_labels` (max 500) → save raw `harness/events/raw/<sym>_240_<date>_campaign.json` → `parse_labels.py --symbol <sym>` → `fetch_bars.py` (ccxt mapping per README; `--since 2026-03-25 --until <tomorrow>`) → `align_check.py` (must exit 0).
- [ ] Commit after each symbol (4 commits). Watch the 500-label cap per symbol (chips + events; if `total_labels` = 500, chunk the window).

### Task 4: Run the campaign + commit the report

- [ ] `py -3 harness/evaluator/report.py --out harness/reports/campaign_2026-06.md` → review stdout for no-pool warnings → commit report + any quarantines.
- [ ] Sanity spot-check: the 11 known v0.3-audited entries must appear with `t1_hit` (they were hand-graded target-first) — any disagreement = walker bug, STOP and fix.

### Task 5: CHANGELOG + USER REVIEW (the real checkpoint)

- [ ] CHANGELOG entry: counts, headline table, gate-question answers, scope cuts (trail/partials), quarantines.
- [ ] **USER REVIEW (blocking):** walk the report together. Decisions on the table, each requiring the user's call, none made by default: `rr_min` (keep 1.5 / lower per pseudo-episode evidence), 1D gate (keep / drop / asymmetric), `gvb` (promote to gate?), and the v0.5 2A-general selection criteria. Spec §8 promotion path: factor → gate **by this evidence only**.
```
