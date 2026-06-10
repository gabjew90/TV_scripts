# Jamal Fable v0.1 ("The Pipe") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Project override:** per standing user rule, NO worktrees/branches — all work inline on `main`, commit + push to `origin main` at the end of every task.

**Goal:** Prove the Jamal Fable validation pipe end-to-end — regime engine on chart emitting machine-readable events, MCP harvest → JSONL parser → ccxt bar fetcher → timestamp-alignment check — passing the three acceptance pins of spec §13 v0.1.

**Architecture:** One Pine v6 script (`jamal-fable.pine`) computes the §3 regime state machine and emits `SYS|PING` (regime transitions) and `SYS|PIV` (pivot confirmations) as compact labels; Python tooling in `harness/` parses harvested labels into provenance-keyed JSONL, fetches exchange bars, and hard-fails on any event/bar misalignment. No trade detectors yet — v0.2+ get their own plans after the chart checkpoint.

**Tech Stack:** Pine Script v6 (via TradingView MCP), Python 3.10+ (ccxt, pytest, stdlib only otherwise).

**Spec:** `docs/superpowers/specs/2026-06-09-jamal-fable-design.md` (rev 2, commit `0967b4d`). Read §3 (engine), §9 (schema), §10 (harness), §13 (acceptance) before starting.

---

## File structure

```
jamal-fable.pine                      # Pine v6 source (canonical copy in repo; lives on TV as "Jamal Fable")
harness/
  README.md                           # binding methodology doc (§10 rules)
  requirements.txt                    # ccxt, pytest
  events/                             # canonical JSONL event logs (one file per provenance group)
    raw/                              # raw MCP harvest dumps (audit trail, committed)
  bars/                               # cached OHLCV CSVs: {exchange}_{symbol}_{tf}.csv
    fetch_bars.py                     # ccxt fetcher (binanceusdm), paginated
  harvest/
    parse_labels.py                   # raw harvest JSON -> events JSONL (dedup, no-pool, quarantine)
  evaluator/
    align_check.py                    # timestamp-alignment hard precondition (§10)
  tests/
    test_parse_labels.py
    test_align_check.py
    test_fetch_bars.py
CHANGELOG.md                          # new "JAMAL FABLE" build-log section
```

**Design decisions locked here (engine details the spec leaves to implementation — surface both at the chart checkpoint):**
1. **Seeding at CHOP→UP:** `hl_ref` seeds with the most recent confirmed pivot low overall (`last_pl`); `trend_high` seeds with the broken range high (avoids an instant continuation-BOS artifact). Mirrors for CHOP→DOWN.
2. **Harvest-window inputs are transport-layer** (`emit_from`/`emit_to` chunk the label budget) and are **excluded from `settings_hash`** — they change which events are *emitted*, never what any event *means*. Task 8 amends the spec to say so.
3. **ATR = SMA of True Range** (not RMA) for trivial cross-language reproducibility later.
4. **Label price-field convention for alignment:** `PIV typ=H` aligns against bar `high`, `PIV typ=L` against `low`, everything else against `close`.
5. **TV→ccxt symbol mapping:** `BTCUSDT.P` (TV/Binance perp) ↔ `BTC/USDT:USDT` (ccxt `binanceusdm`). Mapping table lives in `harness/README.md`.

---

### Task 1: Harness scaffold + methodology doc

**Files:**
- Create: `harness/README.md`
- Create: `harness/requirements.txt`
- Create: `harness/events/raw/.gitkeep`, `harness/bars/.gitkeep`

- [ ] **Step 1: Verify Python is available**

Run: `py -3 --version`
Expected: `Python 3.1x.x`. If `py` is missing, try `python --version`. Use whichever works for all later commands.

- [ ] **Step 2: Write `harness/requirements.txt`**

```
ccxt>=4.0
pytest>=8.0
```

- [ ] **Step 3: Install**

Run: `py -3 -m pip install -r harness/requirements.txt`
Expected: exits 0.

- [ ] **Step 4: Write `harness/README.md`** (the binding methodology doc — spec §10 requires it written in v0.1)

