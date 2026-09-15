from trade_desk.league import build_synthetic
from trade_desk.rules import check_trade, check_signing, apply_waiver, apply_trade
from trade_desk.state import CAP, APRON, ROSTER_MAX, MIN_CONTRACT


def scale_payroll_to(state, team, target):
    """Test fixture: rescale a synthetic team's salaries so its payroll lands on target."""
    roster = state.roster(team)
    f = target / sum(p.salary for p in roster)
    for p in roster:
        p.salary = round(max(MIN_CONTRACT, p.salary * f), 1)
    roster[0].salary = round(roster[0].salary + (target - state.payroll(team)), 1)


def fill_roster_to(state, team, n):
    """Test fixture: add or drop bench players so the team has exactly n."""
    roster = state.roster(team)
    while len(roster) > n:
        p = roster.pop(); p.team = None; p.asking = MIN_CONTRACT
    fas = state.free_agents()
    while len(roster) < n:
        p = fas.pop(); p.team, p.salary, p.years, p.asking = team, MIN_CONTRACT, 1, 0.0
        roster.append(p)


def _codes(vs):
    return sorted({v.rule for v in vs})


def test_league_is_deterministic():
    a, b = build_synthetic(7), build_synthetic(7)
    assert a.to_dict() == b.to_dict()
    assert build_synthetic(8).to_dict() != a.to_dict()


def test_league_shape():
    s = build_synthetic(7)
    assert len(s.teams) == 30
    for t in s.teams:
        assert 13 <= s.roster_size(t) <= 15
        assert len(s.team_picks(t)) == 4
    assert len(s.free_agents()) == 40


def test_salary_matching_violation():
    s = build_synthetic(7)
    scale_payroll_to(s, "SAC", CAP + 10)
    scale_payroll_to(s, "LAL", CAP + 10)
    cheap = s.roster("SAC")[-1]          # low salary out
    star = s.roster("LAL")[0]             # high salary in
    star.no_trade = False
    vs = check_trade(s, "SAC", [cheap.id], "LAL", [star.id])
    assert "R2" in _codes(vs)


def test_matching_not_required_under_cap():
    s = build_synthetic(7)
    scale_payroll_to(s, "SAC", CAP - 60)
    scale_payroll_to(s, "LAL", CAP - 60)
    cheap = s.roster("SAC")[-1]
    good = s.roster("LAL")[2]
    good.no_trade = False
    vs = check_trade(s, "SAC", [cheap.id], "LAL", [good.id])
    assert "R2" not in _codes(vs)


def test_no_trade_clause():
    s = build_synthetic(7)
    star = s.roster("SAC")[0]
    star.no_trade = True
    other = s.roster("LAL")[0]
    vs = check_trade(s, "SAC", [star.id], "LAL", [other.id])
    assert "R5" in _codes(vs)


def test_roster_limit_and_apron():
    s = build_synthetic(7)
    fill_roster_to(s, "SAC", 15)
    scale_payroll_to(s, "SAC", APRON - 1)
    a, b = s.roster("LAL")[1], s.roster("LAL")[2]
    a.no_trade = b.no_trade = False
    out = s.roster("SAC")[-1]
    vs = check_trade(s, "SAC", [out.id], "LAL", [a.id, b.id])
    codes = _codes(vs)
    assert "R4" in codes           # 15 - 1 + 2 = 16
    assert "R3" in codes or "R2" in codes


def test_ownership_checked():
    s = build_synthetic(7)
    p = s.roster("BOS")[0]
    vs = check_trade(s, "SAC", [p.id], "LAL", [])
    assert _codes(vs) == ["R10"]


def test_pick_rule():
    s = build_synthetic(7)
    picks = [k.id for k in s.team_picks("SAC") if k.round == 1]
    vs = check_trade(s, "SAC", picks, "LAL", [])
    assert "R9" in _codes(vs)
    vs = check_trade(s, "SAC", picks[:1], "LAL", [])
    assert "R9" not in _codes(vs)


def test_apply_trade_moves_assets():
    s = build_synthetic(7)
    p = s.roster("SAC")[-1]
    k = s.team_picks("LAL")[0]
    after = apply_trade(s, "SAC", [p.id], "LAL", [k.id])
    assert after.players[p.id].team == "LAL"
    assert after.picks[k.id].owner == "SAC"
    assert s.players[p.id].team == "SAC"   # original untouched


def test_signing_rules():
    s = build_synthetic(7)
    fa = s.free_agents()[0]
    scale_payroll_to(s, "SAC", CAP + 5)
    fill_roster_to(s, "SAC", 14)
    assert "R1" in _codes(check_signing(s, "SAC", fa.id, fa.asking))     # over cap, not a minimum
    cheap = [p for p in s.free_agents() if p.asking <= MIN_CONTRACT]
    if cheap:
        assert check_signing(s, "SAC", cheap[0].id, MIN_CONTRACT) == []
    pricey = [p for p in s.free_agents() if p.asking > MIN_CONTRACT][0]
    assert "R6" in _codes(check_signing(s, "SAC", pricey.id, MIN_CONTRACT))
    fill_roster_to(s, "SAC", ROSTER_MAX)
    assert "R4" in _codes(check_signing(s, "SAC", fa.id, MIN_CONTRACT))


def test_waiver_dead_money():
    s = build_synthetic(7)
    p = s.roster("SAC")[0]
    p.guaranteed = True
    before = s.payroll("SAC")
    after = apply_waiver(s, "SAC", p.id)
    assert after.players[p.id].team is None
    assert abs(after.payroll("SAC") - before) < 0.01     # guaranteed: nothing cleared
    q = s.roster("SAC")[-1]
    q.guaranteed = False
    after2 = apply_waiver(s, "SAC", q.id)
    assert after2.payroll("SAC") < before


def test_over_apron_team_may_waive_and_swap_but_not_add():
    from trade_desk.rules import check_trade, apply_waiver
    s = build_synthetic(7)
    scale_payroll_to(s, "SAC", APRON + 10)
    fill_roster_to(s, "SAC", 14)
    scale_payroll_to(s, "LAL", CAP - 40)
    a = s.roster("SAC")[-1]
    # equal-salary swap: payroll unchanged, allowed
    b = next(p for p in s.roster("LAL") if abs(p.salary - a.salary) < 0.01) if any(
        abs(p.salary - a.salary) < 0.01 for p in s.roster("LAL")) else None
    if b is not None:
        b.no_trade = False
        assert "R3" not in {v.rule for v in check_trade(s, "SAC", [a.id], "LAL", [b.id])}
    # taking back more salary than sent: refused
    big = max(s.roster("LAL"), key=lambda p: p.salary); big.no_trade = False
    assert "R3" in {v.rule for v in check_trade(s, "SAC", [a.id], "LAL", [big.id])}
    # waiver: always allowed, payroll flat when guaranteed
    a.guaranteed = True
    after = apply_waiver(s, "SAC", a.id)
    assert abs(after.payroll("SAC") - s.payroll("SAC")) < 0.01
