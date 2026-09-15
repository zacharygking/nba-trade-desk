"""Summarize trajectory files: one row per run, one table per model, transactions spelled out.

  python -m trade_desk.report runs/agents-haiku runs/agents-sonnet runs/agents-opus
  python -m trade_desk.report runs/agents-sonnet --stories     # include each run's transactions
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from .league import build_league


def load(paths: list[str]) -> list[dict]:
    rows = []
    for p in paths:
        f = Path(p) / "trajectories.jsonl" if Path(p).is_dir() else Path(p)
        if f.exists():
            rows += [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
    return rows


def names(state, ids: list[str]) -> str:
    out = []
    for i in ids:
        if i in state.players:
            p = state.players[i]
            out.append(f"{p.name} (${p.salary}M, {p.rating})")
        else:
            out.append(i)
    return ", ".join(out) or "nothing"


def story(t: dict, state) -> list[str]:
    lines = []
    for tx in t["state_diff"].get("transactions", []):
        if tx["type"] == "trade":
            lines.append(f"trade with {tx['partner']}: sent {names(state, tx['send'])}; "
                         f"got {names(state, tx['receive'])}")
        elif tx["type"] == "sign":
            lines.append(f"signed {names(state, [tx['player']])} at ${tx['salary']}M")
        elif tx["type"] == "waive":
            lines.append(f"waived {names(state, [tx['player']])}"
                         + (f", dead money +${tx['dead_money_added']}M" if tx.get("dead_money_added") else ""))
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--stories", action="store_true")
    a = ap.parse_args(argv)
    rows = load(a.paths)
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)
    state = build_league(source="espn")
    for model, rs in sorted(by_model.items()):
        n_pass = sum(r["ground_truth"]["pass"] for r in rs)
        print(f"\n== {model}: {n_pass}/{len(rs)} pass ==")
        print(f"{'task':30s} {'team':4s} {'gt':4s} {'calls':>5s} {'err':>3s} {'irrev':>5s}  reason")
        for r in sorted(rs, key=lambda r: r["task_id"]):
            gt = r["ground_truth"]
            print(f"{r['task_id']:30s} {r['team']:4s} {'PASS' if gt['pass'] else 'FAIL':4s} "
                  f"{r['n_tool_calls']:5d} {r['n_tool_errors']:3d} {r['irreversible_calls']:5d}  {gt['reason']}")
            if a.stories:
                for line in story(r, state):
                    print(f"{'':30s}      - {line}")
    if len(by_model) > 1:
        print("\n== by task ==")
        tasks = sorted({r["task_id"] for r in rows})
        models = sorted(by_model)
        print(f"{'task':30s} " + " ".join(f"{m.split(':')[-1]:>8s}" for m in models))
        for t in tasks:
            cells = []
            for m in models:
                hit = [r for r in by_model[m] if r["task_id"] == t]
                cells.append(("PASS" if hit[0]["ground_truth"]["pass"] else "FAIL") if hit else "-")
            print(f"{t:30s} " + " ".join(f"{c:>8s}" for c in cells))


if __name__ == "__main__":
    main()
