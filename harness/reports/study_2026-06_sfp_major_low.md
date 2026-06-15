# Study: SFP of a Major Low — the June-5 BTC Miss (2026-06-15)

## Trigger

User: a clean swing-failure (sweep + reclaim) of a **major** BTC low on Fri Jun 5
— "how the hell do we not catch that." The 4H engine logged only skips there.

## Two-part answer

### Part 1 — WHY it was missed (structural)

The Jun-5 16:00 bar wicked to **59,080** and closed back at **60,267**. A raw-bar
pivot scan confirms **59,800 was a genuine prior pivot low** — so it really was an
SFP of a real level (the study flags it: Jun-5 16:00 swept 59,800, reclaimed,
MFE 1.91R; Jun-6 04:00 swept it again, MFE 1.34R).

The engine missed it because its entire memory of "lows" is **the last 5 confirmed
4H pivot lows + prior-day + prior-week low** — a short window. 59,800 was an
*older/major* low, outside that set, so sweeping it triggered nothing. Confirmed:
even in the s0.5.0 data (pivot class ON), the only pivot event near Jun-5 was a
skip against the prior-day low (61,344); 59,800 was never on the radar. Secondary
blocks: a long there is counter-trend (regime DOWN → yellow-OSF suppression), and
the counter-trend pivot-long class was a campaign-killed loser (9%/−0.76R).

### Part 2 — would catching it have been an EDGE? (measured, BTC 4H, Dec–Jun)

Raw-bar SFP-reclaim longs of major lows (pivot(L,L)), entry=close,
stop=wick−0.5·ATR, walked:

| major-low def | n | 2:1 win | expR | medMFE | reach1R | reach1.5R | reach2R |
|---|---|---|---|---|---|---|---|
| pivot(24,24) ~4-day | 10 | 12% | **−0.62** | 1.27R | 60% | 30% | 10% |
| pivot(48,48) ~8-day | 7 | 0% | **−1.00** | 0.82R | 43% | 29% | 0% |

**As a swing trade (2:1) it loses** — independently reconfirming the campaign's
counter-trend pivot-long result (9%/−0.76R) via a totally separate method.
**Bigger/older lows are WORSE, not better** (pivot48 < pivot24) — opposite of the
"more major = stronger reversal" intuition; a deeper structural low that breaks
tends to keep going.

**But the bounce is REAL and SHORT:** 60% reach +1R, only 10% reach +2R. These
flushes pop ~1R then fail (it's still a downtrend). So the only version with a
pulse is a **scalp** — ~1R target, take the bounce, don't let it run (1:1 at 60%
≈ +0.2 expectancy on n=10). Jun-5's 59,800 SFP ran to 1.91R MFE — a top-decile
draw, NOT typical (median 1.27R). We'd have caught a good-looking instance of a
class that loses on average.

## Verdict

The miss is a real radar gap (short level memory) — a longer-memory "major level"
class WOULD see these. But the pattern is a **losing swing trade / marginal scalp**,
same family as every counter-trend/violent setup the project has killed. **Do not
auto-trade it.** If pursued, the only defensible form is a tight-target scalp,
and it needs the deeper + multi-symbol test (blocked now by a transient Binance
451) before any conviction.

## Caveats

n=10/7, BTC only, 6-month window, longs only. Deep-history + multi-symbol
extension pending exchange access. Script: `harness/evaluator/sfp_study.py`.
