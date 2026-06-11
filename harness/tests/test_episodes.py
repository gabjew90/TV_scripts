from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.episodes import walk_episode, build_episodes

BARS = [  # (ts, o, h, l, c) — tiny synthetic tape
    (0, 100, 101, 99, 100),
    (1, 100, 102, 99.2, 101),
    (2, 101, 106, 100, 105),
    (3, 105, 107, 95, 96),
    (4, 96, 97, 90, 91),
    (5, 91, 95, 90, 94),
]


def _ev(ts, dir_, ent, lvl, stop, t1, rt1="2.0", trade="T1", symbol="X"):
    return {"bar_ts": ts, "dir": dir_, "px": ent, "event": "ENT", "trade": trade,
            "symbol": symbol,
            "factors": {"lvl": str(lvl), "stop": str(stop), "t1": str(t1),
                        "rt1": str(rt1), "rsn": "na"}}


def test_t1_hit_long():
    e = walk_episode(_ev(0, "L", 100, 97, 98.5, 105.5), BARS)
    assert e["exit_code"] == "t1_hit" and e["exit_ts"] == 2 and e["r"] == 2.0
    assert e["ambiguous"] == 0


def test_stop_out_long():
    e = walk_episode(_ev(0, "L", 100, 90, 99.3, 200), BARS)
    assert e["exit_code"] == "stop_out" and e["exit_ts"] == 1 and e["r"] == -1.0


def test_ambiguous_bar_grades_stop_first():
    e = walk_episode(_ev(2, "L", 105, 90, 96, 106.5), BARS)  # bar 3 touches BOTH
    assert e["exit_code"] == "stop_out" and e["exit_ts"] == 3 and e["ambiguous"] == 1


def test_thesis_exit_long_with_counterfactual():
    e = walk_episode(_ev(0, "L", 100, 99.0, 89, 200), BARS)  # bar 3 CLOSES 96 < 99
    assert e["exit_code"] == "thesis_exit" and e["exit_ts"] == 3
    assert abs(e["r"] - (96 - 100) / (100 - 89)) < 1e-9
    assert e["counterfactual"] == "open"             # stop 89 never hit, t1 never hit


def test_short_mirror_t1_hit():
    # short entered at bar 3 close 96, stop above pullback high, target below
    e = walk_episode(_ev(3, "S", 96, 100, 107.5, 90.5), BARS)
    assert e["exit_code"] == "t1_hit" and e["exit_ts"] == 4 and e["r"] == 2.0


def test_sequential_per_symbol_direction():
    evs = [_ev(0, "L", 100, 90, 99.3, 200), _ev(1, "L", 101, 90, 95, 200)]
    eps, overlapped = build_episodes(evs, BARS)
    assert len(eps) == 1 and len(overlapped) == 1


def test_no_levels_skipped():
    ev = _ev(0, "L", 100, 97, "na", 105.5)
    eps, _ = build_episodes([ev], BARS)
    assert eps == [] or eps[0].get("exit_code") is None  # dropped, not walked


def test_mfe_computed():
    e = walk_episode(_ev(0, "L", 100, 92, 94.5, 200), BARS)  # stops at bar 4 (low 90)
    assert e["exit_code"] == "stop_out" and e["exit_ts"] == 4
    assert abs(e["mfe_r"] - (107 - 100) / (100 - 94.5)) < 0.01   # ran to 107 first
