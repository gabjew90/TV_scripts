"""Prev-candle-sweep filter study: does requiring the entry bar to ALSO take
out the immediate previous candle's extreme (long: low < low[1]; short:
high > high[1]) improve OSD (and the other OS classes)?"""
import glob
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.episodes import walk_episode
from evaluator.report import load_bars, BARS_MAP, HARNESS

groups = {}
for sym, bf in BARS_MAP.items():
    bars_l = load_bars(HARNESS / "bars" / bf)
    idx = {b[0]: i for i, b in enumerate(bars_l)}
    for f in glob.glob(str(HARNESS / "events" / f"{sym}_*_s0.7.1_*.jsonl")):
        for line in open(f):
            e = json.loads(line)
            if e["trade"] not in ("OSD", "OSW", "OSF") or e["event"] != "ENT":
                continue
            i = idx.get(e["bar_ts"])
            if i is None or i == 0:
                continue
            b, pb = bars_l[i], bars_l[i - 1]
            swept_prev = (b[3] < pb[3]) if e["dir"] == "L" else (b[2] > pb[2])
            ep = walk_episode(e, bars_l)
            if ep.get("drop_reason") or ep["exit_code"] not in ("t1_hit", "stop_out"):
                continue
            ep["_align"] = e["factors"]["align"]
            groups.setdefault((e["trade"], swept_prev), []).append(ep)


def show(label, g):
    if not g:
        print(f"  {label:34s} n=  0")
        return
    w = sum(1 for x in g if x["exit_code"] == "t1_hit")
    r = sum(x["r"] for x in g) / len(g)
    print(f"  {label:34s} n={len(g):3d}  win {100*w/len(g):3.0f}%  avgR {r:+.2f}")


for tr in ("OSD", "OSW", "OSF"):
    print(f"{tr}:")
    yes = groups.get((tr, True), [])
    no = groups.get((tr, False), [])
    show("ALSO swept prev candle extreme", yes)
    show("did NOT (daily level only)", no)
    if tr == "OSD":
        for al in ("W", "N", "A"):
            show(f"  swept-prev & align={al}", [e for e in yes if e["_align"] == al])
            show(f"  not-swept & align={al}", [e for e in no if e["_align"] == al])
    print()
