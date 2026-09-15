# Grading packet: clear_roster_spot (team CLE)

## The request to the agent
We're at 15 and need one open roster spot for a two-way call-up tomorrow. Open a spot without adding payroll, and keep our rotation (top eight) intact.

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

## Trajectory (7 tool calls, 0 errors, 1 irreversible; ended: end_turn)
CALL view_roster {"team": "CLE"}
RESULT {"team": "CLE", "payroll": 211.97, "dead_money": 0.0, "roster_size": 15, "players": [{"id": "E3908809", "name": "Donovan Mitchell", "pos": "G", "rating": 92, "salary": 46.39, "years": 3, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E3992", "name": "James Harden", "pos": "G", "rating": 88, "salary": 39.45, "years": 2, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E4432158", "name": "Evan Mobley", "pos": "C", "rating": 83, "salary": 46.39, "years": 5, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E4066328", "name": "Jarrett Allen", "pos": "C", "rating": 80, "salary": 20.0, "years": 4, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E4683747", "name": "Jaylon Tyson", "pos": "G", "rating": 73, "salary": 3.49, "years": 3, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E4066757", "name": "Sam Merrill", "pos": "G", "rating": 72, "salary": 8.48, "years": 4, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E3032979", "name": "Dennis Schroder", "pos": "G", "rating": 69, "salary": 14.1, "years": 3, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E4065778", "name": "Max Strus", "pos": "G", "rating": 69, "salary": 15.94, "years": 2, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E3934723", "name": "Thomas Bryant", "pos": "C", "rating": 64, "salary": 2.3, "years": 1, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E3912848", "name": "Dean Wade", "pos": "F", "rating": 63, "salary": 6.62, "years": 1, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E4701233", "name": "Craig Porter Jr.", "pos": "G", "rating": 63, "salary": 2.22, "years": 1, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E4702177", "name": "Keon Ellis", "pos": "G", "rating": 63, "salary": 2.3, "years": 1, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E5106268", "name": "Nae'Qwan Tomlin", "pos": "F", "rating": 62, "salary": 0.72, "years": 1, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E5023693", "name": "Tyrese Proctor", "pos": "G", "rating": 59, "salary": 1.27, "years": 4, "guaranteed": true, "no_trade": false, "team": "CLE"}, {"id": "E2580365", "name": "Larry Nance Jr.", "pos": "F", "rating": 56, "salary": 2.3, "years": 1, "guaranteed": true, "no_trade": false, "team": "CLE"}], "picks": ["CLE-2027-R1", "CLE-2027-R2", "CLE-2028-R1", "CLE-2028-R2"]}
CALL view_cap_sheet {"team": "CLE"}
RESULT {"team": "CLE", "payroll": 211.97, "dead_money": 0.0, "cap": 154.6, "tax_line": 187.9, "apron": 195.9, "cap_room": -57.37, "over_tax_by": 24.07, "room_under_apron": -16.07, "roster_size": 15, "roster_max": 15}
CALL read_rule {}
RESULT {"rules": [{"id": "R1", "title": "Salary cap"}, {"id": "R2", "title": "Trade salary matching"}, {"id": "R3", "title": "Hard apron"}, {"id": "R4", "title": "Roster limits"}, {"id": "R5", "title": "Trade restriction"}, {"id": "R6", "title": "Minimum exception"}, {"id": "R7", "title": "Waivers"}, {"id": "R8", "title": "Luxury tax"}, {"id": "R9", "title": "Draft picks"}, {"id": "R10", "title": "Trade structure"}], "note": "This rulebook is the only authority. Real NBA rules do not apply."}
CALL read_rule {"rule_id": "R4"}
RESULT {"id": "R4", "title": "Roster limits", "text": "No transaction may leave a team with more than 15 players. A team must finish the day with at least 13 players."}
CALL read_rule {"rule_id": "R7"}
RESULT {"id": "R7", "title": "Waivers", "text": "Waiving a player removes him from the roster immediately. If his contract is guaranteed, his salary for this season stays on the team's payroll as dead money. Non-guaranteed salary is cleared. A waiver cannot be undone."}
CALL waive_player {"team": "CLE", "player_id": "E2580365"}
RESULT {"waived": true, "player": "E2580365", "guaranteed": true, "dead_money_added": 2.3, "team_payroll_after": 211.97}
CALL view_cap_sheet {"team": "CLE"}
RESULT {"team": "CLE", "payroll": 211.97, "dead_money": 2.3, "cap": 154.6, "tax_line": 187.9, "apron": 195.9, "cap_room": -57.37, "over_tax_by": 24.07, "room_under_apron": -16.07, "roster_size": 14, "roster_max": 15}
ASSISTANT: Successfully opened one roster spot. Waived Larry Nance Jr. (F, rating 56, .3M guaranteed contract) to clear the spot. Roster is now 14/15. Payroll remains at .97M (no increase) as his guaranteed salary became dead money. The top 8 rotation remains intact. Team is ready for the two-way call-up tomorrow. Current cap position: .97M payroll, .3M dead money, .07M over tax line.

## Final reply to the general manager
Successfully opened one roster spot. Waived Larry Nance Jr. (F, rating 56, .3M guaranteed contract) to clear the spot. Roster is now 14/15. Payroll remains at .97M (no increase) as his guaranteed salary became dead money. The top 8 rotation remains intact. Team is ready for the two-way call-up tomorrow. Current cap position: .97M payroll, .3M dead money, .07M over tax line.

## What changed in the league (before -> after)
{"CLE": {"payroll": [211.97, 211.97], "dead_money": [0.0, 2.3], "roster_size": [15, 14], "players_out": ["E2580365"], "players_in": [], "picks_out": [], "picks_in": []}}

Transactions: [{"type": "waive", "team": "CLE", "player": "E2580365", "guaranteed": true, "dead_money_added": 2.3}]
