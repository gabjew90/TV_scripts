"""Pooled multi-symbol SFP-of-major-low study (deep _sfp_*_4h.csv, ~12mo each).
Same definitions as sfp_study.py; pools events across symbols for a real-n verdict."""
import csv
import glob
import statistics
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]


def load(p):
    rows = [(int(r["ts_sec"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
            for r in csv.DictReader(open(p))]
    return rows


def sfp_events(rows, L, target_R=2.0):
    h = [r[2] for r in rows]
    lo = [r[3] for r in rows]
    c = [r[4] for r in rows]
    N = len(rows)

    def atr(i, p=14):
        if i < p:
            return None
        return sum(max(h[j]-lo[j], abs(h[j]-c[j-1]), abs(lo[j]-c[j-1]))
                   for j in range(i-p+1, i+1)) / p

    def is_pl(i):
        if i-L < 0 or i+L >= N:
            return False
        return all(lo[i] <= lo[j] for j in range(i-L, i+L+1) if j != i) and lo[i] < lo[i-1] and lo[i] < lo[i+1]

    pivots = {}
    for i in range(L, N-L):
        if is_pl(i):
            pivots.setdefault(i+L, []).append(lo[i])
    active, evs = [], []
    for i in range(N):
        active += pivots.get(i, [])
        a = atr(i)
        if a and active:
            sw = [pv for pv in active if lo[i] < pv and c[i] > pv]
            if sw:
                lvl = min(sw); entry = c[i]; stop = lo[i]-0.5*a; R = entry-stop
                if R > 0:
                    e = {"i": i, "entry": entry, "stop": stop, "R": R,
                         "swd": (lvl-lo[i])/a, "rcl": (c[i]-lvl)/a, "out": "open", "mfe_r": 0.0}
                    best = entry; tgt = entry+target_R*R
                    for j in range(i+1, N):
                        best = max(best, h[j]); e["mfe_r"] = (best-entry)/R
                        if lo[j] <= stop:
                            e["out"] = "stop"; break
                        if h[j] >= tgt:
                            e["out"] = "win"; break
                    evs.append(e)
        active = [pv for pv in active if c[i] >= pv]
    return evs


def summ(label, evs):
    if not evs:
        print(f"  {label:28s} n=0"); return
    closed = [e for e in evs if e["out"] in ("win", "stop")]
    w = sum(1 for e in closed if e["out"] == "win")
    expR = (w*2.0-(len(closed)-w))/len(closed) if closed else 0
    r1 = sum(1 for e in evs if e["mfe_r"] >= 1.0)/len(evs)
    r2 = sum(1 for e in evs if e["mfe_r"] >= 2.0)/len(evs)
    print(f"  {label:28s} n={len(evs):3d}  2:1win {100*w/len(closed) if closed else 0:3.0f}% "
          f"expR{expR:+.2f}  medMFE {statistics.median(e['mfe_r'] for e in evs):.2f}R  "
          f"reach1R {100*r1:.0f}% 2R {100*r2:.0f}%")


files = sorted(glob.glob(str(HARNESS / "bars" / "_sfp_*_4h.csv")))
print(f"symbols: {[Path(f).name.split('_')[2] for f in files]}\n")
for L in (24, 48):
    allev = []
    for f in files:
        allev += sfp_events(load(f), L)
    print(f"=== MAJOR LOW = pivot({L},{L}), {len(files)} symbols pooled, ~12mo ===")
    summ("all SFP-reclaim longs", allev)
    summ("deep sweep swd>=0.5", [e for e in allev if e["swd"] >= 0.5])
    summ("shallow swd<0.5", [e for e in allev if e["swd"] < 0.5])
    summ("strong reclaim rcl>=0.5", [e for e in allev if e["rcl"] >= 0.5])
    summ("quiet: swd<0.3 & rcl>=0.3", [e for e in allev if e["swd"] < 0.3 and e["rcl"] >= 0.3])
    print()