```markdown
# Jamal Fable — Harness Methodology (BINDING)

Spec: docs/superpowers/specs/2026-06-09-jamal-fable-design.md (§9, §10).
Pine renders and signals; this directory judges. These rules are binding on
every analysis run; violating them invalidates the run.

## Data flow
1. Pine emits decision-time events as compact labels: `JF|<schema_v>|<script_v>|<cfg>|<src>|<trade>|<event>|<dir>|<tf>|<bar_ts>|<px>|k=v|...`
2. MCP harvest (`data_get_pine_labels`) -> raw JSON saved under `events/raw/` (audit trail, committed).
3. `harvest/parse_labels.py` -> canonical JSONL under `events/`, one file per
   provenance group `(schema_v, script_v, cfg, src, tf, symbol)`. Idempotent:
   re-harvests merge by dedup key (bar_ts + trade + event + dir [+ typ for PIV]).
4. `bars/fetch_bars.py` -> OHLCV CSVs from the exchange API (ccxt binanceusdm).
   The label budget is never spent exporting OHLC through the chart.
5. `evaluator/align_check.py` -> HARD PRECONDITION: every event's bar must exist
   in the fetched series with matching price (PIV-H vs high, PIV-L vs low, else
   close; tolerance 0.1%). Mismatches are quarantined and reported, never
   silently included. Nonzero exit = the pipe is broken; nothing downstream runs.

## No-pool rules (enforced by file layout + evaluator loaders)
- `src=B` (backfill) and `src=L` (live) are never pooled. Backfill earns
  hypotheses; only the live log earns conviction.
- Different `settings_hash` or `schema_version` are never pooled without an
  explicit `--allow-mixed` override. A backfill harvested before and after a
  knob tweak is two datasets.
- Harvest-window inputs (`emit_from`/`emit_to`) are transport-layer and are
  EXCLUDED from settings_hash — chunked harvests of the same config pool freely.

## Pre-registered annotations (carried on every report; discovering these is not a finding)
- Deeper pullbacks mechanically have larger R-to-T1 (trend-high T1 definition).
- Flush entries are mechanically deeper than pullback entries.
- V-shaped pullbacks never form a micro_LH -> Trade #1 structurally cannot
  trigger on them; ARM-without-ENT counts measure this hole.

## Episode rules (v0.2+; recorded now so they don't drift)
- Outcomes graded ONLY against ENT-embedded snapshot levels (lvl/stop/t1, rhi/rlo).
- Sequential per symbol per direction across trade types; blocked ENTs logged
  `skip_overlap`, first-class.
- Exit codes: thesis_exit | stop_out | t1_hit | trail. Counterfactual computed
  for every thesis_exit (hold-to-stop: recovered or stopped?).
- Pivot detection is re-implemented in Python ONLY under the pivot-parity
  license: it must reproduce every Pine SYS|PIV bit-exact from fetched bars
  (gates v0.2 acceptance).
- Aggregate statistics on non-overlapping time windows; no significance claims
  pooled across windows.

## Symbol mapping (TV -> ccxt binanceusdm)
| TV          | ccxt            |
|-------------|-----------------|
| BTCUSDT.P   | BTC/USDT:USDT   |
| ETHUSDT.P   | ETH/USDT:USDT   |
| SOLUSDT.P   | SOL/USDT:USDT   |
| NEARUSDT.P  | NEAR/USDT:USDT  |

## TF mapping (TV `timeframe.period` -> ccxt)
| TV   | ccxt |
|------|------|
| 240  | 4h   |
| 60   | 1h   |
| D    | 1d   |
```

- [ ] **Step 5: Create keep-files and commit**

```powershell
New-Item -ItemType Directory -Force harness/events/raw, harness/bars, harness/harvest, harness/evaluator, harness/tests
New-Item -ItemType File harness/events/raw/.gitkeep, harness/bars/.gitkeep
git add harness; git commit -m "feat(fable): harness scaffold + binding methodology doc"; git push origin main
```

---

### Task 2: Bar fetcher (`fetch_bars.py`) — TDD

**Files:**
- Create: `harness/bars/fetch_bars.py`
- Test: `harness/tests/test_fetch_bars.py`

- [ ] **Step 1: Write the failing test**

`harness/tests/test_fetch_bars.py`:

```python
import csv
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bars.fetch_bars import fetch_ohlcv_all, write_csv


class FakeExchange:
    rateLimit = 0
    def __init__(self, candles):
        self.candles = candles  # list of [ts_ms, o, h, l, c, v]
    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1500):
        out = [c for c in self.candles if c[0] >= since][:limit]
        return out


def test_fetch_paginates_dedups_and_truncates():
    h = 4 * 3600 * 1000
    candles = [[1780000000000 + i * h, 1.0 + i, 2.0 + i, 0.5 + i, 1.5 + i, 100.0] for i in range(10)]
    ex = FakeExchange(candles)
    rows = fetch_ohlcv_all(ex, "BTC/USDT:USDT", "4h",
                           since_ms=candles[2][0], until_ms=candles[7][0], limit=3)
    assert [r[0] for r in rows] == [candles[i][0] for i in range(2, 8)]
    assert len({r[0] for r in rows}) == len(rows)  # no duplicate timestamps


def test_write_csv_seconds_and_header(tmp_path):
    rows = [[1780000000000, 1.0, 2.0, 0.5, 1.5, 100.0]]
    out = tmp_path / "x.csv"
    write_csv(rows, out)
    got = list(csv.DictReader(out.open()))
    assert got[0]["ts_sec"] == "1780000000"
    assert got[0]["close"] == "1.5"
```

- [ ] **Step 2: Run to verify it fails**

Run: `py -3 -m pytest harness/tests/test_fetch_bars.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bars'` (or ImportError on names).

- [ ] **Step 3: Write `harness/bars/fetch_bars.py`** (and empty `harness/bars/__init__.py`, `harness/__init__.py` — not needed since we sys.path the harness dir and import `bars.fetch_bars`; create `harness/bars/__init__.py` only)

