# Jamal Fable — Design Spec

**Date:** 2026-06-09 · **Status:** DRAFT, rev 2 (review fixes applied) · **Script:** `jamal-fable.pine` (Pine v6, `overlay=true`) · **TV name:** "Jamal Fable"

> **Rev 2 changes (review):** operational `HL_ref` definition (re-anchoring fixed) · explicit regime state machine + range seeding · ENT events carry level snapshots + evaluator pivot-parity requirement · entry-time snapshot semantics for outcome grading · sweep/trigger coincidence ownership + cross-type concurrency rule · dedup key includes event type · percentile-window knobs · V-shape coverage hole pre-registered.

**Governing principle (from the founding brief):** trade-first, instrument-minimal, validation-before-conviction. The v1–v9 series was instrument-first, trade-later; Fable inverts it. Two trade specs pull in only the detectors they need; derivatives data is a day-one citizen; the validation harness is built **before** the indicator earns any conviction. Pine renders and signals — **something outside TradingView judges it.**

---

## 1. What Jamal Fable is

A 4H-operating-timeframe signal indicator for crypto perpetual futures implementing exactly two trades:

1. **Trade #1 — Pullback-continuation** inside a confirmed structural trend.
2. **Trade #2 — Flush-and-reclaim**, one mechanism with two regime-conditioned variants:
   - **2A (in-trend):** counter-trend flush sweeping `HL_ref`, reclaimed → with-trend entry.
   - **2B (in chop):** range-boundary sweep, reclaimed → fade toward the mean.

Carried over from the v-series: the structural BOS/CHoCH regime engine, percentile-ranked measures, confirmed-bar discipline, isolation testing. Dead on arrival: carry decomposition, ER as anything load-bearing, early visual-encoding effort.

This is a discretionary + alert-driven tool. It is **not a validated edge** until the harness says so.

## 2. System architecture (Approach 1 — approved)

One Pine script; two transports for one event string; repo-side judgment.

```
TradingView (renders + signals)              Repo (judges)
┌─────────────────────────────┐    MCP      ┌──────────────────────────────┐
│ regime engine (measurement) │  harvest →  │ harness/events/*.jsonl       │
│  → trade detectors          │             │ harness/bars/   ← ccxt/REST  │
│  → factor vector            │  webhook →  │ harness/evaluator/*.py       │
│  → event labels + alerts    │  (stage 2)  │  → reports (non-overlapping  │
│ minimal drawing             │             │     windows, counterfactuals)│
└─────────────────────────────┘             └──────────────────────────────┘
```

Rejected alternatives, recorded so they stay rejected:
- **Two-script split** (engine vs harness): Pine scripts cannot share structured state; the harness would re-implement the engine. Two versions to sync, zero real isolation.
- **`strategy()` + TV backtester:** smuggles outcome-grading back inside TradingView under the guise of free fills. TV's fill model muddies counterfactuals; partial/trail semantics would dominate dev time pre-validation. Possible later as an independent cross-check only.

## 3. Regime engine (the measurement layer)

- Structural pivots: `ta.pivothigh/low`, defaults **L=3 / R=3** (knobs). A pivot exists only once confirmed (R bars later); all structure is pivot-confirmed, all breaks are **confirmed body closes**.
- **`HL_ref` (in UP) / `LH_ref` (in DOWN) — operational definition:** the most recent confirmed **pivot low / pivot high while the regime is live**. *Higher/lower is a property of the trend, not a filter on the reference.* This is what lets the engine re-anchor to a proven flush low the honest way: a 2A flush low is by construction lower than the old `HL_ref`; when it confirms as a pivot low (with lag), it **becomes** `HL_ref` and the CHoCH line moves to the deeper, proven level. A "higher low only" filter would never promote it — the CHoCH line would freeze at the stale level and a later pullback that holds the flush low but body-closes below the old line would kill the trend label spuriously (the v7 deep-pullback bug in a new shirt). Safety: reaching a lower pivot low without trend death requires never body-closing below the *current* line on the way — exactly the sweep-and-hold case that should re-anchor. Recomputed only when a new pivot confirms.
- **State machine (explicit — the engine is the component every other section consumes; no implicit transitions):**

```
INIT  = CHOP   (range builds from confirmed pivots from bar 1)
CHOP → UP     confirmed body close above range high   = BOS(up); that boundary becomes the BOS level
CHOP → DOWN   confirmed body close below range low    (mirror)
UP   → UP     body close above the trend high = continuation BOS (new BOS level, no state change)
UP   → CHOP   CHoCH = body close below HL_ref. NEVER UP→DOWN directly — DOWN requires its own BOS from CHOP.
DOWN → CHOP   mirror (CHoCH = body close above LH_ref)
```

  "Relevant swing high" is now exact: from CHOP, BOS measures against the **range boundary**; while trending, against the **most recent confirmed pivot high (trend high)**.
