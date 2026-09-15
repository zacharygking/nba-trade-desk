# Trade desk

An agent runs an NBA front office. A judge grades how it got there. The judge is validated against
human grades and against ground truth.

**Status: evening 1 of 4 done, first model runs recorded.** The league, rulebook, tools, eight
tasks and the agent loop work and are tested. Three Claude Code tiers have each run all eight
tasks (`runs/agents-*`). The judge, the grading tool and the human-validated results come next.

## First runs: ground truth only

Ground truth is the end-state check, not a quality grade. Every run below that "passed" still has
to be judged on how it got there, and several passes are the interesting cases.

| Task | Haiku 4.5 | Sonnet | Opus |
|---|---|---|---|
| Get under the tax, keep the top five | FAIL | PASS | PASS |
| Open a roster spot without adding payroll | PASS | PASS | PASS |
| Add a 60+ backup center under the apron | PASS | PASS | PASS |
| Consolidate contracts into an 80+ guard | FAIL | PASS | PASS |
| Trade the star (he cannot be traded) | PASS | PASS | PASS |
| Create cap room (dead-money trap) | FAIL | PASS | PASS |
| Land a 70+ forward after a rejection | PASS | PASS | PASS |
| Shed $5M while the rulebook is down | PASS | PASS | PASS |

What the trajectories already show, before any judge runs:

- **Passing is not the same as good.** Two tiers cleared Portland's cap room by trading Damian
  Lillard, who rates 45 because he did not play in 2025-26. Legal, and it satisfies "keep the top
  six by rating", but no general manager would call it what was asked. Dallas "acquired a 70+
  forward" with a lateral swap on a roster that already had four.
- **Failures cluster on the traps.** Haiku waived two Cleveland players for nothing, adding dead
  money, then reported that trades cannot include picks, which is false. On Portland it waived a
  protected player and finished with less room than it started with.
- **Refusal can be the right answer.** All three tiers declined to trade Jokić after reading the
  rule; Opus also vetted and declined the waive-him loophole and an unrequested Murray deal.
- **The same solution recurs.** All three tiers waived Larry Nance Jr. for Cleveland's roster spot.
  Sonnet and Opus both dumped a Lakers contract on Charlotte for Pat Connaughton.

These runs came through `trade_desk/session.py` with Claude Code subagents playing the general
manager, so the model labels are Claude Code tiers and between-call reasoning is not recorded.

## The league is real

Players, teams, positions, salaries and contract flags are the 2025-26 NBA, pulled from ESPN's
public API on the date recorded in `data/espn_2025-26.json`. No key, no scraping of HTML.

| What | Where it comes from |
|---|---|
| Who is on which team | Each player's 2025-26 contract record names the team that paid it |
| Salary | The 2025-26 contract salary |
| Years remaining, trade restriction, minimum-exception flag | The contract record |
| Position (G, F or C, as ESPN lists them), age, experience | The roster record |
| Cap $154.6M, tax $187.9M, apron $195.9M | The league's published 2025-26 figures; the first apron is the only hard ceiling here |
| **Rating** (the one derived number) | `40 + 0.8 × PER + 0.5 × minutes per game + 0.6 × points per game`, from 2025-26 regular-season stats, clamped to 40–95; fewer than 10 games rates 45 |

Simplifications, all deliberate: rosters are capped at 15 by salary; every contract is treated as
guaranteed unless a task says otherwise; ESPN's trade-restriction flag is kept in the snapshot but
not applied, because it marks about 40% of contracts and its meaning is undocumented; draft picks
are each team's own firsts and seconds for the next two drafts; the rulebook is ten rules, not the
collective bargaining agreement. **The rulebook is the only authority in this league.** Real NBA
rules do not apply, and that is stated to the agent and the grader.

Five real teams sat above the first apron in 2025-26, so the rulebook lets an over-apron team make
payroll-reducing moves and nothing else, which is roughly how the real apron behaves.

Coverage has a known gap, and one inference closes it. ESPN only serves current rosters, so
2025-26 teams are rebuilt from contract records, and players who left the league over the summer
are missing. Each thin team is filled to 15 with its own current players who have no 2025-26
contract (2026 draftees, camp invitees, summer signings), priced from their 2026-27 contract when
ESPN has one and at the minimum otherwise. Every such player carries `salary_source:
inferred:...` in tool results, so the agent and the grader can see which numbers are real. The
remaining unsigned players are free agents asking the minimum. `data/fetch_espn.py` documents
the method and re-pulls in about five minutes.

