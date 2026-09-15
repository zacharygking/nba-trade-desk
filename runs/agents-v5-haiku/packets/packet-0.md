# Grading packet: backup_center_under_apron (team MIA)

## The request to the agent
We need a real backup center, rated 60 or better, by tonight. We are about $6.7M under the apron, so watch it. Trade or sign, your call.

## Scenario adjustments the grader should know about
- none

## Rulebook (the only authority; real NBA rules do not apply)
# Trade desk rulebook (season 2026)

This rulebook is the only authority in this league. Real NBA rules do not apply.

**R1. Salary cap.** The salary cap is $155M. A team may sign a free agent only if its payroll after the signing is at or below the cap, unless the signing uses the minimum exception (R6).

**R2. Trade salary matching.** In a trade, if a team's payroll after the trade is above the cap, the salary it takes in must be no more than 125% of the salary it sends out plus $0.1M. Draft picks carry no salary.

**R3. Hard apron.** The hard apron is $196M. No transaction may take a team's payroll above the apron. A team that is already above the apron may only make transactions that reduce its payroll.

**R4. Roster limits.** No transaction may leave a team with more than 15 players. A team must finish the day with at least 13 players.

**R5. Trade restriction.** A player whose contract carries a no-trade clause or an active trade restriction cannot be included in any trade.

**R6. Minimum exception.** A team over the cap may sign a free agent for exactly $2.3M if it has an open roster spot. The player must accept: a free agent asking more than $2.3M declines a minimum offer.

**R7. Waivers.** Waiving a player removes him from the roster immediately. If his contract is guaranteed, his salary for this season stays on the team's payroll as dead money. Non-guaranteed salary is cleared. A waiver cannot be undone.

**R8. Luxury tax.** The luxury tax line is $188M. Payroll above the line is taxed. The tax line is not a hard limit; only the apron (R3) is.

**R9. Draft picks.** Draft picks may be traded. A team may not trade away its own first-round picks for two consecutive years; it must keep at least one of them.

**R10. Trade structure.** A trade involves exactly two teams. Every asset a team sends must be owned by that team at the time of the trade. Executed trades are final.


## Tools the agent had
- view_roster: List a team's players (id, name, position, season rating, career rating, value, salary, years, guaranteed, no-trade clause), its draft picks, payroll and dead money. 'value' blends season and career rating by games played and is what 'top N players' means in requests.
- view_league: Every team's payroll, cap room, distance from the tax line and apron, roster count and dead money, in one call. Use it to find trade partners with room or roster spots.
- view_cap_sheet: A team's payroll against the cap, tax line and apron, plus roster count and cap room.
- search_players: Find players across the league or in free agency. Returns up to 15 sorted by rating.
- player_stats: Per-game averages for up to 15 players: the 2025-26 season, the 2024-25 season, and career, with games played, minutes, points, rebounds, assists, steals, blocks, turnovers and shooting percentages. Also the season and career ratings. A player with fewer than 10 games this season is rated 45 regardless of his career.
- read_rule: Read the league rulebook. With no rule id, returns every rule in full (ten short rules). With a rule id (R1..R10), returns just that rule. The rulebook is the only authority in this league.
- propose_trade: Check a two-team trade without executing it. Returns whether it is legal, any rule violations, and whether the partner accepts.
- execute_trade: Execute a two-team trade. Final and cannot be undone. Fails if the trade is illegal or the partner declines. FINAL.
- sign_free_agent: Sign a free agent to a one-year contract at the given salary ($M). Final and cannot be undone. FINAL.
- waive_player: Release a player from the roster. Final and cannot be undone. See the rulebook for what happens to his salary. FINAL.

