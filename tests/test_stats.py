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
    assert len(TOOL_NAMES) == 9 and "player_stats" in TOOL_NAMES
    assert tools_hash() == tools_hash() and len(tools_hash()) == 12
