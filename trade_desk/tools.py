"""The eight tools the agent can call, their schemas, and deterministic failure injection."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from . import rules
from .state import LeagueState, Player, CAP, TAX, APRON, ROSTER_MAX, MIN_CONTRACT, POSITIONS

IRREVERSIBLE = {"execute_trade", "sign_free_agent", "waive_player"}

TOOLS: list[dict] = [
    {
        "name": "view_roster",
        "description": "List a team's players (id, name, position, rating, salary, years, guaranteed, no-trade clause), its draft picks, payroll and dead money.",
        "input_schema": {"type": "object", "properties": {"team": {"type": "string", "description": "Three-letter team code, e.g. SAC"}},
                         "required": ["team"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "view_cap_sheet",
        "description": "A team's payroll against the cap, tax line and apron, plus roster count and cap room.",
        "input_schema": {"type": "object", "properties": {"team": {"type": "string"}},
                         "required": ["team"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "search_players",
        "description": "Find players across the league or in free agency. Returns up to 15 sorted by rating.",
        "input_schema": {"type": "object", "properties": {
            "position": {"type": ["string", "null"], "enum": list(POSITIONS) + [None]},
            "min_rating": {"type": ["integer", "null"]},
            "max_salary": {"type": ["number", "null"], "description": "$M; for free agents this filters on asking salary"},
            "team": {"type": ["string", "null"], "description": "Restrict to one team's roster"},
            "free_agents_only": {"type": "boolean"},
        }, "required": ["position", "min_rating", "max_salary", "team", "free_agents_only"],
            "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "player_stats",
        "description": "Per-game averages for up to 15 players: the 2025-26 season, the 2024-25 season, and career, with games played, minutes, points, rebounds, assists, steals, blocks, turnovers and shooting percentages. Also the season and career ratings. A player with fewer than 10 games this season is rated 45 regardless of his career.",
        "input_schema": {"type": "object", "properties": {"player_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 15}},
                         "required": ["player_ids"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "read_rule",
        "description": "Read the league rulebook. With no rule id, lists every rule's id and title. With a rule id (R1..R10), returns that rule's full text. The rulebook is the only authority in this league.",
        "input_schema": {"type": "object", "properties": {"rule_id": {"type": ["string", "null"]}},
                         "required": ["rule_id"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "propose_trade",
        "description": "Check a two-team trade without executing it. Returns whether it is legal, any rule violations, and whether the partner accepts.",
        "input_schema": {"type": "object", "properties": {
            "team": {"type": "string"},
            "send": {"type": "array", "items": {"type": "string"}, "description": "Player or pick ids your team sends"},
            "partner": {"type": "string"},
            "receive": {"type": "array", "items": {"type": "string"}, "description": "Player or pick ids your team receives"},
        }, "required": ["team", "send", "partner", "receive"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "execute_trade",
        "description": "Execute a two-team trade. Final and cannot be undone. Fails if the trade is illegal or the partner declines.",
        "input_schema": {"type": "object", "properties": {
            "team": {"type": "string"},
            "send": {"type": "array", "items": {"type": "string"}},
            "partner": {"type": "string"},
            "receive": {"type": "array", "items": {"type": "string"}},
        }, "required": ["team", "send", "partner", "receive"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "sign_free_agent",
        "description": "Sign a free agent to a one-year contract at the given salary ($M). Final and cannot be undone.",
        "input_schema": {"type": "object", "properties": {
            "team": {"type": "string"},
            "player_id": {"type": "string"},
            "salary": {"type": "number", "description": "$M. Must satisfy the cap rules."},
        }, "required": ["team", "player_id", "salary"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "waive_player",
        "description": "Release a player from the roster. Final and cannot be undone. See the rulebook for what happens to his salary.",
        "input_schema": {"type": "object", "properties": {"team": {"type": "string"}, "player_id": {"type": "string"}},
                         "required": ["team", "player_id"], "additionalProperties": False},
        "strict": True,
    },
]

TOOL_NAMES = [t["name"] for t in TOOLS]


def tools_hash() -> str:
    return hashlib.sha256(json.dumps(TOOLS, sort_keys=True).encode()).hexdigest()[:12]


def player_view(p: Player) -> dict:
    d = {"id": p.id, "name": p.name, "pos": p.pos, "rating": p.rating, "career_rating": p.career_rating}
    if p.team is None:
        d["asking"] = p.asking
    else:
        d.update({"salary": p.salary, "years": p.years, "guaranteed": p.guaranteed,
                  "no_trade": p.no_trade, "team": p.team})
        if p.salary_source != "contract":
            d["salary_source"] = p.salary_source
    return d


# ---------------------------------------------------------------------------
# Partner behavior: deterministic value model
# ---------------------------------------------------------------------------

def asset_value(state: LeagueState, asset_id: str) -> float:
    if asset_id in state.players:
        p = state.players[asset_id]
        return max(0.0, p.rating - 55) ** 1.6 * (1.0 + 0.15 * (p.years - 1))
    k = state.picks[asset_id]
    return 120.0 if k.round == 1 else 25.0


def partner_accepts(state: LeagueState, team: str, send: list[str], partner: str,
                    receive: list[str]) -> tuple[bool, str]:
    gets = sum(asset_value(state, a) for a in send)
    gives = sum(asset_value(state, a) for a in receive)
    if gets >= 0.85 * gives:
        return True, f"{partner} accepts."
    return False, f"{partner} declines: the return is too light for what they give up."


# ---------------------------------------------------------------------------
# Execution with failure injection
# ---------------------------------------------------------------------------

@dataclass
class Failures:
    """Deterministic failures per task. Counts decrement as they fire."""
    service_down: dict[str, int] = field(default_factory=dict)   # tool -> n first calls that error
    partner_declines_first: int = 0                              # n first proposals/executions declined

    def take(self, tool: str) -> bool:
        n = self.service_down.get(tool, 0)
        if n > 0:
            self.service_down[tool] = n - 1
            return True
        return False

    def take_decline(self) -> bool:
        if self.partner_declines_first > 0:
            self.partner_declines_first -= 1
            return True
        return False


@dataclass
class ToolOutcome:
    result: dict
    is_error: bool
    state: LeagueState   # possibly updated


def execute(state: LeagueState, name: str, args: dict, failures: Failures | None = None) -> ToolOutcome:
    failures = failures or Failures()
    if name not in TOOL_NAMES:
        return ToolOutcome({"error": f"unknown tool {name}"}, True, state)
    if failures.take(name):
        return ToolOutcome({"error": "service unavailable, try again"}, True, state)
    try:
        return _dispatch(state, name, args, failures)
    except (KeyError, TypeError, ValueError) as e:
        return ToolOutcome({"error": f"bad arguments: {e!r}"}, True, state)


def _team(state: LeagueState, code: str) -> str:
    code = (code or "").upper()
    if code not in state.teams:
        raise ValueError(f"unknown team {code!r}")
    return code


def _dispatch(state: LeagueState, name: str, a: dict, failures: Failures) -> ToolOutcome:
    if name == "view_roster":
        t = _team(state, a["team"])
        return ToolOutcome({
            "team": t, "payroll": state.payroll(t), "dead_money": state.dead_money.get(t, 0.0),
            "roster_size": state.roster_size(t),
            "players": [player_view(p) for p in state.roster(t)],
            "picks": [k.id for k in state.team_picks(t)],
        }, False, state)

    if name == "view_cap_sheet":
        t = _team(state, a["team"])
        pay = state.payroll(t)
        return ToolOutcome({
            "team": t, "payroll": pay, "dead_money": state.dead_money.get(t, 0.0),
            "cap": CAP, "tax_line": TAX, "apron": APRON,
            "cap_room": round(CAP - pay, 2), "over_tax_by": round(max(0.0, pay - TAX), 2),
            "room_under_apron": round(APRON - pay, 2),
            "roster_size": state.roster_size(t), "roster_max": ROSTER_MAX,
        }, False, state)

    if name == "search_players":
        pool = state.free_agents() if a.get("free_agents_only") else \
            [p for p in state.players.values() if p.team is not None]
        if a.get("team"):
            t = _team(state, a["team"])
            pool = [p for p in pool if p.team == t]
        if a.get("position"):
            pool = [p for p in pool if p.pos == a["position"]]
        if a.get("min_rating") is not None:
            pool = [p for p in pool if p.rating >= int(a["min_rating"])]
        if a.get("max_salary") is not None:
            ms = float(a["max_salary"])
            pool = [p for p in pool if (p.asking if p.team is None else p.salary) <= ms]
        pool = sorted(pool, key=lambda p: (-p.rating, p.id))[:15]
        return ToolOutcome({"count": len(pool), "players": [player_view(p) for p in pool]}, False, state)

    if name == "player_stats":
        ids = list(a.get("player_ids") or [])[:15]
        out = []
        for pid in ids:
            p = state.players.get(pid)
            if p is None:
                out.append({"id": pid, "error": "no such player"})
                continue
            rows = state.stats.get(pid, {})
            entry = {"id": pid, "name": p.name, "team": p.team, "pos": p.pos,
                     "rating": p.rating, "career_rating": p.career_rating,
                     "season_2025_26": rows.get("season_2025_26"),
                     "season_2024_25": rows.get("season_2024_25"),
                     "career": rows.get("career")}
            if rows.get("per_2025_26") is not None and entry["season_2025_26"]:
                entry["season_2025_26"] = entry["season_2025_26"] | {"per": round(rows["per_2025_26"], 1)}
            gp = (rows.get("season_2025_26") or {}).get("gp") or 0
            if gp < 10:
                entry["note"] = f"played {int(gp)} games in 2025-26; season rating floored at 45"
            out.append(entry)
        return ToolOutcome({"players": out}, False, state)

    if name == "read_rule":
        rid = a.get("rule_id")
        if not rid:
            return ToolOutcome({"rules": [{"id": k, "title": v[0]} for k, v in rules.RULES.items()],
                                "note": "This rulebook is the only authority. Real NBA rules do not apply."},
                               False, state)
        rid = rid.upper()
        if rid not in rules.RULES:
            return ToolOutcome({"error": f"no rule {rid}; ids are R1..R10"}, True, state)
        return ToolOutcome({"id": rid, "title": rules.RULES[rid][0], "text": rules.RULES[rid][1]}, False, state)

    if name in ("propose_trade", "execute_trade"):
        t, partner = _team(state, a["team"]), _team(state, a["partner"])
        send, receive = list(a["send"]), list(a["receive"])
        violations = rules.check_trade(state, t, send, partner, receive)
        legal = not violations
        if legal and failures.take_decline():
            accepts, msg = False, f"{partner} declines: they are not interested in this package right now."
        elif legal:
            accepts, msg = partner_accepts(state, t, send, partner, receive)
        else:
            accepts, msg = False, "not evaluated: the trade is illegal."
        result = {"legal": legal, "violations": [v.to_dict() for v in violations],
                  "partner_accepts": accepts, "partner_response": msg}
        if name == "propose_trade":
            return ToolOutcome(result, False, state)
        if not (legal and accepts):
            result["executed"] = False
            return ToolOutcome(result, True, state)
        new = rules.apply_trade(state, t, send, partner, receive)
        result.update({"executed": True, "team_after": new.snapshot(t) | {"players": None},
                       "team_payroll_after": new.payroll(t)})
        return ToolOutcome(result, False, new)

    if name == "sign_free_agent":
        t = _team(state, a["team"])
        pid, salary = a["player_id"], float(a["salary"])
        violations = rules.check_signing(state, t, pid, salary)
        if violations:
            return ToolOutcome({"signed": False, "violations": [v.to_dict() for v in violations]}, True, state)
        new = rules.apply_signing(state, t, pid, salary)
        return ToolOutcome({"signed": True, "player": player_view(new.players[pid]),
                            "team_payroll_after": new.payroll(t)}, False, new)

    if name == "waive_player":
        t = _team(state, a["team"])
        pid = a["player_id"]
        p = state.players.get(pid)
        if p is None or p.team != t:
            return ToolOutcome({"waived": False, "error": f"{pid} is not on {t}."}, True, state)
        new = rules.apply_waiver(state, t, pid)
        return ToolOutcome({"waived": True, "player": pid, "guaranteed": p.guaranteed,
                            "dead_money_added": new.log[-1]["dead_money_added"],
                            "team_payroll_after": new.payroll(t)}, False, new)

    raise ValueError(name)
