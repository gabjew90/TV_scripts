"""Fallback-target study: every with-trend sweep skip whose structural target
was already overtaken (SKP rsn=rr, rt1=na, tgt=tex for OS* / all 2A) gets a
hypothetical CALENDAR fallback target (shorts: nearest of prev-day/week low
BELOW entry; longs: mirror above), re-gated at 1.5R, and walked. Answers:
does unlocking the waterfall blind-spot pay?"""
import csv
import glob
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.episodes import walk_episode
from evaluator.report import load_bars, BARS_MAP, HARNESS

total_na = 0
no_fallback = 0
sub_gate = 0
unlocked = []
by_tgt = {}
for sym, bf in BARS_MAP.items():
    bars_l = load_bars(HARNESS / "bars" / bf)
    bars = {b[0]: b for b in bars_l}

    def pextreme(start, end, kind):
        vals = []
        t = start
        while t < end:
            if t not in bars:
                return None
            vals.append(bars[t][3] if kind == "lo" else bars[t][2])
            t += 14400
        return min(vals) if kind == "lo" else max(vals)

    for f in glob.glob(str(HARNESS / "events" / f"{sym}_*_s0.7.1_*.jsonl")):
        for line in open(f):
            e = json.loads(line)
            fa = e["factors"]
            is_os = e["trade"] in ("OSD", "OSW", "OSF")
            if e["event"] != "SKP" or fa.get("rsn") != "rr" or fa.get("rt1") != "na":
                continue
            if is_os and fa.get("tgt") != "tex":
                continue
            if not is_os and e["trade"] != "2A":
                continue
            total_na += 1
            ts = e["bar_ts"]
            px = float(e["px"])
            stop = float(fa["stop"]) if fa.get("stop") not in (None, "na") else None
            if stop is None:
                continue
            d = datetime.fromtimestamp(ts, tz=timezone.utc)
            day0 = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
            wk0 = day0 - d.weekday() * 86400
            pdl_ = pextreme(day0 - 86400, day0, "lo")
            pdh_ = pextreme(day0 - 86400, day0, "hi")
            pwl_ = pextreme(wk0 - 7 * 86400, wk0, "lo")
            pwh_ = pextreme(wk0 - 7 * 86400, wk0, "hi")
            if e["dir"] == "S":
                cands = [(v, n) for v, n in ((pdl_, "pdl"), (pwl_, "pwl")) if v is not None and v < px]
                tgt = max(cands) if cands else None          # nearest BELOW
            else:
                cands = [(v, n) for v, n in ((pdh_, "pdh"), (pwh_, "pwh")) if v is not None and v > px]
                tgt = min(cands) if cands else None          # nearest ABOVE
            if tgt is None:
                no_fallback += 1
                continue
            tv, tname = tgt
            risk = (stop - px) if e["dir"] == "S" else (px - stop)
            rew = (px - tv) if e["dir"] == "S" else (tv - px)
            if risk <= 0 or rew / risk < 1.5:
                sub_gate += 1
                continue
            ev2 = dict(e)
            ev2["factors"] = dict(fa)
            ev2["factors"]["t1"] = str(tv)
            ev2["factors"]["rt1"] = f"{rew/risk:.2f}"
            ep = walk_episode(ev2, bars_l)
            if not ep.get("drop_reason") and ep["exit_code"] in ("t1_hit", "stop_out"):
                unlocked.append(ep)
                by_tgt.setdefault(tname, []).append(ep)

print(f"with-trend target-overtaken skips: {total_na}")
print(f"  no reachable calendar fallback:  {no_fallback}  (true abyss - stays skipped)")
print(f"  fallback exists but <1.5R:       {sub_gate}  (stays skipped)")
print(f"  UNLOCKED (fallback >=1.5R):      {len(unlocked)}")
if unlocked:
    w = sum(1 for e in unlocked if e["exit_code"] == "t1_hit")
    r = sum(e["r"] for e in unlocked) / len(unlocked)
    print(f"  unlocked performance: win {100*w/len(unlocked):.0f}%  avgR {r:+.2f}")
    for k, g in sorted(by_tgt.items()):
        w2 = sum(1 for e in g if e["exit_code"] == "t1_hit")
        print(f"    via {k}: n={len(g)}  win {100*w2/len(g):.0f}%  avgR {sum(e['r'] for e in g)/len(g):+.2f}")
