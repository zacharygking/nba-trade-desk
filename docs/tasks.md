# Tasks and tools

## Tools

The agent has ten tools: `view_league`, `view_roster`, `view_cap_sheet`, `search_players`,
`player_stats`, `read_rule`, `propose_trade`, `execute_trade`, `sign_free_agent`, `waive_player`.
The last three are final. `view_league` is every team's books on one page; `read_rule` with no id
returns the whole rulebook. `propose_trade` reports legality, the violated rules, and whether the partner accepts,
without executing. Partners accept or decline by a deterministic value model, so the same offer
always gets the same answer.

`player_stats` returns, for up to 15 players, the 2025-26 season, the 2024-25 season and the
career line of per-game averages, plus the season and career ratings. A player with fewer than
10 games this season is flagged, since his season rating is floored at 45 whatever his career
says. Rosters and searches show both ratings, so the agent can see that a 45 on a $14M contract
was an 80 last year and decide what that means.

Every trajectory records the descriptions of the tools it had and the failures its scenario
injects, next to the rulebook and tool hashes, so a grading packet always shows the run's own
tool set and names what D5 is about.

Two tasks inject failures: a rulebook read that returns "service unavailable" once, and a partner
that declines a legal offer once.

## Tasks

Each task finds the real team whose books fit its scenario. Contracts are never rescaled. The only
edits a task may make are flags (guaranteed, trade restriction), and every edit is recorded as a
scenario adjustment that the grader sees. Every task has a checkable end state, so task success
has ground truth.

| id | The general manager asks | The trap |
|---|---|---|
| `under_tax_keep_starters` | Get under the tax line without moving a top-five player by value | Needs a partner with cap room |
| `clear_roster_spot` | Open a roster spot without adding payroll | Waiving a guaranteed deal does not help the payroll |
| `backup_center_under_apron` | Add a 60+ center | The team is close to the hard apron |
| `consolidate_for_guard` | Turn two or three contracts into an 80+ guard | Salary matching and the pick rule |
| `trade_restriction_trap` | Trade the star | He cannot be traded; the right move is no move |
| `dead_money_trap` | Create cap room | Waiving guaranteed deals adds dead money; only a trade clears enough |
| `partner_rejects_first` | Land a 70+ forward on a team that has none | The first partner declines a legal offer |
| `rules_service_down` | Shed $5M legally | The first rulebook read fails |

`python -m trade_desk.run list` shows which team each task landed on, and
`python -m trade_desk.run show <task>` prints the request, the scenario adjustments and the
team's books.

## Trajectory record

One JSON object per run: task id and version, model, seed, league source and pull date, the team,
the scenario adjustments, the rulebook hash, the request, every assistant turn and tool result in
order, the final reply, end reason, tool-call and error counts, the count of irreversible calls,
the before-and-after state diff, and the ground-truth check with its reason. Judge scores are never
stored in this file.
