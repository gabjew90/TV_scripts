"""s0.7.1 vs s0.7.2: the ONLY change is yellow-OSF suppression. Allowed diffs:
an OSF align=A event may flip ENT->SKP or change rsn rr->aln; everything else
bit-identical (within the shared emission window)."""
import glob
import json
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]


def load(p):
    evs = {}
    for line in open(p):
        e = json.loads(line)
        evs[(e["bar_ts"], e["trade"], e["event"], e["dir"], e["factors"].get("typ", ""))] = e
    return evs


bad = 0
for old_f in sorted(glob.glob(str(HARNESS / "events" / "*_s0.7.1_*.jsonl"))):
    sym = Path(old_f).name.split("_")[0]
    old = load(old_f)
    new = load(glob.glob(str(HARNESS / "events" / f"{sym}_*_s0.7.2_*.jsonl"))[0])
    fails = []
    suppressed = 0
    only_old = set(old) - set(new)
    only_new = set(new) - set(old)
    for k in sorted(only_old):
        twin = (k[0], k[1], "SKP", k[3], "")
        if k[1] == "OSF" and k[2] == "ENT" and old[k]["factors"].get("align") == "A" \
                and twin in new and new[twin]["factors"].get("rsn") == "aln":
            suppressed += 1
            only_new.discard(twin)
        else:
            fails.append(f"MISSING in new: {k}")
    for k in sorted(only_new):
        fails.append(f"EXTRA in new: {k}")
    for k in set(old) & set(new):
        fo, fn = old[k]["factors"], new[k]["factors"]
        allowed = {"rsn"} if (k[1] == "OSF" and fo.get("align") == "A") else set()
        diffs = [x for x in fo if x not in allowed and fo.get(x) != fn.get(x)]
        if diffs:
            fails.append(f"VALUE diff {k}: {diffs}")
        elif fo.get("rsn") != fn.get("rsn"):
            suppressed += 1          # rr -> aln re-tag on an already-skipped yellow OSF
    if fails:
        bad += 1
        for x in fails[:8]:
            print(f"  {sym} {x}")
    print(f"{sym}: {'OK' if not fails else 'FAIL'} (yellow-OSF suppressions/re-tags={suppressed})")
print("diff v0.7.2:", "PASS" if bad == 0 else f"FAIL ({bad})")
raise SystemExit(1 if bad else 0)
