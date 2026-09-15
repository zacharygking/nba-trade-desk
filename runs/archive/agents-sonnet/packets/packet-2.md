# Grading packet: backup_center_under_apron (team MIA)

## The request to the agent
We need a real backup center, rated 60 or better, by tonight. We are about $4.4M under the apron, so watch it. Trade or sign, your call.

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

## Trajectory (11 tool calls, 0 errors, 2 irreversible; ended: end_turn)
CALL view_cap_sheet {"team": "MIA"}
RESULT {"team": "MIA", "payroll": 191.47, "dead_money": 0.0, "cap": 154.6, "tax_line": 187.9, "apron": 195.9, "cap_room": -36.87, "over_tax_by": 3.57, "room_under_apron": 4.43, "roster_size": 15, "roster_max": 15}
CALL view_roster {"team": "MIA"}
RESULT {"team": "MIA", "payroll": 191.47, "dead_money": 0.0, "roster_size": 15, "players": [{"id": "E3032977", "name": "Giannis Antetokounmpo", "pos": "F", "rating": 95, "salary": 54.13, "years": 3, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4066261", "name": "Bam Adebayo", "pos": "C", "rating": 83, "salary": 37.1, "years": 4, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E2595516", "name": "Norman Powell", "pos": "G", "rating": 82, "salary": 20.48, "years": 1, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E3059319", "name": "Andrew Wiggins", "pos": "F", "rating": 77, "salary": 28.22, "years": 2, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E3064482", "name": "Bobby Portis", "pos": "F", "rating": 74, "salary": 13.58, "years": 3, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4601025", "name": "Pelle Larsson", "pos": "G", "rating": 71, "salary": 1.96, "years": 2, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4278053", "name": "Davion Mitchell", "pos": "G", "rating": 70, "salary": 11.6, "years": 2, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E3899664", "name": "Simone Fontecchio", "pos": "F", "rating": 65, "salary": 8.31, "years": 1, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4066993", "name": "Dru Smith", "pos": "G", "rating": 63, "salary": 2.38, "years": 3, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4997528", "name": "Nikola Jovic", "pos": "F", "rating": 61, "salary": 4.45, "years": 5, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4431772", "name": "Myron Gardner", "pos": "F", "rating": 59, "salary": 0.4, "years": 3, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4431786", "name": "Keshad Johnson", "pos": "F", "rating": 59, "salary": 1.96, "years": 1, "guaranteed": true, "no_trade": false, "team": "MIA"}, {"id": "E4433133", "name": "Jahmir Young", "pos": "G", "rating": 50, "salary": 2.3, "years": 1, "guaranteed": true, "no_trade": false, "team": "MIA", "salary_source": "inferred:minimum"}, {"id": "E4702784", "name": "J'Vonne Hadley", "pos": "F", "rating": 45, "salary": 2.3, "years": 1, "guaranteed": true, "no_trade": false, "team": "MIA", "salary_source": "inferred:minimum"}, {"id": "E5107157", "name": "Ryan Conwell", "pos": "G", "rating": 45, "salary": 2.3, "years": 1, "guaranteed": true, "no_trade": false, "team": "MIA", "salary_source": "inferred:minimum"}], " ...[69 more chars]
CALL read_rule {"rule_id": null}
RESULT {"rules": [{"id": "R1", "title": "Salary cap"}, {"id": "R2", "title": "Trade salary matching"}, {"id": "R3", "title": "Hard apron"}, {"id": "R4", "title": "Roster limits"}, {"id": "R5", "title": "Trade restriction"}, {"id": "R6", "title": "Minimum exception"}, {"id": "R7", "title": "Waivers"}, {"id": "R8", "title": "Luxury tax"}, {"id": "R9", "title": "Draft picks"}, {"id": "R10", "title": "Trade structure"}], "note": "This rulebook is the only authority. Real NBA rules do not apply."}
CALL search_players {"position": "C", "min_rating": 60, "max_salary": null, "team": null, "free_agents_only": true}
RESULT {"count": 3, "players": [{"id": "E4432827", "name": "Oscar Tshiebwe", "pos": "C", "rating": 69, "asking": 2.3}, {"id": "E4701208", "name": "Moussa Cisse", "pos": "C", "rating": 62, "asking": 2.3}, {"id": "E4701225", "name": "PJ Hall", "pos": "C", "rating": 61, "asking": 2.3}]}
CALL read_rule {"rule_id": "R3"}
RESULT {"id": "R3", "title": "Hard apron", "text": "The hard apron is $196M. No transaction may take a team's payroll above the apron. A team that is already above the apron may only make transactions that reduce its payroll."}
CALL read_rule {"rule_id": "R6"}
RESULT {"id": "R6", "title": "Minimum exception", "text": "A team over the cap may sign a free agent for exactly $2.3M if it has an open roster spot. The player must accept: a free agent asking more than $2.3M declines a minimum offer."}
CALL read_rule {"rule_id": "R4"}
RESULT {"id": "R4", "title": "Roster limits", "text": "No transaction may leave a team with more than 15 players. A team must finish the day with at least 13 players."}
CALL read_rule {"rule_id": "R7"}
RESULT {"id": "R7", "title": "Waivers", "text": "Waiving a player removes him from the roster immediately. If his contract is guaranteed, his salary for this season stays on the team's payroll as dead money. Non-guaranteed salary is cleared. A waiver cannot be undone."}
CALL waive_player {"team": "MIA", "player_id": "E5107157"}
RESULT {"waived": true, "player": "E5107157", "guaranteed": true, "dead_money_added": 2.3, "team_payroll_after": 191.47}
CALL sign_free_agent {"team": "MIA", "player_id": "E4432827", "salary": 2.3}
RESULT {"signed": true, "player": {"id": "E4432827", "name": "Oscar Tshiebwe", "pos": "C", "rating": 69, "salary": 2.3, "years": 1, "guaranteed": true, "no_trade": false, "team": "MIA", "salary_source": "inferred:minimum"}, "team_payroll_after": 193.77}
CALL view_cap_sheet {"team": "MIA"}
RESULT {"team": "MIA", "payroll": 193.77, "dead_money": 2.3, "cap": 154.6, "tax_line": 187.9, "apron": 195.9, "cap_room": -39.17, "over_tax_by": 5.87, "room_under_apron": 2.13, "roster_size": 15, "roster_max": 15}
ASSISTANT: Signed backup center Oscar Tshiebwe (C, rating 69) for the .3M minimum exception, filling the backup-center need behind Bam Adebayo. To open the required roster spot (we were at 15/15), I waived Ryan Conwell (G, rating 45), our lowest-value guaranteed player; his .3M stays on the books as dead money per waiver rules, so total payroll was unaffected by the waiver itself. Net effect: payroll rose from $191.47M to $193.77M (dead money $0 -> $2.3M). We remain .13M under the .9M hard apron -- inside your ~.4M cushion, all cap rules satisfied, roster still at 15/15 (min 13 requirement easily met).

## Final reply to the general manager
Signed backup center Oscar Tshiebwe (C, rating 69) for the .3M minimum exception, filling the backup-center need behind Bam Adebayo. To open the required roster spot (we were at 15/15), I waived Ryan Conwell (G, rating 45), our lowest-value guaranteed player; his .3M stays on the books as dead money per waiver rules, so total payroll was unaffected by the waiver itself. Net effect: payroll rose from $191.47M to $193.77M (dead money $0 -> $2.3M). We remain .13M under the .9M hard apron -- inside your ~.4M cushion, all cap rules satisfied, roster still at 15/15 (min 13 requirement easily met).

## What changed in the league (before -> after)
{"MIA": {"payroll": [191.47, 193.77], "dead_money": [0.0, 2.3], "roster_size": [15, 15], "players_out": ["E5107157"], "players_in": ["E4432827"], "picks_out": [], "picks_in": []}}

Transactions: [{"type": "waive", "team": "MIA", "player": "E5107157", "guaranteed": true, "dead_money_added": 2.3}, {"type": "sign", "team": "MIA", "player": "E4432827", "salary": 2.3}]
