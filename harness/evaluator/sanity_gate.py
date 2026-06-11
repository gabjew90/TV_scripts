"""Campaign Task-4 sanity gate: the 11 v0.3 hand-audited Trade-#2/T1 entries
must grade t1_hit (they were bar-walked to target in the v0.3 outcome audit).
A disagreement = walker bug -> STOP."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluator.episodes import build_episodes
from evaluator.report import load_bars, BARS_MAP, HARNESS

AUDITED = {
    ("BTCUSDT.P", 1779278400): "t1_hit", ("BTCUSDT.P", 1779681600): "t1_hit",
    ("BTCUSDT.P", 1779696000): "t1_hit", ("BTCUSDT.P", 1779710400): "t1_hit",
    ("BTCUSDT.P", 1779724800): "t1_hit",
    ("NEARUSDT.P", 1780171200): "t1_hit", ("NEARUSDT.P", 1780185600): "t1_hit",
    ("NEARUSDT.P", 1780243200): "t1_hit",
    ("SOLUSDT.P", 1780056000): "t1_hit", ("SOLUSDT.P", 1780185600): "t1_hit",
    ("SOLUSDT.P", 1780200000): "t1_hit",
}

CFG = "209091"   # v0.5.0 settings_hash (OS knobs + use_1d_gate)

fails = 0
for sym in ("BTCUSDT.P", "NEARUSDT.P", "SOLUSDT.P"):
    evs = [json.loads(l) for l in open(HARNESS / "events" / f"{sym}_240_v1_s0.5.0_c{CFG}_B.jsonl")]
    bars = load_bars(HARNESS / "bars" / BARS_MAP[sym])
    eps, ovl = build_episodes(evs, bars)
    epmap = {(e["symbol"], e["ent_ts"]): e for e in eps}
    ovset = {(sym, e["bar_ts"]) for e in ovl}
    for (s, t), exp in AUDITED.items():
        if s != sym:
            continue
        if (s, t) in epmap:
            ep = epmap[(s, t)]
            got = ep["exit_code"]
            # The v0.3 audit walked stop-vs-target ONLY (no thesis-exit rule).
            # Spec-equivalent acceptance: t1_hit, OR thesis_exit whose
            # counterfactual shows the target was reached before the stop.
            ok = got == exp or (got == "thesis_exit" and ep["counterfactual"] == "recovered")
            if not ok:
                fails += 1
            print(f"{s} {t}: {got}"
                  + (f" (cf={ep['counterfactual']})" if got == "thesis_exit" else "")
                  + ("" if ok else f"  <-- EXPECTED {exp}"))
        elif (s, t) in ovset:
            print(f"{s} {t}: skip_overlap (sequential rule absorbed it - acceptable)")
        else:
            fails += 1
            print(f"{s} {t}: MISSING from episodes AND overlap list")
print("gate:", "PASS" if fails == 0 else f"FAIL ({fails})")
raise SystemExit(1 if fails else 0)
