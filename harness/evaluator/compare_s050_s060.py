"""s0.5.0 vs s0.6.0 invariant diff. v0.6 changed ONE thing: OS piv/roll classes
toggled off. Therefore:
  - ALL non-OS events: bit-identical (keys + every factor).
  - OS events in target: must exist in baseline at the same key, and lvl_src must
    be a daily/weekly class. Level-IDENTITY keys (lvl/lvl_src/n_lvls/swd/age_t)
    may differ (a bar whose deepest level was piv/roll re-selects its daily
    candidate); everything else (stop/t1/rt1/rsn/align/oco/covariates) identical.
  - OS events only in baseline: must have been piv/roll-only bars (counted, ok).
Comparison window = baseline's span (emission-time adjusted for PIV)."""
import glob
import json
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
OS_IDENTITY_KEYS = {"lvl", "lvl_src", "n_lvls", "swd", "age_t"}


def load(p):
    evs = {}
    for line in open(p):
        e = json.loads(line)
        k = (e["bar_ts"], e["trade"], e["event"], e["dir"], e["factors"].get("typ", ""))
        evs[k] = e
    return evs


bad = 0
for old_f in sorted(glob.glob(str(HARNESS / "events" / "*_s0.5.0_*.jsonl"))):
    sym = Path(old_f).name.split("_")[0]
    new_fs = glob.glob(str(HARNESS / "events" / f"{sym}_*_s0.6.0_*.jsonl"))
    if not new_fs:
        print(f"{sym}: NO s0.6.0 file")
        bad += 1
        continue
    old_all, new_all = load(old_f), load(new_fs[0])
    lo, hi = min(k[0] for k in old_all), max(k[0] for k in old_all)
    emit_ts = lambda k: k[0] + (3 * 14400 if k[2] == "PIV" else 0)
    old = {k: v for k, v in old_all.items() if lo <= emit_ts(k) <= hi}
    new = {k: v for k, v in new_all.items() if lo <= emit_ts(k) <= hi}

    fails = []
    os_dropped = 0
    os_reselected = 0
    for k in sorted(set(old) - set(new)):
        if k[1] == "OS" and old[k]["factors"].get("lvl_src") in ("piv", "roll"):
            os_dropped += 1
        else:
            fails.append(f"MISSING in new: {k} (lvl_src={old[k]['factors'].get('lvl_src')})")
    for k in sorted(set(new) - set(old)):
        fails.append(f"EXTRA in new: {k}")
    for k in sorted(set(old) & set(new)):
        fo, fn = old[k]["factors"], new[k]["factors"]
        if k[1] == "OS":
            if fn.get("lvl_src") not in ("pdl", "pdh", "pwl", "pwh"):
                fails.append(f"OS non-daily lvl_src in new {k}: {fn.get('lvl_src')}")
            if fo.get("lvl_src") != fn.get("lvl_src"):
                os_reselected += 1
            diffs = [x for x in fo if x not in OS_IDENTITY_KEYS and fo.get(x) != fn.get(x)]
        else:
            diffs = [x for x in fo if fo.get(x) != fn.get(x)]
        if diffs:
            fails.append(f"VALUE diff {k}: {diffs}")
    status = "OK" if not fails else "FAIL"
    if fails:
        bad += 1
        for f in fails[:10]:
            print(f"  {sym} {f}")
    print(f"{sym}: {status} (shared={len(set(old) & set(new))}, OS piv/roll dropped={os_dropped}, "
          f"OS level-reselected={os_reselected})")
print("invariant-diff v0.6:", "PASS" if bad == 0 else f"FAIL ({bad})")
raise SystemExit(1 if bad else 0)
