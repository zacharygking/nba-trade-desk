"""Shell-driven sessions, so an agent that lives outside this process (a Claude Code subagent, a
person at a terminal) can play the general manager. Every tool call is recorded exactly as in
agent.run_task; only the assistant's between-call text is absent.

  python -m trade_desk.session start  --task under_tax_keep_starters --model claude-code:sonnet --out runs/agents [--max-calls 30]
      prints the session id, the system prompt, the request and the tool reference; calls past
      the limit are refused with an error and the trajectory ends with reason "max_steps"
  python -m trade_desk.session call   --session <id> --tool view_roster --args '{"team": "LAL"}'
      executes one tool against the session state and prints the JSON result
  python -m trade_desk.session finish --session <id> --reply-file reply.txt
      records the reply (or --reply "text"; prefer the file, a shell string eats $ figures),
      grades against ground truth, appends the trajectory to trajectories.jsonl
"""
from __future__ import annotations

import argparse
import json
import pickle
import secrets
import sys
import time
from pathlib import Path

from . import tools as T
from .agent import SYSTEM_PROMPT, Trajectory, provenance
from .league import TEAMS
from .rules import rulebook_hash, rulebook_text
from .tasks import TASKS_BY_ID

SESSIONS = Path("runs") / ".sessions"


def _path(sid: str) -> Path:
    return SESSIONS / f"{sid}.pkl"


def _load(sid: str) -> dict:
    p = _path(sid)
    if not p.exists():
        sys.exit(f"no session {sid}")
    return pickle.loads(p.read_bytes())


def _save(sid: str, s: dict) -> None:
    SESSIONS.mkdir(parents=True, exist_ok=True)
    _path(sid).write_bytes(pickle.dumps(s))


def tool_reference() -> str:
    lines = []
    for t in T.TOOLS:
        props = t["input_schema"]["properties"]
        args = ", ".join(f"{k}: {v.get('type')}" for k, v in props.items())
        final = "  FINAL, cannot be undone." if t["name"] in T.IRREVERSIBLE else ""
        lines.append(f"- {t['name']}({args}){final}\n    {t['description']}")
    return "\n".join(lines)


def cmd_start(a):
    task = TASKS_BY_ID[a.task]
    sc = task.build(a.seed, a.league)
    sid = f"{a.task}-{secrets.token_hex(3)}"
    failures = task.failures()
    traj = Trajectory(task_id=task.id, task_version=task.version, model=a.model, seed=a.seed,
                      league=dict(sc.state.meta), team=sc.team, adjustments=list(sc.adjustments),
                      rulebook_hash=rulebook_hash(), tools_hash=T.tools_hash(), max_steps=a.max_calls,
                      request=sc.request,
                      started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                      tools=T.tool_descriptions(), injected_failures=failures.describe(),
                      rulebook=rulebook_text(), **(provenance() if a.league == "espn" else {"code_commit": provenance()["code_commit"]}))
    _save(sid, {"before": sc.state, "state": sc.state.clone(), "failures": failures,
                "traj": traj, "out": a.out, "i": 0, "max_calls": a.max_calls, "over_limit": False})
    system = SYSTEM_PROMPT.format(team=sc.team, team_name=TEAMS[sc.team])
    print(f"SESSION {sid}\nTEAM {sc.team}\nCALL LIMIT {a.max_calls}\n\n{system}\n\nREQUEST: {sc.request}\n\n"
          f"TOOLS:\n{tool_reference()}")


def cmd_call(a):
    s = _load(a.session)
    try:
        args = json.loads(a.args)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"args must be JSON: {e}"}))
        return
    traj: Trajectory = s["traj"]
    i = s["i"]
    call_id = f"call_{i}"
    traj.steps.append({"i": i, "type": "assistant", "text": "", "stop_reason": "tool_use",
                       "tool_calls": [{"id": call_id, "name": a.tool, "input": args}]})
    if i >= s.get("max_calls", 10**9):
        s["over_limit"] = True
        out = T.ToolOutcome({"error": f"call limit of {s['max_calls']} reached; finish the session now"},
                            True, s["state"])
    else:
        out = T.execute(s["state"], a.tool, args, s["failures"])
    s["state"] = out.state
    traj.n_tool_calls += 1
    traj.n_tool_errors += int(out.is_error)
    traj.irreversible_calls += int(a.tool in T.IRREVERSIBLE and not out.is_error)
    traj.steps.append({"i": i, "type": "tool_result", "call_id": call_id, "name": a.tool,
                       "input": args, "result": out.result, "is_error": out.is_error})
    s["i"] = i + 1
    _save(a.session, s)
    print(json.dumps(out.result | ({"is_error": True} if out.is_error else {}), indent=1))


def cmd_finish(a):
    s = _load(a.session)
    traj: Trajectory = s["traj"]
    if a.reply_file:
        reply = Path(a.reply_file).read_text().strip()
    elif a.reply is not None:
        reply = a.reply
    else:
        sys.exit("finish needs --reply-file or --reply")
    traj.steps.append({"i": s["i"], "type": "assistant", "text": reply, "tool_calls": [],
                       "stop_reason": "end_turn"})
    traj.final_reply = reply
    traj.end_reason = "max_steps" if s.get("over_limit") else "end_turn"
    task = TASKS_BY_ID[traj.task_id]
    traj.state_diff = s["before"].diff(s["state"])
    passed, why = task.check(s["before"], s["state"], traj.team)
    traj.ground_truth = {"pass": passed, "reason": why}
    out = Path(s["out"])
    out.mkdir(parents=True, exist_ok=True)
    with (out / "trajectories.jsonl").open("a") as f:
        f.write(json.dumps(traj.to_dict() | {"repeat": 0, "session": a.session}) + "\n")
    _path(a.session).unlink()
    print(f"recorded {traj.task_id} for {traj.model}: {traj.n_tool_calls} calls, "
          f"{traj.irreversible_calls} irreversible")
    if a.show_grade:
        print("ground truth:", "PASS" if passed else f"FAIL ({why})")


def main(argv=None):
    p = argparse.ArgumentParser(prog="trade_desk.session")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--task", required=True); s.add_argument("--model", required=True)
    s.add_argument("--out", default="runs/agents"); s.add_argument("--seed", type=int, default=7)
    s.add_argument("--league", default="espn", choices=["espn", "synthetic"])
    s.add_argument("--max-calls", type=int, default=30)
    s.set_defaults(fn=cmd_start)
    c = sub.add_parser("call")
    c.add_argument("--session", required=True); c.add_argument("--tool", required=True)
    c.add_argument("--args", default="{}")
    c.set_defaults(fn=cmd_call)
    f = sub.add_parser("finish")
    f.add_argument("--session", required=True); f.add_argument("--reply"); f.add_argument("--reply-file")
    f.add_argument("--show-grade", action="store_true")
    f.set_defaults(fn=cmd_finish)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
