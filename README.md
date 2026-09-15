# NBA trade desk

An agentic evaluation sandbox. An LLM agent plays general manager over the real 2025-26 NBA:
it reads the rulebook, works the cap sheet, and trades, signs and waives with tools whose effects
are final. A rubric judge grades each trajectory on six dimensions, and the judge itself is
validated against human grades and against ground truth.

The point is not the basketball. It is a small, deterministic world with real stakes, real data
and checkable end states, so that questions about agent evaluation have answers: does the judge
agree with people, where does it fail, and does the agent act on what its tools return or on what
it remembers.

## Status

The league, rulebook, tools, eight tasks and the agent loop are built and tested. Three Claude
Code tiers have run every task; the trajectories are committed. The judge, the grading tool and
the human-validated agreement numbers are next.

| Ground truth passes, 8 tasks | Haiku 4.5 | Sonnet | Opus |
|---|---|---|---|
| First runs, eight tools | 5 | 8 | 8 |
| Second runs, ten tools, call limit enforced | 7 | 8 | 8 |

Passing ground truth is not the same as doing the job well. For the same forward, one tier sent
Chet Holmgren and a first-round pick and called it not overpaying; another negotiated the price
down to a second. That is what the judge is for. Details in [docs/results.md](docs/results.md).

## How it works

- **The league is real.** Rosters, contracts and cap lines from ESPN's public API, with one
  derived rating and every inference flagged. A synthetic league of invented players runs on the
  same engine as the tool-grounding baseline. [docs/league.md](docs/league.md)
- **Ten rules, eight tools, eight tasks.** The rulebook is the only authority; real NBA rules do
  not apply. Each task finds the real team whose books fit its scenario and has a checkable end
  state. Two tasks inject failures. [docs/tasks.md](docs/tasks.md)
- **Six grading dimensions.** Task success, tool-call correctness, unnecessary calls, irreversible
  moves without checking, recovery after failure, and tool grounding.
  [rubric/RUBRIC.md](rubric/RUBRIC.md)
- **Every number is reproducible.** Trajectories, the data snapshot and the rulebook hash are
  committed. [docs/running.md](docs/running.md)

## Quick start

```
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m trade_desk.run show under_tax_keep_starters
.venv/bin/python -m trade_desk.run run --model claude-opus-5 --tasks all --out runs/opus5
```

## Documents

| | |
|---|---|
| [docs/league.md](docs/league.md) | Where the data comes from, the rating formula, simplifications, coverage |
| [docs/tasks.md](docs/tasks.md) | Tools, tasks and their traps, the trajectory record |
| [docs/running.md](docs/running.md) | Setup, CLI, outside-agent sessions, repo layout |
| [docs/results.md](docs/results.md) | First runs, what they show, what is next |
| [rulebook/RULEBOOK.md](rulebook/RULEBOOK.md) | The rulebook the agent and the grader read |
| [rubric/RUBRIC.md](rubric/RUBRIC.md) | The grading rubric |
