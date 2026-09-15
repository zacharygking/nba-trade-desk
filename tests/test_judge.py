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


def test_packet_uses_the_runs_own_tools_and_names_injected_failures():
    from trade_desk.tasks import TASKS_BY_ID
    t = _traj()
    assert len(t["tools"]) == 10 and t["injected_failures"] == []
    text = judge.render_packet(t)
    assert "Injected failures in this scenario" in text and "- none" in text
    assert "reconstructed" not in text
    old = dict(t, tools=[{"name": "read_rule", "description": "old", "final": False}])
    assert "old" in judge.render_packet(old)
    legacy = dict(t); legacy.pop("tools")
    assert "reconstructed" in judge.render_packet(legacy)
    r = TASKS_BY_ID["rules_service_down"].failures().describe()
    assert r == ["the first 1 call to read_rule return 'service unavailable'"]


def test_handpick_and_labels_round_trip(tmp_path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "trajectories.jsonl").write_text(json.dumps(_traj()) + "\n")
    pool = tmp_path / "pool"
    judge.main(["pool", "--runs", str(run), "--out", str(pool)])
    key = next(iter(json.loads((pool / "manifest.json").read_text())))
    scores = json.dumps({d: {"score": "NA" if d in ("D4", "D5") else 1, "rationale": "why"} for d in judge.DIMENSIONS})
    judge.main(["record", "--key", key, "--pool", str(pool), "--judge", "j", "--scores", scores])
    out = tmp_path / "hp"
    judge.main(["handpick", "--pool", str(pool), "--out", str(out), "--rater", "z", "--dimensions", "D1", "D4"])
    assert (out / "grade-D1.html").exists() and (out / "grade-D4.html").exists()
    html = (out / "grade-D1.html").read_text()
    assert judge.rubric_hash() in html and "judge_D1" in html
    assert "1: why" not in html                      # hidden field is encoded, not in the clear
    item = json.loads((out / "items.jsonl").read_text())
    assert item["id"] == key and item["judge_D4"] == "NA: why" and "Rulebook" in item["packet"]
    judge.main(["labels", "--pool", str(pool), "--dimension", "D4", "--out", str(out / "judge-D4.jsonl")])
    row = json.loads((out / "judge-D4.jsonl").read_text())
    assert row == {"item_id": key, "rater": "j", "label": "NA", "rubric_hash": judge.rubric_hash(), "pass": "blind"}


def test_rubric_hash_matches_motherlode():
    from motherlode.grading import rubric_hash
    assert judge.rubric_hash() == rubric_hash(judge.rubric_text())
