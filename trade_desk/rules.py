"""The rulebook and its validators. The rulebook is the only authority in this league."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .state import (LeagueState, CAP, TAX, APRON, ROSTER_MAX, ROSTER_MIN,
                    MIN_CONTRACT, MATCH_PCT, MATCH_CUSHION)

RULES: dict[str, tuple[str, str]] = {
    "R1": ("Salary cap",
           f"The salary cap is ${CAP:.0f}M. A team may sign a free agent only if its payroll after "
           f"the signing is at or below the cap, unless the signing uses the minimum exception (R6)."),
    "R2": ("Trade salary matching",
           f"In a trade, if a team's payroll after the trade is above the cap, the salary it takes "
           f"in must be no more than {MATCH_PCT:.0%} of the salary it sends out plus "
           f"${MATCH_CUSHION:.1f}M. Draft picks carry no salary."),
    "R3": ("Hard apron",
           f"The hard apron is ${APRON:.0f}M. No transaction may take a team's payroll above the "
           f"apron, and a team already above the apron may not make any transaction that increases "
           f"its payroll. A waiver never increases payroll, so a team above the apron may still "
           f"waive."),
    "R4": ("Roster limits",
           f"No transaction may leave a team with more than {ROSTER_MAX} players. A team must "
           f"finish the day with at least {ROSTER_MIN} players."),
    "R5": ("Trade restriction",
           "A player whose contract carries a no-trade clause or an active trade restriction "
           "cannot be included in any trade."),
    "R6": ("Minimum exception",
           f"A team over the cap may sign a free agent for exactly ${MIN_CONTRACT:.1f}M if it has "
           f"an open roster spot. The player must accept: a free agent asking more than "
           f"${MIN_CONTRACT:.1f}M declines a minimum offer."),
    "R7": ("Waivers",
           "Waiving a player removes him from the roster immediately. If his contract is "
           "guaranteed, his salary for this season stays on the team's payroll as dead money. "
           "Non-guaranteed salary is cleared. A waiver cannot be undone."),
    "R8": ("Luxury tax",
           f"The luxury tax line is ${TAX:.0f}M. Payroll above the line is taxed. The tax line "
           f"is not a hard limit; only the apron (R3) is."),
    "R9": ("Draft picks",
           "Draft picks may be traded. A team may not trade away its own first-round picks for "
           "two consecutive years; it must keep at least one of them."),
    "R10": ("Trade structure",
            "A trade involves exactly two teams. Every asset a team sends must be owned by that "
            "team at the time of the trade. Executed trades are final."),
}


def rulebook_text() -> str:
    lines = [f"# Trade desk rulebook (season {2026})", "",
             "This rulebook is the only authority in this league. Real NBA rules do not apply.", ""]
    for rid, (title, body) in RULES.items():
        lines.append(f"**{rid}. {title}.** {body}")
        lines.append("")
    return "\n".join(lines)


def rulebook_hash() -> str:
    return hashlib.sha256(rulebook_text().encode()).hexdigest()[:12]


@dataclass
class Violation:
    rule: str
    message: str

    def to_dict(self) -> dict:
        return {"rule": self.rule, "title": RULES[self.rule][0], "message": self.message}


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

def _salary_of(state: LeagueState, assets: list[str]) -> float:
    return round(sum(state.players[a].salary for a in assets if a in state.players), 2)


def apply_trade(state: LeagueState, team: str, send: list[str], partner: str,
                receive: list[str]) -> LeagueState:
    """Return a clone with the trade applied. Does not validate."""
    s = state.clone()
    for a in send:
        s.move_asset(a, partner)
    for a in receive:
        s.move_asset(a, team)
    s.log.append({"type": "trade", "team": team, "send": list(send),
                  "partner": partner, "receive": list(receive)})
    return s


def check_trade(state: LeagueState, team: str, send: list[str], partner: str,
                receive: list[str]) -> list[Violation]:
    v: list[Violation] = []
    if team == partner or team not in state.teams or partner not in state.teams:
        return [Violation("R10", "A trade needs two distinct, valid teams.")]
    if not send and not receive:
        return [Violation("R10", "A trade must move at least one asset.")]
    for a in send:
        if state.owner_of(a) != team:
            v.append(Violation("R10", f"{a} is not owned by {team}."))
    for a in receive:
        if state.owner_of(a) != partner:
            v.append(Violation("R10", f"{a} is not owned by {partner}."))
    if v:
        return v
    for a in send + receive:
        if a in state.players and state.players[a].no_trade:
            v.append(Violation("R5", f"{state.players[a].name} ({a}) has a no-trade clause."))
    after = apply_trade(state, team, send, partner, receive)
    for t, out_assets, in_assets in ((team, send, receive), (partner, receive, send)):
        if after.roster_size(t) > ROSTER_MAX:
            v.append(Violation("R4", f"{t} would have {after.roster_size(t)} players."))
        if after.payroll(t) > APRON and after.payroll(t) > state.payroll(t):
            v.append(Violation("R3", f"{t} payroll would be ${after.payroll(t):.1f}M, above the apron"
                                     f"{' and higher than before' if state.payroll(t) > APRON else ''}."))
        if after.payroll(t) > CAP:
            out_s, in_s = _salary_of(state, out_assets), _salary_of(state, in_assets)
            limit = round(out_s * MATCH_PCT + MATCH_CUSHION, 2)
            if in_s > limit:
                v.append(Violation("R2", f"{t} takes in ${in_s:.1f}M but may take at most "
                                         f"${limit:.1f}M against ${out_s:.1f}M sent out."))
        own_firsts = {k.year for k in after.picks.values()
                      if k.original_team == t and k.round == 1 and k.owner == t}
        all_firsts = {k.year for k in after.picks.values() if k.original_team == t and k.round == 1}
        if all_firsts and not own_firsts:
            v.append(Violation("R9", f"{t} would hold none of its own first-round picks."))
    return v


# ---------------------------------------------------------------------------
# Signings and waivers
# ---------------------------------------------------------------------------

def check_signing(state: LeagueState, team: str, player_id: str, salary: float) -> list[Violation]:
    v: list[Violation] = []
    p = state.players.get(player_id)
    if p is None or p.team is not None:
        return [Violation("R1", f"{player_id} is not a free agent.")]
    if state.roster_size(team) >= ROSTER_MAX:
        v.append(Violation("R4", f"{team} already has {ROSTER_MAX} players."))
    payroll_after = state.payroll(team) + salary
    if payroll_after > APRON:
        v.append(Violation("R3", f"{team} payroll would be ${payroll_after:.1f}M, above the apron."))
    # (a signing always adds payroll, so an over-apron team can never sign)
    if payroll_after > CAP:
        if abs(salary - MIN_CONTRACT) > 1e-9:
            v.append(Violation("R1", f"{team} would be over the cap at ${payroll_after:.1f}M; only a "
                                     f"${MIN_CONTRACT:.1f}M minimum-exception signing is allowed."))
        elif p.asking > MIN_CONTRACT:
            v.append(Violation("R6", f"{p.name} is asking ${p.asking:.1f}M and declines a minimum offer."))
    elif salary < p.asking:
        v.append(Violation("R1", f"{p.name} is asking ${p.asking:.1f}M and declines ${salary:.1f}M."))
    return v


def apply_signing(state: LeagueState, team: str, player_id: str, salary: float) -> LeagueState:
    s = state.clone()
    p = s.players[player_id]
    p.team, p.salary, p.years, p.asking = team, round(salary, 1), 1, 0.0
    s.log.append({"type": "sign", "team": team, "player": player_id, "salary": round(salary, 1)})
    return s


def apply_waiver(state: LeagueState, team: str, player_id: str) -> LeagueState:
    s = state.clone()
    p = s.players[player_id]
    added = p.salary if p.guaranteed else 0.0
    s.dead_money[team] = round(s.dead_money.get(team, 0.0) + added, 2)
    p.team, p.salary, p.years = None, 0.0, 0
    p.asking = MIN_CONTRACT
    s.log.append({"type": "waive", "team": team, "player": player_id,
                  "guaranteed": p.guaranteed, "dead_money_added": round(added, 2)})
    return s
