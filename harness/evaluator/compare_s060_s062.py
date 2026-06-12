"""s0.6.0 vs s0.6.2: alignment-aware OS targets ONLY. Allowed diffs:
  - OS events: t1/rt1/rsn/tgt may change (new target rule); an OS bar may flip
    ENT<->SKP (rt1 re-gated against the new target) — same (ts,dir) must exist.
  - Everything else (T1/2A/2B/SYS): bit-identical."""
import glob
import json
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
OS_TARGET_KEYS = {"t1", "rt1", "rsn", "tgt"}


def load(p):
    evs = {}
    for line in open(p):
        e = json.loads(line)
        evs[(e["bar_ts"], e["trade"], e["event"], e["dir"], e["factors"].get("typ", ""))] = e
    return evs


bad = 0
for old_f in sorted(glob.glob(str(HARNESS / "events" / "*_s0.6.0_*.jsonl"))):
    sym = Path(old_f).name.split("_")[0]
    new = load(glob.glob(str(HARNESS / "events" / f"{sym}_*_s0.6.2_*.jsonl"))[0])
    old = load(old_f)
    fails = []
    flips = 0
    retgt = 0
    only_old = set(old) - set(new)
    only_new = set(new) - set(old)
    for k in sorted(only_old):
        twin = (k[0], "OS", "SKP" if k[2] == "ENT" else "ENT", k[3], "")
        if k[1] == "OS" and twin in new:
            flips += 1
            only_new.discard(twin)
        else:
            fails.append(f"MISSING in new: {k}")
    for k in sorted(only_new):
        fails.append(f"EXTRA in new: {k}")
    for k in sorted(set(old) & set(new)):
        fo, fn = old[k]["factors"], new[k]["factors"]
        allowed = OS_TARGET_KEYS if k[1] == "OS" else set()
        diffs = [x for x in fo if x not in allowed and fo.get(x) != fn.get(x)]
        if diffs:
            fails.append(f"VALUE diff {k}: {diffs}")
        elif k[1] == "OS" and fo.get("t1") != fn.get("t1"):
            retgt += 1
    status = "OK" if not fails else "FAIL"
    if fails:
        bad += 1
        for f in fails[:8]:
            print(f"  {sym} {f}")
    print(f"{sym}: {status} (OS ENT<->SKP flips={flips}, OS retargeted={retgt})")
print("diff v0.6.2:", "PASS" if bad == 0 else f"FAIL ({bad})")
raise SystemExit(1 if bad else 0)
