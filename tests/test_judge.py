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


def test_items_and_labels_round_trip(tmp_path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "trajectories.jsonl").write_text(json.dumps(_traj()) + "\n")
    pool = tmp_path / "pool"
    judge.main(["pool", "--runs", str(run), "--out", str(pool)])
    key = next(iter(json.loads((pool / "manifest.json").read_text())))
    scores = json.dumps({d: {"score": "NA" if d in ("D4", "D5") else 1, "rationale": "why"} for d in judge.DIMENSIONS})
    judge.main(["score", "--key", key, "--pool", str(pool), "--judge", "j", "--scores", scores])
    judge.main(["record", "--key", key, "--pool", str(pool), "--judge", "j2", "--scores", scores])   # old name
    judge.main(["items", "--pool", str(pool), "--dimension", "D4", "--out", str(tmp_path / "items-D4.jsonl")])
    item = json.loads((tmp_path / "items-D4.jsonl").read_text().splitlines()[0])
    assert item["id"] == f"{key}:D4" and item["judge"].startswith("NA: why") and "Rulebook" in item["packet"]
    out = capsys.readouterr().out
    assert "motherlode handpick" in out and "--labels 0 1 2 NA" in out
    judge.main(["labels", "--pool", str(pool), "--dimension", "D4", "--out", str(tmp_path / "judge-D4.jsonl")])
    rows = [json.loads(l) for l in (tmp_path / "judge-D4.jsonl").read_text().splitlines()]
    assert rows[0] == {"item_id": f"{key}:D4", "rater": "j", "label": "NA", "rubric_hash": judge.rubric_hash(), "pass": "blind"}
    assert rows[1]["rater"] == "j2"
    judge.main(["report", str(run)])
    assert "D1 agrees with ground truth" in capsys.readouterr().out


def test_console_script_dispatches(capsys):
    from trade_desk import cli
    import pytest
    with pytest.raises(SystemExit) as e:
        cli.main(["--help"])
    assert e.value.code == 0 and "judge" in capsys.readouterr().out
    cli.main(["run", "rulebook"])
    assert "R1" in capsys.readouterr().out


def test_rubric_hash_matches_motherlode():
    from motherlode.grading import rubric_hash
    assert judge.rubric_hash() == rubric_hash(judge.rubric_text())


def test_packet_uses_the_runs_own_rulebook_and_drift_is_reported(capsys):
    t = _traj()
    assert t["rulebook"] and "R3" in t["rulebook"]
    assert judge.drift(t) == []
    stale = dict(t, rulebook="OLD RULEBOOK TEXT", rulebook_hash="deadbeef0000")
    assert "OLD RULEBOOK TEXT" in judge.render_packet(stale)
    assert any(d.startswith("rulebook deadbeef0000") for d in judge.drift(stale))
    assert judge.drift(t, {"rubric_hash": "nope"}) == [f"rubric nope (judgment) vs {judge.rubric_hash()} (now)"]


def test_pool_keys_are_deterministic_and_opaque(tmp_path):
    run = tmp_path / "agents-x"
    run.mkdir()
    t = _traj()
    (run / "trajectories.jsonl").write_text(json.dumps(t) + "\n")
    a = judge.pool_key(str(run), 0, t)
    b = judge.pool_key(str(tmp_path / "other" / "agents-x"), 0, t)   # same run name elsewhere
    assert a == b and len(a) == 8 and "agents" not in a
    assert judge.pool_key(str(run), 1, t) != a
    for out in ("p1", "p2"):
        judge.main(["pool", "--runs", str(run), "--out", str(tmp_path / out)])
    m1 = json.loads((tmp_path / "p1" / "manifest.json").read_text())
    m2 = json.loads((tmp_path / "p2" / "manifest.json").read_text())
    assert list(m1) == list(m2) == [a]


def test_trajectories_record_provenance():
    t = _traj()
    assert t["code_commit"] and len(t["code_commit"]) >= 7
    assert t["snapshot_sha256"] == ""     # synthetic league: no snapshot
    from trade_desk.agent import provenance
    assert len(provenance()["snapshot_sha256"]) == 12
