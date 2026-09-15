import json
import shutil
from pathlib import Path

from trade_desk import session


def _run(argv, capsys):
    session.main(argv)
    return capsys.readouterr().out


def test_call_limit_is_enforced_and_recorded(capsys, tmp_path):
    out_dir = tmp_path / "out"
    head = _run(["start", "--task", "clear_roster_spot", "--model", "test", "--league", "synthetic",
                 "--out", str(out_dir), "--max-calls", "2"], capsys)
    sid = head.splitlines()[0].split()[1]
    assert "CALL LIMIT 2" in head
    try:
        for _ in range(3):
            last = _run(["call", "--session", sid, "--tool", "read_rule", "--args", '{"rule_id": "R4"}'], capsys)
        assert "call limit of 2 reached" in last
        _run(["finish", "--session", sid, "--reply", "stopped"], capsys)
        rec = json.loads((out_dir / "trajectories.jsonl").read_text().splitlines()[-1])
        assert rec["end_reason"] == "max_steps" and rec["max_steps"] == 2
        assert rec["n_tool_calls"] == 3 and rec["n_tool_errors"] == 1
    finally:
        shutil.rmtree(session.SESSIONS, ignore_errors=True)
