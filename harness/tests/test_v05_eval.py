"""v0.5 evaluator: thesis-exit R-delta, 1D-cohort split, oriented conditioning, glob."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.episodes import walk_episode
from evaluator.report import EVENT_GLOB, oneD_blocked, oriented, oriented_q


def _ent(lvl, stop, t1, ts=1000):
    return {"symbol": "X", "trade": "2A", "event": "ENT", "dir": "L", "bar_ts": ts,
            "px": 100.0, "factors": {"lvl": str(lvl), "stop": str(stop), "t1": str(t1),
                                     "rt1": "2.0", "reg1d": "D"}}


def test_thesis_exit_carries_rule_delta_r():
    # entry 100, stop 95, t1 110; bar2 closes below lvl 98 (thesis exit at 97),
    # then price recovers to t1 -> cf=recovered, cf_r=+2.0
    bars = [(1000, 100, 101, 99, 100), (2000, 99, 99.5, 96.5, 97),
            (3000, 97, 111, 96.9, 110)]
    ep = walk_episode(_ent(98, 95, 110), bars)
    assert ep["exit_code"] == "thesis_exit" and ep["counterfactual"] == "recovered"
    assert ep["cf_r"] == 2.0
    assert abs(ep["rule_delta_r"] - (ep["r"] - 2.0)) < 1e-9


def test_thesis_exit_stopped_cf_r_minus_one():
    bars = [(1000, 100, 101, 99, 100), (2000, 99, 99.5, 96.5, 97),
            (3000, 97, 97.5, 94.0, 94.5)]
    ep = walk_episode(_ent(98, 95, 110), bars)
    assert ep["exit_code"] == "thesis_exit" and ep["counterfactual"] == "stopped"
    assert ep["cf_r"] == -1.0
    assert abs(ep["rule_delta_r"] - (ep["r"] + 1.0)) < 1e-9


def test_oneD_blocked_cohort_rule():
    assert oneD_blocked({"dir": "L", "factors": {"reg1d": "D"}})
    assert not oneD_blocked({"dir": "L", "factors": {"reg1d": "U"}})
    assert oneD_blocked({"dir": "S", "factors": {"reg1d": "U"}})


def test_oriented_flips_sign_for_longs():
    e = {"dir": "L", "factors": {"os": "-2.0"}}
    assert oriented(e, "os") == 2.0           # stretched-down long = supportive
    e2 = {"dir": "S", "factors": {"os": "-2.0"}}
    assert oriented(e2, "os") == -2.0
    e3 = {"dir": "S", "factors": {"fp": "80"}}
    assert oriented(e3, "fp") == 30.0          # crowded-long supports the short fade


def test_oriented_q_is_trade_relative():
    assert oriented_q({"dir": "L", "factors": {"q": "PU.OD"}}) == "PW.OD"
    assert oriented_q({"dir": "S", "factors": {"q": "PU.OD"}}) == "PA.OD"


def test_event_glob_is_s060():
    assert "s0.6.0" in EVENT_GLOB
