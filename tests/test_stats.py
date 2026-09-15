import pytest

from trade_desk.league import SNAPSHOT, build_league, rating_from
from trade_desk.tools import execute, tools_hash, TOOL_NAMES

SOURCES = ["synthetic"] + (["espn"] if SNAPSHOT.exists() else [])


def test_rating_formula_reference_points():
    assert rating_from({"gp": 70, "min": 36.7, "pts": 29.6, "reb": 12.7, "ast": 10.2, "fg_pct": 58}) == 95
    assert rating_from({"gp": 70, "min": 30.8, "pts": 16.1, "reb": 10.7, "ast": 4.9, "fg_pct": 56}) == 80
    assert rating_from({"gp": 70, "min": 24, "pts": 9, "reb": 4, "ast": 2, "fg_pct": 45}) == 64
    assert rating_from({"gp": 70, "min": 10, "pts": 4, "reb": 2, "ast": 1, "fg_pct": 42}) == 50
    assert rating_from({"gp": 9, "min": 36, "pts": 30, "reb": 10, "ast": 8, "fg_pct": 55}) == 45
    assert rating_from(None) == 45


@pytest.mark.parametrize("source", SOURCES)
def test_player_stats_tool(source):
    s = build_league(source=source)
    top = s.roster("SAC")[0]
    out = execute(s, "player_stats", {"player_ids": [top.id, "nope"]})
    assert not out.is_error
    rows = out.result["players"]
    assert rows[0]["name"] == top.name and rows[0]["rating"] == top.rating
    assert rows[0]["career_rating"] == top.career_rating
    assert rows[0]["season_2025_26"] and rows[0]["career"]
    assert "gp" in rows[0]["season_2025_26"] and "pts" in rows[0]["career"]
    assert rows[1]["error"] == "no such player"
    # ratings are recomputable from the rows the tool shows
    assert rating_from(rows[0]["season_2025_26"]) == top.rating
    assert rating_from(rows[0]["career"]) == top.career_rating


@pytest.mark.parametrize("source", SOURCES)
def test_low_games_are_flagged(source):
    s = build_league(source=source)
    low = [p for p in s.players.values() if p.team and (s.stats.get(p.id, {}).get("season_2025_26") or {}).get("gp", 0) < 10]
    if not low:
        pytest.skip("no low-games player in this league")
    out = execute(s, "player_stats", {"player_ids": [low[0].id]})
    assert out.result["players"][0]["rating"] == 45
    assert "floored" in out.result["players"][0]["note"]


def test_tools_hash_is_stable_and_lists_nine_tools():
    assert len(TOOL_NAMES) == 10 and "player_stats" in TOOL_NAMES and "view_league" in TOOL_NAMES
    assert tools_hash() == tools_hash() and len(tools_hash()) == 12


def test_salary_in_dollars_is_rejected_clearly():
    s = build_league(source="synthetic")
    fa = s.free_agents()[0]
    out = execute(s, "sign_free_agent", {"team": "SAC", "player_id": fa.id, "salary": 2300000})
    assert out.is_error and "millions" in out.result["error"] and "2.30" in out.result["error"]


def test_read_rule_without_id_returns_full_text():
    s = build_league(source="synthetic")
    out = execute(s, "read_rule", {"rule_id": None})
    assert len(out.result["rules"]) == 10 and all(r["text"] for r in out.result["rules"])


def test_view_league_lists_every_team():
    s = build_league(source="synthetic")
    out = execute(s, "view_league", {})
    assert len(out.result["teams"]) == 30
    assert out.result["teams"][0]["payroll"] >= out.result["teams"][-1]["payroll"]
    assert {"cap_room", "open_spots", "over_tax_by"} <= set(out.result["teams"][0])


def test_value_blend_reference_points():
    from trade_desk.league import value_of
    career = {"gp": 900, "pts": 25}
    assert value_of(45, 87, {"gp": 0}, career) == 87          # missed the season: career
    assert value_of(74, 61, {"gp": 15}, career) == 66         # small sample: mostly career
    assert value_of(95, 88, {"gp": 65}, career) == 95         # full season: season
    assert value_of(70, 45, {"gp": 5}, None) == 70            # rookie, no career row: season


@pytest.mark.parametrize("source", SOURCES)
def test_value_is_shown_and_used_for_protection(source):
    from trade_desk.tasks import top_n_ids, by_value
    s = build_league(source=source)
    top = by_value(s, "POR")[:6]
    assert top_n_ids(s, "POR", 6) == {p.id for p in top}
    out = execute(s, "view_roster", {"team": "POR"})
    assert all("value" in p for p in out.result["players"])
    if source == "espn":
        lillard = next(p for p in s.players.values() if p.name == "Damian Lillard")
        assert lillard.rating == 45 and lillard.value >= 80
        assert lillard.id in top_n_ids(s, "POR", 6)
