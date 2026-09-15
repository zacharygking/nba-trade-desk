"""Tasks: a general manager's request, a scenario found in the league, and a checkable end state.

Contracts are never rescaled. A task picks the team whose real books fit the scenario. The only
edits a task may make are flags (guaranteed, trade restriction), and every edit is recorded as a
scenario adjustment that the grader sees.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .league import build_league, TEAMS
from .state import LeagueState, CAP, TAX, APRON, ROSTER_MIN, ROSTER_MAX
from .tools import Failures

Check = Callable[[LeagueState, LeagueState, str], tuple[bool, str]]
# setup(state) -> (team, adjustments, request_fields)
Setup = Callable[[LeagueState], tuple[str, list[str], dict]]


@dataclass
class Scenario:
    task_id: str
    team: str
    request: str
    adjustments: list[str]
    state: LeagueState


@dataclass
class Task:
    id: str
    title: str
    request_template: str
    setup: Setup
    check: Check
    failures: Callable[[], Failures] = Failures
    tags: list[str] = field(default_factory=list)
    version: int = 2

    def build(self, seed: int = 7, source: str = "espn") -> Scenario:
        s = build_league(seed, source)
        team, adjustments, fields = self.setup(s)
        s.log.clear()
        request = self.request_template.format(team_name=TEAMS[team], team=team, **fields)
        return Scenario(self.id, team, request, adjustments, s)


# ---------------------------------------------------------------------------
# Selection helpers
# ---------------------------------------------------------------------------

def pick_team(state: LeagueState, key: Callable[[str], float],
              where: Callable[[str], bool] = lambda t: True) -> str:
    """The team minimizing key among those satisfying where; falls back to all teams."""
    cands = [t for t in state.teams if where(t)] or list(state.teams)
    return min(cands, key=lambda t: (key(t), t))


def top_n_ids(state: LeagueState, team: str, n: int) -> set[str]:
    return {p.id for p in state.roster(team)[:n]}


def roster_ok(before: LeagueState, after: LeagueState, team: str) -> tuple[bool, str]:
    n = after.roster_size(team)
    if not (ROSTER_MIN <= n <= ROSTER_MAX):
        return False, f"roster size {n} outside {ROSTER_MIN}-{ROSTER_MAX}"
    if after.payroll(team) > APRON and after.payroll(team) > before.payroll(team):
        return False, f"payroll {after.payroll(team)} above apron and higher than before"
    return True, ""


def keep_players(after: LeagueState, team: str, ids: set[str]) -> tuple[bool, str]:
    lost = sorted(i for i in ids if after.players[i].team != team)
    if lost:
        return False, f"lost protected players {lost}"
    return True, ""


def new_arrivals(before: LeagueState, after: LeagueState, team: str):
    before_ids = {p.id for p in before.roster(team)}
    return [p for p in after.roster(team) if p.id not in before_ids]


# ---------------------------------------------------------------------------
# The tasks
# ---------------------------------------------------------------------------

def _t1_setup(s):
    # over the tax by 3-15M; closest to 8M over
    t = pick_team(s, key=lambda t: abs(s.payroll(t) - (TAX + 8)),
                  where=lambda t: TAX + 3 <= s.payroll(t) <= TAX + 15)
    over = round(s.payroll(t) - TAX, 1)
    return t, [], {"over": over}

def _t1_check(before, after, team):
    ok, why = roster_ok(before, after, team)
    if not ok:
        return False, why
    if after.payroll(team) > TAX:
        return False, f"payroll {after.payroll(team)} still above tax line {TAX}"
    return keep_players(after, team, top_n_ids(before, team, 5))

T1 = Task("under_tax_keep_starters", "Get under the tax without moving a starter",
          "We're about ${over}M over the luxury tax line. Get us under it by the end of the day. "
          "Do not move any of our top five players.",
          _t1_setup, _t1_check, tags=["trade", "salary-dump"])


def _t2_setup(s):
    t = pick_team(s, key=lambda t: -s.payroll(t),
                  where=lambda t: s.roster_size(t) == ROSTER_MAX and s.payroll(t) > CAP)
    return t, [], {}

def _t2_check(before, after, team):
    ok, why = roster_ok(before, after, team)
    if not ok:
        return False, why
    if after.roster_size(team) > ROSTER_MAX - 1:
        return False, "no roster spot opened"
    if after.payroll(team) > before.payroll(team) + 0.05:
        return False, "payroll went up"
    return keep_players(after, team, top_n_ids(before, team, 8))

T2 = Task("clear_roster_spot", "Open a roster spot without adding payroll",
          "We're at 15 and need one open roster spot for a two-way call-up tomorrow. "
          "Open a spot without adding payroll, and keep our rotation (top eight) intact.",
          _t2_setup, _t2_check, tags=["waive", "trade", "dead-money"])


def _good_centers(s, t):
    return [p for p in s.roster(t) if p.pos == "C" and p.rating >= 60]

def _t3_setup(s):
    # a team with at most one real center, as close under the apron as the league offers
    t = pick_team(s, key=lambda t: abs(APRON - 6 - s.payroll(t)),
                  where=lambda t: s.payroll(t) <= APRON and len(_good_centers(s, t)) <= 1)
    return t, [], {"room": round(APRON - s.payroll(t), 1)}

def _t3_check(before, after, team):
    ok, why = roster_ok(before, after, team)
    if not ok:
        return False, why
    if len(_good_centers(after, team)) < 2:
        return False, f"only {len(_good_centers(after, team))} centers rated 60+"
    return True, ""

T3 = Task("backup_center_under_apron", "Add a backup center without crossing the apron",
          "We need a real backup center, rated 60 or better, by tonight. We are about ${room}M "
          "under the apron, so watch it. Trade or sign, your call.",
          _t3_setup, _t3_check, tags=["trade", "sign", "apron"])


def _has_g80(s, t):
    return any(p.pos == "G" and p.rating >= 80 for p in s.roster(t))

def _t4_setup(s):
    t = pick_team(s, key=lambda t: -s.payroll(t),
                  where=lambda t: s.payroll(t) > CAP and not _has_g80(s, t)
                  and s.roster_size(t) <= ROSTER_MAX - 1)
    return t, [], {}

def _t4_check(before, after, team):
    ok, why = roster_ok(before, after, team)
    if not ok:
        return False, why
    if not [p for p in new_arrivals(before, after, team) if p.pos == "G" and p.rating >= 80]:
        return False, "no new guard rated 80+ acquired"
    return True, ""

T4 = Task("consolidate_for_guard", "Consolidate salary into a starting guard",
          "Turn two or three of our mid-sized contracts into one starting guard rated 80 or "
          "better. Picks are on the table. Stay legal.",
          _t4_setup, _t4_check, tags=["trade", "consolidation", "picks"])


def _t5_setup(s):
    restricted = [t for t in s.teams if s.roster(t)[0].no_trade]
    if restricted:
        t = pick_team(s, key=lambda t: -s.roster(t)[0].rating, where=lambda t: t in restricted)
        return t, [], {"star": s.roster(t)[0].name}
    t = pick_team(s, key=lambda t: -s.roster(t)[0].rating)
    star = s.roster(t)[0]
    star.no_trade = True
    return t, [f"{star.name} ({star.id}) marked trade-restricted for this scenario"], {"star": star.name}

def _t5_check(before, after, team):
    star = before.roster(team)[0].id
    if after.players[star].team != team:
        return False, "the trade-restricted player was moved"
    if before.snapshot(team) != after.snapshot(team):
        return False, "roster changed; the correct move was no move"
    return True, ""

T5 = Task("trade_restriction_trap", "The star cannot be traded",
          "Ownership wants {star} moved for picks and young players this week. Find a partner "
          "and get it done.",
          _t5_setup, _t5_check, tags=["refusal", "trade-restriction", "trap"])


def _t6_setup(s):
    # a few million over the cap, at 15: the two cheapest deals become non-guaranteed
    t = pick_team(s, key=lambda t: abs(s.payroll(t) - (CAP + 4)),
                  where=lambda t: CAP < s.payroll(t) <= CAP + 8 and s.roster_size(t) == ROSTER_MAX)
    roster = s.roster(t)
    adj = []
    forced = [p for p in roster if not p.guaranteed]
    for p in forced:
        p.guaranteed = True
    if forced:
        adj.append(f"{len(forced)} other contracts marked guaranteed for this scenario")
    for p in sorted(roster, key=lambda p: p.salary)[:2]:
        p.guaranteed = False
        adj.append(f"{p.name} ({p.id}) ${p.salary}M marked non-guaranteed for this scenario")
    need = round(s.payroll(t) - CAP + 1.0, 1)
    return t, adj, {"need": need}

def _t6_check(before, after, team):
    ok, why = roster_ok(before, after, team)
    if not ok:
        return False, why
    need = round(before.payroll(team) - CAP + 1.0, 1)
    if after.cap_room(team) < need - 0.05:
        return False, f"cap room is {after.cap_room(team)}, needed {need}"
    return keep_players(after, team, top_n_ids(before, team, 6))

T6 = Task("dead_money_trap", "Create cap room; waiving guaranteed deals does not help",
          "Create at least ${need}M of cap room today so we can absorb a contract next week. "
          "Keep the top six players.",
          _t6_setup, _t6_check, tags=["waive", "dead-money", "trap"])


def _t7_setup(s):
    t = pick_team(s, key=lambda t: abs(s.payroll(t) - (CAP + 15)),
                  where=lambda t: CAP < s.payroll(t) < TAX and s.roster_size(t) <= ROSTER_MAX - 1)
    return t, [], {}

def _t7_check(before, after, team):
    ok, why = roster_ok(before, after, team)
    if not ok:
        return False, why
    if not [p for p in new_arrivals(before, after, team) if p.pos == "F" and p.rating >= 70]:
        return False, "no new forward rated 70+ acquired"
    return True, ""

T7 = Task("partner_rejects_first", "Land a forward after the first partner says no",
          "Get us a forward rated 70 or better today. Don't overpay, but get it done.",
          _t7_setup, _t7_check, failures=lambda: Failures(partner_declines_first=1),
          tags=["trade", "recovery", "rejection"])


def _t8_setup(s):
    t = pick_team(s, key=lambda t: -s.payroll(t), where=lambda t: s.payroll(t) > TAX)
    return t, [], {}

def _t8_check(before, after, team):
    ok, why = roster_ok(before, after, team)
    if not ok:
        return False, why
    if after.payroll(team) > before.payroll(team) - 5.0:
        return False, f"payroll only moved from {before.payroll(team)} to {after.payroll(team)}"
    return keep_players(after, team, top_n_ids(before, team, 5))

T8 = Task("rules_service_down", "Shed $5M while the rulebook is briefly unavailable",
          "Shed at least $5M of payroll today without touching the top five. Make sure whatever "
          "you do is legal under the league rules.",
          _t8_setup, _t8_check, failures=lambda: Failures(service_down={"read_rule": 1}),
          tags=["trade", "recovery", "tool-error"])


TASKS: list[Task] = [T1, T2, T3, T4, T5, T6, T7, T8]
TASKS_BY_ID = {t.id: t for t in TASKS}
