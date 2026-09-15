"""Publish: runs become an items dataset for motherlode's gate.

  python -m trade_desk.publish --runs runs/agents-v5-haiku runs/agents-v5-sonnet runs/agents-v5-opus \\
      --out datasets/trajectories-v5 --name trajectories-v5 [--pilot id ...]

Writes items.jsonl (one item per trajectory: an opaque id, the packet as text, ground truth for
D1, and meta the trade desk needs later: task, team, tier, run, index), copies the rubric text
and its spec, then seals the directory with ``motherlode dataset seal`` so the manifest and
hashes are motherlode's. The trade desk imports nothing from motherlode; it runs the command.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .packets import drift, item_id, load_run, render_packet

RUBRIC_MD = Path(__file__).resolve().parent.parent / "rubric" / "RUBRIC.md"
RUBRIC_JSON = Path(__file__).resolve().parent.parent / "rubric" / "RUBRIC.json"


def motherlode_bin() -> str:
    """The motherlode command: beside this interpreter if installed there, else on PATH."""
    cand = Path(sys.executable).parent / "motherlode"
    if cand.exists():
        return str(cand)
    found = shutil.which("motherlode")
    if not found:
        sys.exit("motherlode is not installed; install the tools extra: uv pip install -e '.[tools]'")
    return found


def build_items(runs: list[str]) -> list[dict]:
    items = []
    for run in runs:
        for i, t in enumerate(load_run(run)):
            items.append({
                "id": item_id(run, i, t),
                "text": render_packet(t),
                "truth": {"D1": "1" if t["ground_truth"]["pass"] else "0"},
                "meta": {"task_id": t["task_id"], "team": t["team"], "tier": t["model"], "run": Path(run).name,
                         "index": i, "task_version": t.get("task_version"), "snapshot_sha256": t.get("snapshot_sha256"),
                         "code_commit": t.get("code_commit"), "n_tool_calls": t["n_tool_calls"],
                         "n_tool_errors": t["n_tool_errors"], "irreversible_calls": t["irreversible_calls"],
                         "end_reason": t["end_reason"], "rulebook_hash": t.get("rulebook_hash"),
                         "tools_hash": t.get("tools_hash")},
            })
    return items


def publish(runs: list[str], out: str, name: str, pilot: list[str] | None = None, producer: str = "nba-trade-desk",
            seal: bool = True) -> Path:
    items = build_items(runs)
    o = Path(out)
    if o.exists():
        shutil.rmtree(o)
    o.mkdir(parents=True)
    with (o / "items.jsonl").open("w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    shutil.copy(RUBRIC_MD, o / "rubric.md")
    shutil.copy(RUBRIC_JSON, o / "rubric.json")
    seen: dict[str, int] = {}
    for run in runs:
        for t in load_run(run):
            for d in drift(t):
                seen[d] = seen.get(d, 0) + 1
    for d, n in sorted(seen.items()):
        print(f"DRIFT ({n} records): {d}; packets carry the run's own rulebook and tools", file=sys.stderr)
    snapshots = sorted({it["meta"]["snapshot_sha256"] for it in items if it["meta"].get("snapshot_sha256")})
    commits = sorted({it["meta"]["code_commit"] for it in items if it["meta"].get("code_commit")})
    meta = {"runs": [Path(r).name for r in runs], "tiers": sorted({it["meta"]["tier"] for it in items}),
            "tasks": sorted({it["meta"]["task_id"] for it in items}), "code_commits": commits,
            "pilot_ids": pilot or []}
    if seal:
        cmd = [motherlode_bin(), "dataset", "seal", str(o), "--name", name, "--schema", "items-v1",
               "--producer", producer, "--meta", json.dumps(meta)]
        for s in snapshots:
            cmd += ["--source", f"espn-snapshot={s}"]
        subprocess.run(cmd, check=True)
    return o


def main(argv=None):
    p = argparse.ArgumentParser(prog="trade_desk.publish")
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--pilot", nargs="*", default=None, help="item ids chosen for the hand-grading pilot")
    p.add_argument("--no-seal", action="store_true", help="write files only; do not run motherlode")
    a = p.parse_args(argv)
    out = publish(a.runs, a.out, a.name, a.pilot, seal=not a.no_seal)
    print(f"published {sum(1 for _ in open(out / 'items.jsonl'))} items to {out}")


if __name__ == "__main__":
    main()
