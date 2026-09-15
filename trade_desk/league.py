"""Two leagues on one engine.

- "espn": the real 2025-26 league. Players, teams, positions, salaries and contract flags come from
  the ESPN snapshot in data/espn_2025-26.json (see data/fetch_espn.py for provenance). The one
  derived number is `rating`, computed from 2025-26 per-game stats by the formula in `rating_from`.
- "synthetic": invented players and contracts, seeded. Kept for the tool-grounding comparison:
  an agent cannot know these rosters from memory.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from .state import LeagueState, Player, Pick, POSITIONS, MIN_CONTRACT, ROSTER_MAX

SEASON = 2026   # ESPN's year for 2025-26
SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "espn_2025-26.json"

TEAMS = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}

# ESPN position labels -> the three the sandbox uses
POS_MAP = {"G": "G", "PG": "G", "SG": "G", "F": "F", "SF": "F", "PF": "F", "GF": "F",
           "C": "C", "FC": "C"}


def build_league(seed: int = 7, source: str = "espn") -> LeagueState:
    if source == "espn":
        return load_espn()
    if source == "synthetic":
        return build_synthetic(seed)
    raise ValueError(f"unknown league source {source!r}")


# ---------------------------------------------------------------------------
# Real league from the ESPN snapshot
# ---------------------------------------------------------------------------

STAT_KEYS = ("gp", "gs", "min", "pts", "reb", "ast", "stl", "blk", "to", "fg_pct", "three_pct", "ft_pct")


def rating_from(row: dict | None) -> int:
    """40-95 scale from per-game averages. One formula for a season and for a career, so the two
    ratings are comparable. Documented so a reader can recompute it.

    rating = 40 + 0.55 * minutes + 0.75 * points + 0.5 * rebounds + 0.9 * assists
             + 0.15 * (field-goal % - 45), clamped to [40, 95].
    A row with fewer than 10 games, or no row, is rated 45.
    Reference points: 36.7 min, 29.6 pts, 12.7 reb, 10.2 ast, 58% -> 95 (clamped);
    30.8 min, 16.1 pts, 10.7 reb, 4.9 ast, 56% -> 80; 24 min, 9 pts, 4 reb, 2 ast, 45% -> 64;
    10 min, 4 pts, 2 reb, 1 ast, 42% -> 50.
    """
    if not row or (row.get("gp") or 0) < 10:
        return 45
    v = (40.0 + 0.55 * (row.get("min") or 0) + 0.75 * (row.get("pts") or 0)
         + 0.5 * (row.get("reb") or 0) + 0.9 * (row.get("ast") or 0)
         + 0.15 * ((row.get("fg_pct") or 45) - 45))
    return int(round(max(40.0, min(95.0, v))))


def value_of(season_rating: int, career_rating: int, season_row: dict | None, career_row: dict | None) -> int:
    """Protection value: trust the season in proportion to games played.

    w = min(1, games / 41); value = w * season_rating + (1 - w) * career_rating.
    A player with no career row is his season rating. A player with no games is his career.
    """
    if not career_row:
        return season_rating
    gp = float((season_row or {}).get("gp") or 0)
    w = min(1.0, gp / 41.0)
    return int(round(w * season_rating + (1 - w) * career_rating))


def _row_from_core(st: dict) -> dict | None:
    """Fallback season row from the core statistics endpoint when the stats page has none."""
    if not st:
        return None
    return {"gp": st.get("gamesPlayed"), "min": st.get("avgMinutes"), "pts": st.get("avgPoints"),
            "reb": st.get("avgRebounds"), "ast": st.get("avgAssists"), "fg_pct": st.get("fieldGoalPct")}


def _clean(row: dict | None) -> dict | None:
    if not row:
        return None
    out = {k: row.get(k) for k in STAT_KEYS if row.get(k) is not None}
    if "seasons" in row:
        out["seasons"] = row["seasons"]
    if "team" in row and row["team"]:
        out["team"] = row["team"]
    return out or None


def stat_rows(r: dict) -> dict:
    """season / prior / career rows for one snapshot record, plus PER for the season."""
    by_season = {x.get("season"): x for x in (r.get("seasons") or [])}
    season = by_season.get("2025-26") or _row_from_core(r.get("stats_2025_26") or {})
    prior = by_season.get("2024-25")
    career = r.get("career")
    return {"season_2025_26": _clean(season), "season_2024_25": _clean(prior),
            "career": _clean(career), "per_2025_26": (r.get("stats_2025_26") or {}).get("PER")}


def load_espn(path: Path = SNAPSHOT) -> LeagueState:
    snap = json.loads(Path(path).read_text())
    teams = sorted(TEAMS)
    players: dict[str, Player] = {}
    rows = [r for r in snap["players"] if r["team"] in TEAMS]
    # Trim each team to 15 by salary; everyone trimmed becomes a free agent asking his salary.
    by_team: dict[str, list[dict]] = {}
    for r in rows:
        by_team.setdefault(r["team"], []).append(r)
    kept: list[tuple[dict, str | None]] = []
    for t, rs in by_team.items():
        rs.sort(key=lambda r: (-r["salary_2025_26"], r["name"]))
        for i, r in enumerate(rs):
            kept.append((r, t if i < ROSTER_MAX else None))
    stats: dict[str, dict] = {}
    for r, team in sorted(kept, key=lambda x: x[0]["espn_id"]):
        sal = round(r["salary_2025_26"] / 1e6, 2)
        rows = stat_rows(r)
        stats[f"E{r['espn_id']}"] = rows
        players[f"E{r['espn_id']}"] = Player(
            id=f"E{r['espn_id']}", name=r["name"], pos=POS_MAP.get(r["pos"], "F"),
            rating=rating_from(rows["season_2025_26"]),
            career_rating=rating_from(rows["career"]),
            value=value_of(rating_from(rows["season_2025_26"]), rating_from(rows["career"]),
                           rows["season_2025_26"], rows["career"]),
            salary=sal if team else 0.0,
            years=max(1, int(r.get("years_remaining") or 1)) if team else 0,
            guaranteed=True,
            # ESPN's tradeRestriction flag is set on ~40% of contracts and its meaning is not
            # documented, so it is kept in the snapshot but not applied. Tasks set no_trade
            # explicitly and record it as a scenario adjustment.
            no_trade=False,
            team=team,
            asking=max(MIN_CONTRACT, sal) if team is None else 0.0,
        )
    # Real players on a current roster with no 2025-26 contract. ESPN only serves current rosters,
    # so the rebuilt 2025-26 teams run thin; each is filled to 15 with its own current players,
    # priced from their 2026-27 contract when ESPN has one and at the minimum otherwise. The
    # salary_source flag says so in every tool result. The rest become free agents at the minimum.
    unsigned = sorted(snap.get("unsigned", []),
                      key=lambda r: (-(r.get("salary_2026_27") or 0), r["name"]))
    for r in unsigned:
        team = r.get("current_team")
        pid = f"E{r['espn_id']}"
        rows = stat_rows(r)
        stats[pid] = rows
        rating, career = rating_from(rows["season_2025_26"]), rating_from(rows["career"])
        val = value_of(rating, career, rows["season_2025_26"], rows["career"])
        if team in TEAMS and sum(1 for p in players.values() if p.team == team) < ROSTER_MAX:
            nxt = r.get("salary_2026_27")
            players[pid] = Player(
                id=pid, name=r["name"], pos=POS_MAP.get(r["pos"], "F"), rating=rating,
                career_rating=career, value=val,
                salary=round(nxt / 1e6, 2) if nxt else MIN_CONTRACT, years=1, guaranteed=True,
                no_trade=False, team=team,
                salary_source="inferred:2026-27 contract" if nxt else "inferred:minimum",
            )
        else:
            players[pid] = Player(
                id=pid, name=r["name"], pos=POS_MAP.get(r["pos"], "F"), rating=rating,
                career_rating=career, value=val,
                salary=0.0, years=0, guaranteed=True, no_trade=False, team=None,
                asking=MIN_CONTRACT, salary_source="inferred:minimum",
            )
    picks = _own_picks(teams)
    return LeagueState(season=SEASON, teams=teams, players=players, picks=picks,
                       dead_money={t: 0.0 for t in teams}, stats=stats,
                       meta={"source": "espn", "pulled_on": snap["provenance"]["pulled_on"],
                             "season": snap["provenance"]["season"]})


def _own_picks(teams: list[str]) -> dict[str, Pick]:
    picks: dict[str, Pick] = {}
    for t in teams:
        for year in (SEASON + 1, SEASON + 2):
            for rnd in (1, 2):
                k = f"{t}-{year}-R{rnd}"
                picks[k] = Pick(id=k, owner=t, original_team=t, year=year, round=rnd)
    return picks


# ---------------------------------------------------------------------------
# Synthetic league
# ---------------------------------------------------------------------------

FIRST = ["Marcus", "Devin", "Jalen", "Tyrese", "Cam", "Isaiah", "Malik", "Jaden", "Andre",
         "Kellan", "Donte", "Rashad", "Elijah", "Trey", "Dorian", "Kobe", "Jamal", "Terrence",
         "Nikola", "Luka", "Bogdan", "Jonas", "Kristaps", "Goran", "Rui", "Yuta", "Josh",
         "Keegan", "Davion", "Zion", "Amir", "Brandon", "Caleb", "Darius", "Evan", "Franz",
         "Gabe", "Herb", "Ivan", "Jaylen", "Kyle", "Lonnie", "Moses", "Naz", "Obi", "Payton",
         "Quentin", "Reggie", "Saddiq", "Tari", "Usman", "Vince", "Wendell", "Xavier", "Ziaire"]
LAST = ["Holloway", "Banks", "Reyes", "Okafor", "Whitfield", "Castellanos", "Nakamura", "Petrov",
        "Delgado", "Mbeki", "Sørensen", "Ferreira", "Kowalski", "Haddad", "Thornton", "Vance",
        "Ibarra", "Lindqvist", "Okonkwo", "Marchetti", "Pruitt", "Sato", "Ellison", "Grigoryan",
        "Duplessis", "Fontaine", "Yilmaz", "Bautista", "Hargrove", "Novak", "Achebe", "Mercer",
        "Quintero", "Radovic", "Sandoval", "Tremblay", "Ueda", "Villanueva", "Winslow", "Zamora"]


def salary_for(rating: int, rng: random.Random) -> float:
    """Salary in $M from rating with noise, scaled to the 2025-26 cap."""
    base = 2.2 * (1.0825 ** (rating - 50))
    noisy = base * rng.uniform(0.8, 1.2)
    return round(max(MIN_CONTRACT, min(noisy, 60.0)), 1)


def synthetic_row(rating: int, pos: str, rng: random.Random, gp: int = 65) -> dict:
    """Per-game averages consistent with a target rating, with position flavour."""
    r = rating
    row = {"gp": gp, "gs": max(0, gp - rng.randint(0, 30)),
           "min": round(8 + (r - 40) * 0.5 * rng.uniform(0.9, 1.1), 1),
           "pts": round(max(1.0, (r - 40) * 0.5 * rng.uniform(0.85, 1.15)), 1),
           "reb": round(max(0.5, 2 + (r - 45) * 0.15 + (2.5 if pos == "C" else -0.5 if pos == "G" else 0)), 1),
           "ast": round(max(0.3, 1 + (r - 45) * 0.12 + (1.5 if pos == "G" else -0.5 if pos == "C" else 0)), 1),
           "stl": round(rng.uniform(0.3, 1.5), 1), "blk": round(rng.uniform(0.1, 1.8 if pos == "C" else 0.6), 1),
           "to": round(max(0.3, (r - 45) * 0.05), 1),
           "fg_pct": round(44 + (r - 60) * 0.1 + (6 if pos == "C" else 0) + rng.uniform(-2, 2), 1),
           "three_pct": round(rng.uniform(28, 41), 1), "ft_pct": round(rng.uniform(65, 90), 1)}
    return row


def build_synthetic(seed: int = 7) -> LeagueState:
    rng = random.Random(seed)
    teams = sorted(TEAMS)
    players: dict[str, Player] = {}
    stats: dict[str, dict] = {}
    used_names: set[str] = set()

    def attach(pid: str, target: int, pos: str) -> tuple[int, int, int]:
        season = synthetic_row(target, pos, rng)
        exp = rng.randint(1, 10)
        career = synthetic_row(int(target + rng.uniform(-6, 3)), pos, rng, gp=60 * exp)
        career["seasons"] = exp
        stats[pid] = {"season_2025_26": season, "season_2024_25": synthetic_row(int(target + rng.uniform(-4, 4)), pos, rng),
                      "career": career, "per_2025_26": None}
        sr, cr = rating_from(season), rating_from(career)
        return sr, cr, value_of(sr, cr, season, career)

    def new_name() -> str:
        while True:
            n = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            if n not in used_names:
                used_names.add(n)
                return n

    pid = 0
    for t in teams:
        n_players = rng.choice([13, 14, 14, 15])
        ratings = ([rng.randint(84, 92)] + [rng.randint(74, 83) for _ in range(2)]
                   + [rng.randint(64, 76) for _ in range(5)]
                   + [rng.randint(48, 66) for _ in range(n_players - 8)])
        positions = ["G"] * 6 + ["F"] * 6 + ["C"] * 3   # a real roster has few centers
        rng.shuffle(positions)
        for i, r in enumerate(ratings):
            pid += 1
            rating, career, val = attach(f"P{pid:04d}", r, positions[i])
            players[f"P{pid:04d}"] = Player(
                id=f"P{pid:04d}", name=new_name(), pos=positions[i], rating=rating, career_rating=career, value=val,
                salary=salary_for(r, rng), years=rng.choice([1, 1, 2, 2, 3, 4]),
                guaranteed=(r >= 60 or rng.random() < 0.5),
                no_trade=(r >= 85 and rng.random() < 0.4), team=t,
            )
    for _ in range(40):
        pid += 1
        r = rng.randint(45, 74)
        pos = rng.choice(POSITIONS)
        rating, career, val = attach(f"P{pid:04d}", r, pos)
        players[f"P{pid:04d}"] = Player(
            id=f"P{pid:04d}", name=new_name(), pos=pos, rating=rating, career_rating=career, value=val, salary=0.0,
            years=0, guaranteed=True, no_trade=False, team=None, asking=salary_for(r, rng),
        )
    return LeagueState(season=SEASON, teams=teams, players=players, picks=_own_picks(teams),
                       dead_money={t: 0.0 for t in teams}, stats=stats,
                       meta={"source": "synthetic", "seed": seed})
