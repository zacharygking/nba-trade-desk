# Tasks and tools

## Tools

The agent has ten tools: `view_league`, `view_roster`, `view_cap_sheet`, `search_players`,
`player_stats`, `read_rule`, `propose_trade`, `execute_trade`, `sign_free_agent`, `waive_player`.
The last three are final. `view_league` is every team's books on one page; `read_rule` with no id
returns the whole rulebook. `propose_trade` reports legality, the violated rules, and whether the partner accepts,
without executing. Partners accept or decline by a deterministic value model, so the same offer
always gets the same answer.

### The partner is a formula, not a negotiator

There is no second agent on the other side of a trade. `partner_accepts` in `trade_desk/tools.py`
prices every asset and accepts when what the partner receives is worth at least 85% of what it
gives up:

| Asset | Value |
|---|---|
| Player | `max(0, value − 55) ^ 1.6 × (1 + 0.15 × (years − 1))`, where `value` is the games-weighted rating |
| First-round pick | 120 |
| Second-round pick | 25 |

A 60-rated player on a one-year deal is worth about 13, a 75 about 120 (one first), a 90 about
300. The partner has no roster needs, no cap position of its own to protect beyond the rules
the engine enforces on both sides, and no memory of earlier offers. It does not prefer picks to
players or the reverse.

What this means for reading the results:

- **"Don't overpay" has a computable answer.** The cheapest package the partner accepts is a
  threshold, and an agent that negotiates down is searching for it. When one tier sends a star
  and a first for a forward and another sends a second, the gap is real and the judge can see
  it, but it is a gap against a price list, not against a counterparty who might have taken less.
- **Ground truth ignores price.** The end-state checks ask whether the request was met legally,
  never whether the agent paid a fair price. Overpayment shows up only in the judge's dimensions
  and the write-up's stories, not in the pass table.
- **The formula is not exposed to the agent.** The tool says "accepts" or "declines: the return
  is too light", nothing more. An agent that reads the repository could recover it; session-mode
  agents are instructed not to, and the API path cannot. See [running.md](running.md).
- **Value is the same number the requests protect.** "Top five by value" and the partner's price
  list use the same games-weighted rating, so an agent that reads its own roster has everything
  it needs to estimate what a partner will accept.

The model is deliberately simple so that a trajectory is reproducible and a disagreement between
judge and human is never about what the partner would have done. A negotiation model would be a
second agent to evaluate.

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