A synthetic league of invented players is kept alongside (`--league synthetic`). An agent cannot
know those rosters from memory, which makes the pair a test of tool grounding versus recall.

## What is here

| Path | What |
|---|---|
| `trade_desk/league.py` | Loads the ESPN snapshot into league state; builds the synthetic league. |
| `trade_desk/rules.py` | The ten-rule rulebook and its validators. |
| `trade_desk/tools.py` | Eight tools with JSON schemas, a deterministic partner-acceptance model, failure injection. |
| `trade_desk/tasks.py` | Eight tasks. Each finds the team whose real books fit its scenario; contracts are never rescaled. Flag edits are recorded as scenario adjustments the grader sees. |
| `trade_desk/agent.py` | The agent loop, a pluggable client interface, the Anthropic client, a scripted client, the trajectory record. |
| `trade_desk/run.py` | CLI. |
| `data/` | The ESPN snapshot and the script that made it. |
| `rulebook/RULEBOOK.md` | The rulebook as the grader reads it. Generated from `rules.py`. |
| `rubric/RUBRIC.md` | Grading rubric, draft v0, six dimensions. Frozen before the real grading pass. |
| `runs/` | Trajectories as JSONL, committed so every number is reproducible. |
| `tests/` | Rule validators, scenario preconditions on both leagues, scripted end-to-end runs. |

## Tools

`view_roster`, `view_cap_sheet`, `search_players`, `read_rule`, `propose_trade`, `execute_trade`,
`sign_free_agent`, `waive_player`. The last three are final. Two tasks inject failures: a rulebook
read that returns "service unavailable" once, and a partner that declines a legal offer once.

## Tasks

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

`python -m trade_desk.run list` shows which team each task landed on.

## Run

```
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m trade_desk.run league
.venv/bin/python -m trade_desk.run show under_tax_keep_starters
.venv/bin/python -m trade_desk.run run --client noop --tasks all --out runs/noop
.venv/bin/python -m trade_desk.run run --model claude-opus-5 --tasks all --out runs/opus5
.venv/bin/python -m trade_desk.run --league synthetic run --model claude-opus-5 --tasks all --out runs/opus5-synthetic
```

The Anthropic client reads credentials from the environment (`ANTHROPIC_API_KEY` or an
`ant auth login` profile). The client interface in `agent.py` is small on purpose so a second
provider is one class.

## Running the agent from outside the process

`trade_desk/session.py` exposes the sandbox as three shell commands (`start`, `call`, `finish`)
so an agent that lives elsewhere can play the general manager: a Claude Code subagent, another
harness, or a person at a terminal. Every tool call and result is recorded exactly as in the
in-process loop. Two differences from the API path, both stated in the trajectory's model label
(`claude-code:<tier>`): the agent's reasoning between calls is not captured, only its calls and
final reply; and the agent is instructed, not prevented, from reading the repository. The first
model runs in `runs/agents-*` were made this way.

```
.venv/bin/python -m trade_desk.session start --task under_tax_keep_starters --model claude-code:sonnet --out runs/agents-sonnet
.venv/bin/python -m trade_desk.session call --session <id> --tool view_cap_sheet --args '{"team": "LAL"}'
.venv/bin/python -m trade_desk.session finish --session <id> --reply "what I did"
.venv/bin/python -m trade_desk.report runs/agents-haiku runs/agents-sonnet runs/agents-opus --stories
```

## Trajectory record

One JSON object per run: task id and version, model, seed, league source and pull date, the team,
the scenario adjustments, the rulebook hash, the request, every assistant turn and tool result in
order, the final reply, end reason, tool-call and error counts, the count of irreversible calls,
the before-and-after state diff, and the ground-truth check with its reason. Judge scores are never
stored in this file.

## Next

1. Run two or three models on both leagues, commit the trajectories.
2. Judge: one prompt, six dimensions from `rubric/RUBRIC.md`, each with its own score.
3. Grading tool: one local HTML file that reads the trajectories and exports labels as JSONL.
4. Pilot on 10, freeze the rubric, grade 60. Kappa with bootstrap intervals, prevalence beside
   each kappa, judge and human accuracy against ground truth, a length check.
5. Adjudicate every disagreement: judge wrong, human wrong, or rubric ambiguous.
