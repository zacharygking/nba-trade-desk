"""CLI: list tasks, print the rulebook, show scenarios, run agents, write trajectories.

  python -m trade_desk.run list
  python -m trade_desk.run rulebook > rulebook/RULEBOOK.md
  python -m trade_desk.run league                      # payroll table for the loaded league
  python -m trade_desk.run show under_tax_keep_starters
  python -m trade_desk.run run --model claude-opus-5 --tasks all --out runs/opus5
  python -m trade_desk.run run --client noop --tasks all --out runs/noop   # wiring check, no API
  add --league synthetic to any command to use the invented league instead of the ESPN snapshot
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import run_task, scripted
from .league import build_league
from .rules import rulebook_text, rulebook_hash
from .state import CAP, TAX, APRON
from .tasks import TASKS, TASKS_BY_ID
from .tools import TOOLS


def _select(spec: str):
    if spec == "all":
        return TASKS
    ids = [s.strip() for s in spec.split(",")]
    missing = [i for i in ids if i not in TASKS_BY_ID]
    if missing:
        sys.exit(f"unknown tasks: {missing}")
    return [TASKS_BY_ID[i] for i in ids]


def cmd_list(args):
    for t in TASKS:
        sc = t.build(args.seed, args.league)
        print(f"{t.id:32s} v{t.version}  {sc.team}  [{', '.join(t.tags)}]  {t.title}")


def cmd_rulebook(_):
    print(rulebook_text())
    print(f"<!-- rulebook hash {rulebook_hash()} -->")


def cmd_league(args):
    s = build_league(args.seed, args.league)
    print(f"source={s.meta}  cap={CAP} tax={TAX} apron={APRON}")
    print("team  payroll  n  restricted  top player (rating, salary)")
    for t in sorted(s.teams, key=lambda t: -s.payroll(t)):
        top = s.roster(t)[0]
        flag = "TAX" if s.payroll(t) > TAX else ("cap" if s.payroll(t) > CAP else "   ")
        print(f"{t:4s} {s.payroll(t):7.1f} {s.roster_size(t):2d} {flag}  "
              f"{sum(1 for p in s.roster(t) if p.no_trade):2d}  {top.name} ({top.rating}, ${top.salary}M)")
    print(f"free agents: {len(s.free_agents())}")


def cmd_show(args):
    sc = TASKS_BY_ID[args.task].build(args.seed, args.league)
    print(f"# {TASKS_BY_ID[args.task].title}\n\nTeam: {sc.team}\n\nRequest: {sc.request}\n")
    if sc.adjustments:
        print("Scenario adjustments:", *sc.adjustments, sep="\n  ")
    print(json.dumps(sc.state.snapshot(sc.team), indent=1))
    print("\nFailures:", TASKS_BY_ID[args.task].failures().__dict__)


def _make_client(args):
    if args.client == "noop":
        def factory():
            return scripted(("view_roster", {"team": "SAC"}), ("read_rule", {"rule_id": None}),
                            "I looked at a roster and the rulebook and made no moves.")
        return factory
    if args.client == "anthropic":
        from .agent import AnthropicClient
        return lambda: AnthropicClient(model=args.model, effort=args.effort)
    sys.exit(f"unknown client {args.client}")


def cmd_run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    factory = _make_client(args)
    path = out / "trajectories.jsonl"
    n_pass = 0
    tasks = _select(args.tasks)
    with path.open("a") as f:
        for t in tasks:
            for rep in range(args.repeats):
                traj = run_task(t, factory(), seed=args.seed, source=args.league, max_steps=args.max_steps)
                f.write(json.dumps(traj.to_dict() | {"repeat": rep}) + "\n")
                f.flush()
                gt = traj.ground_truth
                n_pass += int(gt["pass"])
                flag = "PASS" if gt["pass"] else "FAIL"
                print(f"{flag}  {t.id:30s} {traj.team}  calls={traj.n_tool_calls:2d} errors={traj.n_tool_errors} "
                      f"irreversible={traj.irreversible_calls} end={traj.end_reason}"
                      + ("" if gt["pass"] else f"  ({gt['reason']})"))
    total = len(tasks) * args.repeats
    print(f"\n{n_pass}/{total} passed. Wrote {path}")


def cmd_tools(_):
    print(json.dumps(TOOLS, indent=1))


def main(argv=None):
    p = argparse.ArgumentParser(prog="trade_desk")
    p.add_argument("--league", default="espn", choices=["espn", "synthetic"])
    p.add_argument("--seed", type=int, default=7)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("rulebook").set_defaults(fn=cmd_rulebook)
    sub.add_parser("league").set_defaults(fn=cmd_league)
    sub.add_parser("tools").set_defaults(fn=cmd_tools)
    s = sub.add_parser("show"); s.add_argument("task"); s.set_defaults(fn=cmd_show)
    r = sub.add_parser("run")
    r.add_argument("--client", default="anthropic", choices=["anthropic", "noop"])
    r.add_argument("--model", default="claude-opus-5")
    r.add_argument("--effort", default=None, choices=[None, "low", "medium", "high", "xhigh", "max"])
    r.add_argument("--tasks", default="all")
    r.add_argument("--repeats", type=int, default=1)
    r.add_argument("--max-steps", type=int, default=30)
    r.add_argument("--out", required=True)
    r.set_defaults(fn=cmd_run)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
