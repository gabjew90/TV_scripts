import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harvest.parse_labels import parse_label, dedup_key, run

GOOD_PIV = "JF|1|0.1|184223|B|SYS|PIV|N|240|1780444800|2.627|typ=H"
GOOD_PING = "JF|1|0.1|184223|B|SYS|PING|N|240|1780459200|2.7|reg=U|age=0"


def test_parse_label_head_and_tail():
    ev = parse_label(GOOD_PIV)
    assert ev["schema_v"] == "1" and ev["script_v"] == "0.1" and ev["cfg"] == "184223"
    assert ev["src"] == "B" and ev["trade"] == "SYS" and ev["event"] == "PIV"
    assert ev["bar_ts"] == 1780444800 and ev["px"] == 2.627
    assert ev["factors"] == {"typ": "H"}


def test_malformed_label_raises():
    import pytest
    with pytest.raises(ValueError):
        parse_label("JF|1|0.1|184223|B|SYS")          # short head
    with pytest.raises(ValueError):
        parse_label(GOOD_PING + "|noequalsign")        # bad tail


def test_dedup_key_distinguishes_event_type_and_piv_typ():
    a = parse_label(GOOD_PIV)
    b = parse_label(GOOD_PIV.replace("typ=H", "typ=L"))
    c = parse_label(GOOD_PIV.replace("PIV", "PING"))
    assert dedup_key(a) != dedup_key(b)
    assert dedup_key(a) != dedup_key(c)


def test_run_groups_by_provenance_and_is_idempotent(tmp_path):
    raw = {"labels": [{"text": GOOD_PIV}, {"text": GOOD_PING},
                      {"text": GOOD_PING.replace("184223", "999999")},  # different cfg
                      {"text": "decorative non-event"}]}
    raw_file = tmp_path / "raw.json"
    raw_file.write_text(json.dumps(raw))
    out_dir = tmp_path / "events"
    n1, malformed = run(str(raw_file), "BTCUSDT.P", str(out_dir))
    files = sorted(p.name for p in out_dir.glob("*.jsonl"))
    assert files == ["BTCUSDT.P_240_v1_s0.1_c184223_B.jsonl",
                     "BTCUSDT.P_240_v1_s0.1_c999999_B.jsonl"]  # no-pool: cfg split
    assert n1 == 3 and malformed == []
    n2, _ = run(str(raw_file), "BTCUSDT.P", str(out_dir))       # re-harvest
    assert n2 == 0                                              # idempotent: nothing new
    lines = (out_dir / files[0]).read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["symbol"] == "BTCUSDT.P"
