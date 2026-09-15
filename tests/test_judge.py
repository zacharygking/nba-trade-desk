import json

import pytest

from trade_desk import judge
from trade_desk.agent import run_task, scripted
from trade_desk.tasks import TASKS_BY_ID


def _traj():
    t = TASKS_BY_ID["clear_roster_spot"]
    sc = t.build(source="synthetic")
    low = sorted(sc.state.roster(sc.team), key=lambda p: p.value)[0]
    traj = run_task(t, scripted(("view_roster", {"team": sc.team}),
                                ("waive_player", {"team": sc.team, "player_id": low.id}),
                                "Waived the lowest-value player."), source="synthetic")
    return traj.to_dict()


def test_packet_is_blind_and_complete():
    t = _traj()
    text = judge.render_packet(t)
    assert "ground_truth" not in text and "PASS" not in text and "scripted" not in text
    assert t["request"] in text and "R7" in text and "waive_player" in text
    assert "Waived the lowest-value player." in text
    assert "Transactions:" in text


def test_parse_scores_validates():
    good = json.dumps({"D1": {"score": 1, "rationale": "done"}, "D2": {"score": 2, "rationale": ""},
                       "D3": {"score": 1, "rationale": ""}, "D4": {"score": "NA", "rationale": ""},
                       "D5": {"score": "na", "rationale": ""}, "D6": {"score": 2, "rationale": ""}})
    s = judge.parse_scores("Here you go:\n" + good)
    assert s["D1"]["score"] == 1 and s["D4"]["score"] == "NA" and s["D5"]["score"] == "NA"
    with pytest.raises(ValueError):
        judge.parse_scores(json.dumps({"D1": {"score": 1}, "D2": {"score": 3}, "D3": {"score": 0},
                                       "D4": {"score": 0}, "D5": {"score": 0}, "D6": {"score": 0}}))
    with pytest.raises(ValueError):
        judge.parse_scores(json.dumps({"D1": {"score": "NA"}, "D2": {"score": 1}, "D3": {"score": 0},
                                       "D4": {"score": 0}, "D5": {"score": 0}, "D6": {"score": 0}}))


def test_record_and_summary_round_trip(tmp_path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "trajectories.jsonl").write_text(json.dumps(_traj()) + "\n")
    judge.main(["packets", "--run", str(run), "--out", str(run / "packets")])
    assert (run / "packets" / "packet-0.md").exists() and (run / "packets" / "RUBRIC.md").exists()
    scores = json.dumps({d: {"score": 1 if d == "D1" else 2, "rationale": "ok"} for d in judge.DIMENSIONS})
    judge.main(["record", "--run", str(run), "--index", "0", "--judge", "test-judge", "--scores", scores])
    rec = json.loads((run / "judgments.jsonl").read_text())
    assert rec["judge"] == "test-judge" and rec["scores"]["D6"]["score"] == 2 and rec["rubric_hash"]
    judge.main(["summary", str(run)])
    out = capsys.readouterr().out
    assert "D1 agrees with ground truth on 1/1" in out
