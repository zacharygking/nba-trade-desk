# Running it

## Setup

```
uv venv --python 3.12 .venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

## Look around

```
.venv/bin/python -m trade_desk.run league                        # payroll table for every team
.venv/bin/python -m trade_desk.run list                          # tasks and the team each landed on
.venv/bin/python -m trade_desk.run show under_tax_keep_starters  # one scenario in full
.venv/bin/python -m trade_desk.run rulebook                      # the rulebook the agent reads
```

## Run an agent in-process

```
.venv/bin/python -m trade_desk.run run --client noop --tasks all --out runs/noop
.venv/bin/python -m trade_desk.run run --model claude-opus-5 --tasks all --out runs/opus5
.venv/bin/python -m trade_desk.run --league synthetic run --model claude-opus-5 --tasks all --out runs/opus5-synthetic
```

The `noop` client reads a roster and stops; it checks the wiring without an API. The Anthropic
client reads credentials from the environment (`ANTHROPIC_API_KEY` or an `ant auth login`
profile). The client interface in `trade_desk/agent.py` is small on purpose so a second provider
is one class.

## Run an agent from outside the process

`trade_desk/session.py` exposes the sandbox as three shell commands so an agent that lives
elsewhere can play the general manager: a Claude Code subagent, another harness, or a person at a
terminal. Every tool call and result is recorded exactly as in the in-process loop.

```
.venv/bin/python -m trade_desk.session start --task under_tax_keep_starters --model claude-code:sonnet --out runs/agents-sonnet
.venv/bin/python -m trade_desk.session call --session <id> --tool view_cap_sheet --args '{"team": "LAL"}'
.venv/bin/python -m trade_desk.session finish --session <id> --reply "what I did"
```

Two differences from the API path, both stated in the trajectory's model label
(`claude-code:<tier>`): the agent's reasoning between calls is not captured, only its calls and
final reply; and the agent is instructed, not prevented, from reading the repository.

## Compare runs

```
.venv/bin/python -m trade_desk.report runs/agents-haiku runs/agents-sonnet runs/agents-opus --stories
```

One table per model, then a by-task grid. `--stories` spells out each run's transactions.

## Layout

| Path | What |
|---|---|
| `trade_desk/league.py` | Loads the ESPN snapshot into league state; builds the synthetic league. |
| `trade_desk/rules.py` | The ten-rule rulebook and its validators. |
| `trade_desk/tools.py` | Eight tools with JSON schemas, the partner-acceptance model, failure injection. |
| `trade_desk/tasks.py` | Eight tasks with scenario selection and end-state checks. |
| `trade_desk/agent.py` | The agent loop, the client interface, the Anthropic and scripted clients, the trajectory record. |
| `trade_desk/session.py` | Shell-driven sessions for outside agents. |
| `trade_desk/report.py` | Results tables. |
| `trade_desk/run.py` | CLI. |
| `data/` | The ESPN snapshot and the script that made it. |
| `rulebook/RULEBOOK.md` | The rulebook as the grader reads it. Generated from `rules.py`. |
| `rubric/RUBRIC.md` | Grading rubric, six dimensions. |
| `runs/` | Trajectories as JSONL, committed so every number is reproducible. |
| `tests/` | Rule validators, scenario preconditions on both leagues, scripted end-to-end runs. |
