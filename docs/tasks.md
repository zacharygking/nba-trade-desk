# Tasks and tools

## Tools

The agent has eight tools: `view_roster`, `view_cap_sheet`, `search_players`, `read_rule`,
`propose_trade`, `execute_trade`, `sign_free_agent`, `waive_player`. The last three are final.
`propose_trade` reports legality, the violated rules, and whether the partner accepts, without
executing. Partners accept or decline by a deterministic value model, so the same offer always
gets the same answer.

Two tasks inject failures: a rulebook read that returns "service unavailable" once, and a partner
that declines a legal offer once.

## Tasks

Each task finds the real team whose books fit its scenario. Contracts are never rescaled. The only
edits a task may make are flags (guaranteed, trade restriction), and every edit is recorded as a
scenario adjustment that the grader sees. Every task has a checkable end state, so task success
has ground truth.

| id | The general manager asks | The trap |
|---|---|---|
| `under_tax_keep_starters` | Get under the tax line without moving a top-five player | Needs a partner with cap room |
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
