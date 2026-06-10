from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.pivots import pivot_points


def test_simple_pivot_high_and_low():
    highs = [1, 2, 3, 9, 3, 2, 1, 2, 3, 4]
    lows  = [1, 2, 3, 8, 3, 2, 0.5, 2, 3, 4]
    ts    = list(range(100, 110))
    pivots = pivot_points(ts, highs, lows, left=3, right=3)
    assert (103, "H", 9) in pivots          # bar 3 high=9 > 3 left & 3 right
    assert (106, "L", 0.5) in pivots        # bar 6 low (needs 3 right bars: 7,8,9)
    assert all(t in (103, 106) for t, _, _ in pivots)


def test_tie_does_not_make_pivot():
    highs = [1, 2, 9, 3, 9, 2, 1]           # equal high 2 bars apart
    lows  = [0, 0, 0, 0, 0, 0, 0]
    pivots = pivot_points(list(range(7)), highs, lows, left=2, right=2)
    assert (2, "H", 9) not in pivots        # right side contains an equal value
