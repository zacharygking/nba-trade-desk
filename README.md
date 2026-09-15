# NBA trade desk

[![tests](https://github.com/zacharygking/nba-trade-desk/actions/workflows/tests.yml/badge.svg)](https://github.com/zacharygking/nba-trade-desk/actions/workflows/tests.yml)

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
Code tiers have run every task twice. The current set is published as a dataset, a blind judge
has graded it on six dimensions through motherlode's gate, and the graded dataset is committed
beside it. The judge agrees with ground truth on task success in 23 of 24 current trajectories;
the one disagreement has a proposed adjudication. The blind hand-grading tool is built. Next is
the human pass: a ten-item pilot to freeze the rubric, then a stratified set of about sixty
trajectories graded by a person and by a judge from a different model family, and the
chance-corrected agreement between them. The plan for that set is in
[docs/results.md](docs/results.md#next).

| Ground truth passes, 8 tasks | Haiku 4.5 | Sonnet | Opus |
|---|---|---|---|
| First runs, eight tools (archived, not replayable) | 5 | 8 | 8 |
| Second runs, ten tools, call limit enforced | 7 | 8 | 8 |

Passing ground truth is not the same as doing the job well. For the same forward, one tier sent
Chet Holmgren and a first-round pick and called it not overpaying; another negotiated the price
down to a second. That is what the judge is for. Details in [docs/results.md](docs/results.md).

## How it works

- **The league is real.** Rosters, contracts and cap lines from ESPN's public API, with one
  derived rating and every inference flagged. A synthetic league of invented players runs on the
  same engine as the tool-grounding baseline. [docs/league.md](docs/league.md)
- **Ten rules, ten tools, eight tasks.** The rulebook is the only authority; real NBA rules do
  not apply. Each task finds the real team whose books fit its scenario and has a checkable end
  state. Two tasks inject failures. [docs/tasks.md](docs/tasks.md)
- **Six grading dimensions.** Task success, tool-call correctness, unnecessary calls, irreversible
  moves without checking, recovery after failure, and tool grounding.
  [rubric/RUBRIC.md](rubric/RUBRIC.md)
- **Every number is reproducible.** Trajectories, the data snapshot and the rulebook hash are
  committed. Judging, hand grading and validation happen in
  [motherlode](https://github.com/zacharygking/motherlode), which the trade desk talks to only
  through datasets: it publishes one, motherlode grades it, it reads the graded one back.
  [docs/datasets.md](docs/datasets.md)

## Quick start

```
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/nba-trade-desk run show under_tax_keep_starters
.venv/bin/nba-trade-desk run run --model claude-opus-5 --tasks all --out runs/opus5
```

## Documents

| | |
|---|---|
| [docs/league.md](docs/league.md) | Where the data comes from, the rating formula, simplifications, coverage |
| [docs/tasks.md](docs/tasks.md) | Tools, tasks and their traps, the trajectory record |
| [docs/running.md](docs/running.md) | Setup, CLI, outside-agent sessions, repo layout |
| [docs/datasets.md](docs/datasets.md) | The datasets the trade desk publishes and reads back, and the gate that runs between them |
| [docs/results.md](docs/results.md) | Both run sets, the judge passes, what is next |
| [rulebook/RULEBOOK.md](rulebook/RULEBOOK.md) | The rulebook the agent and the grader read |
| [rubric/RUBRIC.md](rubric/RUBRIC.md) | The grading rubric |
