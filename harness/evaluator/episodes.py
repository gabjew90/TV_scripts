"""Campaign episode walker (spec section 7 + campaign plan decisions 1-6).

Every ENT (or pseudo-episode from a SKP) is walked forward through exchange
bars against its OWN snapshot levels (lvl/stop/t1 from the event tail - never
reconstructed). Pre-registered rules:
  - Ambiguous bar (stop AND target touched): grades STOP FIRST, ambiguous=1.
  - R accounting v1: stop_out=-1R; t1_hit=+rt1 (full position); thesis_exit =
    mark-to-exit R at the confirmed close. Trail/partials NOT simulated in v1.
  - Counterfactual on thesis_exit: keep walking - target-before-stop =
    'recovered', stop-first = 'stopped', neither by data end = 'open'.
  - MFE: max favorable excursion in R over the episode's life (entry->exit
    bar inclusive; to data end for open episodes); mfe30_r capped at 30 bars.
  - Sequential per (symbol, dir) across trade types: an ENT at or before the
    open episode's exit bar -> skip_overlap.

Bars: list of (ts, o, h, l, c) tuples sorted ascending (CSV loaders adapt).

THIRD EXIT REMOVED (user ruling 2026-06-12): trades run to stop or target only.
Evidence: campaigns 2-4 net rule_delta_r was negative (OS/2A strongly negative;
2B/T1 mildly positive but overruled for one-rule simplicity). Flag retained for
reversibility - flipping it restores section-7 thesis-exit grading exactly.
"""

APPLY_THESIS_EXIT = False


def _f(factors, key):
    v = factors.get(key)
    if v is None or v == "na":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def walk_episode(ev, bars):
    """Walk one event forward. Returns the episode dict (exit_code None if the
    event lacks levels or has no bars after entry)."""
    factors = ev["factors"]
    lvl, stop, t1 = _f(factors, "lvl"), _f(factors, "stop"), _f(factors, "t1")
    rt1 = _f(factors, "rt1")
    ent = float(ev["px"])
    is_long = ev["dir"] == "L"
    ep = {"ent_ts": ev["bar_ts"], "dir": ev["dir"], "trade": ev["trade"],
          "symbol": ev.get("symbol", "?"), "ent": ent, "lvl": lvl, "stop": stop,
          "t1": t1, "rt1": rt1, "factors": factors, "exit_code": None,
          "exit_ts": None, "exit_px": None, "r": None, "mfe_r": None,
          "mfe30_r": None, "ambiguous": 0, "counterfactual": None,
          "cf_r": None, "rule_delta_r": None,
          "pseudo": factors.get("rsn") if factors.get("rsn") in ("rr", "1d") else None}
    if lvl is None or stop is None or t1 is None:
        ep["exit_code"] = None
        ep["drop_reason"] = "no_levels"
        return ep
    risk = abs(ent - stop)
    if risk <= 0:
        ep["drop_reason"] = "bad_risk"
        return ep

    idx = {b[0]: i for i, b in enumerate(bars)}
    if ev["bar_ts"] not in idx:
        ep["drop_reason"] = "entry_bar_missing"
        return ep
    start = idx[ev["bar_ts"]] + 1

    best = ent
    thesis_ts = None
    for j in range(start, len(bars)):
        ts, _o, h, l, c = bars[j]
        nbar = j - start + 1
        # MFE tracking (until exit; mfe30 capped)
        best = max(best, h) if is_long else min(best, l)
        mfe = (best - ent) / risk if is_long else (ent - best) / risk
        if nbar <= 30:
            ep["mfe30_r"] = mfe
        if thesis_ts is None:
            stop_hit = (l <= stop) if is_long else (h >= stop)
            tgt_hit = (h >= t1) if is_long else (l <= t1)
            if stop_hit and tgt_hit:
                ep.update(exit_code="stop_out", exit_ts=ts, exit_px=stop, r=-1.0,
                          ambiguous=1, mfe_r=mfe)
                return ep
            if stop_hit:
                ep.update(exit_code="stop_out", exit_ts=ts, exit_px=stop, r=-1.0,
                          mfe_r=mfe)
                return ep
            if tgt_hit:
                r = rt1 if rt1 is not None else abs(t1 - ent) / risk
                ep.update(exit_code="t1_hit", exit_ts=ts, exit_px=t1, r=r, mfe_r=mfe)
                return ep
            thesis_dead = APPLY_THESIS_EXIT and ((c < lvl) if is_long else (c > lvl))
            if thesis_dead:
                r = (c - ent) / risk if is_long else (ent - c) / risk
                ep.update(exit_code="thesis_exit", exit_ts=ts, exit_px=c, r=r,
                          mfe_r=mfe, counterfactual="open")
                thesis_ts = ts
        else:
            # counterfactual walk after thesis exit
            stop_hit = (l <= stop) if is_long else (h >= stop)
            tgt_hit = (h >= t1) if is_long else (l <= t1)
            if stop_hit:
                # thesis-exit v2 (2026-06-11): price-tag the third exit.
                # cf_r = R the trade would have realized if HELD to stop/target;
                # rule_delta_r = R actually saved (+) or cost (-) by exiting early.
                ep["counterfactual"] = "stopped"
                ep["cf_r"] = -1.0
                ep["rule_delta_r"] = ep["r"] - ep["cf_r"]
                return ep
            if tgt_hit:
                ep["counterfactual"] = "recovered"
                ep["cf_r"] = rt1 if rt1 is not None else abs(t1 - ent) / risk
                ep["rule_delta_r"] = ep["r"] - ep["cf_r"]
                return ep
    if ep["exit_code"] is None:
        ep.update(exit_code="open", mfe_r=(best - ent) / risk if is_long else (ent - best) / risk)
    return ep


def build_episodes(events, bars, pseudo=False):
    """Sequential episode construction per (symbol, dir) ACROSS trade types.
    pseudo=False walks ENT events; pseudo=True walks SKP rsn in (rr, 1d).
    Returns (episodes, overlapped_events). Level-less events are dropped
    (reported via drop list inside episodes with exit_code None filtered out)."""
    if pseudo:
        cand = [e for e in events if e["event"] == "SKP"
                and e["factors"].get("rsn") in ("rr", "1d")]
    else:
        cand = [e for e in events if e["event"] == "ENT"]
    cand.sort(key=lambda e: e["bar_ts"])
    open_until = {}     # (symbol, dir) -> exit_ts of the open/last episode
    episodes, overlapped = [], []
    for ev in cand:
        key = (ev.get("symbol", "?"), ev["dir"])
        until = open_until.get(key)
        if until is not None and ev["bar_ts"] <= until:
            overlapped.append(ev)
            continue
        ep = walk_episode(ev, bars)
        if ep.get("drop_reason"):
            continue
        episodes.append(ep)
        # an 'open' episode blocks to the end of data; others to their exit bar
        open_until[key] = ep["exit_ts"] if ep["exit_ts"] is not None else bars[-1][0]
    return episodes, overlapped
