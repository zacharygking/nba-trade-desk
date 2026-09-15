import json

import pytest

from trade_desk.agent import run_task, scripted
from trade_desk.league import SNAPSHOT, build_league
from trade_desk.state import TAX, CAP, ROSTER_MAX
from trade_desk.tasks import TASKS, TASKS_BY_ID
from trade_desk.tools import execute

SOURCES = ["synthetic"] + (["espn"] if SNAPSHOT.exists() else [])


@pytest.mark.parametrize("source", SOURCES)
def test_every_task_builds_and_noop_is_graded(source):
    for t in TASKS:
        sc = t.build(source=source)
        s = sc.state
        assert 13 <= s.roster_size(sc.team) <= ROSTER_MAX, (t.id, sc.team)
        assert "{" not in sc.request
        passed, why = t.check(s, s.clone(), sc.team)
        if t.id == "trade_restriction_trap":
            assert passed, why
        else:
            assert not passed, f"{t.id} passes on a no-op: {why}"


@pytest.mark.parametrize("source", SOURCES)
def test_scenarios_match_their_requests(source):
    sc = TASKS_BY_ID["under_tax_keep_starters"].build(source=source)
    assert sc.state.payroll(sc.team) > TAX
    sc = TASKS_BY_ID["clear_roster_spot"].build(source=source)
    assert sc.state.roster_size(sc.team) == ROSTER_MAX
    sc = TASKS_BY_ID["dead_money_trap"].build(source=source)
    ng = [p for p in sc.state.roster(sc.team) if not p.guaranteed]
    assert len(ng) == 2 and len(sc.adjustments) >= 2
    assert sc.state.cap_room(sc.team) < 0
    sc = TASKS_BY_ID["trade_restriction_trap"].build(source=source)
    assert sc.state.roster(sc.team)[0].no_trade
    assert sc.state.roster(sc.team)[0].name in sc.request


@pytest.mark.parametrize("source", SOURCES)
def test_dead_money_trap(source):
    t = TASKS_BY_ID["dead_money_trap"]
    sc = t.build(source=source)
    ng = [p.id for p in sc.state.roster(sc.team) if not p.guaranteed]
    g = [p.id for p in sc.state.roster(sc.team) if p.guaranteed][-1]
    traj = run_task(t, scripted(("waive_player", {"team": sc.team, "player_id": ng[0]}),
                                ("waive_player", {"team": sc.team, "player_id": ng[1]}), "done"),
                    source=source)
    assert traj.irreversible_calls == 2
    assert traj.state_diff["teams"][sc.team]["dead_money"] == [0.0, 0.0]
    assert traj.adjustments == sc.adjustments and traj.team == sc.team
    traj = run_task(t, scripted(("waive_player", {"team": sc.team, "player_id": g}), "done"), source=source)
    assert not traj.ground_truth["pass"]
    assert traj.steps[1]["result"]["dead_money_added"] > 0


def test_failure_injection_and_recovery_recorded():
    t = TASKS_BY_ID["rules_service_down"]
    client = scripted(("read_rule", {"rule_id": "R2"}), ("read_rule", {"rule_id": "R2"}), "ok")
    traj = run_task(t, client, source="synthetic")
    results = [s for s in traj.steps if s["type"] == "tool_result"]
    assert results[0]["is_error"] and "unavailable" in results[0]["result"]["error"]
    assert not results[1]["is_error"] and results[1]["result"]["id"] == "R2"
    assert traj.n_tool_errors == 1


@pytest.mark.parametrize("source", SOURCES)
def test_partner_declines_first_then_accepts(source):
    t = TASKS_BY_ID["partner_rejects_first"]
    sc = t.build(source=source)
    s, f = sc.state, t.failures()
    # dump a mid-salary player on an under-cap team, taking back its cheapest contract
    p = sorted(s.roster(sc.team), key=lambda p: p.salary)[len(s.roster(sc.team)) // 2]
    partner = next(x for x in s.teams if x != sc.team and s.payroll(x) + p.salary <= CAP + 5)
    back = min(s.roster(partner), key=lambda q: q.salary)
    args = {"team": sc.team, "send": [p.id], "partner": partner, "receive": [back.id]}
    first = execute(s, "propose_trade", args, f)
    assert first.result["legal"] and not first.result["partner_accepts"]
    second = execute(s, "propose_trade", args, f)
    assert second.result["legal"] and second.result["partner_accepts"]


@pytest.mark.parametrize("source", SOURCES)
def test_illegal_execute_does_not_mutate(source):
    sc = TASKS_BY_ID["trade_restriction_trap"].build(source=source)
    s = sc.state
    star = s.roster(sc.team)[0]
    partner = next(x for x in s.teams if x != sc.team)
    other = s.roster(partner)[0]
    out = execute(s, "execute_trade", {"team": sc.team, "send": [star.id], "partner": partner, "receive": [other.id]})
    assert out.is_error and not out.result["executed"]
    assert any(v["rule"] == "R5" for v in out.result["violations"])
    assert out.state.players[star.id].team == sc.team


def test_trajectory_is_json_serializable():
    traj = run_task(TASKS[0], scripted(("view_cap_sheet", {"team": "SAC"}), "looked"), source="synthetic")
    s = json.dumps(traj.to_dict())
    assert "rulebook_hash" in s and traj.end_reason == "end_turn" and traj.league["source"] == "synthetic"


@pytest.mark.skipif("espn" not in SOURCES, reason="no ESPN snapshot")
def test_espn_league_shape():
    s = build_league(source="espn")
    assert len(s.teams) == 30
    for t in s.teams:
        # ESPN only serves current rosters, so 2025-26 teams reconstructed from contracts run thin
        assert 10 <= s.roster_size(t) <= ROSTER_MAX, t
    assert len(s.free_agents()) > 50
    assert "Domantas Sabonis" in {p.name for p in s.roster("SAC")}
    assert any(p.rating >= 80 for p in s.players.values())
    assert s.meta["source"] == "espn"
