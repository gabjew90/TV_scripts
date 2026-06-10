"""Fetch perp OHLCV from the exchange API into harness/bars/ CSVs.

Spec ref: design doc section 10 - bars come repo-side from the exchange API;
the label budget is never spent exporting OHLC through the chart.

Usage:
  py -3 harness/bars/fetch_bars.py --symbol "BTC/USDT:USDT" --tf 4h ^
      --since 2026-03-01 --until 2026-06-09 --out harness/bars/binanceusdm_BTCUSDT_4h.csv
"""
import argparse
import csv
import time as _time
from datetime import datetime, timezone
from pathlib import Path


def fetch_ohlcv_all(ex, symbol, timeframe, since_ms, until_ms, limit=1500):
    """Paginate fetch_ohlcv from since_ms to until_ms inclusive. Returns
    sorted, de-duplicated rows [ts_ms, o, h, l, c, v]."""
    rows = []
    cursor = since_ms
    while cursor <= until_ms:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=cursor, limit=limit)
        if not batch:
            break
        rows.extend(batch)
        nxt = batch[-1][0] + 1
        if nxt <= cursor:
            break
        cursor = nxt
        if getattr(ex, "rateLimit", 0):
            _time.sleep(ex.rateLimit / 1000)
    seen = set()
    out = []
    for r in sorted(rows, key=lambda r: r[0]):
        if since_ms <= r[0] <= until_ms and r[0] not in seen:
            seen.add(r[0])
            out.append(r)
    return out


def drop_incomplete(rows, tf_ms, now_ms):
    """Exclude the in-progress candle: keep only bars whose close time has
    passed. A committed CSV must never contain a non-final bar - the v0.2
    evaluator (trail simulation) reads bars directly."""
    return [r for r in rows if r[0] + tf_ms <= now_ms]


def write_csv(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_sec", "open", "high", "low", "close", "volume"])
        for ts_ms, o, h, l, c, v in rows:
            w.writerow([ts_ms // 1000, o, h, l, c, v])


def _parse_date(s):
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def main():
    import ccxt  # imported here so tests don't need network/ccxt internals
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True, help="ccxt symbol, e.g. BTC/USDT:USDT")
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--since", required=True, help="YYYY-MM-DD (UTC)")
    ap.add_argument("--until", required=True, help="YYYY-MM-DD (UTC)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    ex = ccxt.binanceusdm()
    rows = fetch_ohlcv_all(ex, args.symbol, args.tf, _parse_date(args.since), _parse_date(args.until))
    rows = drop_incomplete(rows, ex.parse_timeframe(args.tf) * 1000, ex.milliseconds())
    write_csv(rows, args.out)
    print(f"wrote {len(rows)} bars -> {args.out}")


if __name__ == "__main__":
    main()
