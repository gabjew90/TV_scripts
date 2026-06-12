"""Single-use FVG study: would 'a zone is consumed by its first wick-through'
improve OSF? For every OSF ENT (s0.7.1, post-Feb warm-up), re-simulate the zone
lifecycle, find the swept zone, and flag whether any earlier bar since the
zone's birth had already wicked through its near edge. Compare first-touch vs
re-touch performance (independent walk)."""
import glob
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.episodes import walk_episode
from evaluator.report import load_bars, BARS_MAP, HARNESS

first, retouch = [], []
re_skp = fr_skp = 0
for sym, bf in BARS_MAP.items():
    bars_l = load_bars(HARNESS / "bars" / bf)
    seq = [b[0] for b in bars_l]
    idx = {t: i for i, t in enumerate(seq)}
    O = {b[0]: b for b in bars_l}

    # zone lifecycle (same rules as live): alive list state at START of each bar
    alive_at = {}
    bull, bear = [], []          # (top, bot, born_idx)
    for i, t in enumerate(seq):
        alive_at[t] = ([tuple(z) for z in bull], [tuple(z) for z in bear])
        _, h, l, c = O[t][1], O[t][2], O[t][3], O[t][4]
        h, l, c = O[t][2], O[t][3], O[t][4]
        bull = [z for z in bull if c >= z[1]]
        bear = [z for z in bear if c <= z[0]]
        if i >= 2:
            if l > O[seq[i - 2]][2]:
                bull.append((l, O[seq[i - 2]][2], i))
                if len(bull) > 20:
                    bull.pop(0)
            if h < O[seq[i - 2]][3]:
                bear.append((O[seq[i - 2]][3], h, i))
                if len(bear) > 20:
                    bear.pop(0)

    for f in glob.glob(str(HARNESS / "events" / f"{sym}_*_s0.7.1_*.jsonl")):
        for line in open(f):
            e = json.loads(line)
            if e["trade"] != "OSF" or e["event"] not in ("ENT", "SKP"):
                continue
            if e["factors"].get("rsn") == "1d":
                continue
            ts = e["bar_ts"]
            if ts < 1769904000:           # warm-up (zone birth unknown)
                continue
            lvl = float(e["factors"]["lvl"])
            zones = alive_at[ts][0] if e["dir"] == "L" else alive_at[ts][1]
            zone = None
            for z in zones:
                edge = z[0] if e["dir"] == "L" else z[1]
                if abs(lvl - edge) <= 1e-6 * max(edge, 1e-9):
                    zone = z
                    break
            if zone is None:
                continue
            born = zone[2]
            i_ev = idx[ts]
            touched = False
            for j in range(born + 1, i_ev):
                if e["dir"] == "L" and O[seq[j]][3] < zone[0]:
                    touched = True
                    break
                if e["dir"] == "S" and O[seq[j]][2] > zone[1]:
                    touched = True
                    break
            if e["event"] == "SKP":
                if touched:
                    re_skp += 1
                else:
                    fr_skp += 1
                continue
            ep = walk_episode(e, bars_l)
            if ep.get("drop_reason") or ep["exit_code"] not in ("t1_hit", "stop_out"):
                continue
            ep["_align"] = e["factors"]["align"]
            (retouch if touched else first).append(ep)


def show(name, g):
    if not g:
        print(f"{name}: n=0")
        return
    w = sum(1 for e in g if e["exit_code"] == "t1_hit")
    r = sum(e["r"] for e in g) / len(g)
    print(f"{name}: n={len(g):3d}  win {100*w/len(g):3.0f}%  avgR {r:+.2f}")
    for al in ("W", "N", "A"):
        s = [e for e in g if e["_align"] == al]
        if s:
            w2 = sum(1 for e in s if e["exit_code"] == "t1_hit")
            print(f"    align={al}: n={len(s):3d}  win {100*w2/len(s):3.0f}%  avgR {sum(e['r'] for e in s)/len(s):+.2f}")


print("OSF entries by zone-touch history (post-Feb, independent walk):")
show("FIRST touch of the zone", first)
show("RE-touch (zone wicked before)", retouch)
print(f"\nskips: first-touch {fr_skp}, re-touch {re_skp} (volume context)")
