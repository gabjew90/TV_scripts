"""s0.4.5 vs s0.4.6: same events on same bars (head identity + old factor keys
equal); only script_v/cfg and the NEW keys may differ. Any delta = logic change."""
import glob
import json
from pathlib import Path

NEW_KEYS = {"os", "osp", "er", "vz", "dlt", "fr", "lqb", "lqs", "swd", "age_t", "lq_tot"}
HARNESS = Path(__file__).resolve().parents[1]


def load(p):
    evs = {}
    for line in open(p):
        e = json.loads(line)
        k = (e["bar_ts"], e["trade"], e["event"], e["dir"], e["factors"].get("typ", ""))
        evs[k] = e
    return evs


bad = 0
for old_f in sorted(glob.glob(str(HARNESS / "events" / "*_s0.4.5_*.jsonl"))):
    sym = Path(old_f).name.split("_")[0]
    new_fs = glob.glob(str(HARNESS / "events" / f"{sym}_*_s0.4.6_*.jsonl"))
    if not new_fs:
        print(f"{sym}: NO s0.4.6 file")
        bad += 1
        continue
    old, new = load(old_f), load(new_fs[0])
    only_old = set(old) - set(new)
    only_new = set(new) - set(old)
    # the new harvest extends past the old one's last bar — tolerate strictly-later
    # extras. PIV events are backdated by pivot_right bars (spec section 9: bar_ts =
    # pivot bar, EMISSION bar = bar_ts + 3 bars) — compare their emission time.
    horizon = max(k[0] for k in old)
    emit_ts = lambda k: k[0] + (3 * 14400 if k[2] == "PIV" else 0)
    only_new = {k for k in only_new if emit_ts(k) <= horizon}
    val_diff = 0
    for k in set(old) & set(new):
        fo, fn = old[k]["factors"], new[k]["factors"]
        for fk, fv in fo.items():
            if fk not in NEW_KEYS and fn.get(fk) != fv:
                val_diff += 1
                print(f"{sym} {k}: factor {fk} {fv} -> {fn.get(fk)}")
    status = "OK" if not (only_old or only_new or val_diff) else "DIFF"
    if status == "DIFF":
        bad += 1
        for k in sorted(only_old):
            print(f"{sym} MISSING in new: {k}")
        for k in sorted(only_new):
            print(f"{sym} EXTRA in new:   {k}")
    print(f"{sym}: {status} (shared={len(set(old) & set(new))}, old-only={len(only_old)}, "
          f"new-only={len(only_new)}, value-diffs={val_diff})")
print("emission-diff:", "PASS" if bad == 0 else f"FAIL ({bad})")
raise SystemExit(1 if bad else 0)