- **States:** `UP` (≥1 BOS up, no CHoCH since) · `DOWN` (mirror) · `CHOP` (no live regime).
- **Range (CHOP) — definition + seeding:** at trend death, the side price just broke is left **undefined**; it fills with the first pivot confirmed after death (range low, for an UP death). The opposite boundary seeds with the dead trend's extreme (range high = trend high, for an UP death). Boundaries then extend monotonically: range high = max(seed, confirmed pivot highs since death); range low = min(seed, confirmed pivot lows since death). While a boundary is undefined: **no 2B setups on that side and no regime entry through that side.** Consequences (intentional): 2B-short at the old trend high can exist immediately after an UP death; 2B-long needs one post-death confirmed pivot low first; and no instant CHoCH→opposite-BOS flip is possible, because the broken side has no boundary to close beyond. **No minimum-width parameter** — the ≥1.5R skip gate (§5/§6) is the width gate; a second one would be v8-style stacking.
- **1D filter:** the same engine evaluated on 1D via `request.security` (`lookahead_off`), reading only the **last confirmed 1D bar's** regime. No intra-bar 1D reads — confirmed-bar discipline holds across timeframes.
- **Engine details decided at implementation (surfaced at the v0.1 checkpoint):** (a) **seeding at regime entry** — at CHOP→UP, `hl_ref` seeds with the most recent confirmed pivot low overall and `trend_high` seeds with the broken range high (avoids an instant continuation-BOS artifact); mirrors for CHOP→DOWN; (b) **within-bar ordering** — pivot bookkeeping runs BEFORE the FSM on the same confirmed bar, so a pivot confirming alongside a potential CHoCH re-anchors the reference first and the FSM evaluates against the NEW line (parity-relevant: the v0.2 Python reimplementation must replicate this tie-break bit-exact); (c) **all pivot bookkeeping is confirmed-bar gated** — realtime pivot flicker must never mutate `var` state (invisible in backfill, divergent live); (d) **engine detail #8 (parity-relevant):** T1's micro-chain grows and can trigger in the SAME bar pass — an engulfing bar that prints a lower low may trigger against the micro-LH formed that very bar; the Python reimplementation must replicate this ordering exactly.
- **Doctrine:** the engine is the measurement layer; trades are consumers. **Open positions never mutate the engine's structural reference** — otherwise regime labels become path-dependent on trade state and the harness's regime column stops being a measurement. The engine re-anchors to a flush low the honest way: pivot confirmation, with lag.
- No ER gate anywhere. A dim, resting trend is valid context; structure alone decides.

## 4. Shared definitions

- **Bar discipline:** everything evaluates on confirmed bars (`barstate.isconfirmed`). No intra-bar entries, ever.
- **Body close beyond a level:** `close` beyond `L` on a confirmed bar. Wicks never count as breaks.
- **Sweep (one-bar definition, the only definition):** long side — `low < L` AND confirmed `close ≥ L`. Short side mirrored. There is no two-bar sweep: a body close beyond `L` is a structural break, and the sweep ceases to exist.
- **Boundary Event Resolution (the handoff table — specced once; both trades reference it and define no penetration logic of their own).** For a bar interacting with governing level `L` (long context):

| Event | Bar-level definition | Owner |
|---|---|---|
| **HOLD** | `low ≥ L` | Trade #1 keeps the setup |
| **SWEEP** | `low < L` AND confirmed `close ≥ L` | **Trade #2** (2A when `L = HL_ref`; 2B when `L` = range boundary) |
| **BREAK** | confirmed body `close < L` | Nobody — structural event fires (CHoCH / range exit), setups on that side die |

One candle, one owner, no overlap. The table governs **setup ownership only** — in-trade management is per-trade (§7).

**Coincidence rule (sweep-and-trigger in one candle):** a single bar can be a SWEEP of `HL_ref` *and* satisfy Trade #1's S3 trigger (close above `micro_LH`). The SWEEP wins: **#2A owns the entry**; Trade #1's armed setup converts — Pine emits a #1 `CXL` with `reason=handoff` (no suppressed #1 ENT), and the 2A ENT carries factor `t1_coincident=1` so backfill can study these bars as a cohort. This is decidable same-bar, so it lives in Pine; **cross-bar concurrency lives in the evaluator** (§10).

## 5. Trade #1 — Pullback-continuation (long form; short = strict mirror)

**S1. Context (arm the watch):** 4H regime = UP. 1D regime ≠ DOWN (**1D chop allowed** — only an actively opposing 1D regime blocks). A most-recent confirmed `HL_ref` exists as backbone.

**S2. Pullback qualification:** price retraces toward the breakout zone / `HL_ref` region, holding above `HL_ref` (penetrations resolve via §4).
- **No minimum depth.** Any retrace that later prints the S3 trigger is valid. Depth is a measured factor, never a gate: log `depth_atr` (distance from trend high in ATRs), `depth_pct` (% of leg retraced), `touched_bz` (reached the last BOS level, boolean).
- **Depth never invalidates** (codified v7/v8 lesson). A pullback may run to a tick above `HL_ref` and remain valid. Only S4's body close kills it. Everything between "barely dipped" and "almost broke structure" is data, not doctrine.
- **OI behavior is a logged factor, never a gate** (§8 rationale). `oi_delta_setup` = net OI change from pullback start to current bar.

**S3. Entry trigger:** track the pullback's internal **micro lower-high chain** (`micro_LH` = high of the most recent bar from which the pullback made a subsequent lower low; the chain needs ≥1 member before any trigger can exist). Trigger = **confirmed bar closing above the current `micro_LH`**. OI turning up on the trigger bar = logged preference (`oi_trigger_dir`), never a requirement. Entry = that bar's close.

