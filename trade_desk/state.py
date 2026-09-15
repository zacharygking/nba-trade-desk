"""League state: players, contracts, picks, dead money. Deterministic and cloneable."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field, asdict

# League constants, in $M. Cap, tax and apron are the real 2025-26 figures (cap $154.647M,
# tax $187.895M, first apron $195.945M). The rulebook treats the first apron as the only hard
# ceiling and uses one simplified minimum contract; see rules.py.
CAP = 154.6
TAX = 187.9
APRON = 195.9
ROSTER_MAX = 15
ROSTER_MIN = 13
MIN_CONTRACT = 2.3
MATCH_PCT = 1.25
MATCH_CUSHION = 0.1

# ESPN lists most players as G, F or C, so the sandbox uses those three positions.
POSITIONS = ("G", "F", "C")


@dataclass
class Player:
    id: str
    name: str
    pos: str
    rating: int
    salary: float          # this season, $M
    years: int             # seasons remaining including this one
    guaranteed: bool
    no_trade: bool
    team: str | None       # None = free agent
    asking: float = 0.0    # free agents only: asking salary
    salary_source: str = "contract"   # "contract" | "inferred:2026-27 contract" | "inferred:minimum"
    career_rating: int = 45           # same formula as rating, over career per-game averages


@dataclass
class Pick:
    id: str
    owner: str
    original_team: str
    year: int
    round: int


@dataclass
class LeagueState:
    season: int
    teams: list[str]
    players: dict[str, Player]
    picks: dict[str, Pick]
    dead_money: dict[str, float] = field(default_factory=dict)
    log: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)   # source, pulled_on, seed
    stats: dict[str, dict] = field(default_factory=dict)   # player id -> season / prior / career rows

    # --- queries -------------------------------------------------------
    def roster(self, team: str) -> list[Player]:
        return sorted((p for p in self.players.values() if p.team == team),
                      key=lambda p: (-p.rating, p.id))

    def free_agents(self) -> list[Player]:
        return sorted((p for p in self.players.values() if p.team is None),
                      key=lambda p: (-p.rating, p.id))

    def team_picks(self, team: str) -> list[Pick]:
        return sorted((k for k in self.picks.values() if k.owner == team),
                      key=lambda k: (k.year, k.round, k.id))

    def payroll(self, team: str) -> float:
        return round(sum(p.salary for p in self.roster(team)) + self.dead_money.get(team, 0.0), 2)

    def cap_room(self, team: str) -> float:
        return round(CAP - self.payroll(team), 2)

    def roster_size(self, team: str) -> int:
        return len(self.roster(team))

    def owner_of(self, asset_id: str) -> str | None:
        if asset_id in self.players:
            return self.players[asset_id].team
        if asset_id in self.picks:
            return self.picks[asset_id].owner
        return None

    # --- mutation helpers (rules are checked in rules.py, not here) ---
    def move_asset(self, asset_id: str, to_team: str) -> None:
        if asset_id in self.players:
            self.players[asset_id].team = to_team
        elif asset_id in self.picks:
            self.picks[asset_id].owner = to_team
        else:
            raise KeyError(asset_id)

    def clone(self) -> "LeagueState":
        return copy.deepcopy(self)

    def snapshot(self, team: str) -> dict:
        """Compact, comparable view of one team, used for diffs and checks."""
        return {
            "payroll": self.payroll(team),
            "dead_money": round(self.dead_money.get(team, 0.0), 2),
            "roster_size": self.roster_size(team),
            "players": {p.id: {"name": p.name, "pos": p.pos, "rating": p.rating,
                               "salary": p.salary, "years": p.years,
                               "guaranteed": p.guaranteed, "no_trade": p.no_trade,
                               "salary_source": p.salary_source}
                        for p in self.roster(team)},
            "picks": [k.id for k in self.team_picks(team)],
        }

    def diff(self, other: "LeagueState") -> dict:
        """What changed between self (before) and other (after), across all teams."""
        out: dict = {"teams": {}, "transactions": other.log[len(self.log):]}
        for t in self.teams:
            a, b = self.snapshot(t), other.snapshot(t)
            if a == b:
                continue
            out["teams"][t] = {
                "payroll": [a["payroll"], b["payroll"]],
                "dead_money": [a["dead_money"], b["dead_money"]],
                "roster_size": [a["roster_size"], b["roster_size"]],
                "players_out": sorted(set(a["players"]) - set(b["players"])),
                "players_in": sorted(set(b["players"]) - set(a["players"])),
                "picks_out": sorted(set(a["picks"]) - set(b["picks"])),
                "picks_in": sorted(set(b["picks"]) - set(a["picks"])),
            }
        return out

    def to_dict(self) -> dict:
        return {
            "season": self.season,
            "teams": self.teams,
            "players": {k: asdict(v) for k, v in self.players.items()},
            "picks": {k: asdict(v) for k, v in self.picks.items()},
            "dead_money": self.dead_money,
            "log": self.log,
        }
