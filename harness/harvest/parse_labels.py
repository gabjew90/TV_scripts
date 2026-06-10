"""Parse raw MCP label harvests into canonical, provenance-grouped events JSONL.

Robust to the MCP output shape: walks the whole JSON tree and collects every
string starting with "JF|". Symbol is NOT in the label string (spec section 9
head) - it is stamped at harvest time via --symbol.

No-pool enforcement: one output file per (schema_v, script_v, cfg, src, tf,
symbol). Idempotent: merges with existing file by dedup key.
"""
import argparse
import json
from pathlib import Path

HEAD_FIELDS = ["schema_v", "script_v", "cfg", "src", "trade", "event", "dir", "tf", "bar_ts", "px"]


def iter_jf_strings(node):
    if isinstance(node, str):
        if node.startswith("JF|"):
            yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from iter_jf_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_jf_strings(v)


def parse_label(text):
    parts = text.split("|")
    if parts[0] != "JF" or len(parts) < 1 + len(HEAD_FIELDS):
        raise ValueError(f"malformed head: {text}")
    ev = dict(zip(HEAD_FIELDS, parts[1:1 + len(HEAD_FIELDS)]))
    try:
        ev["bar_ts"] = int(ev["bar_ts"])
        ev["px"] = float(ev["px"])
    except ValueError:
        raise ValueError(f"non-numeric ts/px: {text}")
    factors = {}
    for kv in parts[1 + len(HEAD_FIELDS):]:
        k, sep, v = kv.partition("=")
        if not sep or not k:
            raise ValueError(f"malformed tail '{kv}': {text}")
        factors[k] = v
    ev["factors"] = factors
    return ev


def dedup_key(ev):
    key = (ev["bar_ts"], ev["trade"], ev["event"], ev["dir"])
    if ev["event"] == "PIV":
        key += (ev["factors"].get("typ", ""),)
    return key


def run(raw_path, symbol, out_dir):
    """Returns (n_new_events_written, malformed_list)."""
    raw = json.loads(Path(raw_path).read_text())
    events, malformed = [], []
    for s in iter_jf_strings(raw):
        try:
            events.append(parse_label(s))
        except ValueError as e:
            malformed.append(str(e))
    groups = {}
    for ev in events:
        ev["symbol"] = symbol
        gkey = (ev["schema_v"], ev["script_v"], ev["cfg"], ev["src"], ev["tf"])
        groups.setdefault(gkey, []).append(ev)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n_new = 0
    for (sv, scv, cfg, src, tf), evs in sorted(groups.items()):
        out = out_dir / f"{symbol}_{tf}_v{sv}_s{scv}_c{cfg}_{src}.jsonl"
        existing = {}
        if out.exists():
            for line in out.read_text().splitlines():
                e = json.loads(line)
                existing[dedup_key(e)] = e
        for ev in evs:
            if dedup_key(ev) not in existing:
                existing[dedup_key(ev)] = ev
                n_new += 1
        ordered = sorted(existing.values(), key=lambda e: (e["bar_ts"], e["trade"], e["event"]))
        out.write_text("\n".join(json.dumps(e, sort_keys=True) for e in ordered) + "\n")
    return n_new, malformed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", help="raw harvest JSON (saved MCP data_get_pine_labels output)")
    ap.add_argument("--symbol", required=True, help="TV symbol, e.g. BTCUSDT.P")
    ap.add_argument("--out-dir", default="harness/events")
    args = ap.parse_args()
    n_new, malformed = run(args.raw, args.symbol, args.out_dir)
    print(f"new events: {n_new}; malformed: {len(malformed)}")
    for m in malformed:
        print(f"  MALFORMED: {m}")
    raise SystemExit(1 if malformed else 0)


if __name__ == "__main__":
    main()
