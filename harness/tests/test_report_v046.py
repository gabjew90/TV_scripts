"""v0.4.6 report helpers: per-trade rt1 conditioning + nested lq-within-swd."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.report import bucket_rows_nested, EVENT_GLOB


def _ep(trade, swd, lq, r, code="t1_hit"):
    return {"trade": trade, "exit_code": code, "r": r, "mfe_r": r,
            "ambiguous": 0, "factors": {"swd": str(swd), "lq_tot": str(lq)}}


def test_event_glob_is_s046():
    assert "s0.4.6" in EVENT_GLOB


def test_nested_buckets_split_outer_then_inner():
    eps = [_ep("2A", 0.1, 5, 1.0), _ep("2A", 0.1, 50, -1.0, "stop_out"),
           _ep("2A", 0.9, 50, 2.0)]
    rows = bucket_rows_nested(eps, "swd", [(None, 0.5), (0.5, None)], ["<0.5", ">=0.5"],
                              "lq_tot", [(None, 10), (10, None)], ["<10", ">=10"])
    # 4 rows: 2 outer x 2 inner; the (<0.5, <10) row holds exactly 1 episode
    assert len(rows) == 4
    assert rows[0][0] == "<0.5 | <10" and rows[0][1] == 1
    assert rows[3][0] == ">=0.5 | >=10" and rows[3][1] == 1
