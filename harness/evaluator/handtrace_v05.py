"""v0.5 hand-traces: recompute OS event levels (stop/swd/rt1/t1=linreg anchor,
level identity, roll stretch gate) from independent ccxt bars and compare to
the emitted tails at displayed precision. The four spec'd cases on NEAR:
piv ENT, roll ENT, stacked n_lvls>=2, oco=1 bar."""
import csv
import json
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
BARS = [(int(r["ts_sec"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
        for r in csv.DictReader(open(HARNESS / "bars" / "binanceusdm_NEARUSDT_4h.csv"))]
IDX = {b[0]: i for i, b in enumerate(BARS)}
EVS = {}
for line in open(HARNESS / "events" / "NEARUSDT.P_240_v1_s0.5.0_c209091_B.jsonl"):
    e = json.loads(line)
    EVS.setdefault((e["bar_ts"], e["trade"], e["event"], e["dir"]), e)

PIVL, PIVR, ATRP, LRW, ROLLK, OSM, STOPB = 3, 3, 14, 50, 20, 5, 0.5


def atr14(i):
    trs = []
    for j in range(i - ATRP + 1, i + 1):
        hi, lo, pc = BARS[j][2], BARS[j][3], BARS[j - 1][4]
        trs.append(max(hi - lo, abs(hi - pc), abs(lo - pc)))
    return sum(trs) / ATRP


def linreg_end(i):
    """LSMA endpoint over LRW closes ending at bar i (Pine ta.linreg(close,LRW,0) at i)."""
    ys = [BARS[j][4] for j in range(i - LRW + 1, i + 1)]
    n = LRW
    xs = list(range(n))
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    intercept = (sy - slope * sx) / n
    return intercept + slope * (n - 1)


def pivots_before(i, kind):
    """Confirmed pivot lows/highs (3,3 strict) known as of bar i, oldest->newest."""
    out = []
    for c in range(PIVL + PIVR, i + 1):       # c = confirmation bar index
        p = c - PIVR
        v = BARS[p][3] if kind == "L" else BARS[p][2]
        neigh = [BARS[j][3] if kind == "L" else BARS[j][2]
                 for j in range(p - PIVL, p + PIVR + 1) if j != p]
        ok = all(v < x for x in neigh) if kind == "L" else all(v > x for x in neigh)
        if ok:
            out.append(v)
    return out[-5:]


def f2(x):
    return f"{x:.2f}".rstrip("0").rstrip(".") or "0"


fails = 0


def check(name, got, want):
    """Numeric comparison, rel tol 1e-6 (display formats differ between Pine and Python)."""
    global fails
    g, w = float(got), float(want)
    ok = abs(g - w) <= 1e-6 * max(abs(w), 1e-9)
    if not ok:
        fails += 1
    print(f"  {name}: emitted={want} recomputed={got} {'OK' if ok else '<-- MISMATCH'}")


def trace(ts, trade, event, d, expect_src):
    e = EVS[(ts, trade, event, d)]
    i = IDX[ts]
    o, h, l, c = BARS[i][1:5]
    a = atr14(i)
    f = e["factors"]
    print(f"\n{event} {d} @ {ts} (lvl_src={f['lvl_src']}, n_lvls={f['n_lvls']}, oco={f['oco']}) px={e['px']}")
    assert f["lvl_src"] == expect_src, f"expected {expect_src}"
    lvl = float(f["lvl"])
    # 1. the emitted level must be the DEEPEST swept-reclaimed candidate
    cands = []
    for pv in pivots_before(i - 1, "L" if d == "L" else "H"):
        if (d == "L" and l < pv and c > pv) or (d == "S" and h > pv and c < pv):
            cands.append(("piv", pv))
    if d == "L":
        roll = min(BARS[j][3] for j in range(i - ROLLK, i))
        if l < roll and c > roll:
            osm = min((BARS[j][4] - linreg_end(j - 1)) / atr14(j) for j in range(i - OSM + 1, i + 1))
            if osm <= -1.5:
                cands.append(("roll", roll))
        deepest = min(cands, key=lambda x: x[1]) if cands else None
    else:
        roll = max(BARS[j][2] for j in range(i - ROLLK, i))
        if h > roll and c < roll:
            osm = max((BARS[j][4] - linreg_end(j - 1)) / atr14(j) for j in range(i - OSM + 1, i + 1))
            if osm >= 1.5:
                cands.append(("roll", roll))
        deepest = max(cands, key=lambda x: x[1]) if cands else None
    # (pdl/pdh/pwl/pwh candidates not recomputed here — daily/weekly closed-candle
    #  extremes need the D/W series; the piv+roll classes cover the traced cases)
    if deepest:
        check("deepest piv/roll candidate", deepest[1], lvl)
    # 2. stop / swd / rt1 / t1 anchor
    stp = l - STOPB * a if d == "L" else h + STOPB * a
    check("stop", stp, f["stop"])
    swd = (lvl - l) / a if d == "L" else (h - lvl) / a
    check("swd", round(swd, 2), f["swd"])
    t1 = linreg_end(i - 1)
    check("t1(anchor)", round(t1, 8), f["t1"])
    rt1 = (t1 - c) / (c - stp) if d == "L" else (c - t1) / (stp - c)
    check("rt1", round(rt1, 2), f["rt1"])


trace(1775203200, "OS", "ENT", "S", "piv")     # piv short ENT (chop, align=N)
trace(1775289600, "OS", "ENT", "S", "roll")    # roll short ENT (against-regime, stretch-gated)
trace(1775980800, "OS", "ENT", "L", "piv")     # stacked n_lvls=2 + oco=1 long ENT
trace(1775563200, "OS", "SKP", "L", "piv")     # oco=1 rr-skip (2A also fired this bar)
# oco cross-check: the kill-line sweep must ALSO have emitted on the oco bars
for ts in (1775980800, 1775563200):
    has_2a = any(k[0] == ts and k[1] == "2A" for k in EVS)
    print(f"\noco bar {ts}: 2A event also present = {has_2a}" + ("" if has_2a else "  <-- MISMATCH"))
    if not has_2a:
        fails += 1
print("\nhandtrace:", "PASS" if fails == 0 else f"FAIL ({fails})")
raise SystemExit(1 if fails else 0)
