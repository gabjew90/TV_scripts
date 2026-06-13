# Study: Does the Instrument Transfer to 1h? (2026-06-13)

## Question (user)

Everything to date is 4H. Validate on 1h candles — same code, same rules,
chart timeframe = 60 instead of 240.

## Method

- Pilot: BTC 1h, 2 weeks — pipe validated (provenance auto-segregated to a
  `_60_` event file, 248/248 aligned, edges replicated on n=12).
- Full: BTC + HYPE on 1h, Jan 1 → Jun 13, 12 two-week chunks each (1h packs
  ~4× the events; windows narrowed to stay under the 500-label cap).
  BTC 3,589 events / HYPE 3,614 events, **every event aligned** (hard precondition).
- `report.py --tf 60`: timeframe folded into the no-pool provenance key so 1h
  can NEVER pool with 4H. Same s0.7.2 ruleset (yellow-OSF gate on, etc.).
- Script: per-symbol independent walk + the standard report.

## Result 1 — the edge does NOT transfer

| | 4H (campaign 6) | **1h** |
|---|---|---|
| pooled book | 36% / +0.17R | **27% / −0.13R** |
| BTC alone | solidly + | **28% / +0.05R** (independent walk) |
| HYPE alone | mixed | **26% / −0.19R** |

What is +0.17R on 4H is breakeven-to-negative on 1h. BTC degrades from a real
edge to ~zero; the volatile HYPE goes outright negative. **The 4H calibration
(pivot 3/3, ATR 14, the whole structure) is tuned to 4H rhythm; on 1h the same
rules fire on microstructure that doesn't mean-revert the same way.**

## Result 2 — the FACTOR STRUCTURE partially survives (compressed, shifted down)

| factor | 4H | 1h | verdict |
|---|---|---|---|
| **osp>85 (extreme stretch)** | worst (20%/−0.34) | **worst (17%/−0.39; BTC 20%/−0.29, HYPE 14%/−0.55)** | **REPLICATES — most robust signal in the project** |
| align W vs A | W clearly > A | W −0.13 > A −0.18 (ordering kept, edge gone) | compressed |
| vz quiet vs active | quiet > active | <0: −0.05 > 0–1.5: −0.27 | ordering kept |
| **er chop (<0.2)** | **GOOD** (+0.12) | **WORST (−0.31)** | **INVERTS** |

The stretch and quiet/violence orderings hold direction across both timeframes
and every symbol — but every cell shifts below breakeven. One relationship
flips outright: low-ER "chop" is tradeable mean-reversion on 4H and pure noise
on 1h (spread/microstructure, not a range to fade).

## Conclusion

**The instrument is a 4H tool. Do not trade it on 1h as-is** — BTC ≈ breakeven,
HYPE negative, after costs both are losers. A 1h deployment would require its
own recalibration (pivot lengths, ATR period, gate, the whole structure scaled
to 1h) and its own validation campaign — a separate project, not a timeframe
toggle. This confirms the standing memo ("all validation is 4H-only; 1h is
mechanically the same code but statistically unvalidated") with the actual
number: unvalidated → negative.

**The keeper:** `osp>85` extreme-stretch entries lose on every timeframe, every
symbol, six campaigns — the single most validated finding in the project, and
independent cross-timeframe confirmation that the osp>85 demotion (still open
on 4H) is real signal, not a 4H artifact.

## Caveats

- 2 symbols (BTC + HYPE); BTC is the cleaner read, HYPE the high-vol stress test.
- No 1h sanity gate (the 11 audited entries are 4H-specific) and no bit-exact 1h
  OS audit run — but align_check (OHLC match at every event bar) passed 7,203/7,203,
  so level/sweep identity is sound; only the FVG zone-lifecycle re-sim was skipped.
- 1h events live in `*_60_*` files, fully partitioned from 4H by the provenance key.
