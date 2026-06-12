"""Full OS audit (s0.6.2): for EVERY OS event on every symbol, recompute from
raw ccxt bars and assert:
  1. lvl equals the true prev-day / prev-week extreme for its lvl_src
     (TV daily/weekly = UTC midnight / Monday-start week, last CLOSED candle)
  2. the sweep-reclaim arithmetic holds on the event bar
     (L: low < lvl and close > lvl ; S: high > lvl and close < lvl)
  3. align is consistent with the event's regime + direction
     (W: reg==U&L or reg==D&S ; A: opposite ; N: reg==C)
  4. tgt class matches align (W->tex, A->fv, N->mid)
Events whose prev-period isn't fully covered by the bars file are skipped."""
import csv
import glob
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
BARS_MAP = {"BTCUSDT.P": "binanceusdm_BTCUSDT_4h.csv", "ETHUSDT.P": "binanceusdm_ETHUSDT_4h.csv",
            "SOLUSDT.P": "binanceusdm_SOLUSDT_4h.csv", "NEARUSDT.P": "binanceusdm_NEARUSDT_4h.csv"}

checked = skipped = 0
fails = []
for sym, bf in BARS_MAP.items():
    bars = {}
    for r in csv.DictReader(open(HARNESS / "bars" / bf)):
        bars[int(r["ts_sec"])] = (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
    min_ts = min(bars)

    def period_extreme(start, end, kind):
        """min low / max high over [start, end); None if not fully covered."""
        vals = []
        t = start
        while t < end:
            if t not in bars:
                return None
            vals.append(bars[t][2] if kind == "lo" else bars[t][1])
            t += 14400
        return min(vals) if kind == "lo" else max(vals)

    for f in glob.glob(str(HARNESS / "events" / f"{sym}_*_s0.6.2_*.jsonl")):
        for line in open(f):
            e = json.loads(line)
            if e["trade"] != "OS":
                continue
            fa = e["factors"]
            ts = e["bar_ts"]
            o, h, l, c = bars[ts]
            d = datetime.fromtimestamp(ts, tz=timezone.utc)
            day0 = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())
            wk0 = day0 - d.weekday() * 86400          # Monday 00:00 of event's week
            src = fa["lvl_src"]
            if src == "pdl":
                want = period_extreme(day0 - 86400, day0, "lo")
            elif src == "pdh":
                want = period_extreme(day0 - 86400, day0, "hi")
            elif src == "pwl":
                want = period_extreme(wk0 - 7 * 86400, wk0, "lo")
            elif src == "pwh":
                want = period_extreme(wk0 - 7 * 86400, wk0, "hi")
            else:
                fails.append(f"{sym} {ts}: unexpected lvl_src {src}")
                continue
            if want is None:
                skipped += 1
                continue
            checked += 1
            lvl = float(fa["lvl"])
            if abs(lvl - want) > 1e-6 * max(want, 1e-9):
                fails.append(f"{sym} {ts}: lvl {lvl} != recomputed {src} {want}")
            ok_sweep = (l < lvl and c > lvl) if e["dir"] == "L" else (h > lvl and c < lvl)
            if not ok_sweep:
                fails.append(f"{sym} {ts}: sweep FALSE dir={e['dir']} lvl={lvl} bar l={l} h={h} c={c}")
            reg = fa["reg"]
            want_al = "N" if reg == "C" else ("W" if (reg == "U") == (e["dir"] == "L") else "A")
            if fa["align"] != want_al:
                fails.append(f"{sym} {ts}: align {fa['align']} != {want_al} (reg={reg} dir={e['dir']})")
            want_tgt = {"W": "tex", "A": "fv", "N": "mid"}[want_al]
            if fa.get("tgt") != want_tgt:
                fails.append(f"{sym} {ts}: tgt {fa.get('tgt')} != {want_tgt}")
print(f"checked {checked} OS events ({skipped} skipped: prev-period before bars coverage)")
for x in fails[:20]:
    print(" ", x)
print("OS audit:", "PASS" if not fails else f"FAIL ({len(fails)})")
raise SystemExit(1 if fails else 0)
