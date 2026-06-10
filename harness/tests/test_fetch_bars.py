import csv
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bars.fetch_bars import fetch_ohlcv_all, write_csv, drop_incomplete


class FakeExchange:
    rateLimit = 0
    def __init__(self, candles):
        self.candles = candles  # list of [ts_ms, o, h, l, c, v]
    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1500):
        out = [c for c in self.candles if c[0] >= since][:limit]
        return out


def test_fetch_paginates_dedups_and_truncates():
    h = 4 * 3600 * 1000
    candles = [[1780000000000 + i * h, 1.0 + i, 2.0 + i, 0.5 + i, 1.5 + i, 100.0] for i in range(10)]
    ex = FakeExchange(candles)
    rows = fetch_ohlcv_all(ex, "BTC/USDT:USDT", "4h",
                           since_ms=candles[2][0], until_ms=candles[7][0], limit=3)
    assert [r[0] for r in rows] == [candles[i][0] for i in range(2, 8)]
    assert len({r[0] for r in rows}) == len(rows)  # no duplicate timestamps


def test_write_csv_seconds_and_header(tmp_path):
    rows = [[1780000000000, 1.0, 2.0, 0.5, 1.5, 100.0]]
    out = tmp_path / "x.csv"
    write_csv(rows, out)
    got = list(csv.DictReader(out.open()))
    assert got[0]["ts_sec"] == "1780000000"
    assert got[0]["close"] == "1.5"


def test_drop_incomplete_excludes_inprogress_bar():
    h = 4 * 3600 * 1000
    rows = [[1780000000000, 1.0, 2.0, 0.5, 1.5, 100.0],
            [1780000000000 + h, 1.0, 2.0, 0.5, 1.5, 100.0]]
    # "now" is mid-second-bar -> second bar is in progress, must be dropped
    kept = drop_incomplete(rows, tf_ms=h, now_ms=1780000000000 + h + 1000)
    assert [r[0] for r in kept] == [1780000000000]
