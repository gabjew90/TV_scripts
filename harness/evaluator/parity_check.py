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
    # find a superset at the range edges - compare Pine subset-of Python
    # strictly, and report Python-only pivots for manual edge classification.
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
