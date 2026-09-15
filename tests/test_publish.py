import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from trade_desk import packets, publish, results
from trade_desk.agent import run_task, scripted
from trade_desk.tasks import TASKS_BY_ID


def _run_dir(tmp_path: Path) -> Path:
    t = TASKS_BY_ID["clear_roster_spot"]
    sc = t.build(source="synthetic")
    low = sorted(sc.state.roster(sc.team), key=lambda p: p.value)[0]
    traj = run_task(t, scripted(("view_roster", {"team": sc.team}),
                                ("waive_player", {"team": sc.team, "player_id": low.id}),
                                "Waived the lowest-value player."), source="synthetic")
    d = tmp_path / "agents-test"
    d.mkdir()
    (d / "trajectories.jsonl").write_text(json.dumps(traj.to_dict()) + "\n")
    return d


def test_packet_is_blind_and_complete(tmp_path):
    d = _run_dir(tmp_path)
    t = packets.load_run(str(d))[0]
    text = packets.render_packet(t)
    assert "ground_truth" not in text and "scripted" not in text and "PASS" not in text
    assert t["request"] in text and "R7" in text and "waive_player" in text
    assert "Injected failures in this scenario" in text and "- none" in text
    assert t["rulebook"] in text and "reconstructed" not in text
    assert packets.drift(t) == []
    stale = dict(t, rulebook="OLD RULEBOOK TEXT", rulebook_hash="deadbeef0000")
    assert "OLD RULEBOOK TEXT" in packets.render_packet(stale) and packets.drift(stale)


def test_item_ids_are_deterministic_and_opaque(tmp_path):
    d = _run_dir(tmp_path)
    t = packets.load_run(str(d))[0]
    a = packets.item_id(str(d), 0, t)
    assert a == packets.item_id(str(tmp_path / "elsewhere" / "agents-test"), 0, t) and len(a) == 8 and "agents" not in a
    assert packets.item_id(str(d), 1, t) != a


def test_publish_writes_items_rubric_and_truth(tmp_path):
    d = _run_dir(tmp_path)
    out = publish.publish([str(d)], str(tmp_path / "ds"), "test-items", pilot=["x"], seal=False)
    items = [json.loads(l) for l in (out / "items.jsonl").read_text().splitlines()]
    assert len(items) == 1 and items[0]["truth"]["D1"] in ("0", "1") and items[0]["meta"]["tier"] == "scripted"
    assert "Rulebook" in items[0]["text"] and (out / "rubric.md").exists() and (out / "rubric.json").exists()
    spec = json.loads((out / "rubric.json").read_text())
    assert [x["id"] for x in spec["dimensions"]] == ["D1", "D2", "D3", "D4", "D5", "D6"]


@pytest.mark.skipif(not (Path(sys.executable).parent / "motherlode").exists() and not shutil.which("motherlode"),
                    reason="motherlode tools extra not installed")
def test_publish_seals_with_motherlode_and_results_read_back(tmp_path, capsys):
    d = _run_dir(tmp_path)
    out = publish.publish([str(d)], str(tmp_path / "ds"), "test-items", seal=True)
    man = json.loads((out / "manifest.json").read_text())
    assert man["schema"] == "items-v1" and man["producer"] == "nba-trade-desk" and man["name"] == "test-items"
    assert set(man["files"]) == {"items.jsonl", "rubric.md", "rubric.json"}
    assert subprocess.run([publish.motherlode_bin(), "dataset", "verify", str(out)], capture_output=True).returncode == 0
    results.main(["--items", str(out)])
    text = capsys.readouterr().out
    assert "ground truth by task" in text and "clear_roster_spot" in text