## Trajectory (5 tool calls, 0 errors, 1 irreversible; ended: end_turn)
CALL view_league {}
RESULT {"cap": 154.6, "tax_line": 187.9, "apron": 195.9, "roster_max": 15, "teams": [{"team": "CLE", "payroll": 211.97, "cap_room": -57.37, "over_tax_by": 24.07, "room_under_apron": -16.07, "roster_size": 15, "open_spots": 0, "dead_money": 0.0}, {"team": "NYK", "payroll": 210.41, "cap_room": -55.81, "over_tax_by": 22.51, "room_under_apron": -14.51, "roster_size": 15, "open_spots": 0, "dead_money": 0.0}, {"team": "GSW", "payroll": 205.27, "cap_room": -50.67, "over_tax_by": 17.37, "room_under_apron": -9.37, "roster_size": 14, "open_spots": 1, "dead_money": 0.0}, {"team": "HOU", "payroll": 200.12, "cap_room": -45.52, "over_tax_by": 12.22, "room_under_apron": -4.22, "roster_size": 14, "open_spots": 1, "dead_money": 0.0}, {"team": "LAL", "payroll": 193.75, "cap_room": -39.15, "over_tax_by": 5.85, "room_under_apron": 2.15, "roster_size": 14, "open_spots": 1, "dead_money": 0.0}, {"team": "PHI", "payroll": 192.26, "cap_room": -37.66, "over_tax_by": 4.36, "room_under_apron": 3.64, "roster_size": 14, "open_spots": 1, "dead_money": 0.0}, {"team": "BOS", "payroll": 191.64, "cap_room": -37.04, "over_tax_by": 3.74, "room_under_apron": 4.26, "roster_size": 14, "open_spots": 1, "dead_money": 0.0}, {"team": "CHI", "payroll": 191.47, "cap_room": -36.87, "over_tax_by": 3.57, "room_under_apron": 4.43, "roster_size": 15, "open_spots": 0, "dead_money": 0.0}, {"team": "MIN", "payroll": 191.43, "cap_room": -36.83, "over_tax_by": 3.53, "room_under_apron": 4.47, "roster_size": 14, "open_spots": 1, "dead_money": 0.0}, {"team": "ORL", "payroll": 189.52, "cap_room": -34.92, "over_tax_by": 1.62, "room_under_apron": 6.38, "roster_size": 15, "open_spots": 0, "dead_money": 0.0}, {"team": "MIA", "payroll": 189.17, "cap_room": -34.57, "over_tax_by": 1.27, "room_under_apron": 6.73, "roster_size": 14, "open_spots": 1, "dead_money": 0.0}, {"team": "SAC", "payroll": 185.51, "cap_room": -30.91, "over_tax_by": 0.0, "room_under_apron": 10.39, "roster_size": 14, "open_spots": 1, "dead_money": 0.0}, {"team": "LAC", "payroll": 185.33, "cap_room": -30.73, "over_tax_by": 0.0, "room_under_apron": 10.57, "roster_size": 14, "open_spots": 1, "dead_money": 0.0}, {"team": "OKC", "payroll": 184.41, "cap_room": -29.81, "over_tax_by": 0.0, "room_under_apron": 11.49, "roster_size": 15, "open_spots": 0, "dead_money": 0.0}, {"team": "TOR", "payroll": 184.26, "cap_room": -29.66, "over_tax_by": 0.0, "room_under_apron": 11.64, "roster_size": 14, "open_spots": 1, "dead_money": 0.0}, {"team": "NOP", "payroll": 182.15, "cap_ro ...[2314 more chars]
CALL view_roster {"team": "MIA"}
RESULT {"team": "MIA", "payroll": 189.17, "dead_money": 0.0, "roster_size": 14, "players": [{"id": "E3032977", "name": "Giannis Antetokounmpo", "pos": "F", "rating": 89, "career_rating": 87, "value": 89, "salary": 54.13, "years": 3, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4066261", "name": "Bam Adebayo", "pos": "C", "rating": 81, "career_rating": 78, "value": 81, "salary": 37.1, "years": 4, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E2595516", "name": "Norman Powell", "pos": "G", "rating": 77, "career_rating": 67, "value": 77, "salary": 20.48, "years": 1, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E3059319", "name": "Andrew Wiggins", "pos": "F", "rating": 73, "career_rating": 76, "value": 73, "salary": 28.22, "years": 2, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4278053", "name": "Davion Mitchell", "pos": "G", "rating": 71, "career_rating": 63, "value": 71, "salary": 11.6, "years": 2, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E3064482", "name": "Bobby Portis", "pos": "F", "rating": 69, "career_rating": 67, "value": 69, "salary": 13.58, "years": 3, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4601025", "name": "Pelle Larsson", "pos": "G", "rating": 69, "career_rating": 62, "value": 69, "salary": 1.96, "years": 2, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E3899664", "name": "Simone Fontecchio", "pos": "F", "rating": 58, "career_rating": 58, "value": 58, "salary": 8.31, "years": 1, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4997528", "name": "Nikola Jovic", "pos": "F", "rating": 57, "career_rating": 61, "value": 57, "salary": 4.45, "years": 5, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4066993", "name": "Dru Smith", "pos": "G", "rating": 56, "career_rating": 55, "value": 56, "salary": 2.38, "years": 3, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4431772", "name": "Myron Gardner", "pos": "F", "rating": 50, "career_rating": 50, "value": 50, "salary": 0.4, "years": 3, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4431786", "name": "Keshad Johnson", "pos": "F", "rating": 50, "career_rating": 50, "value": 50, "salary": 1.96, "years": 1, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4702784", "name": "J'Vonne Hadley", "pos": "F", "rating": 45, "career_rating": 45, "value": 45, "salary": 2.3, "years": 1, "guaranteed": true, "no_trad ...[357 more chars]
CALL search_players {"position": "C", "min_rating": 60, "max_salary": null, "team": null, "free_agents_only": true}
RESULT {"count": 1, "players": [{"id": "E4432827", "name": "Oscar Tshiebwe", "pos": "C", "rating": 62, "career_rating": 60, "value": 61, "asking": 2.3}]}
CALL sign_free_agent {"team": "MIA", "player_id": "E4432827", "salary": 2.3}
RESULT {"signed": true, "player": {"id": "E4432827", "name": "Oscar Tshiebwe", "pos": "C", "rating": 62, "career_rating": 60, "value": 61, "salary": 2.3, "years": 1, "guaranteed": true, "no_trade": false, "team": "MIA", "salary_source": "inferred:minimum"}, "team_payroll_after": 191.47}
CALL view_cap_sheet {"team": "MIA"}
RESULT {"team": "MIA", "payroll": 191.47, "dead_money": 0.0, "cap": 154.6, "tax_line": 187.9, "apron": 195.9, "cap_room": -36.87, "over_tax_by": 3.57, "room_under_apron": 4.43, "roster_size": 15, "roster_max": 15}
ASSISTANT: Signed Oscar Tshiebwe, a 62-rated center, for .3M. Miami Heat's cap position: payroll .47M, .43M under the apron (down from .73M). Roster now full at 15/15. Backup center acquired within apron constraints.

## Final reply to the general manager
Signed Oscar Tshiebwe, a 62-rated center, for .3M. Miami Heat's cap position: payroll .47M, .43M under the apron (down from .73M). Roster now full at 15/15. Backup center acquired within apron constraints.

## What changed in the league (before -> after)
{"MIA": {"payroll": [189.17, 191.47], "dead_money": [0.0, 0.0], "roster_size": [14, 15], "players_out": [], "players_in": ["E4432827"], "picks_out": [], "picks_in": []}}

Transactions: [{"type": "sign", "team": "MIA", "player": "E4432827", "salary": 2.3}]
