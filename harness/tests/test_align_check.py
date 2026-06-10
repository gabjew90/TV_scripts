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


def test_piv_without_typ_quarantines(tmp_path):
    bars = load_bars(_bars_csv(tmp_path))
    ok, failures = check([_ev(1780444800, 3.0, event="PIV")], bars)  # no typ -> malformed
    assert ok == 0 and len(failures) == 1
    assert "malformed PIV" in failures[0]["reason"]
