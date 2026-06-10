"""Compare two event JSONL files ignoring provenance (script_v) - the
refactor regression gate: same bars in, same events out."""
import json
import sys


def core(path):
    out = set()
    for line in open(path):
        e = json.loads(line)
        out.add((e["bar_ts"], e["trade"], e["event"], e["dir"], e["px"],
                 tuple(sorted(e["factors"].items()))))
    return out


a, b = core(sys.argv[1]), core(sys.argv[2])
only_a, only_b = a - b, b - a
print(f"A: {len(a)} events, B: {len(b)} events, common: {len(a & b)}")
for x in sorted(only_a)[:10]:
    print("  only A:", x)
for x in sorted(only_b)[:10]:
    print("  only B:", x)
raise SystemExit(0 if not only_a and not only_b else 1)