```python
"""Fetch perp OHLCV from the exchange API into harness/bars/ CSVs.

Spec ref: design doc section 10 - bars come repo-side from the exchange API;
the label budget is never spent exporting OHLC through the chart.

Usage:
  py -3 harness/bars/fetch_bars.py --symbol "BTC/USDT:USDT" --tf 4h ^
      --since 2026-03-01 --until 2026-06-09 --out harness/bars/binanceusdm_BTCUSDT_4h.csv
"""
import argparse
import csv
import time as _time
from datetime import datetime, timezone
from pathlib import Path


def fetch_ohlcv_all(ex, symbol, timeframe, since_ms, until_ms, limit=1500):
    """Paginate fetch_ohlcv from since_ms to until_ms inclusive. Returns
    sorted, de-duplicated rows [ts_ms, o, h, l, c, v]."""
    rows = []
    cursor = since_ms
    while cursor <= until_ms:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=cursor, limit=limit)
        if not batch:
            break
        rows.extend(batch)
        nxt = batch[-1][0] + 1
        if nxt <= cursor:
            break
        cursor = nxt
        if getattr(ex, "rateLimit", 0):
            _time.sleep(ex.rateLimit / 1000)
    seen = set()
    out = []
    for r in sorted(rows, key=lambda r: r[0]):
        if since_ms <= r[0] <= until_ms and r[0] not in seen:
            seen.add(r[0])
            out.append(r)
    return out


def write_csv(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_sec", "open", "high", "low", "close", "volume"])
        for ts_ms, o, h, l, c, v in rows:
            w.writerow([ts_ms // 1000, o, h, l, c, v])


def _parse_date(s):
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def main():
    import ccxt  # imported here so tests don't need network/ccxt internals
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True, help="ccxt symbol, e.g. BTC/USDT:USDT")
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--since", required=True, help="YYYY-MM-DD (UTC)")
    ap.add_argument("--until", required=True, help="YYYY-MM-DD (UTC)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    ex = ccxt.binanceusdm()
    rows = fetch_ohlcv_all(ex, args.symbol, args.tf, _parse_date(args.since), _parse_date(args.until))
    write_csv(rows, args.out)
    print(f"wrote {len(rows)} bars -> {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify pass**

Run: `py -3 -m pytest harness/tests/test_fetch_bars.py -v`
Expected: 2 passed.

- [ ] **Step 5: Live smoke test (network)**

Run: `py -3 harness/bars/fetch_bars.py --symbol "BTC/USDT:USDT" --tf 4h --since 2026-04-01 --until 2026-06-09 --out harness/bars/binanceusdm_BTCUSDT_4h.csv`
Expected: `wrote ~414 bars -> ...` (69 days × 6 bars/day). Open the CSV, confirm `ts_sec` ascending and prices sane.

- [ ] **Step 6: Commit**

```powershell
git add harness; git commit -m "feat(fable): ccxt bar fetcher with pagination + CSV cache (tested)"; git push origin main
```

---

### Task 3: Label parser (`parse_labels.py`) — TDD

**Files:**
- Create: `harness/harvest/parse_labels.py` (+ `harness/harvest/__init__.py`)
- Test: `harness/tests/test_parse_labels.py`

- [ ] **Step 1: Write the failing test**

`harness/tests/test_parse_labels.py`:

```python
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harvest.parse_labels import parse_label, dedup_key, run

GOOD_PIV = "JF|1|0.1|184223|B|SYS|PIV|N|240|1780444800|2.627|typ=H"
GOOD_PING = "JF|1|0.1|184223|B|SYS|PING|N|240|1780459200|2.7|reg=U|age=0"


def test_parse_label_head_and_tail():
    ev = parse_label(GOOD_PIV)
    assert ev["schema_v"] == "1" and ev["script_v"] == "0.1" and ev["cfg"] == "184223"
    assert ev["src"] == "B" and ev["trade"] == "SYS" and ev["event"] == "PIV"
    assert ev["bar_ts"] == 1780444800 and ev["px"] == 2.627
    assert ev["factors"] == {"typ": "H"}


def test_malformed_label_raises():
    import pytest
    with pytest.raises(ValueError):
        parse_label("JF|1|0.1|184223|B|SYS")          # short head
    with pytest.raises(ValueError):
        parse_label(GOOD_PING + "|noequalsign")        # bad tail


def test_dedup_key_distinguishes_event_type_and_piv_typ():
    a = parse_label(GOOD_PIV)
    b = parse_label(GOOD_PIV.replace("typ=H", "typ=L"))
    c = parse_label(GOOD_PIV.replace("PIV", "PING"))
    assert dedup_key(a) != dedup_key(b)
    assert dedup_key(a) != dedup_key(c)


