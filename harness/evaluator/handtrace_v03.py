"""v0.3 Task-4 hand-trace: verify Trade #2 episodes to the tick against
independently fetched bars (audit evidence; values transcribed from the live
harvest).

2A episodes (BTC 4H, s0.3.0 cfg 509208) — stateless one-bar: entry px = sweep
bar close; stop = sweep bar wick extreme +/- 0.5*ATR(14); t1 = trend extreme.
  A1 ENT S 1779681600: close 77377,   lvl 77600,   stop 78083.42857143, t1 74203.6, rt1 4.49
  A2 SKP S 1779796800: close 76478.2, lvl 77887.9, stop 78478.06428571, t1 76056,   rt1 0.21 (the t1co=1 handoff bar)

Checks per episode: (a) px == bar close; (b) sweep condition on the BAR itself
(high > lvl and close <= lvl); (c) stop == bar high + 0.5*ATR14 exactly;
(d) rt1 recomputes to printed precision.
"""
import csv
from pathlib import Path

BARS = Path(__file__).resolve().parents[1] / "bars" / "binanceusdm_BTCUSDT_4h.csv"

rows = list(csv.DictReader(BARS.open()))
ts = [int(r["ts_sec"]) for r in rows]
h = [float(r["high"]) for r in rows]
l = [float(r["low"]) for r in rows]
c = [float(r["close"]) for r in rows]
idx = {t: i for i, t in enumerate(ts)}


def atr14(i):
    trs = []
    for j in range(i - 13, i + 1):
        tr = max(h[j] - l[j], abs(h[j] - c[j - 1]), abs(l[j] - c[j - 1]))
        trs.append(tr)
    return sum(trs) / 14


def check_2a_short(name, t, close_ev, lvl, stop, t1, rt1):
    i = idx[t]
    a = atr14(i)
    ok = []
    ok.append(("px==close", abs(c[i] - close_ev) < 1e-6))
    ok.append(("sweep: high>lvl", h[i] > lvl))
    ok.append(("sweep: close<=lvl", c[i] <= lvl))
    ok.append(("stop==high+0.5atr", abs((h[i] + 0.5 * a) - stop) < 1e-4))
    ok.append(("rt1", abs((close_ev - t1) / (stop - close_ev) - rt1) < 0.01))
    bad = [k for k, v in ok if not v]
    print(f"{name}: ATR14={a:.2f} bar_high={h[i]} -> " + ("ALL OK" if not bad else f"FAIL {bad}"))
    return not bad


r1 = check_2a_short("A1 2A ENT S", 1779681600, 77377.0, 77600.0, 78083.42857143, 74203.6, 4.49)
r2 = check_2a_short("A2 2A SKP S (t1co=1)", 1779796800, 76478.2, 77887.9, 78478.06428571, 76056.0, 0.21)

# ── 2B episode (NEAR 4H): ENT L 1780171200 close 2.248, lvl(range_lo) 2.245,
#    stop 2.16246429, t1(midpoint) 2.6115, rt1 4.25.
#    midpoint = (range_hi + range_lo)/2 -> implied range_hi = 2*t1 - lvl = 2.978
#    (= the seeded wall: NEAR's trend high handed to range_hi at the May-26 death).
NBARS = Path(__file__).resolve().parents[1] / "bars" / "binanceusdm_NEARUSDT_4h.csv"
nrows = list(csv.DictReader(NBARS.open()))
nts = [int(r["ts_sec"]) for r in nrows]
nh = [float(r["high"]) for r in nrows]
nl = [float(r["low"]) for r in nrows]
nc = [float(r["close"]) for r in nrows]
nidx = {t: i for i, t in enumerate(nts)}


def natr14(i):
    trs = []
    for j in range(i - 13, i + 1):
        tr = max(nh[j] - nl[j], abs(nh[j] - nc[j - 1]), abs(nl[j] - nc[j - 1]))
        trs.append(tr)
    return sum(trs) / 14


def check_2b_long(name, t, close_ev, lvl, stop, t1, rt1):
    i = nidx[t]
    a = natr14(i)
    ok = []
    ok.append(("px==close", abs(nc[i] - close_ev) < 1e-9))
    ok.append(("sweep: low<lvl", nl[i] < lvl))
    ok.append(("sweep: close>=lvl", nc[i] >= lvl))
    ok.append(("stop==low-0.5atr", abs((nl[i] - 0.5 * a) - stop) < 1e-4))
    ok.append(("rt1", abs((t1 - close_ev) / (close_ev - stop) - rt1) < 0.01))
    ok.append(("implied range_hi==2.978", abs((2 * t1 - lvl) - 2.978) < 1e-9))
    bad = [k for k, v in ok if not v]
    print(f"{name}: ATR14={a:.5f} bar_low={nl[i]} -> " + ("ALL OK" if not bad else f"FAIL {bad}"))
    return not bad


r3 = check_2b_long("B1 2B ENT L (NEAR)", 1780171200, 2.248, 2.245, 2.16246429, 2.6115, 4.25)
raise SystemExit(0 if (r1 and r2 and r3) else 1)
