from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.episodes import walk_episode
from evaluator.report import render_report

BARS = [(0, 100, 101, 99, 100), (1, 100, 102, 99.2, 101), (2, 101, 106, 100, 105)]


def _ev(ts, rsn="na", event="ENT"):
    return {"bar_ts": ts, "dir": "L", "px": 100.0, "event": event, "trade": "T1",
            "symbol": "X", "factors": {"lvl": "97", "stop": "98.5", "t1": "105.5",
                                       "rt1": "2.0", "rsn": rsn, "gvb": "0.2",
                                       "fp": "50", "q": "PU.OD", "t1co": "0",
                                       "reg1d": "U", "age": "12", "d_pct": "70"}}


def test_render_smoke():
    ep = walk_episode(_ev(0), BARS)
    ps = walk_episode(_ev(0, rsn="rr", event="SKP"), BARS)
    ps["pseudo"] = "rr"
    md = render_report([ep], [ps], {"X": 1}, ["events/X_240_v1_s0.4.4_c509208_B.jsonl"])
    assert "Pre-registered annotations" in md
    assert "by `gvb`" in md
    assert "rr gate" in md and "1D gate" in md
    assert "skip_overlap dropped: 1" in md