def test_run_groups_by_provenance_and_is_idempotent(tmp_path):
    raw = {"labels": [{"text": GOOD_PIV}, {"text": GOOD_PING},
                      {"text": GOOD_PING.replace("184223", "999999")},  # different cfg
                      {"text": "decorative non-event"}]}
    raw_file = tmp_path / "raw.json"
    raw_file.write_text(json.dumps(raw))
    out_dir = tmp_path / "events"
    n1, malformed = run(str(raw_file), "BTCUSDT.P", str(out_dir))
    files = sorted(p.name for p in out_dir.glob("*.jsonl"))
    assert files == ["BTCUSDT.P_240_v1_s0.1_c184223_B.jsonl",
                     "BTCUSDT.P_240_v1_s0.1_c999999_B.jsonl"]  # no-pool: cfg split
    assert n1 == 3 and malformed == []
    n2, _ = run(str(raw_file), "BTCUSDT.P", str(out_dir))       # re-harvest
    assert n2 == 0                                              # idempotent: nothing new
    lines = (out_dir / files[0]).read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["symbol"] == "BTCUSDT.P"
```

- [ ] **Step 2: Run to verify it fails**

Run: `py -3 -m pytest harness/tests/test_parse_labels.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'harvest'`.

- [ ] **Step 3: Write `harness/harvest/parse_labels.py`**

```python
"""Parse raw MCP label harvests into canonical, provenance-grouped events JSONL.

Robust to the MCP output shape: walks the whole JSON tree and collects every
string starting with "JF|". Symbol is NOT in the label string (spec section 9
head) - it is stamped at harvest time via --symbol.

No-pool enforcement: one output file per (schema_v, script_v, cfg, src, tf,
symbol). Idempotent: merges with existing file by dedup key.
"""
import argparse
import json
from pathlib import Path

HEAD_FIELDS = ["schema_v", "script_v", "cfg", "src", "trade", "event", "dir", "tf", "bar_ts", "px"]


def iter_jf_strings(node):
    if isinstance(node, str):
        if node.startswith("JF|"):
            yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from iter_jf_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_jf_strings(v)


def parse_label(text):
    parts = text.split("|")
    if parts[0] != "JF" or len(parts) < 1 + len(HEAD_FIELDS):
        raise ValueError(f"malformed head: {text}")
    ev = dict(zip(HEAD_FIELDS, parts[1:1 + len(HEAD_FIELDS)]))
    try:
        ev["bar_ts"] = int(ev["bar_ts"])
        ev["px"] = float(ev["px"])
    except ValueError:
        raise ValueError(f"non-numeric ts/px: {text}")
    factors = {}
    for kv in parts[1 + len(HEAD_FIELDS):]:
        k, sep, v = kv.partition("=")
        if not sep or not k:
            raise ValueError(f"malformed tail '{kv}': {text}")
        factors[k] = v
    ev["factors"] = factors
    return ev


def dedup_key(ev):
    key = (ev["bar_ts"], ev["trade"], ev["event"], ev["dir"])
    if ev["event"] == "PIV":
        key += (ev["factors"].get("typ", ""),)
    return key


