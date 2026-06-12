# Study: Should OSD Also Require Sweeping the Previous Candle's Extreme? (2026-06-12)

## Question (user hypothesis)

Make OSD stricter: the entry bar must sweep the immediate previous candle's low
(longs) / high (shorts) IN ADDITION to the prev-day level. Intuition: a "real"
sweep takes out the nearest liquidity too.

## Definitions (exact)

- Condition tested, per entry bar vs its predecessor (4h ccxt bars):
  longs: `low < low[1]` · shorts: `high > high[1]`.
- Population: every OSD/OSW/OSF ENT in the s0.7.1 dataset (Jan 1–Jun 12, 4
  symbols), walked INDEPENDENTLY to stop or target (third exit off, per current
  rules). Open episodes excluded.
- Script: `harness/evaluator/prevbar_sweep_study.py`.

## Results

### OSD — the filter selects the WRONG group

| entry bar | n | win% | avg R |
|---|---|---|---|
| ALSO swept prev candle extreme (filter keeps) | 119 | 37% | +0.33 |
| did NOT — daily level only (filter deletes) | **45** | **49%** | **+0.73** |

Within-trend cross-split:

| | n | win% | avg R |
|---|---|---|---|
| swept-prev × align=W | 81 | 37% | +0.36 |
| **not-swept × align=W** | 30 | **53%** | **+0.97** |
| swept-prev × align=N | 20 | 30% | +0.11 |
| not-swept × align=N | 5 | 40% | +0.40 |
| swept-prev × align=A | 18 | 44% | +0.44 |
| not-swept × align=A | 10 | 40% | +0.14 |

### Other classes (direction NOT consistent)

| | n | win% | avg R |
|---|---|---|---|
| OSF swept-prev | 177 | 36% | +0.16 |
| OSF not-swept | 83 | 29% | −0.10 |
| OSW swept-prev | 26 | 35% | −0.01 |
| OSW not-swept | 7 | 29% | +0.11 |

For gap zones the lean is mildly the OTHER way — so the proposed rule isn't even
directionally portable across classes.

## The 45 "daily-only" OSD trades (full list — chart-verifiable)

```
BTC  02-24 20:00 L A pdl  t1_hit  +1.52      NEAR 01-15 08:00 L W pdl  stop  -1.00
BTC  03-07 08:00 L W pdl  stop    -1.00      NEAR 02-02 16:00 S W pdh  t1    +1.51
BTC  04-09 04:00 L W pdl  t1_hit  +2.29      NEAR 02-21 16:00 S N pdh  t1    +1.99
BTC  04-15 08:00 L W pdl  t1_hit  +1.77      NEAR 03-07 20:00 L A pdl  stop  -1.00
BTC  04-19 08:00 L W pdl  stop    -1.00      NEAR 03-09 04:00 S W pdh  stop  -1.00
BTC  04-19 12:00 L W pdl  stop    -1.00      NEAR 03-12 12:00 S W pdh  stop  -1.00
BTC  04-29 20:00 L A pdl  t1_hit  +1.64      NEAR 04-07 08:00 L W pdl  t1    +4.08
BTC  05-25 16:00 S W pdh  t1_hit  +1.78      NEAR 04-12 12:00 L W pdl  t1    +4.10
BTC  05-31 04:00 S W pdh  t1_hit  +2.09      NEAR 05-10 04:00 L W pdl  t1    +1.62
ETH  01-12 20:00 L N pdl  t1_hit  +3.03      NEAR 05-14 04:00 L W pdl  stop  -1.00
ETH  01-14 20:00 S A pdh  t1_hit  +2.35      NEAR 05-27 12:00 L W pdl  stop  -1.00
ETH  02-07 20:00 S W pdh  stop    -1.00      SOL  02-16 08:00 L W pdl  stop  -1.00
ETH  03-07 20:00 L A pdl  stop    -1.00      SOL  02-16 20:00 L W pdl  stop  -1.00
ETH  03-08 08:00 L A pdl  stop    -1.00      SOL  03-04 04:00 S N pdh  stop  -1.00
ETH  03-14 12:00 L W pdl  t1_hit  +5.10      SOL  03-19 20:00 L A pdl  stop  -1.00
ETH  04-09 04:00 L W pdl  t1_hit  +3.17      SOL  04-06 04:00 S A pdh  stop  -1.00
ETH  04-09 08:00 L W pdl  t1_hit  +3.42      SOL  04-09 04:00 L W pdl  t1    +3.57
ETH  05-06 20:00 L W pdl  stop    -1.00      SOL  04-15 08:00 L W pdl  t1    +2.57
ETH  05-20 16:00 S W pdh  t1_hit  +1.81      SOL  04-15 12:00 L W pdl  t1    +2.40
ETH  06-06 08:00 L A pdl  t1_hit  +1.89      SOL  04-28 16:00 L N pdl  stop  -1.00
NEAR (cont. left column)                     SOL  04-28 20:00 L N pdl  stop  -1.00
                                             SOL  05-01 04:00 S W pdh  stop  -1.00
                                             SOL  05-01 16:00 S W pdh  stop  -1.00
                                             SOL  05-14 04:00 L A pdl  stop  -1.00
                                             SOL  05-31 04:00 S W pdh  t1    +1.96
```

Tally check: 22 wins / 45 = 49%; sum R = +32.7 → +0.73 avg. The edge is carried
by CHUNKY winners (+2R to +5R: ETH 03-14 +5.10, NEAR 04-07/04-12 +4.1, SOL/ETH
Apr-9 cluster ~+3R) — these are reclaims after the flush already happened, so
entries sit close to the low with the full bounce ahead of them.

## Interpretation

`low >= low[1]` while still wicking under the prev-day level means: the
previous bar(s) had ALREADY pressed into the level, and the entry bar is a
HIGHER LOW that dips and reclaims — absorption/basing, the flush exhausted a
bar earlier. Requiring a fresh local low (the proposal) selects momentum still
pouring downhill — the same "violence loses" result as wkp/vz/osp, in micro
form. (`low < low[1]` is literally T1's pullback-chain CONTINUATION signature —
the wrong thing to demand at a reversal entry.)

## Caveats (read before believing)

1. **Cross-symbol correlation:** the Apr-9 04:00 long appears on BTC, ETH and
   SOL simultaneously — one market event, three rows. Effective n is meaningfully
   below 45/119. (This caveat applies to every basket-pooled table in the
   project; it bites hardest at these cell sizes.)
2. Independent walk (no sequential rule): consecutive-bar duplicates inflate
   both groups (e.g. SOL 04-15 08:00+12:00, 04-28 ×2, NEAR pairs).
3. n=45 / 30-per-cell are chance-sized; ~10 cells examined here.
4. OSF leans the opposite way — any rule built on this must be OSD-scoped.

## Verdict

**REJECTED as a requirement** — it deletes the best trades in the class.
**Registered for campaign 6 (inverse form):** "OSD reclaims holding a HIGHER LOW
at the daily level (no fresh local extreme on the entry bar) outperform."
Pure bar arithmetic — the harness computes it forever without any Pine change.
