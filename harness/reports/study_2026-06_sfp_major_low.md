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

### Part 2 — would catching it have been an EDGE?

**POOLED VERDICT (5 symbols, ~12 months each, n=138 — the real answer):**

| major-low def | n | 2:1 win | expR | medMFE | reach1R | reach2R |
|---|---|---|---|---|---|---|
| pivot(24,24) ~4-day | **138** | 24% | **−0.28** | 0.68R | 41% | 24% |
| pivot(48,48) ~8-day | 67 | 18% | **−0.45** | 0.46R | 33% | 18% |

EVERY slice loses: deep-sweep −0.38, shallow −0.24, strong-reclaim −0.35, and
even the quiet filter (swd<0.3 & rcl≥0.3) −0.38. Bigger/older lows worse (−0.45).
**No quality filter rescues it.**

Critically, the bigger sample KILLED the BTC-only optimism: BTC alone (n=10) had
medMFE 1.27R / reach1R 60% — looked like a scalp edge. Pooled across 5 symbols
it's medMFE 0.68R / reach1R 41% — the bounce is far weaker and less reliable than
BTC alone suggested. The n=10 read was favorable small-sample luck; June 5 itself
was a top-decile draw inside a losing population.

---

#### (first-pass BTC-only table, kept for the record — superseded by the pool above)

measured, BTC 4H, Dec–Jun:

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

## Verdict (FINAL — multi-symbol confirmed)

The miss is a real radar gap (short level memory) — a longer-memory "major level"
class WOULD see these. But the pattern is **NOT an edge**: counter-trend major-low
SFP longs lose as a 2:1 swing (−0.28R pooled, −0.45R for bigger lows), no quality
filter helps, and the bounce isn't even reliable enough for a clean scalp (only
41% reach +1R pooled). Same family as every counter-trend/violent setup the
project has killed. **Do not auto-trade it.** June 5 was a beautiful-looking
member of a losing population, and the BTC-only n=10 that hinted at a scalp edge
did not survive pooling. Closed.

## Caveats

138/67 events, 5 symbols, ~12-month window, longs only, mechanical 2:1 + MFE
(no trail/discretion). Scripts: `harness/evaluator/sfp_study.py` (single, with
Jun-5 trace), `sfp_study_pooled.py` (multi-symbol verdict).
