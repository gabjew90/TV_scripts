"""Pivot detection mirroring Pine ta.pivothigh/ta.pivotlow (L/R bars).

PARITY LICENSE (spec section 10): this module exists only because trail
simulation needs post-entry pivots. It must reproduce Pine's SYS|PIV events
bit-exact (parity_check.py); if TV's tie semantics differ from the initial
strict-inequality assumption, fix THIS module to match Pine, never vice versa.
Initial semantics: a pivot high at i requires high[i] strictly greater than
every high in [i-L, i) and (i, i+R]. Mirror for lows.
"""


def pivot_points(ts, highs, lows, left, right):
    out = []
    n = len(ts)
    for i in range(left, n - right):
        win_h = highs[i - left:i] + highs[i + 1:i + 1 + right]
        if all(highs[i] > h for h in win_h):
            out.append((ts[i], "H", highs[i]))
        win_l = lows[i - left:i] + lows[i + 1:i + 1 + right]
        if all(lows[i] < l for l in win_l):
            out.append((ts[i], "L", lows[i]))
    return out
