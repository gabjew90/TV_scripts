"""Campaign report generator (campaign plan Task 2).

Loads s0.4.5 event JSONLs ONLY (no-pool: single settings_hash+schema set
unless --allow-mixed), builds sequential episodes per symbol from that
symbol's bars CSV, walks pseudo-episodes (SKP rsn=rr|1d) INDIVIDUALLY
(counterfactual questions need independence, not portfolio sequencing),
and renders the factor-conditioned markdown report.
"""
import argparse
import csv
import glob
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.episodes import build_episodes, walk_episode

HARNESS = Path(__file__).resolve().parents[1]
EVENT_GLOB = "*_s0.6.0_*.jsonl"
LQ_SPLIT = 3834.5  # lq_tot inner-band edge = harvested median over sweep ENTs (n=32).
                   # CAVEAT: lq units are feed-native and NOT comparable across symbols —
                   # a global split is a coarse v1; per-symbol normalization is the v2 fix.
BARS_MAP = {
    "BTCUSDT.P": "binanceusdm_BTCUSDT_4h.csv",
    "ETHUSDT.P": "binanceusdm_ETHUSDT_4h.csv",
    "SOLUSDT.P": "binanceusdm_SOLUSDT_4h.csv",
    "NEARUSDT.P": "binanceusdm_NEARUSDT_4h.csv",
}

PREREG = """## Pre-registered annotations (read FIRST — discovering these is not a finding)
- Deeper pullbacks mechanically have larger R-to-T1 (trend-high T1 definition).
- Flush entries are mechanically deeper than pullback entries.
- V-shaped pullbacks cannot trigger T1 (no micro-LH) — ARM-without-ENT counts measure the hole.
- Ambiguous bars (stop AND target touched) grade STOP-FIRST: results are conservative.
- R accounting v1: full position at T1 (rt1); NO trail/partial simulation — stated scope cut.
- Monthly windows are reported separately; pooled rows carry no significance claims.
- Pseudo-episodes are walked independently (no portfolio sequencing) — they answer
  "what would this class of skipped signal have done", not "what would the book have done".
- Liquidation totals correlate mechanically with sweep depth; lq is read WITHIN swd bands.
- rt1 is conditioned per trade type; the pooled rt1 table from the 2026-06 campaign mixed geometries.
- CAMPAIGN-2 HYPOTHESIS (pre-registered 2026-06-11, BEFORE any s0.5.0 data was seen):
  quiet, shallow sweeps revert; violent ones don't - CONDITIONAL ON CHOP (er>0.45 had
  ZERO events in campaign 1; the violence prior is untested in trends, not refuted).
- Multiple-comparisons honesty: ~15 conditioning tables at n~30 GUARANTEE impressive
  splits by chance (campaign 1's vz split was ~p0.1 unadjusted). Nothing promotes
  without surviving this campaign's pre-registered test.
- The 1D gate is OFF by user ruling (2026-06-11, AGAINST the n=9 campaign-1 evidence);
  the blocked-cohort table below is that ruling's standing scoreboard.
- OS roll-class rt1 correlates with os by construction (target = the stretch anchor).
"""


def load_bars(path):
    rows = list(csv.DictReader(open(path)))
    return [(int(r["ts_sec"]), float(r["open"]), float(r["high"]), float(r["low"]),
             float(r["close"])) for r in rows]


def load_events(allow_mixed=False):
    files = sorted(glob.glob(str(HARNESS / "events" / EVENT_GLOB)))
    by_symbol = defaultdict(list)
    provenance = set()
    for f in files:
        for line in open(f):
            e = json.loads(line)
            provenance.add((e["schema_v"], e["cfg"]))
            # lq_tot synthesized at load: a missing SIDE legitimately means 0
            # liquidations on that side (unlike OI, where nz fabricates state);
            # BOTH sides missing -> key absent -> "na" bucket.
            fct = e.get("factors", {})
            b, s = fct.get("lqb"), fct.get("lqs")
            if (b not in (None, "na")) or (s not in (None, "na")):
                fct["lq_tot"] = str((0 if b in (None, "na") else float(b)) +
                                    (0 if s in (None, "na") else float(s)))
            by_symbol[e["symbol"]].append(e)
    if len(provenance) > 1 and not allow_mixed:
        raise SystemExit(f"NO-POOL VIOLATION: mixed provenance {provenance}; rerun with --allow-mixed to override")
    return by_symbol, files


