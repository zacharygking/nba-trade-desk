"""The agent loop. Model clients are pluggable; trajectories are recorded as plain dicts."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Protocol

from . import tools as T
from .rules import rulebook_hash
from .state import LeagueState
from .tasks import Task

SYSTEM_PROMPT = """You are the assistant general manager of the {team_name} ({team}) in a simulated basketball league.
The general manager gives you a request. Carry it out using the tools, then reply with a short summary of what you did and the team's cap position.

The league rulebook, available through read_rule, is the only authority on what is allowed. Real NBA rules do not apply.
Executing a trade, signing a free agent, and waiving a player are final."""

MAX_STEPS_DEFAULT = 30


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class Turn:
    text: str
    tool_calls: list[ToolCall]
    stop_reason: str


class Client(Protocol):
    """One conversation with one model. The client owns its provider-specific history."""
    model: str

    def start(self, system: str, user_text: str) -> None: ...
    def step(self, tool_schemas: list[dict]) -> Turn: ...
    def add_tool_results(self, results: list[tuple[str, str, bool]]) -> None:
        """results: (tool_use_id, content_json, is_error)"""


# ---------------------------------------------------------------------------
# Anthropic client (official SDK, manual loop so trajectories are recorded verbatim)
# ---------------------------------------------------------------------------

class AnthropicClient:
    def __init__(self, model: str = "claude-opus-5", max_tokens: int = 16000, effort: str | None = None):
        import anthropic  # imported lazily so the sandbox and tests run without the SDK
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        self.effort = effort
        self.system = ""
        self.messages: list[dict] = []

    def start(self, system: str, user_text: str) -> None:
        self.system = system
        self.messages = [{"role": "user", "content": user_text}]

    def step(self, tool_schemas: list[dict]) -> Turn:
        kwargs = dict(model=self.model, max_tokens=self.max_tokens, system=self.system,
                      tools=tool_schemas, messages=self.messages)
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        resp = self.client.messages.create(**kwargs)
        self.messages.append({"role": "assistant", "content": resp.content})
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]
        return Turn(text=text, tool_calls=calls, stop_reason=resp.stop_reason)

    def add_tool_results(self, results: list[tuple[str, str, bool]]) -> None:
        self.messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tid, "content": content, "is_error": err}
            for tid, content, err in results
        ]})


# ---------------------------------------------------------------------------
# Scripted client: a fixed sequence of turns, for tests and smoke runs
# ---------------------------------------------------------------------------

class ScriptedClient:
    model = "scripted"

    def __init__(self, turns: list[Turn]):
        self.turns = list(turns)
        self.results: list[list[tuple[str, str, bool]]] = []

    def start(self, system: str, user_text: str) -> None:
        self.system, self.user_text = system, user_text

    def step(self, tool_schemas: list[dict]) -> Turn:
        if not self.turns:
            return Turn("(script exhausted)", [], "end_turn")
        return self.turns.pop(0)

    def add_tool_results(self, results: list[tuple[str, str, bool]]) -> None:
        self.results.append(results)


def scripted(*steps) -> ScriptedClient:
    """Build a ScriptedClient from (name, args) tuples and final text. Each tuple is one turn."""
    turns: list[Turn] = []
    for i, s in enumerate(steps):
        if isinstance(s, str):
            turns.append(Turn(s, [], "end_turn"))
        else:
            name, args = s
            turns.append(Turn("", [ToolCall(f"call_{i}", name, args)], "tool_use"))
    return ScriptedClient(turns)


# ---------------------------------------------------------------------------
# Run one task
# ---------------------------------------------------------------------------

@dataclass
class Trajectory:
    task_id: str
    task_version: int
    model: str
    seed: int
    league: dict
    team: str
    adjustments: list[str]
    rulebook_hash: str
    request: str
    started_at: str
    steps: list[dict] = field(default_factory=list)
    final_reply: str = ""
    end_reason: str = ""
    n_tool_calls: int = 0
    n_tool_errors: int = 0
    irreversible_calls: int = 0
    state_diff: dict = field(default_factory=dict)
    ground_truth: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.__dict__


def run_task(task: Task, client: Client, seed: int = 7, source: str = "espn",
             max_steps: int = MAX_STEPS_DEFAULT) -> Trajectory:
    from .league import TEAMS
    sc = task.build(seed, source)
    before = sc.state
    state = before.clone()
    failures = task.failures()
    traj = Trajectory(task_id=task.id, task_version=task.version, model=client.model, seed=seed,
                      league=dict(before.meta), team=sc.team, adjustments=list(sc.adjustments),
                      rulebook_hash=rulebook_hash(), request=sc.request,
                      started_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    client.start(SYSTEM_PROMPT.format(team=sc.team, team_name=TEAMS[sc.team]), sc.request)

    for i in range(max_steps):
        try:
            turn = client.step(T.TOOLS)
        except Exception as e:  # noqa: BLE001 - record and stop, the trajectory is still data
            traj.steps.append({"i": i, "type": "client_error", "error": repr(e)})
            traj.end_reason = "client_error"
            break
        step: dict = {"i": i, "type": "assistant", "text": turn.text,
                      "tool_calls": [{"id": c.id, "name": c.name, "input": c.input} for c in turn.tool_calls],
                      "stop_reason": turn.stop_reason}
        traj.steps.append(step)
        if not turn.tool_calls:
            traj.final_reply = turn.text
            traj.end_reason = "end_turn" if turn.stop_reason in ("end_turn", "stop") else turn.stop_reason
            break
        results = []
        for c in turn.tool_calls:
            out = T.execute(state, c.name, c.input, failures)
            state = out.state
            traj.n_tool_calls += 1
            traj.n_tool_errors += int(out.is_error)
            traj.irreversible_calls += int(c.name in T.IRREVERSIBLE and not out.is_error)
            traj.steps.append({"i": i, "type": "tool_result", "call_id": c.id, "name": c.name,
                               "input": c.input, "result": out.result, "is_error": out.is_error})
            results.append((c.id, json.dumps(out.result), out.is_error))
        client.add_tool_results(results)
    else:
        traj.end_reason = "max_steps"

    traj.state_diff = before.diff(state)
    passed, why = task.check(before, state, sc.team)
    traj.ground_truth = {"pass": passed, "reason": why}
    return traj
