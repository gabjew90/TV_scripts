# Jamal Fable — Harness Methodology (BINDING)

Spec: docs/superpowers/specs/2026-06-09-jamal-fable-design.md (§9, §10).
Pine renders and signals; this directory judges. These rules are binding on
every analysis run; violating them invalidates the run.

## Data flow
1. Pine emits decision-time events as compact labels: `JF|<schema_v>|<script_v>|<cfg>|<src>|<trade>|<event>|<dir>|<tf>|<bar_ts>|<px>|k=v|...`
2. MCP harvest (`data_get_pine_labels`) -> raw JSON saved under `events/raw/` (audit trail, committed).
3. `harvest/parse_labels.py` -> canonical JSONL under `events/`, one file per
   provenance group `(schema_v, script_v, cfg, src, tf, symbol)`. Idempotent:
   re-harvests merge by dedup key (bar_ts + trade + event + dir [+ typ for PIV]).
4. `bars/fetch_bars.py` -> OHLCV CSVs from the exchange API (ccxt binanceusdm).
   The label budget is never spent exporting OHLC through the chart. The
   in-progress candle is always dropped — a committed CSV never contains a
   non-final bar.
   FETCH-RANGE RULES (foot-guns): `--until` is a date at 00:00 UTC — to cover
   events from earlier today, pass TOMORROW's date (the incomplete-bar drop
   makes over-fetching safe). And fetch `--since` at least `pivot_right` bars
   BEFORE the emit window start: a PIV event's bar_ts is the pivot bar, which
   precedes its in-window confirmation bar. align_check reports violations of
   either as "missing bar".
5. `evaluator/align_check.py` -> HARD PRECONDITION: every event's bar must exist
   in the fetched series with matching price (PIV-H vs high, PIV-L vs low, else
   close; tolerance 0.1%; a PIV without typ is malformed and quarantines).
   Mismatches are quarantined and reported, never silently included. Nonzero
   exit = the pipe is broken; nothing downstream runs.

## No-pool rules (enforced by file layout + evaluator loaders)
- `src=B` (backfill) and `src=L` (live) are never pooled. Backfill earns
  hypotheses; only the live log earns conviction.
- Different `settings_hash` or `schema_version` are never pooled without an
  explicit `--allow-mixed` override. A backfill harvested before and after a
  knob tweak is two datasets.
- Harvest-window inputs (`emit_from`/`emit_to`) are transport-layer, half-open
  `[from, to)`, and EXCLUDED from settings_hash — chunked harvests of the same
  config pool freely.

## Pre-registered annotations (carried on every report; discovering these is not a finding)
- Deeper pullbacks mechanically have larger R-to-T1 (trend-high T1 definition).
- Flush entries are mechanically deeper than pullback entries.
- V-shaped pullbacks never form a micro_LH -> Trade #1 structurally cannot
  trigger on them; ARM-without-ENT counts measure this hole.

## Episode rules (v0.2+; recorded now so they don't drift)
- Outcomes graded ONLY against ENT-embedded snapshot levels (lvl/stop/t1, rhi/rlo).
- Sequential per symbol per direction across trade types; blocked ENTs logged
  `skip_overlap`, first-class.
- Exit codes: thesis_exit | stop_out | t1_hit | trail. Counterfactual computed
  for every thesis_exit (hold-to-stop: recovered or stopped?).
- Pivot detection is re-implemented in Python ONLY under the pivot-parity
  license: it must reproduce every Pine SYS|PIV bit-exact from fetched bars
  (gates v0.2 acceptance). Parity includes the engine's within-bar ordering:
  pivot bookkeeping before FSM on the same confirmed bar.
- Aggregate statistics on non-overlapping time windows; no significance claims
  pooled across windows.

## Symbol mapping (TV -> ccxt binanceusdm)
| TV          | ccxt            |
|-------------|-----------------|
| BTCUSDT.P   | BTC/USDT:USDT   |
| ETHUSDT.P   | ETH/USDT:USDT   |
| SOLUSDT.P   | SOL/USDT:USDT   |
| NEARUSDT.P  | NEAR/USDT:USDT  |

## TF mapping (TV `timeframe.period` -> ccxt)
| TV   | ccxt |
|------|------|
| 240  | 4h   |
| 60   | 1h   |
| D    | 1d   |
