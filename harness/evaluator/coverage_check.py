"""Per-month na-rate for the v0.4.6 factor keys, across all s0.5.0 events."""
import glob
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

KEYS = ["os", "osp", "er", "vz", "dlt", "fr", "lqb", "lqs", "swd", "age_t"]
HARNESS = Path(__file__).resolve().parents[1]
tot = defaultdict(int)
nas = defaultdict(lambda: defaultdict(int))
for f in glob.glob(str(HARNESS / "events" / "*_s0.5.0_*.jsonl")):
    for line in open(f):
        e = json.loads(line)
        if e["trade"] == "SYS":
            continue
        m = datetime.fromtimestamp(e["bar_ts"], tz=timezone.utc).strftime("%Y-%m")
        tot[m] += 1
        for k in KEYS:
            if e["factors"].get(k, "na") == "na":
                nas[m][k] += 1
print("month   n      " + "  ".join(f"{k:>6}" for k in KEYS))
for m in sorted(tot):
    print(f"{m} {tot[m]:5d}  " + "  ".join(f"{100*nas[m][k]/tot[m]:5.0f}%" for k in KEYS))