def run(raw_path, symbol, out_dir):
    """Returns (n_new_events_written, malformed_list)."""
    raw = json.loads(Path(raw_path).read_text())
    events, malformed = [], []
    for s in iter_jf_strings(raw):
        try:
            events.append(parse_label(s))
        except ValueError as e:
            malformed.append(str(e))
    groups = {}
    for ev in events:
        ev["symbol"] = symbol
        gkey = (ev["schema_v"], ev["script_v"], ev["cfg"], ev["src"], ev["tf"])
        groups.setdefault(gkey, []).append(ev)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n_new = 0
    for (sv, scv, cfg, src, tf), evs in sorted(groups.items()):
        out = out_dir / f"{symbol}_{tf}_v{sv}_s{scv}_c{cfg}_{src}.jsonl"
        existing = {}
        if out.exists():
            for line in out.read_text().splitlines():
                e = json.loads(line)
                existing[dedup_key(e)] = e
        for ev in evs:
            if dedup_key(ev) not in existing:
                existing[dedup_key(ev)] = ev
                n_new += 1
        ordered = sorted(existing.values(), key=lambda e: (e["bar_ts"], e["trade"], e["event"]))
        out.write_text("\n".join(json.dumps(e, sort_keys=True) for e in ordered) + "\n")
    return n_new, malformed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", help="raw harvest JSON (saved MCP data_get_pine_labels output)")
    ap.add_argument("--symbol", required=True, help="TV symbol, e.g. BTCUSDT.P")
    ap.add_argument("--out-dir", default="harness/events")
    args = ap.parse_args()
    n_new, malformed = run(args.raw, args.symbol, args.out_dir)
    print(f"new events: {n_new}; malformed: {len(malformed)}")
    for m in malformed:
        print(f"  MALFORMED: {m}")
    raise SystemExit(1 if malformed else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify pass**

Run: `py -3 -m pytest harness/tests/test_parse_labels.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add harness; git commit -m "feat(fable): label parser - provenance grouping, dedup-idempotent, quarantines malformed (tested)"; git push origin main
```

---

### Task 4: Alignment check (`align_check.py`) — TDD

**Files:**
- Create: `harness/evaluator/align_check.py` (+ `harness/evaluator/__init__.py`)
- Test: `harness/tests/test_align_check.py`

- [ ] **Step 1: Write the failing test**

`harness/tests/test_align_check.py`:

```python
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.align_check import load_bars, check


def _bars_csv(tmp_path):
    p = tmp_path / "bars.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_sec", "open", "high", "low", "close", "volume"])
        w.writerow([1780444800, 2.6, 3.0, 2.5, 2.627, 1000])
        w.writerow([1780459200, 2.627, 2.8, 2.6, 2.7, 900])
    return p


def _ev(ts, px, event="PING", typ=None):
    f = {"typ": typ} if typ else {}
    return {"bar_ts": ts, "px": px, "event": event, "trade": "SYS", "dir": "N", "factors": f}


def test_alignment_pass_and_field_convention(tmp_path):
    bars = load_bars(_bars_csv(tmp_path))
    ok, failures = check([
        _ev(1780444800, 2.627),                       # PING vs close
        _ev(1780444800, 3.0, event="PIV", typ="H"),   # PIV-H vs high
        _ev(1780444800, 2.5, event="PIV", typ="L"),   # PIV-L vs low
    ], bars)
    assert ok == 3 and failures == []


def test_missing_bar_and_price_mismatch_fail(tmp_path):
    bars = load_bars(_bars_csv(tmp_path))
    ok, failures = check([
        _ev(1799999999, 1.0),          # no such bar
        _ev(1780459200, 9.99),         # close is 2.7 -> mismatch
        _ev(1780459200, 2.7007),       # within 0.1% tolerance -> ok
    ], bars)
    assert ok == 1 and len(failures) == 2
    assert "missing bar" in failures[0]["reason"]
    assert "price mismatch" in failures[1]["reason"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `py -3 -m pytest harness/tests/test_align_check.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evaluator'`.

- [ ] **Step 3: Write `harness/evaluator/align_check.py`**

```python
"""Timestamp-alignment check - HARD PRECONDITION of the harness (spec section 10).

Every event's bar must exist in the fetched series with matching price:
PIV typ=H -> bar high, PIV typ=L -> bar low, everything else -> bar close.
Tolerance: relative 0.1% (feed rounding). Mismatches are quarantined to a
sibling *_quarantine.jsonl and reported; exit 1 if any. Never silently included.
"""
import argparse
import csv
import json
from pathlib import Path

TOL = 0.001


def load_bars(csv_path):
    bars = {}
    with Path(csv_path).open() as f:
        for row in csv.DictReader(f):
            bars[int(row["ts_sec"])] = {
                "open": float(row["open"]), "high": float(row["high"]),
                "low": float(row["low"]), "close": float(row["close"]),
            }
    return bars


def _ref_field(ev):
    if ev["event"] == "PIV":
        return "high" if ev["factors"].get("typ") == "H" else "low"
    return "close"


def check(events, bars, tol=TOL):
    ok, failures = 0, []
    for ev in events:
        bar = bars.get(ev["bar_ts"])
        if bar is None:
            failures.append({"event": ev, "reason": f"missing bar {ev['bar_ts']}"})
            continue
        field = _ref_field(ev)
        ref = bar[field]
        if abs(ev["px"] - ref) > tol * max(abs(ref), 1e-12):
            failures.append({"event": ev,
                             "reason": f"price mismatch: px={ev['px']} vs {field}={ref}"})
            continue
        ok += 1
    return ok, failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events_jsonl")
    ap.add_argument("bars_csv")
    args = ap.parse_args()
    events = [json.loads(l) for l in Path(args.events_jsonl).read_text().splitlines() if l.strip()]
    bars = load_bars(args.bars_csv)
    ok, failures = check(events, bars)
    print(f"aligned: {ok}/{len(events)}")
    if failures:
        qpath = Path(args.events_jsonl).with_name(Path(args.events_jsonl).stem + "_quarantine.jsonl")
        qpath.write_text("\n".join(json.dumps(f) for f in failures) + "\n")
        for f in failures[:20]:
            print(f"  FAIL: {f['reason']}")
        print(f"quarantined {len(failures)} -> {qpath}")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify pass**

Run: `py -3 -m pytest harness/tests -v`
Expected: all tests pass (fetch 2, parse 4, align 2).

- [ ] **Step 5: Commit**

```powershell
git add harness; git commit -m "feat(fable): alignment check - hard precondition, quarantine on mismatch (tested)"; git push origin main
```

---

### Task 5: Pine v0.1 — regime engine + system events

**Files:**
- Create: `jamal-fable.pine`

**Pine pitfalls binding on this task:** one `var` declaration per line (multi-declare only persists the first); `max_labels_count=500`; in-place compile does NOT refresh the on-chart study — remove + re-add; create the TV script via editor **Make-a-copy** (NOT `pine_new` — it doesn't persist a tab and can clobber the open script).

- [ ] **Step 1: Write `jamal-fable.pine`** (complete v0.1 source)

```pine
//@version=6
indicator("Jamal Fable v0.1", shorttitle = "JFable0.1", overlay = true,
     max_labels_count = 500, max_lines_count = 500)

// ════════════════ Identity (spec §9 provenance) ════════════════
SCHEMA_V = "1"
SCRIPT_V = "0.1"

// ════════════════ Knobs (§12) — semantic; ALL feed settings_hash ════════════════
pivot_left            = input.int(3,    "Pivot left bars",          minval = 1)
pivot_right           = input.int(3,    "Pivot right bars",         minval = 1)
atr_period            = input.int(14,   "ATR period",               minval = 1)
stop_buffer_atr       = input.float(0.5, "Stop buffer (ATR mult)",  step = 0.1)
rr_min                = input.float(1.5, "Min R to T1 (skip gate)", step = 0.1)
quadrant_window       = input.int(14,   "Quadrant window")
funding_pctile_window = input.int(200,  "Funding pctile window")
wick_pctile_window    = input.int(200,  "Wick pctile window")

// Transport-layer inputs — EXCLUDED from settings_hash (they chunk the label
// budget; they change which events are emitted, never what an event means).
emit_from = input.time(timestamp("2026-04-01T00:00:00+00:00"), "Emit events from (UTC)")
emit_to   = input.time(timestamp("2027-01-01T00:00:00+00:00"), "Emit events to (UTC)")

// ════════════════ settings_hash (deterministic over semantic knobs) ════════════════
f_mix(int acc, int v) => (acc * 31 + v) % 1000003

var int cfg_i = 0
if barstate.isfirst
    int h = 17
    h := f_mix(h, pivot_left)
    h := f_mix(h, pivot_right)
    h := f_mix(h, atr_period)
    h := f_mix(h, math.round(stop_buffer_atr * 1000))
    h := f_mix(h, math.round(rr_min * 1000))
    h := f_mix(h, quadrant_window)
    h := f_mix(h, funding_pctile_window)
    h := f_mix(h, wick_pctile_window)
    cfg_i := h

// ════════════════ ATR (SMA of TR — cross-language reproducible) ════════════════
atr = ta.sma(ta.tr(true), atr_period)

// ════════════════ Pivots ════════════════
ph = ta.pivothigh(high, pivot_left, pivot_right)
pl = ta.pivotlow(low,  pivot_left, pivot_right)
ph_new = not na(ph)
pl_new = not na(pl)

// ════════════════ Engine state (ONE var PER LINE — Pine multi-declare bug) ════════════════
var int   regime     = 0      // 0=CHOP, 1=UP, -1=DOWN
var int   regime_age = 0
var float hl_ref     = na     // UP: most recent confirmed pivot low while live
var float lh_ref     = na     // DOWN: most recent confirmed pivot high while live
var float trend_high = na     // UP: most recent confirmed pivot high
var float trend_low  = na     // DOWN: most recent confirmed pivot low
var float range_hi   = na     // CHOP boundaries (na = undefined side, §3 seeding)
var float range_lo   = na
var float bos_level  = na     // last broken level (touched_bz reference, v0.2)
var float last_ph    = na     // most recent confirmed pivot high, any regime
var float last_pl    = na     // most recent confirmed pivot low, any regime

// ════════════════ Event emission (§9 label transport) ════════════════
in_window = time >= emit_from and time <= emit_to

f_emit(string trade, string event, string dir, int ts_sec, float px, string tail) =>
    if in_window and barstate.isconfirmed
        string txt = "JF|" + SCHEMA_V + "|" + SCRIPT_V + "|" + str.tostring(cfg_i)
             + "|B|" + trade + "|" + event + "|" + dir + "|" + timeframe.period
             + "|" + str.tostring(ts_sec) + "|" + str.tostring(px, "#.########")
             + (tail == "" ? "" : "|" + tail)
        label.new(bar_index, high, txt, style = label.style_label_down,
             color = color.new(color.gray, 85), textcolor = color.new(color.black, 30),
             size = size.tiny)

f_reg_str(int r) => r == 1 ? "U" : r == -1 ? "D" : "C"

// ════════════════ Pivot bookkeeping + SYS|PIV events ════════════════
if ph_new
    last_ph := ph
    if regime == 1
        trend_high := ph
    else if regime == -1
        lh_ref := ph                      // re-anchor included by definition (§3)
    else
        range_hi := na(range_hi) ? ph : math.max(range_hi, ph)
    f_emit("SYS", "PIV", "N", math.round(time[pivot_right] / 1000), ph, "typ=H")

if pl_new
    last_pl := pl
    if regime == -1
        trend_low := pl
    else if regime == 1
        hl_ref := pl                      // re-anchor included by definition (§3)
    else
        range_lo := na(range_lo) ? pl : math.min(range_lo, pl)
    f_emit("SYS", "PIV", "N", math.round(time[pivot_right] / 1000), pl, "typ=L")

// ════════════════ State machine (§3, explicit FSM) — confirmed body closes only ════════════════
int prev_regime = regime
if barstate.isconfirmed
    if regime == 0
        if not na(range_hi) and close > range_hi          // CHOP→UP = BOS(up)
            regime     := 1
            bos_level  := range_hi
            hl_ref     := last_pl       // seed: most recent confirmed pivot low (engine detail #1)
            trend_high := range_hi      // seed: broken boundary (avoids instant-BOS artifact)
        else if not na(range_lo) and close < range_lo     // CHOP→DOWN
            regime    := -1
            bos_level := range_lo
            lh_ref    := last_ph
            trend_low := range_lo
    else if regime == 1
        if not na(hl_ref) and close < hl_ref              // CHoCH: UP→CHOP (never UP→DOWN)
            regime   := 0
            range_hi := trend_high      // seed opposite boundary w/ dead trend's extreme
            range_lo := na              // broken side undefined until first post-death pivot
        else if not na(trend_high) and close > trend_high
            bos_level := trend_high     // continuation BOS — no state change
    else  // regime == -1
        if not na(lh_ref) and close > lh_ref              // CHoCH: DOWN→CHOP
            regime   := 0
            range_lo := trend_low
            range_hi := na
        else if not na(trend_low) and close < trend_low
            bos_level := trend_low

    if regime != prev_regime
        regime_age := 0
        f_emit("SYS", "PING", "N", math.round(time / 1000), close,
             "reg=" + f_reg_str(regime) + "|age=0")
    else
        regime_age += 1

// ════════════════ Rendering (§11 — minimal by design) ════════════════
bgcolor(regime == 1 ? color.new(color.green, 88) : regime == -1 ? color.new(color.red, 88) : na)
plot(regime == 1  ? hl_ref   : na, "HL_ref",    color.new(color.green,  0), 2, plot.style_linebr)
plot(regime == -1 ? lh_ref   : na, "LH_ref",    color.new(color.red,    0), 2, plot.style_linebr)
plot(regime == 0  ? range_hi : na, "Range high", color.new(color.orange, 0), 1, plot.style_linebr)
plot(regime == 0  ? range_lo : na, "Range low",  color.new(color.orange, 0), 1, plot.style_linebr)

var table vt = table.new(position.top_right, 1, 1)
if barstate.islast
    table.cell(vt, 0, 0, "Jamal Fable v" + SCRIPT_V + " · schema " + SCHEMA_V + " · cfg " + str.tostring(cfg_i),
         text_color = color.white, bgcolor = color.new(color.black, 20), text_size = size.small)
```

- [ ] **Step 2: Create the TV script "Jamal Fable" via Make-a-copy** (memory `tv-new-script-via-copy` — NOT `pine_new`)

1. `mcp__tradingview__ui_mouse_click` on the editor script-title dropdown (~x891, y79).
2. Click **"Make a copy…"**; in the dialog click the name field, Ctrl+A, type `Jamal Fable`, click **"Make copy"**.
3. `mcp__tradingview__pine_open` with `"Jamal Fable"` to confirm the editor is on it.

- [ ] **Step 3: Inject + compile**

1. `mcp__tradingview__pine_set_source` with the full Step-1 source.
2. `mcp__tradingview__pine_smart_compile`; on errors, `pine_get_errors`, fix in the local file first, re-inject. Keep `jamal-fable.pine` on disk identical to what compiles.

- [ ] **Step 4: Add to chart and verify visually** (BTCUSDT.P, 4H)

1. `chart_set_symbol BTCUSDT.P`, `chart_set_timeframe 240`.
2. Add via editor "Add to chart" (~x1069, y79). If already present from a retry: remove + re-add (in-place compile doesn't refresh the study).
3. `capture_screenshot` — verify: green/red tint alternating with neutral gaps; HL_ref steps under uptrends; orange range lines in chop; gray event labels; version cell "Jamal Fable v0.1 · schema 1 · cfg NNNNNN".
4. `data_get_pine_labels` with `study_filter="Jamal Fable"` — verify JF strings present and well-formed.
5. Eyeball 2–3 regime transitions against §3: UP→CHOP only via body close below HL_ref; no UP→DOWN direct flip; broken side's range line absent until a post-death pivot confirms.

- [ ] **Step 5: Commit**

```powershell
git add jamal-fable.pine; git commit -m "feat(fable): v0.1 Pine - regime FSM + SYS|PING/PIV event emission + minimal render"; git push origin main
```

---

### Task 6: End-to-end pipe run (pins 1 + 2)

**Files:**
- Create: `harness/events/raw/BTCUSDT.P_240_<date>.json` (raw harvest dump)
- Create: `harness/events/BTCUSDT.P_240_v1_s0.1_c*_B.jsonl` (parser output)

- [ ] **Step 1: Harvest** — `data_get_pine_labels` (`study_filter="Jamal Fable"`), save the raw JSON verbatim to `harness/events/raw/BTCUSDT.P_240_2026-06-09.json` via the Write tool.

- [ ] **Step 2: Parse**

Run: `py -3 harness/harvest/parse_labels.py harness/events/raw/BTCUSDT.P_240_2026-06-09.json --symbol BTCUSDT.P`
Expected: `new events: N; malformed: 0` (N ≈ 40–80 for the default Apr-01→now window), one `BTCUSDT.P_240_v1_s0.1_c*_B.jsonl` file. **Pin 2 check:** the filename embeds schema/script/cfg/src — provenance grouping visible on disk.

- [ ] **Step 3: Align**

Run: `py -3 harness/evaluator/align_check.py harness/events/BTCUSDT.P_240_v1_s0.1_c<CFG>_B.jsonl harness/bars/binanceusdm_BTCUSDT_4h.csv`
Expected: `aligned: N/N`, exit 0. **Pin 1 passes.** If PIV events fail on price: check the pivot-bar timestamp math (`time[pivot_right]`) before touching tolerance — misalignment is a bug, not noise.

- [ ] **Step 4: Idempotency** — re-run Step 2 unchanged.

Expected: `new events: 0`. **Pin 3 (dedup) passes.**

- [ ] **Step 5: Commit**

```powershell
git add harness/events; git commit -m "feat(fable): first end-to-end pipe run - harvest/parse/align all green (pins 1-2 + dedup)"; git push origin main
```

---

### Task 7: Chunked-harvest path (pin 3 complete)

- [ ] **Step 1: Shift the emit window one chunk older** — `mcp__tradingview__indicator_set_inputs` on "Jamal Fable": `Emit events from (UTC)` = 2026-02-01, `Emit events to (UTC)` = 2026-04-01. Remove + re-add is NOT needed for input changes (inputs apply live); confirm labels moved via screenshot.

- [ ] **Step 2: Harvest chunk 2** → save raw to `harness/events/raw/BTCUSDT.P_240_2026-06-09_chunk2.json`, parse with the same `--symbol BTCUSDT.P`.
Expected: `new events: M; malformed: 0`, events MERGED into the **same** provenance file (same cfg — transport window excluded from hash). This is the design's point: chunks of one config pool freely.

- [ ] **Step 3: Extend bars + re-align** — re-run `fetch_bars.py` with `--since 2026-02-01`, then `align_check.py` on the merged JSONL.
Expected: `aligned: (N+M)/(N+M)`, exit 0. **Pin 3 fully passes.**

- [ ] **Step 4: Restore the emit window** to 2026-04-01 → 2027-01-01 via `indicator_set_inputs`.

- [ ] **Step 5: Commit**

```powershell
git add harness; git commit -m "feat(fable): chunked harvest exercised - same-cfg chunks merge, full alignment green (pin 3)"; git push origin main
```

---

### Task 8: Spec amendment, CHANGELOG, checkpoint

- [ ] **Step 1: Amend the spec** (`docs/superpowers/specs/2026-06-09-jamal-fable-design.md`): in §9 after the label-format block and in §12 under the knob table, add: *"Harvest-window inputs (`emit_from`/`emit_to`) are transport-layer and excluded from `settings_hash`: they change which events are emitted, never what an event means. Chunked harvests of one config pool freely."* Also append the two §3 engine-detail decisions (HL_ref/trend_high seeding at regime entry) to the spec's §3 with a "decided at implementation, surfaced at v0.1 checkpoint" note.

- [ ] **Step 2: CHANGELOG** — add a `# ========================= JAMAL FABLE — TRADE-FIRST SIGNAL + HARNESS (BUILD LOG) =========================` section at the end of `CHANGELOG.md` with a v0.1 entry: what was built (engine FSM, SYS events, parser/fetcher/align), pin results with the actual aligned counts, the two seeding decisions, and the spec amendment.

- [ ] **Step 3: Commit + push**

```powershell
git add CHANGELOG.md docs; git commit -m "docs(fable): v0.1 build log + spec amendment (transport-window hash exclusion, seeding details)"; git push origin main
```

- [ ] **Step 4: USER CHECKPOINT (blocking).** Present on the live chart: regime tint quality on BTCUSDT.P 4H (and spot-check NEARUSDT.P), the two seeding decisions, and the pin results. **Do not start the v0.2 plan until the user approves the engine's chart behavior** — every detector consumes it; if the regime labels look wrong here, v0.2+ inherits the error.

---

## Roadmap after this plan (each gets its own plan, written after the prior checkpoint)

- **v0.2:** Trade #1 detector (ARM/ENT/SKP/CXL + §7 snapshot levels in ENT) + Python pivot-parity check + chart quizzes. Acceptance: parity bit-exact, quiz convergence.
- **v0.3:** Trade #2 A+B + §4 coincidence rule end-to-end.
- **v0.4:** Derivatives factors (`oi_delta_setup`, `oi_trigger_dir`, `quadrant`, `funding_pctile`), null-safe.
- **Backfill campaign:** 4-symbol basket, episode simulation, evaluator report.
- **Stage 2:** webhook listener (`src=L`), only after a rule-set freezes.
```
