import glob
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.episodes import walk_episode
from evaluator.report import load_bars, BARS_MAP, HARNESS

rows = {}
for sym, bf in BARS_MAP.items():
    bars = load_bars(HARNESS / "bars" / bf)
    for f in glob.glob(str(HARNESS / "events" / f"{sym}_*_s0.7.1_*.jsonl")):
        for line in open(f):
            e = json.loads(line)
            if e["trade"] in ("OSF", "OSD", "OSW") and e["event"] == "ENT":
                ep = walk_episode(e, bars)
                if not ep.get("drop_reason") and ep["exit_code"] in ("t1_hit", "stop_out"):
                    k = (e["trade"], e["factors"]["align"])
                    rows.setdefault(k, []).append(ep)
for k in sorted(rows):
    g = rows[k]
    w = sum(1 for e in g if e["exit_code"] == "t1_hit")
    r = sum(e["r"] for e in g) / len(g)
    print(f"{k[0]} align={k[1]}: n={len(g):3d}  win {100*w/len(g):3.0f}%  avgR {r:+.2f}")
