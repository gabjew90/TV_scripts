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
EVENT_GLOB = "*_s0.4.6_*.jsonl"
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


def render_report(eps_all, pseudo_all, overlap_counts, file_list):
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

    # ── Gate questions (pseudo-episodes) ──
    L.append("\n## Gate questions (pseudo-episodes, walked independently)\n")
    rr_ps = [e for e in pseudo_all if e["pseudo"] == "rr"]
    L.append("\n### (a) rr gate — skipped-on-R signals, bucketed by their rt1\n")
    L.append(table(FACTOR_HEADER, bucket_rows(rr_ps, "rt1",
             [(None, 0.5), (0.5, 1.0), (1.0, 1.25), (1.25, 1.5)],
             ["<0.5", "0.5-1.0", "1.0-1.25", "1.25-1.5"])))
    oned_ps = [e for e in pseudo_all if e["pseudo"] == "1d"]
    s = stats_row(oned_ps)
    L.append("\n### (b) 1D gate — blocked sweeps, graded as if taken\n")
    L.append(f"n={s['n']} closed={s['closed']} win%={fmt(s['win%'],0)} avgR={fmt(s['avg_r'])} "
             f"medMFE={fmt(s['med_mfe'])}\n")
    cf = defaultdict(int)
    for e in eps_all:
        if e["exit_code"] == "thesis_exit":
            cf[e["counterfactual"] or "open"] += 1
    L.append("\n### (c) thesis-exit counterfactuals (hold-to-stop instead)\n")
    L.append(table(["outcome if held", "n"], sorted(cf.items())))
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
    eps_all, pseudo_all, overlap_counts = [], [], {}
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
            if ev["event"] == "SKP" and ev["factors"].get("rsn") in ("rr", "1d"):
                p = walk_episode(ev, bars)
                if not p.get("drop_reason"):
                    pseudo_all.append(p)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(eps_all, pseudo_all, overlap_counts, files), encoding="utf-8")
    print(f"report: {out}  (episodes={len(eps_all)}, pseudo={len(pseudo_all)}, "
          f"overlap_dropped={sum(overlap_counts.values())})")


if __name__ == "__main__":
    main()
