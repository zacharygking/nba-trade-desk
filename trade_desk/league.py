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

def rating_from(stats: dict) -> int:
    """40-95 scale from 2025-26 per-game stats. Documented so a reader can recompute it.

    rating = 40 + 0.8 * PER + 0.5 * minutes per game + 0.6 * points per game, clamped to [40, 95].
    A player with fewer than 10 games, or no stats, is rated 45.
    Reference points: PER 32, 36 min, 29 pts -> 95 (clamped); PER 22, 35 min, 26 pts -> 91;
    PER 22, 30 min, 13 pts -> 80; PER 13, 24 min, 9 pts -> 68; PER 10, 10 min, 4 pts -> 55.
    Minutes and points keep small-sample bench efficiency from outranking starters.
    """
    if not stats or stats.get("gamesPlayed", 0) < 10:
        return 45
    per = float(stats.get("PER", 0.0))
    mins = float(stats.get("avgMinutes", 0.0))
    pts = float(stats.get("avgPoints", 0.0))
    return int(round(max(40.0, min(95.0, 40.0 + 0.8 * per + 0.5 * mins + 0.6 * pts))))


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
    for r, team in sorted(kept, key=lambda x: x[0]["espn_id"]):
        sal = round(r["salary_2025_26"] / 1e6, 2)
        players[f"E{r['espn_id']}"] = Player(
            id=f"E{r['espn_id']}", name=r["name"], pos=POS_MAP.get(r["pos"], "F"),
            rating=rating_from(r.get("stats_2025_26") or {}),
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
        rating = rating_from(r.get("stats_2025_26") or {})
        if team in TEAMS and sum(1 for p in players.values() if p.team == team) < ROSTER_MAX:
            nxt = r.get("salary_2026_27")
            players[pid] = Player(
                id=pid, name=r["name"], pos=POS_MAP.get(r["pos"], "F"), rating=rating,
                salary=round(nxt / 1e6, 2) if nxt else MIN_CONTRACT, years=1, guaranteed=True,
                no_trade=False, team=team,
                salary_source="inferred:2026-27 contract" if nxt else "inferred:minimum",
            )
        else:
            players[pid] = Player(
                id=pid, name=r["name"], pos=POS_MAP.get(r["pos"], "F"), rating=rating,
                salary=0.0, years=0, guaranteed=True, no_trade=False, team=None,
                asking=MIN_CONTRACT, salary_source="inferred:minimum",
            )
    picks = _own_picks(teams)
    return LeagueState(season=SEASON, teams=teams, players=players, picks=picks,
                       dead_money={t: 0.0 for t in teams},
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


def build_synthetic(seed: int = 7) -> LeagueState:
    rng = random.Random(seed)
    teams = sorted(TEAMS)
    players: dict[str, Player] = {}
    used_names: set[str] = set()

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
            players[f"P{pid:04d}"] = Player(
                id=f"P{pid:04d}", name=new_name(), pos=positions[i], rating=r,
                salary=salary_for(r, rng), years=rng.choice([1, 1, 2, 2, 3, 4]),
                guaranteed=(r >= 60 or rng.random() < 0.5),
                no_trade=(r >= 85 and rng.random() < 0.4), team=t,
            )
    for _ in range(40):
        pid += 1
        r = rng.randint(45, 74)
        players[f"P{pid:04d}"] = Player(
            id=f"P{pid:04d}", name=new_name(), pos=rng.choice(POSITIONS), rating=r, salary=0.0,
            years=0, guaranteed=True, no_trade=False, team=None, asking=salary_for(r, rng),
        )
    return LeagueState(season=SEASON, teams=teams, players=players, picks=_own_picks(teams),
                       dead_money={t: 0.0 for t in teams}, meta={"source": "synthetic", "seed": seed})
