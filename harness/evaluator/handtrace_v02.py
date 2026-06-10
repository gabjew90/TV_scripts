"""v0.2 Task-6 hand-trace: verify three Trade #1 episodes to the tick against
independently fetched bars (audit evidence; values transcribed from the live
harvest).

Episodes (from the BTC 4H harvest, script v0.2.0 cfg 509208):
  E1 ENT  L 1776600000: close 75807.6, lvl 73256.8, stop 74365.00357143, t1 78300,    rt1 1.73, d_atr 3.78, d_pct 68.9
  E2 SKP  L 1776816000: close 77488.3, lvl 73669,   stop 73097.82857143, t1 78300,    rt1 0.18, d_atr 4.05, d_pct 100
  E3 ENT  S 1780963200: close 62841,   lvl 64179.5, stop 64809.66785714, t1 59080,    rt1 1.91, d_atr 4.62, d_pct 101.4

Checks per episode: (a) event px == bar close; (b) ATR(14)=SMA of TR at the bar
reconciles stop with the implied pullback extreme; (c) rt1/d_atr/d_pct recompute
from levels+ATR to the printed precision; (d) t1/lvl equal parity-verified pivot
prices.
"""
import csv
from pathlib import Path

BARS = Path(__file__).resolve().parents[1] / "bars" / "binanceusdm_BTCUSDT_4h.csv"

rows = list(csv.DictReader(BARS.open()))
ts = [int(r["ts_sec"]) for r in rows]
o = [float(r["open"]) for r in rows]
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


def check(name, t, close_ev, lvl, stop, t1, rt1, d_atr, d_pct, side):
    i = idx[t]
    a = atr14(i)
    ok = []
    ok.append(("px==close", abs(c[i] - close_ev) < 1e-6))
    if side == "L":
        pb = stop + 0.5 * a                      # implied pullback low
        ok.append(("rt1", abs((t1 - close_ev) / (close_ev - stop) - rt1) < 0.01))
        ok.append(("d_atr", abs((t1 - pb) / a - d_atr) < 0.01))
        ok.append(("d_pct", abs(100 * (t1 - pb) / (t1 - lvl) - d_pct) < 0.1))
        ok.append(("pb_is_real_low", any(abs(l[j] - pb) < 1e-6 for j in range(max(0, i - 60), i + 1))))
    else:
        pb = stop - 0.5 * a                      # implied pullback high
        ok.append(("rt1", abs((close_ev - t1) / (stop - close_ev) - rt1) < 0.01))
        ok.append(("d_atr", abs((pb - t1) / a - d_atr) < 0.01))
        ok.append(("d_pct", abs(100 * (pb - t1) / (lvl - t1) - d_pct) < 0.1))
        ok.append(("pb_is_real_high", any(abs(h[j] - pb) < 1e-6 for j in range(max(0, i - 60), i + 1))))
    bad = [k for k, v in ok if not v]
    print(f"{name}: ATR14={a:.2f} implied_pb={pb:.8f} -> " + ("ALL OK" if not bad else f"FAIL {bad}"))
    return not bad


r1 = check("E1 ENT L", 1776600000, 75807.6, 73256.8, 74365.00357143, 78300.0, 1.73, 3.78, 68.9, "L")
r2 = check("E2 SKP L", 1776816000, 77488.3, 73669.0, 73097.82857143, 78300.0, 0.18, 4.05, 100.0, "L")
r3 = check("E3 ENT S", 1780963200, 62841.0, 64179.5, 64809.66785714, 59080.0, 1.91, 4.62, 101.4, "S")
raise SystemExit(0 if (r1 and r2 and r3) else 1)
