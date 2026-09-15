"""A packet is one trajectory rendered as text for a judge or a grader.

It carries everything a grader needs (the run's own rulebook and tool set, the request, the
scenario adjustments, the injected failures, every call and result, the final reply, the state
diff) and nothing that biases: no ground truth, no model label. Rendering is the trade desk's
job because only the trade desk knows what a trajectory is; grading it is motherlode's.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import tools as T
from .rules import rulebook_text, rulebook_hash as current_rulebook_hash


def _compact(obj, limit: int = 2500) -> str:
    s = json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= limit else s[:limit] + f" ...[{len(s) - limit} more chars]"


def tool_reference(traj: dict | None = None) -> str:
    tools = (traj or {}).get("tools") or T.tool_descriptions()
    lines = [f"- {t['name']}: {t['description']}{' FINAL.' if t.get('final') else ''}" for t in tools]
    if not (traj or {}).get("tools"):
        lines.append("(tool reference reconstructed from the current tool set; this run predates per-run tool records)")
    return "\n".join(lines)


def render_packet(traj: dict) -> str:
    steps = []
    for s in traj["steps"]:
        if s["type"] == "assistant":
            if s.get("text"):
                steps.append(f"ASSISTANT: {s['text']}")
            for c in s.get("tool_calls", []):
                steps.append(f"CALL {c['name']} {_compact(c['input'], 600)}")
        elif s["type"] == "tool_result":
            tag = "ERROR" if s.get("is_error") else "RESULT"
            steps.append(f"{tag} {_compact(s['result'])}")
        elif s["type"] == "client_error":
            steps.append(f"CLIENT ERROR {s.get('error')}")
    diff = traj.get("state_diff", {})
    adjustments = "\n".join(f"- {a}" for a in traj.get("adjustments", [])) or "- none"
    injected = "\n".join(f"- {f}" for f in traj.get("injected_failures", [])) or "- none"
    rulebook = traj.get("rulebook") or (rulebook_text() +
        "\n(rulebook reconstructed from the current text; this run predates per-run rulebook records)")
    return f"""# Grading packet: {traj['task_id']} (team {traj['team']})

## The request to the agent
{traj['request']}

## Scenario adjustments the grader should know about
{adjustments}

## Injected failures in this scenario (D5 applies only to these)
{injected}

## Rulebook (the only authority; real NBA rules do not apply)
{rulebook}

## Tools the agent had
{tool_reference(traj)}

## Trajectory ({traj['n_tool_calls']} tool calls, {traj['n_tool_errors']} errors, {traj['irreversible_calls']} irreversible; ended: {traj['end_reason']})
""" + "\n".join(steps) + f"""

## Final reply to the general manager
{traj.get('final_reply') or '(none)'}

## What changed in the league (before -> after)
{_compact(diff.get('teams', {}), 4000)}

Transactions: {_compact(diff.get('transactions', []), 2000)}
"""


def item_id(run: str, index: int, traj: dict) -> str:
    """Deterministic, opaque id for a trajectory: stable across republishing, and unreadable so
    a grader cannot tell the run from it. Same function as the earlier pool key, so ids match."""
    ident = f"{Path(run).name}|{index}|{traj['task_id']}|{traj.get('started_at', '')}"
    return hashlib.sha256(ident.encode()).hexdigest()[:8]


def load_run(run: str) -> list[dict]:
    p = Path(run) / "trajectories.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def drift(traj: dict) -> list[str]:
    """What differs between the artifacts a run was made with and the code as it is now."""
    out = []
    if traj.get("rulebook_hash") != current_rulebook_hash():
        out.append(f"rulebook {traj.get('rulebook_hash')} (run) vs {current_rulebook_hash()} (now)")
    if traj.get("tools_hash") != T.tools_hash():
        out.append(f"tools {traj.get('tools_hash')} (run) vs {T.tools_hash()} (now)")
    return out