**S4. Invalidation:**
- **Thesis-exit (structural):** confirmed body close below `HL_ref` = CHoCH. Pre-entry: setup cancelled (`cancel` event). Post-entry: exit. Unconditional for Trade #1 — its premise *is* the trend.
- **Stop (catastrophic backstop only):** pullback low − `stop_buffer_atr × ATR(14)` (default 0.5). For gaps and fast moves; never the thesis boundary.

**S5. Targets:**
- **T1 = the trend high** — the most recent confirmed swing high before the pullback began. Partial there, **mandatory**. (The BOS level — the older swing high the last breakout closed through — is an entry support reference, never a destination: entries often fire at or near it, so targeting it would produce near-zero R and the skip gate would reject everything.) Tagging T1 is exactly the moment the trade prints the next BOS or stalls into a lower high — `t1_hit` and `bos_or_stall` are one observable.
- **Runner:** trails under each new confirmed higher low; exits on confirmed body close below it (same body-close grammar).
- **Skip gate:** if `(T1 − entry)/(entry − stop) < 1.5` → no trade, logged as `skip` with full vector. Skips are data.

## 6. Trade #2 — Flush-and-reclaim

**Doctrine (the only one in Trade #2):** **no entry without the reclaim close.** A wick that hasn't closed back inside isn't a flush, it's a breakdown in progress.

### 6A. In-trend variant (long form)

- **Context:** 4H regime = UP per the engine. **The only sweepable level in v1 is `HL_ref`** — sweeping arbitrary support levels is scope creep; other levels are backlog (§14).
- **Setup + entry:** a §4 SWEEP of `HL_ref`. **Entry = the sweep bar's own close** — earliest confirmed entry, uniquely defined (the bar simultaneously swept and reclaimed); a confirmation bar would cost price for protection the stop already provides. 2A does not require a qualified Trade-#1 pullback to precede it; it is its own setup. Wick-magnitude percentile (`wick_pctile`, ranked against its own distribution) is a logged factor, not a gate.
- **Thesis-exit:** 2A's premise is **"the reclaim is real"** — *not* "the wick low holds." A body close back below `HL_ref` is the textbook failed reclaim: price accepted below the structure it supposedly reclaimed. So **Trade #1 and Trade #2A thesis-die at the same line — body close below `HL_ref`** — and differ only in entry price and stop placement.
- **Stop (backstop):** flush wick low − `stop_buffer_atr × ATR(14)`. Structurally cheaper than Trade #1's stop relative to entry.
- **Target:** the trend high, same as Trade #1 — **targets derive from structure, not from setup type** (doctrine, §7). The flush doesn't earn a different destination; it earns a better price to the same destination. Skip gate ≥1.5R applies.

### 6B. Chop variant (both directions)

- **Context:** 4H regime = CHOP with a defined range (§3). 1D rule identical to Trade #1: only an opposing 1D regime blocks the direction (long sweep at range low is dead if 1D = DOWN; chop-on-chop is fully tradeable both ways).
- **Setup + entry:** §4 SWEEP of a range boundary (low pierces range low / high pierces range high, body closes back inside). Entry = the sweep bar's close.
- **Thesis-exit:** premise is "back inside the range" → confirmed body close beyond the swept boundary (as at entry).
- **Stop (backstop):** beyond the wick extreme ± `stop_buffer_atr × ATR(14)`.
- **Targets:** **T1 = range midpoint**, partial mandatory; runner toward the far boundary. Mean reversion's thesis is reversion to the mean — full rotation is the bonus, not the objective. Skip gate ≥1.5R applies (this is what self-skips too-narrow ranges).

## 7. Unified invalidation grammar (all three trades)

**Rule: thesis-exit = body close beyond the governing structural level. The stop order is for gaps and fast moves — never the thesis boundary. Each trade dies when its own entry thesis is negated; context (regime) gates entry, it does not force exits.**

| Trade | Thesis | Thesis-exit (structural) | Stop (backstop only) | T1 (structure-derived) |
|---|---|---|---|---|
| #1 PB-continuation | trend alive | body close < `HL_ref` (CHoCH) | pullback low − 0.5·ATR | trend high |
| #2A flush (trend) | reclaim is real | body close < `HL_ref` (same line as #1) | wick low − 0.5·ATR | trend high |
| #2B flush (chop) | back inside range | body close beyond swept boundary | wick extreme ± 0.5·ATR | range midpoint |

- **Snapshot semantics (binding):** outcome grading uses **entry-time snapshots** of the table's levels — `lvl` (thesis-exit line), `stop`, `t1`, plus `rhi`/`rlo` for 2B — carried in the ENT event (§9). They do not evolve mid-episode. Otherwise: `choch_while_open` is vacuous (an evolving thesis line makes every engine-CHoCH automatically a thesis-exit), and 2B's midpoint T1 becomes path-dependent on pivot-confirmation timing. The **runner's trail is the sole exception, by definition** — its thesis is "each new confirmed higher low holds," so it follows evolving pivots.
- **`choch_while_open`** is logged on any open trade when the *engine* fires a CHoCH at its **evolved** levels (relevant to runners/trails; it does not grade the exit — the snapshot does). If backfill shows such trades bleed, CHoCH gets promoted to a forced exit **by evidence, not prose**.
- The thesis-exit-vs-stop ruling is itself testable: because price keeps printing after a thesis-exit, the evaluator computes the counterfactual for every one (*would holding to the wick have recovered or stopped out?*). If thesis-exits systematically forfeit recoveries, the rule gets revised by evidence — same promotion path as everything else.

## 8. Factors — all logged, none gate

**Promotion path:** factor → gate, by backfill evidence only. Three reasons gating is banned at birth (recorded verbatim because each is load-bearing):
1. Gating hard-codes the hypothesis instead of testing it (e.g., "falling OI = profit-taking, not new shorts" is plausible folklore until validated on *these* setups).
2. A gated setup produces **no event** — no factor vector, no counterfactual, no way to ever learn whether the gated-out setups actually fail more often.
3. Derivatives data is single-exchange, occasionally gapped, absent on some symbols. A hard gate turns every data hiccup into a silently killed setup. As a factor, missing data is just `null` in the vector — never a kill.

| Factor | Definition |
|---|---|
| `regime`, `regime_1d`, `regime_age` | engine state 4H / last-confirmed-1D state / bars in current state |
| `oi_delta_setup` | net OI change over the setup window (pullback start→trigger for #1; the sweep bar for #2). **Priority-flagged:** OI contraction at the wick is the closest thing to direct liquidation evidence Pine can see; the flush thesis rests on it. It is the factor most likely to earn promotion — **which is exactly why it must start unpromoted.** |
| `oi_trigger_dir` | OI direction on the trigger/entry bar |
| `quadrant` | sign(Δprice) × sign(ΔOI) over a fixed 14-bar window — crude by design; a crude version of the right input beats a refined version of an ambiguous one |
| `funding_pctile` | funding/premium percentile vs its own trailing distribution (`null` where unavailable) |
| `depth_atr`, `depth_pct`, `touched_bz` | pullback depth in ATRs from trend high / % of leg / reached-BOS-level boolean |
| `wick_pctile` | flush wick magnitude percentile (Trade #2) |
| `micro_lh_count` | micro lower-highs formed before trigger (Trade #1) |
| `r_to_t1` | entry-to-T1 distance in R at signal time |
| `choch_while_open` | CHoCH fired during open episode (outcome-side join key) |
| `t1_coincident` | 2A entry bar also satisfied Trade #1's trigger (§4 coincidence rule) |
| `gvb` | giveback from the level in ATRs at fill (`|close − lvl|/ATR14`) — the measurable form of the v0.3 "that's not a snipe" eye-test; logged, never gates (added v0.4) |

**v0.4 implementation notes:** `oi_d` = setup-window OI %change for T1 (snapshot `oi0` at pullback start) and the sweep bar's own %change for 2A/2B; `oi_t` is T1-only. `fp` uses the Binance `_PREMIUM` derivative-metrics feed when present, else the perp-vs-spot premium — rank-invariant either way. OI auto-ticker `<prefix>:<ticker>_OI` resolves on Binance AND Bybit; ccxt cross-check confirmed sign agreement on all sampled windows (magnitude slack ±2% from feed sampling). **Caution:** the OI override `input.symbol` must hold a REAL symbol — TV validates it before `ignore_invalid_symbol` applies; a garbage override kills the study. T1's 1D block now emits `ARM rsn=1d` (visible, was silent — closes the v0.3 recall-audit observability gap). **v0.4.4 (pre-campaign emission fixes):** (1) blocked-ARM emits ONCE per pullback cycle via a `blk` flag — unbounded re-emission would silently FIFO-evict real events at the 500-label cap, the one failure `align_check` cannot detect; (2) all `SKP rsn=1d` events carry full computed snapshot levels (`stop`/`rt1`) so the campaign's 1D-gate pseudo-episodes are walkable; (3) `t1co` is set by T1's own handoff branch — consistent with the `CXL|handoff` event by construction (the pre-capture could disagree on same-bar chain-growth handoffs).

**v0.4.6 covariate enrichment (approved 2026-06-11; emission-only release, no logic changes):** new append-only tail keys on all trade tails — `os`/`os_pct` (linreg-anchored ATR-normalized overshoot, raw + percentrank; anchor computed on `[1]` so the signal bar never drags the fit), `swd` (sweep penetration depth in ATR, 2A/2B), `er` (Kaufman efficiency ratio, own window knob), `vz` (volume z-score on the signal bar), `dlt` (CVD via `ta.requestVolumeDelta` if budget-workable; confirmed bars only, `na` fallback), `age_t` (bars since the swept level was set, where cheap), `fr` (actual funding rate), `lqb`/`lqs` (liquidations buy = shorts force-closed / sell = longs force-closed — counterintuitive side semantics, memorize). **Derivative data migrates to the official `TradingView/Request` library** (`import TradingView/Request/3 as r`): OI via `r.openInterestCrypto()` (5-tuple; NEVER `nz()` raw OI — fabricates a 0 prior and a spurious bar-1 delta; ccxt cross-check re-run before trust), funding + liquidations via `r.cryptoDerivativeMetric()`. This deletes the OI-override `input.symbol` hazard outright (no override input remains). All calls global-scope (request budget), all downstream math na-guarded. Build-time check: confirm funding/liq history covers the harvest window — shallow history shows as `na` buckets in the report, never silently.

**Annotated mechanical correlations** (the evaluator must carry these as analysis annotations so the tape measure can't masquerade as edge): deeper pullbacks mechanically have larger R-to-T1 under the trend-high T1 definition; flush entries are mechanically deeper than pullback entries. **v0.4.6 additions:** liquidation spikes on sweep bars correlate mechanically with sweep depth (bigger flushes liquidate more) — condition `lqb`/`lqs` within `swd` bands, never raw; for the v0.5 roll-class (OS), `rt1` ≈ `os` by construction (target = stretch anchor, stop = sweep wick) — stretched OS trades "having big R" is the tape measure, not a finding; `rt1` conditioning is reported PER TRADE TYPE (the pooled rt1>3 row mixed trade types — critique #5). Discovering any of these in backfill is not a finding.

**Pre-registered coverage hole:** a V-shaped pullback that never prints a lower-low bar never forms a `micro_LH`, so Trade #1 **structurally cannot trigger on it**. ARM-without-ENT counts measure this hole. Discovering it in backfill is not a finding either.

## 9. Event taxonomy & schema

**Pine emits decision-time events only:** `ARM` (setup qualifies), `ENT` (entry signal), `SKP` (skip-gate rejection), `CXL` (pre-entry thesis death, with reason code — e.g. `reason=handoff` per §4). These are the moments that need the factor vector. **Outcomes are NOT exported from Pine** — `thesis_exit`, `stop_out`, `t1_hit`, `trail` are computed repo-side by the evaluator, deterministically from fetched bars per §7. Rationale: the evaluator has the bars anyway; it halves the label budget; outcome semantics live in exactly one place; and it is the doctrine taken seriously — Pine doesn't even narrate its homework, let alone grade it. Pine's on-chart entry marks remain the visual cross-check.

**ENT events additionally embed the entry-time level snapshot:** `lvl` (thesis-exit line), `stop`, `t1`, and for 2B `rhi`/`rlo`. The evaluator grades against these embedded prices, **never against its own structural reconstruction** — otherwise the Python side re-derives §7's level-dependent lines from a re-implemented pivot engine, which is the rejected two-script problem resurrected cross-language, with drift now invisible. (The evaluator does re-implement pivot detection for trail simulation — under the parity license of §10.)

The engine also emits two system events: `SYS|PING` on every regime transition, and `SYS|PIV` on every pivot confirmation (type H/L, pivot-bar timestamp, price) — the latter is the input to §10's pivot-parity check.

**Provenance, on every event:** `schema_version` (integer, starts at 1), script version string, `settings_hash` (deterministic short hash of all knob values, computed in-script). **Events generated under different parameter sets can never silently pool** — a backfill harvested before and after a threshold tweak is two datasets; the evaluator refuses to mix differing `settings_hash`/`schema_version` unless explicitly flagged. Contamination must be impossible to commit by accident.

**Source tag:** every event is `src=B` (backfill, MCP-harvested) or `src=L` (live, webhook-delivered). **Validation statistics never pool the two.** Backfill earns hypotheses; only the live log earns conviction.

**Label format (transport 1, MCP harvest):** one compact machine-readable label per event, pipe-delimited head + `key=value` tail, nothing decorative:

```
JF|<schema_v>|<script_v>|<cfg_hash>|<src>|<trade>|<event>|<dir>|<tf>|<bar_ts>|<px>|k=v|k=v|...
e.g. JF|1|0.2|a3f2|B|T1|ENT|L|240|1780444800|2.627|lvl=2.540|stop=2.528|t1=2.978|reg=U|reg1d=C|age=37|oi_d=-1.8|q=PU.OD|fp=62|d_atr=1.4|d_pct=38|bz=1|mlh=2|rt1=2.3
```

- `max_labels_count = 500`. **Dedup key = bar time + trade type + event type + direction** (ARM and CXL of the same setup must not collide; PIV additionally keys on `typ`) → repeated MCP harvests are idempotent.
- **Harvest-window inputs (`emit_from`/`emit_to`) are transport-layer, half-open `[from, to)`, and excluded from `settings_hash`:** they change which events are *emitted*, never what an event *means*. Chunked harvests of one config pool freely. (Added at v0.1 implementation; Pine keeps only the most recent `max_labels_count` labels, so deep backfill = slide the window chunk by chunk and merge.)
- **`show_labels` (display-layer, default OFF, also hash-excluded):** event labels are the machine transport, not chart annotations. Hidden = rendered fully transparent — the label objects still exist, so MCP harvest reads them unchanged; suppressing creation would leave nothing to harvest. (Added at v0.1.1.)
- A `PIV` event's `bar_ts` is the **pivot bar** (confirmation bar − `pivot_right`), which can precede `emit_from` — the *emission* bar is what the window gates. Bar fetches must extend ≥ `pivot_right` bars before the window start.
- If a backfill window exceeds 500 events, that is not a label problem: **harvest in chart-range chunks** (`chart_set_visible_range` / `chart_scroll_to_date` per chunk) — never invent a compression format.

**Alert format (transport 2, stage 2):** `alertcondition`/`alert()` carrying the **same event string** — the full checklist state at signal time, not just direction/price, so the analysis can ask which factors actually predicted outcomes. Two transports, one string: backfill and live logs cannot schema-drift.

## 10. Repo-side harness

**Layout:** `harness/events/*.jsonl` (append-only event logs) · `harness/bars/` (cached OHLCV per exchange/symbol/TF) · `harness/evaluator/*.py` (Python; deterministic, re-runnable, versioned with the repo) · `harness/README.md` (binding methodology doc, written in v0.1).

**Bars, not just events (load-bearing):** every harness promise — counterfactuals, R-to-T1 grading, t1_hit, trail simulation — needs the price series *after* each event, which events.jsonl alone cannot provide. Bars are pulled repo-side from the exchange API (ccxt or raw REST; Binance USDT-M perps to match TV symbols), keyed by symbol/timeframe, cached under `harness/bars/`. The label budget is never spent exporting OHLC through the chart.

**Timestamp-alignment check (hard precondition, part of v0.1 acceptance):** every harvested event's bar must exist in the fetched series with matching OHLC (tolerance knob ε for feed rounding; default exact-to-0.1%). Mismatched events are quarantined and reported, never silently included. This check *is* the pipe being proven — without it, misalignment surfaces months later as quietly wrong statistics.

**Evaluator rules (binding):**
- Episode simulation is sequential **per symbol per direction, across trade types**: a new entry cannot open while a same-direction episode is open, same type or not — an open 2A long plus a fresh #1 long is doubled exposure on the same thesis-exit line, not a second observation. Blocked ENTs are logged `skip_overlap`, first-class rows.
- Outcomes graded per §7 with distinct exit codes (`thesis_exit | stop_out | t1_hit | trail`), **against the ENT-embedded snapshot levels — never against the evaluator's own structural reconstruction.**
- The evaluator nevertheless **re-implements pivot detection** (trail simulation needs post-entry pivots regardless). The license for reimplementation is the **pivot-parity check**: the Python detector must reproduce every Pine `SYS|PIV` event **bit-exact** from fetched bars. Parity failure blocks v0.2 acceptance — silent cross-language drift is the rejected two-script problem resurrected where it can't be seen.
- Counterfactual computed for every thesis-exit (hold-to-stop: recovered or stopped?).
- Aggregate statistics reported on **non-overlapping time windows**; no significance claims pooled across windows.
- Never pools `src=B` with `src=L`; never pools across `settings_hash` or `schema_version` without an explicit override flag.
- Carries the §8 mechanical-correlation annotations on every report.
- Skips (`SKP`) and cancels (`CXL`) are first-class rows — the counterfactual population.

**First backfill campaign (after v0.4):** default basket BTCUSDT.P, ETHUSDT.P, SOLUSDT.P, NEARUSDT.P on 4H; window = as deep as chunked harvest allows. Output: factor-conditioned outcome report. No threshold tuning before this exists.

## 11. Rendering (v1 = minimal, by design)

`HL_ref`/`LH_ref` and range-boundary lines · entry/skip/cancel marks (distinct shapes) · regime background tint · version cell (table, top-right). Visual-encoding effort comes **last** — the v-series spent design effort making the instrument legible before knowing which parts mattered. Title/shorttitle carry the version per project convention (shorttitle ≤10 chars, e.g. `JFable0.1`).

## 12. Knobs (all defaults, all logged into `settings_hash`)

| Knob | Default |
|---|---|
| `pivot_left` / `pivot_right` | 3 / 3 |
| `atr_period` | 14 |
| `stop_buffer_atr` | 0.5 |
| `rr_min` (skip gate) | 1.5 |
| `quadrant_window` | 14 |
| `funding_pctile_window` | 200 |
| `wick_pctile_window` | 200 |
| `oi_symbol` / `funding_source` | auto from chart symbol; `null` factors when absent |
| `emit_from` / `emit_to` | transport-layer harvest window — half-open `[from, to)`, **excluded from `settings_hash`** (see §9) |
| `show_labels` | false — display-layer; hidden labels stay harvestable (transparent, not suppressed); **excluded from `settings_hash`** |
| `max_labels_count` | 500 |

## 13. Build order & acceptance criteria

Per increment: on-chart version bump (title + shorttitle + version cell), CHANGELOG entry (Jamal Fable build-log section), commit+push to main. One render at a time; each increment chart-verified before the next.

- **v0.1 — the pipe.** Regime engine (explicit §3 state machine) + event schema + system events (`SYS|PING` on each regime transition, `SYS|PIV` on each pivot confirmation, full provenance + stub vector) emitted → MCP-harvested → parsed to JSONL → **aligned against ccxt-fetched bars**. Acceptance = the three pins: (1) timestamp-alignment check passes on every harvested event; (2) every event carries `schema_version`/script version/`settings_hash` and the parser enforces no-pool; (3) label discipline verified — one machine label per event, idempotent re-harvest via dedup key (incl. event type), chunked-harvest path exercised.
- **v0.2 — Trade #1 detector.** ARM/ENT/SKP/CXL events live, ENT carrying the §7 snapshot levels; chart-quizzed against hand-traced examples (the Jamal-OB-style quiz loop — it caught two real rule bugs there). Acceptance additionally requires the **pivot-parity check** (§10): the Python detector reproduces every `SYS|PIV` bit-exact from fetched bars.
- **v0.3 — Trade #2 (A + B).** Handoff table observable end-to-end; sweep ownership quizzed at the boundary.
- **v0.4 — derivatives factors** wired into the vector (`oi_delta_setup`, `oi_trigger_dir`, `quadrant`, `funding_pctile`), `null`-safe.
- **First backfill campaign + evaluator report.** Only after this: any talk of thresholds, weights, or promotion.
- **Stage 2 — webhook listener** for `src=L`, only once a rule-set freezes. Same event string, separate log, never pooled.

## 14. Backlog (explicitly out of scope for v1)

- **Sweeps of levels other than `HL_ref` — PROMOTED to the v0.5 slot ("2A-general") after the v0.3 recall audit:** on BTC 4H Apr–Jun, ~312 sweep-and-reclaim bars existed against the last-5 confirmed pivots vs 8 considered at the kill line — scope, not thresholds, is the quantity constraint. v0.5 ships sweeps of the last-N confirmed pivots (both sides, stacked-level dedup rules), **filtered by whatever the backfill campaign's factor report proves** (`wkp`/`gvb`/`oi_d` selection). **Daily levels added to the level set (user decision 2026-06-11):** prior-day low/high (and prior-week as a cheap extra class) join the sweepable set alongside pivots, each event tagged `lvl_src=` (`piv`/`pdl`/`pdh`/`pwl`/`pwh`) so the report conditions on level class. Rationale: daily extremes are canonical stop-run liquidity, are known with ZERO confirmation lag (closes the pivot-lag side of coverage hole #2 with a measured comparison), and are TF-invariant. **Constraint: HL_ref/LH_ref remain pivot-based** — the regime kill line, CHoCH trigger, and T1 thesis line are structural and stay untouched; daily levels are 2A-general sweep sources only, judged by evidence before any promotion. **v0.5 is a UNIFIED generalized sweep-reclaim engine (user-approved 2026-06-11), absorbing the advisor's Trade #3 "OS" (overstretch reversal) rather than building a third standalone detector:** one sweep grammar (`low < lvl[1] and close > lvl`, mirror for shorts; level as of the PRIOR bar), with level classes tagged `lvl_src=` — `kill` (HL_ref/LH_ref, = today's 2A), `piv` (last-N confirmed pivots), `pdl/pdh/pwl/pwh` (daily/weekly extremes, zero confirmation lag), `roll` (rolling k-bar extreme, zero lag — closes coverage hole #3b). The roll class carries the OS stretch precondition: linreg-anchored ATR-normalized overshoot (`os`), extreme required within the last m bars (not necessarily the trigger bar), threshold = a LOOSE fixed scope knob, pre-registered as event-volume control and NOT a tuned edge (`os_pct` logged so the report finds the real cut; doctrine exception granted eyes-open — an ungated roll class fires too often for the 500-label transport). OS specifics: fires in ALL regimes, alignment logged not gated (`align=W/A/N`, chip color green/red/gray); target = the linreg anchor SNAPSHOTTED at entry (thesis-consistent doctrine exception: reversion-to-fair-value IS the thesis; `rt1`≈`os` mechanical correlation pre-registered in §8); stop = sweep extreme ± `stop_buffer_atr`; `rr_min` and 1D gates apply (1D opposition = logged `SKP rsn=1d`); same-bar coincidence with kill-class = emit both + `oco=1` cross-flag, dedup offline; stacked-level dedup rules shared across ALL classes. Prior evidence the OS thesis must answer to (pre-registered): Phase 1 killed enter-because-stretched (OS is enter-because-reclaimed GIVEN stretched — the trigger is the difference); campaign `wkp` INVERTED (violent wicks underperformed). New knobs (linreg window, m, k, N, os threshold) enter `settings_hash` → new cfg, full-basket re-harvest, no pooling with prior campaigns. Sequencing: v0.4.6 covariates ship FIRST so `os_pct` lands on existing-trade episodes before the OS detector exists — a free first read on the stretch thesis. **User rulings at the v0.4.6 checkpoint (2026-06-11):** rr_min STAYS 1.5; gvb STAYS logged-only; **the 1D gate is DEMOTED from gate to logged tag — a user ruling AGAINST the current n=9 evidence (blocked sweeps −0.25R as-if-taken), pre-registered as such**: implemented as `use_1d_gate` knob (hashed, default false), `reg1d` stays stamped on every event, and the report carries a STANDING "would-have-been-blocked cohort" table so the ruling itself is kept under judgment (flip the knob back if the cohort bleeds). T1's blocked-ARM machinery (`blk`, `ARM rsn=1d`) only operates when the knob is on. **Thesis-exit validation v2 is v0.5 evaluator scope (user request):** every thesis_exit carries cf_r (the R the trade would have realized if held: +rt1 if recovered, −1 if stopped) and rule_delta_r = r − cf_r; the report renders a per-trade-type table (n, recovered/stopped split, NET R saved by the rule) — the §7 third exit is kept or demoted on this number. **v0.5 taxonomy decisions:** kill-line sweeps STAY trade=2A and wall sweeps STAY 2B (history continuity); ALL new level classes emit under ONE new trade code `OS` with `lvl_src=` (`piv`/`pdl`/`pdh`/`pwl`/`pwh`/`roll`); one target doctrine for OS = entry-snapshotted linreg anchor; the stretch knob gates the roll class ONLY (piv/daily are sparse enough); stacked-level dedup = one OS event per bar per direction at the DEEPEST swept level, `n_lvls` counts the stack. **Campaign-2 pre-registrations (2026-06-11, from the external review of the s046 report — registered BEFORE any s0.5.0 data is seen):** (1) **HYPOTHESIS: quiet, shallow sweeps revert; violent ones don't — CONDITIONAL ON CHOP-TO-WEAK-TREND** (the vz/wkp/lq cluster contradicted the registered violence prior coherently across three covariates, but er>0.45 had ZERO events — the flush-in-strong-trend prior was never tested; the conclusion is "extend depth", not "demote violence"). (2) **Direction-oriented conditioning is an evaluator REQUIREMENT:** signed/directional covariates (`os`, `fr`, `fp`, `q`) are bucketed oriented-to-trade-direction (supportive = positive), never direction-blind — the flat pooled `os` table is the mechanical wash-out, not a finding. (3) The backfill window EXTENDS to Jan 2026 (chunked) under the v0.5 cfg so the er>0.45 bucket populates; basket unchanged. (4) `rr_min` sensitivity (the 2.0 counterfactual) is studied OFFLINE from logged `rt1` — no knob change earns itself yet. (5) Multiple-comparisons honesty: ~15 conditioning tables at n≈30 GUARANTEE impressive splits by chance (the vz split is p≈0.1 unadjusted); nothing promotes without surviving campaign 2's pre-registered test. reg1d=D 100%/4.49R on n=4 is a sentence, not a finding. (6) skip_overlap sensitivity appendix: episodes also walked independently to show whether the sequential rule shapes the dataset at these n. **v0.6 DESIGN (user rulings 2026-06-12, all campaign-2-evidence-backed):** ① OS sweep levels = prev DAY/WEEK extremes ONLY (piv/roll classes toggled OFF via hashed bools, not deleted — their s0.5.0 data remains minable offline; the stretch gate dies with the roll class). ② **UNIFIED TARGETS:** every trade (T1/2A/2B/OS) targets the NEAREST overhead structure from the candidate set {range midpoint, opposing kill line, trend extreme, prev D/W high/low, weekly VWAP, nearest unfilled opposite FVG (near edge; removed when fully traded through)} — frozen at entry, identity logged `tgt_src=`; the linreg anchor is DEMOTED from target to logged factor (removes the §14 doctrine exception; kills the OS rt1>3 pathology, 8% win). A dust-target (e.g. tiny FVG overhead) failing the gate is CORRECT — price directly under a ceiling is a bad entry. ③ **rr_min default 1.5 → 1.0** ("nearest structure must pay ≥1R") — near targets get hit; campaign-2 pseudo-episodes in the 1.0–1.5 band were weakly positive even against FAR targets. ④ OS loses the §7 thesis exit (campaign 2: −4.78R net on n=74; its lvl is a swept level, not a regime line) — evaluator-side rule, 2B/T1 keep theirs (+3.43/+0.36). ⑤ **Stretch-episode marker** `SYS|STR`: one event per episode when |os| first ≥ 2.5 ATR (dir U/D), hysteresis re-arm only after |os| < 1.0 ATR; both knobs hashed; stretch is INSTRUMENTATION not trigger (campaign-2 verdict on stretched fades). ⑥ Report: rr-pseudo table EXCLUDES rt1=na rows (anchor-wrong-side artifact graded meaninglessly), lq conditioned per-symbol (percentile, units not cross-comparable). Entry CONDITIONS unchanged for all trades — the candidate-bar set (ENT∪SKP-rr per trade/dir) is the v0.5→v0.6 diff invariant. Harvest rule at this density: ALWAYS ≤6-week emit-window chunks (500-label FIFO eviction proven on NEAR). The campaign's evaluator additionally computes **MFE (max favorable excursion)** per episode, since the conservative prior-extreme T1 was shown to cap measured R well below realized moves (June waterfall skips at 0.5–1.0R to the prior low preceded far larger extensions).
- CHoCH promoted to forced exit (pending `choch_while_open` evidence).
- Any factor promoted to gate (pending backfill evidence).
- `strategy()` cross-check of the evaluator.
- **PRE-STAGE-2 GATE — `barstate.isconfirmed` inside the `request.security` 1D engine copy:** TV's documented `barstate.*` behavior in security contexts is counterintuitive (it can reflect chart-bar state, not the requested timeframe's), so the D-copy's `var` state could mutate on a *developing* daily bar intra-day and carry corruption forward. Backfill is immune (all bars confirmed); LIVE operation must verify this before the webhook stage ships — robust pattern: gate the D-copy's mutations on a daily rollover detector (`ta.change(time("D"))`) instead.
- Visual polish beyond §11.
- Jamal OB integration (parked separately — see `2026-06-09-jamal-ob-parked-state.md`).

## 15. Anti-overfitting commitments (v-series lessons, baked in)

1. **No gates without evidence** — every filter starts as a logged factor (§8).
2. **No silent dataset pooling** — provenance + source tags enforced by the evaluator (§9, §10).
3. **No in-chart win-rate panels** — every in-chart scoreboard lies to its author; judgment lives in the repo (§2).
4. **Mechanical correlations pre-registered** — the tape measure is not an edge (§8).
5. **Skips and cancels logged** — the counterfactual population exists from day one (§5, §10).
6. **Engine/trade separation** — measurement never path-depends on position state (§3).
7. **One sweep definition, one handoff table, one invalidation grammar** — shared sections referenced, never re-implemented per trade (§4, §7).
