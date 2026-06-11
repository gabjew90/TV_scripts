"""s0.4.6 vs s0.5.0 emission diff with the v0.5 EXPECTED-change taxonomy.

v0.5 changed behavior in exactly two ways: (1) trade=OS is new, (2) the 1D gate
defaults OFF. Everything else must be bit-identical. Expected classes:
  - trade=OS in target only: NEW DETECTOR (counted, ok)
  - shared 2A/2B key where baseline rsn=1d: re-gated (rsn -> na/rr, ENT may appear) (ok)
  - target-only 2A/2B ENT whose baseline twin was SKP rsn=1d at same (ts,trade,dir) (ok)
  - T1 deltas of any kind: gate-off arms earlier -> state evolution legitimately
    diverges after the first previously-blocked ARM (counted per symbol, ok)
  - SYS deltas, or any other 2A/2B delta: FAIL (engine/sweep logic must be untouched)
Comparison window = the baseline harvest's span (target extends to January)."""
import glob
import json
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]


def load(p):
    evs = {}
    for line in open(p):
        e = json.loads(line)
        k = (e["bar_ts"], e["trade"], e["event"], e["dir"], e["factors"].get("typ", ""))
        evs[k] = e
    return evs


bad = 0
for old_f in sorted(glob.glob(str(HARNESS / "events" / "*_s0.4.6_*.jsonl"))):
    sym = Path(old_f).name.split("_")[0]
    new_fs = glob.glob(str(HARNESS / "events" / f"{sym}_*_s0.5.0_*.jsonl"))
    if not new_fs:
        print(f"{sym}: NO s0.5.0 file")
        bad += 1
        continue
    old_all, new = load(old_f), load(new_fs[0])
    lo, hi = min(k[0] for k in old_all), max(k[0] for k in old_all)
    emit_ts = lambda k: k[0] + (3 * 14400 if k[2] == "PIV" else 0)
    # window-filter BOTH sides by emission time: a boundary PIV whose emission
    # bar lies beyond the baseline's last event bar is outside the comparison.
    old = {k: v for k, v in old_all.items() if lo <= emit_ts(k) <= hi}
    new_w = {k: v for k, v in new.items() if lo <= emit_ts(k) <= hi}

    n_os = sum(1 for k in new_w if k[1] == "OS")
    t1_delta = 0
    swaps = 0
    fails = []

    only_old = set(old) - set(new_w)
    only_new = {k for k in set(new_w) - set(old) if k[1] != "OS"}
    for k in sorted(only_old):
        if k[1] == "T1":
            t1_delta += 1
        elif old[k]["factors"].get("rsn") == "1d":
            swaps += 1          # re-gated: the 1d-SKP became an ENT (different key)
        else:
            fails.append(f"MISSING in new: {k}")
    for k in sorted(only_new):
        if k[1] == "T1":
            t1_delta += 1
        elif k[1] in ("2A", "2B") and k[2] == "ENT" and (k[0], k[1], "SKP", k[3], "") in old \
                and old[(k[0], k[1], "SKP", k[3], "")]["factors"].get("rsn") == "1d":
            swaps += 1
        else:
            fails.append(f"EXTRA in new: {k}")
    for k in set(old) & set(new_w):
        fo, fn = old[k]["factors"], new_w[k]["factors"]
        if k[1] == "T1":
            if any(fo.get(x) != fn.get(x) for x in fo):
                t1_delta += 1
            continue
        if fo.get("rsn") == "1d":
            swaps += 1
            continue
        diffs = [x for x in fo if fo.get(x) != fn.get(x)]
        if diffs:
            fails.append(f"VALUE diff {k}: {diffs}")
    status = "OK" if not fails else "FAIL"
    if fails:
        bad += 1
        for f in fails[:10]:
            print(f"  {sym} {f}")
    print(f"{sym}: {status} (shared-in-window={len(set(old) & set(new_w))}, OS new={n_os}, "
          f"1d-regate/swaps={swaps}, T1 expected-deltas={t1_delta})")
print("emission-diff v0.5:", "PASS" if bad == 0 else f"FAIL ({bad})")
raise SystemExit(1 if bad else 0)
