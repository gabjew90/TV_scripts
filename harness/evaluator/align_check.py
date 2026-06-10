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
    """PIV typ=H -> high, typ=L -> low, anything else on a PIV is malformed
    (quarantine, never silently align against an arbitrary field); else close."""
    if ev["event"] == "PIV":
        typ = ev["factors"].get("typ")
        if typ == "H":
            return "high"
        if typ == "L":
            return "low"
        return None
    return "close"


def check(events, bars, tol=TOL):
    ok, failures = 0, []
    for ev in events:
        bar = bars.get(ev["bar_ts"])
        if bar is None:
            failures.append({"event": ev, "reason": f"missing bar {ev['bar_ts']}"})
            continue
        field = _ref_field(ev)
        if field is None:
            failures.append({"event": ev, "reason": "malformed PIV: missing/bad typ"})
            continue
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