def month_of(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m")


def fnum(factors, key):
    v = factors.get(key)
    if v in (None, "na"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def stats_row(eps):
    closed = [e for e in eps if e["exit_code"] in ("t1_hit", "stop_out", "thesis_exit")]
    wins = [e for e in closed if e["exit_code"] == "t1_hit"]
    rs = [e["r"] for e in closed if e["r"] is not None]
    mfes = [e["mfe_r"] for e in eps if e["mfe_r"] is not None]
    return {
        "n": len(eps), "closed": len(closed), "win%": (100 * len(wins) / len(closed)) if closed else None,
        "avg_r": statistics.mean(rs) if rs else None,
        "med_mfe": statistics.median(mfes) if mfes else None,
        "ambig": sum(e["ambiguous"] for e in eps),
        "open": sum(1 for e in eps if e["exit_code"] == "open"),
    }


def fmt(v, nd=2):
    return "—" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out) + "\n"


def bucket_rows(eps, key, edges, labels):
    """Bucket episodes by a numeric factor; returns table rows."""
    rows = []
    for lab, (lo, hi) in zip(labels, edges):
        sub = []
        for e in eps:
            v = fnum(e["factors"], key)
            if v is not None and (lo is None or v >= lo) and (hi is None or v < hi):
                sub.append(e)
        s = stats_row(sub)
        rows.append([lab, s["n"], fmt(s["win%"], 0), fmt(s["avg_r"]), fmt(s["med_mfe"])])
    miss = [e for e in eps if fnum(e["factors"], key) is None]
    if miss:
        s = stats_row(miss)
        rows.append(["na", s["n"], fmt(s["win%"], 0), fmt(s["avg_r"]), fmt(s["med_mfe"])])
    return rows


def oneD_blocked(e):
    """Would the campaign-era 1D gate have blocked this? (dir vs 1D regime opposition)"""
    r1d = (e.get("factors") or {}).get("reg1d")
    return (e["dir"] == "L" and r1d == "D") or (e["dir"] == "S" and r1d == "U")


def oriented(e, key):
    """Signed covariate oriented to trade direction: positive = supportive of the trade.
    os: stretched-down supports a long -> orient = -os for L, +os for S.
    fr/fp: crowded-long (positive funding / high pctile) supports a SHORT fade ->
           +for S, -for L (fp is centered at 50 before orienting)."""
    v = fnum(e["factors"], key)
    if v is None:
        return None
    if key == "fp":
        v = v - 50.0
    return -v if e["dir"] == "L" else v


def oriented_q(e):
    """Quadrant with the price leg made trade-relative: PW=price moved WITH trade dir pre-entry."""
    q = e["factors"].get("q", "na")
    if q == "na" or "." not in q:
        return "na"
    px, oi = q.split(".")
    with_trade = (px == "PU") == (e["dir"] == "L")
    return ("PW" if with_trade else "PA") + "." + oi


def bucket_rows_nested(eps, okey, oedges, olabels, ikey, iedges, ilabels):
    """Two-level conditioning: outer factor bands, inner factor bands within each."""
    rows = []
    for olab, (olo, ohi) in zip(olabels, oedges):
        outer = []
        for e in eps:
            v = fnum(e["factors"], okey)
            if v is not None and (olo is None or v >= olo) and (ohi is None or v < ohi):
                outer.append(e)
        for ilab, (ilo, ihi) in zip(ilabels, iedges):
            sub = []
            for e in outer:
                w = fnum(e["factors"], ikey)
                if w is not None and (ilo is None or w >= ilo) and (ihi is None or w < ihi):
                    sub.append(e)
            s = stats_row(sub)
            rows.append([f"{olab} | {ilab}", s["n"], fmt(s["win%"], 0), fmt(s["avg_r"]), fmt(s["med_mfe"])])
    return rows


def cat_rows(eps, key):
    groups = defaultdict(list)
    for e in eps:
        groups[e["factors"].get(key, "na")].append(e)
    rows = []
    for k in sorted(groups):
        s = stats_row(groups[k])
        rows.append([k, s["n"], fmt(s["win%"], 0), fmt(s["avg_r"]), fmt(s["med_mfe"])])
    return rows


FACTOR_HEADER = ["bucket", "n", "win%", "avg R", "med MFE"]


def render_report(eps_all, pseudo_all, overlap_counts, file_list, indep_all=None):
    L = []
    L.append(f"# Jamal Fable — Backfill Campaign Report ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})\n")
    L.append(PREREG)
    L.append(f"\nSources ({len(file_list)} provenance files, glob `{EVENT_GLOB}`):\n" +
             "\n".join(f"- {Path(f).name}" for f in file_list) + "\n")

    # ── Headline ──
    L.append("\n## Headline — real episodes (sequential per symbol-direction)\n")
    rows = []
    for (sym, trade, d), eps in sorted(group_by(eps_all, lambda e: (e["symbol"], e["trade"], e["dir"])).items()):
        s = stats_row(eps)
        rows.append([sym, trade, d, s["n"], s["closed"], fmt(s["win%"], 0), fmt(s["avg_r"]),
                     fmt(s["med_mfe"]), s["ambig"], s["open"]])
    L.append(table(["symbol", "trade", "dir", "n", "closed", "win%", "avg R", "med MFE", "ambig", "open"], rows))
    s = stats_row(eps_all)
    L.append(f"\n**ALL (pooled, no significance claim):** n={s['n']} closed={s['closed']} "
             f"win%={fmt(s['win%'],0)} avgR={fmt(s['avg_r'])} medMFE={fmt(s['med_mfe'])} "
             f"open={s['open']} | skip_overlap dropped: {sum(overlap_counts.values())}\n")

    # ── 1D ruling-watch (standing scoreboard for the 2026-06-11 gate-off ruling) ──
    L.append("\n## Standing ruling-watch: 1D gate OFF (2026-06-11 user ruling, against n=9 evidence)\n")
    blocked = [e for e in eps_all if oneD_blocked(e)]
    passed_ = [e for e in eps_all if not oneD_blocked(e)]
    rows = []
    for lab, grp in (("would-have-been-BLOCKED", blocked), ("would-have-passed", passed_)):
        s2 = stats_row(grp)
        rows.append([lab, s2["n"], s2["closed"], fmt(s2["win%"], 0), fmt(s2["avg_r"]), fmt(s2["med_mfe"])])
    L.append(table(["cohort", "n", "closed", "win%", "avg R", "med MFE"], rows))
    L.append("\n_If the blocked cohort bleeds as n grows, flip `use_1d_gate` back on._\n")

    # ── Monthly windows ──
    L.append("\n## Monthly windows (not pooled for significance)\n")
    rows = []
    for m, eps in sorted(group_by(eps_all, lambda e: month_of(e["ent_ts"])).items()):
        st = stats_row(eps)
        rows.append([m, st["n"], st["closed"], fmt(st["win%"], 0), fmt(st["avg_r"]), fmt(st["med_mfe"])])
    L.append(table(["month", "n", "closed", "win%", "avg R", "med MFE"], rows))

    # ── Factor conditioning ──
    L.append("\n## Factor conditioning (real episodes)\n")
    specs = [
        ("gvb", [(None, 0.3), (0.3, 0.7), (0.7, None)], ["<0.3", "0.3-0.7", ">0.7"]),
        ("wkp", [(None, 50), (50, 85), (85, None)], ["<50", "50-85", ">85"]),
        ("fp",  [(None, 25), (25, 75), (75, None)], ["<25", "25-75", ">75"]),
        ("oi_d", [(None, 0), (0, None)], ["<0 (contracting)", ">=0 (building)"]),
        ("d_pct", [(None, 60), (60, 100), (100, None)], ["<60", "60-100", ">100 (wick-swept)"]),
        ("age", [(None, 10), (10, 50), (50, None)], ["<10", "10-50", ">50"]),
        ("rt1", [(None, 2.0), (2.0, 3.0), (3.0, None)], ["1.5-2", "2-3", ">3"]),
        ("os",  [(None, -1.0), (-1.0, 1.0), (1.0, None)], ["<-1 (stretched dn)", "-1..1", ">1 (stretched up)"]),
        ("osp", [(None, 50), (50, 85), (85, None)], ["<50", "50-85", ">85"]),
        ("er",  [(None, 0.2), (0.2, 0.45), (0.45, None)], ["<0.2 (chop)", "0.2-0.45", ">0.45 (trendy)"]),
        ("vz",  [(None, 0), (0, 1.5), (1.5, None)], ["<0", "0-1.5", ">1.5 (heavy)"]),
        ("fr",  [(None, 0), (0, None)], ["<0 (shorts pay)", ">=0 (longs pay)"]),
        ("swd", [(None, 0.3), (0.3, 0.8), (0.8, None)], ["<0.3", "0.3-0.8", ">0.8 (deep)"]),
        ("age_t", [(None, 10), (10, 40), (40, None)], ["<10", "10-40", ">40"]),
    ]
    for key, edges, labels in specs:
        L.append(f"\n### by `{key}`\n")
        L.append(table(FACTOR_HEADER, bucket_rows(eps_all, key, edges, labels)))
    for key in ("q", "t1co", "reg1d"):
        L.append(f"\n### by `{key}`\n")
        L.append(table(FACTOR_HEADER, cat_rows(eps_all, key)))

    L.append("\n### by `rt1` PER TRADE TYPE (pooled rt1 mixes trade geometries — pre-registered)\n")
    for tr, teps in sorted(group_by(eps_all, lambda e: e["trade"]).items()):
        L.append(f"\n**{tr}:**\n")
        L.append(table(FACTOR_HEADER, bucket_rows(teps, "rt1",
                 [(None, 2.0), (2.0, 3.0), (3.0, None)], ["1.5-2", "2-3", ">3"])))

    L.append("\n### by `lq_tot` WITHIN `swd` bands (mechanical correlation pre-registered in §8)\n")
    L.append(table(FACTOR_HEADER, bucket_rows_nested(
        eps_all, "swd", [(None, 0.3), (0.3, 0.8), (0.8, None)], ["swd<0.3", "swd 0.3-0.8", "swd>0.8"],
        "lq_tot", [(None, LQ_SPLIT), (LQ_SPLIT, None)], ["lq low", "lq high"])))

    # ── Direction-oriented conditioning (s046 review: fixes the pooled-signed wash-out) ──
    L.append("\n## Direction-ORIENTED conditioning (supportive = positive; fixes the pooled-signed-factor wash-out)\n")
    for key in ("os", "fr", "fp"):
        L.append(f"\n### by oriented `{key}`\n")
        rows = []
        for lab, lo, hi in (("against (<0)", None, 0.0), ("supportive (>=0)", 0.0, None)):
            sub = []
            for e in eps_all:
                w = oriented(e, key)
                if w is not None and (lo is None or w >= lo) and (hi is None or w < hi):
                    sub.append(e)
            s2 = stats_row(sub)
            rows.append([lab, s2["n"], fmt(s2["win%"], 0), fmt(s2["avg_r"]), fmt(s2["med_mfe"])])
        L.append(table(FACTOR_HEADER, rows))
    L.append("\n### by oriented `q` (PW=price moved with trade pre-entry, PA=against)\n")
    qgroups = defaultdict(list)
    for e in eps_all:
        qgroups[oriented_q(e)].append(e)
    rows = []
    for k in sorted(qgroups):
        s2 = stats_row(qgroups[k])
        rows.append([k, s2["n"], fmt(s2["win%"], 0), fmt(s2["avg_r"]), fmt(s2["med_mfe"])])
    L.append(table(FACTOR_HEADER, rows))

    # ── OS: the new population, judged separately ──
    os_eps = [e for e in eps_all if e["trade"] == "OS"]
    if os_eps:
        L.append("\n## OS — generalized sweeps (NEW population, judge separately)\n")
        for key in ("lvl_src", "align"):
            L.append(f"\n### OS by `{key}`\n")
            L.append(table(FACTOR_HEADER, cat_rows(os_eps, key)))
        L.append("\n### OS by `osp` (rt1~os is MECHANICAL for roll class — pre-registered)\n")
        L.append(table(FACTOR_HEADER, bucket_rows(os_eps, "osp", [(None, 50), (50, 85), (85, None)], ["<50", "50-85", ">85"])))
        L.append("\n### OS by `vz` (the campaign-1 quiet-bar lead, tested out-of-population)\n")
        L.append(table(FACTOR_HEADER, bucket_rows(os_eps, "vz", [(None, 0), (0, 1.5), (1.5, None)], ["<0", "0-1.5", ">1.5"])))

    # ── Sensitivity appendices (s046 review) ──
    L.append("\n## Sensitivity appendices\n")
    L.append("\n### (i) rr_min sensitivity — offline counterfactual, no knob change\n")
    rows = []
    for lab, grp in (("book as-is (rr 1.5)", eps_all),
                     ("book if rr_min were 2.0", [e for e in eps_all
                      if (v := fnum(e["factors"], "rt1")) is not None and v >= 2.0])):
        s2 = stats_row(grp)
        rows.append([lab, s2["n"], s2["closed"], fmt(s2["win%"], 0), fmt(s2["avg_r"]), fmt(s2["med_mfe"])])
    L.append(table(["book", "n", "closed", "win%", "avg R", "med MFE"], rows))
    if indep_all is not None:
        L.append("\n### (ii) skip_overlap sensitivity — every ENT walked independently (sequential rule OFF)\n")
        s2 = stats_row(indep_all)
        L.append(f"n={s2['n']} closed={s2['closed']} win%={fmt(s2['win%'],0)} "
                 f"avgR={fmt(s2['avg_r'])} medMFE={fmt(s2['med_mfe'])} "
                 f"(sequential book: n={len(eps_all)}) — if these stories diverge, "
                 f"the sequential rule is shaping the dataset.\n")

    # ── Gate questions (pseudo-episodes) ──
    L.append("\n## Gate questions (pseudo-episodes, walked independently)\n")
    # v0.6 artifact fix: rt1=na skips (target on the wrong side of entry at signal
    # time) grade meaninglessly when walked — they are skipped-on-geometry, not
    # skipped-on-R, and are EXCLUDED from the rr-gate table.
    rr_ps = [e for e in pseudo_all if e["pseudo"] == "rr" and fnum(e["factors"], "rt1") is not None]
    L.append("\n### (a) rr gate — skipped-on-R signals, bucketed by their rt1\n")
    L.append(table(FACTOR_HEADER, bucket_rows(rr_ps, "rt1",
             [(None, 0.5), (0.5, 1.0), (1.0, 1.25), (1.25, 1.5)],
             ["<0.5", "0.5-1.0", "1.0-1.25", "1.25-1.5"])))
    oned_ps = [e for e in pseudo_all if e["pseudo"] == "1d"]
    s = stats_row(oned_ps)
    L.append("\n### (b) 1D gate — blocked sweeps, graded as if taken\n")
    L.append(f"n={s['n']} closed={s['closed']} win%={fmt(s['win%'],0)} avgR={fmt(s['avg_r'])} "
             f"medMFE={fmt(s['med_mfe'])}\n")
    L.append("\n### (c) thesis-exit v2 — net R saved by the third exit (per trade type)\n")
    tx = [e for e in eps_all if e["exit_code"] == "thesis_exit"]
    rows = []
    groups = sorted(group_by(tx, lambda e: e["trade"]).items())
    for tr, grp in groups:
        deltas = [e["rule_delta_r"] for e in grp if e.get("rule_delta_r") is not None]
        rec = sum(1 for e in grp if e["counterfactual"] == "recovered")
        stp = sum(1 for e in grp if e["counterfactual"] == "stopped")
        rows.append([tr, len(grp), rec, stp, fmt(sum(deltas)) if deltas else "—"])
    all_d = [e["rule_delta_r"] for e in tx if e.get("rule_delta_r") is not None]
    rows.append(["ALL", len(tx), sum(1 for e in tx if e["counterfactual"] == "recovered"),
                 sum(1 for e in tx if e["counterfactual"] == "stopped"),
                 fmt(sum(all_d)) if all_d else "—"])
    L.append(table(["trade", "n", "recovered (exit cost us)", "stopped (exit saved us)",
                    "NET R saved by rule"], rows))
    return "\n".join(L)


def group_by(items, keyfn):
    g = defaultdict(list)
    for it in items:
        g[keyfn(it)].append(it)
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HARNESS / "reports" / "campaign.md"))
    ap.add_argument("--allow-mixed", action="store_true")
    args = ap.parse_args()
    by_symbol, files = load_events(args.allow_mixed)
    eps_all, pseudo_all, overlap_counts, indep_all = [], [], {}, []
    for sym, evs in sorted(by_symbol.items()):
        bars_file = HARNESS / "bars" / BARS_MAP.get(sym, "")
        if not bars_file.exists():
            print(f"WARN: no bars for {sym} — symbol skipped ({len(evs)} events)")
            continue
        bars = load_bars(bars_file)
        eps, overlapped = build_episodes(evs, bars)
        overlap_counts[sym] = len(overlapped)
        eps_all.extend(eps)
        for ev in evs:
            if ev["event"] == "ENT":          # sensitivity appendix: no sequential rule
                p = walk_episode(ev, bars)
                if not p.get("drop_reason"):
                    indep_all.append(p)
            if ev["event"] == "SKP" and ev["factors"].get("rsn") in ("rr", "1d"):
                p = walk_episode(ev, bars)
                if not p.get("drop_reason"):
                    pseudo_all.append(p)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(eps_all, pseudo_all, overlap_counts, files, indep_all), encoding="utf-8")
    print(f"report: {out}  (episodes={len(eps_all)}, pseudo={len(pseudo_all)}, "
          f"overlap_dropped={sum(overlap_counts.values())})")


if __name__ == "__main__":
    main()
