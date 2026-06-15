"""SFP-of-a-major-low study (user-requested 2026-06-15, the Jun-5 BTC miss).

QUESTION: the instrument missed a clean swing-failure (sweep + reclaim) of a
major low because (a) it only tracks the last-5 4H pivot lows + prev D/W, so an
older/major low is off-radar, and (b) such a long is counter-trend. Is "SFP of a
MAJOR low" a real edge that a longer-memory level class would capture?

METHOD (pure bars, no engine): identify MAJOR swing lows = pivot(L,L) lows
(lowest in +/- L bars). A major low is ACTIVE from its confirmation bar until a
bar CLOSES below it (genuine breakdown). An SFP-reclaim long fires on a bar whose
LOW < an active major low AND CLOSE > it (swept liquidity, reclaimed). Deepest
swept level wins. Entry=close, stop=bar low - 0.5*ATR14, R=entry-stop. Walk
forward: MFE in R, and a 2:1 trade (target +2R, stop -1R, stop-first on ambiguous).
Slice by sweep depth, reclaim strength, lookback L. Mirror not done (longs only,
that's the asked pattern).

Usage: py sfp_study.py <bars.csv> [L]
"""
import csv
import statistics
import sys

BARS = sys.argv[1] if len(sys.argv) > 1 else "harness/bars/_sfp_BTCUSDT_4h.csv"
rows = [(int(r["ts_sec"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
        for r in csv.DictReader(open(BARS))]
ts = [r[0] for r in rows]
o = [r[1] for r in rows]
h = [r[2] for r in rows]
lo = [r[3] for r in rows]
c = [r[4] for r in rows]
N = len(rows)


def atr(i, p=14):
    if i < p:
        return None
    s = 0.0
    for j in range(i - p + 1, i + 1):
        s += max(h[j] - lo[j], abs(h[j] - c[j - 1]), abs(lo[j] - c[j - 1]))
    return s / p


def is_pivot_low(i, L):
    if i - L < 0 or i + L >= N:
        return False
    return all(lo[i] <= lo[j] for j in range(i - L, i + L + 1) if j != i) and \
        all(lo[i] < lo[j] for j in (i - 1, i + 1))


def run(L, target_R=2.0):
    # active major lows: list of (price, born_idx); confirmed at idx+L
    events = []
    active = []          # (price, born_idx)
    confirmed_upto = {}   # pivot price by confirmation idx
    # precompute pivots
    pivots = {}           # confirm_idx -> price
    for i in range(L, N - L):
        if is_pivot_low(i, L):
            pivots.setdefault(i + L, []).append(lo[i])
    for i in range(N):
        # add pivots confirmed at i
        for pv in pivots.get(i, []):
            active.append(pv)
        a = atr(i)
        if a and active:
            swept = [pv for pv in active if lo[i] < pv and c[i] > pv]   # SFP reclaim
            if swept:
                lvl = min(swept)                                       # deepest
                entry = c[i]
                stop = lo[i] - 0.5 * a
                R = entry - stop
                if R > 0:
                    swd = (lvl - lo[i]) / a                            # wick past level, ATR
                    rcl = (c[i] - lvl) / a                             # reclaim above level, ATR
                    events.append({"i": i, "ts": ts[i], "entry": entry, "stop": stop,
                                   "R": R, "lvl": lvl, "swd": swd, "rcl": rcl})
        # retire majors killed by a CLOSE below
        active = [pv for pv in active if c[i] >= pv]

    # walk each forward: MFE, and 2:1 outcome
    for e in events:
        best = e["entry"]
        e["mfe_r"] = 0.0
        e["out"] = "open"
        tgt = e["entry"] + target_R * e["R"]
        for j in range(e["i"] + 1, N):
            best = max(best, h[j])
            e["mfe_r"] = (best - e["entry"]) / e["R"]
            stop_hit = lo[j] <= e["stop"]
            tgt_hit = h[j] >= tgt
            if stop_hit and tgt_hit:
                e["out"] = "stop"; break          # ambiguous -> stop-first
            if stop_hit:
                e["out"] = "stop"; break
            if tgt_hit:
                e["out"] = "win"; break
    return events


def summ(label, evs):
    closed = [e for e in evs if e["out"] in ("win", "stop")]
    if not closed:
        print(f"  {label:30s} n={len(evs):3d} (no closed)")
        return
    w = sum(1 for e in closed if e["out"] == "win")
    expR = (w * 2.0 - (len(closed) - w) * 1.0) / len(closed)
    medmfe = statistics.median(e["mfe_r"] for e in evs)
    r1 = sum(1 for e in evs if e["mfe_r"] >= 1.0) / len(evs)
    r15 = sum(1 for e in evs if e["mfe_r"] >= 1.5) / len(evs)
    r2 = sum(1 for e in evs if e["mfe_r"] >= 2.0) / len(evs)
    print(f"  {label:30s} n={len(evs):3d}  2:1win {100*w/len(closed):3.0f}% expR{expR:+.2f}  "
          f"medMFE {medmfe:.2f}R  reach1R {100*r1:.0f}% 1.5R {100*r15:.0f}% 2R {100*r2:.0f}%")


for L in (24, 48):
    evs = run(L)
    print(f"=== MAJOR LOW = pivot({L},{L})  [~{L*4/24:.0f}-day swing low] ===")
    summ("all SFP-reclaim longs", evs)
    summ("  deep sweep swd>=0.5", [e for e in evs if e["swd"] >= 0.5])
    summ("  shallow swd<0.5", [e for e in evs if e["swd"] < 0.5])
    summ("  strong reclaim rcl>=0.5", [e for e in evs if e["rcl"] >= 0.5])
    summ("  weak reclaim rcl<0.5", [e for e in evs if e["rcl"] < 0.5])
    import datetime
    for e in evs:
        d = datetime.datetime.utcfromtimestamp(e["ts"]).strftime("%Y-%m-%d %H:%M")
        if 1780531200 <= e["ts"] < 1780790400:
            print(f"    >>> JUN5-AREA SFP: {d} lvl={e['lvl']:.0f} swd={e['swd']:.2f} "
                  f"rcl={e['rcl']:.2f} -> {e['out']} mfe={e['mfe_r']:.2f}R")
    print()
