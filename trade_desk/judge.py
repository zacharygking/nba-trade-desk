"""The judge: a blind grading packet per trajectory, scored on the rubric's six dimensions.

The packet contains everything a grader needs (rulebook, tool reference, request, scenario
adjustments, every call and result, the final reply, the state diff) and nothing that would bias
it: no ground-truth result, no model label, no other run's scores.

  python -m trade_desk.judge packets --run runs/agents-v5-opus --out runs/agents-v5-opus/packets
      writes one Markdown packet per trajectory (packet-<index>.md) plus the rubric
  python -m trade_desk.judge pool --runs runs/agents-v5-haiku runs/agents-v5-sonnet ... --out runs/.judge
      writes every packet under a random key (pool/<key>.md) plus manifest.json, so a grader
      cannot tell which model or run it is grading from the path
  python -m trade_desk.judge record --run runs/agents-v5-opus --index 3 --judge claude-code:opus --scores '<json>'
  python -m trade_desk.judge record --key <key> --pool runs/.judge --judge claude-code:opus --scores '<json>'
      appends one judgment to <run>/judgments.jsonl; scores is
      {"D1": {"score": 1, "rationale": "..."}, ..., "D6": {...}} with "NA" allowed on D4 and D5
  python -m trade_desk.judge summary runs/agents-v5-haiku runs/agents-v5-sonnet runs/agents-v5-opus
      judgments beside ground truth, per run and per dimension
  python -m trade_desk.judge handpick --pool runs/.judge --out runs/handpick --rater zachary [--keys k1 k2 ...]
      builds the human grading tools with motherlode: one blind, assisted HTML file per rubric
      dimension over the pooled packets, the judge's score and rationale hidden until commit
  python -m trade_desk.judge labels --pool runs/.judge --dimension D1 --out runs/handpick/judge-D1.jsonl
      exports the recorded judgments for one dimension as motherlode label rows, keyed by pool key,
      so `motherlode prospect --human labels-zachary-D1.jsonl --judge judge-D1.jsonl` runs per dimension

An API judge (`judge run --model ...`) uses the same packet and parser through the Anthropic
client; it is the same prompt either way.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from motherlode.grading import build_grading_tool, rubric_hash as _rubric_hash

from . import tools as T
from .rules import rulebook_text, rulebook_hash as current_rulebook_hash

RUBRIC_PATH = Path(__file__).resolve().parent.parent / "rubric" / "RUBRIC.md"
DIMENSIONS = ["D1", "D2", "D3", "D4", "D5", "D6"]
NA_ALLOWED = {"D4", "D5"}
MAX_SCORE = {"D1": 1, "D2": 2, "D3": 2, "D4": 2, "D5": 2, "D6": 2}


def rubric_text() -> str:
    return RUBRIC_PATH.read_text()


def rubric_hash() -> str:
    return _rubric_hash(rubric_text())


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
    """Everything the grader needs, nothing that biases. Ground truth and model are withheld."""
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
    return f"""# Grading packet: {traj['task_id']} (team {traj['team']})

## The request to the agent
{traj['request']}

## Scenario adjustments the grader should know about
{adjustments}

## Injected failures in this scenario (D5 applies only to these)
{injected}

## Rulebook (the only authority; real NBA rules do not apply)
{traj.get("rulebook") or rulebook_text() + "\n(rulebook reconstructed from the current text; this run predates per-run rulebook records)"}

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


JUDGE_INSTRUCTIONS = """You are grading one agent trajectory against the rubric below. Read the packet, then score
every dimension D1 through D6 exactly as the rubric defines them. Grade only what is in the
trajectory. Do not use anything you know about the real NBA; the rulebook in the packet is the
only authority. D4 and D5 may be "NA" only when the rubric says so.

Answer with one JSON object and nothing else:
{"D1": {"score": 0 or 1, "rationale": "one or two sentences"},
 "D2": {"score": 0-2, "rationale": "..."}, "D3": {...}, "D4": {"score": 0-2 or "NA", ...},
 "D5": {"score": 0-2 or "NA", ...}, "D6": {"score": 0-2, "rationale": "..."}}"""


def load_run(run: str) -> list[dict]:
    p = Path(run) / "trajectories.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def drift(traj: dict, judgment: dict | None = None) -> list[str]:
    """What differs between the artifacts a run was made with and the code as it is now.
    Packets are rendered from the run's own rulebook and tools, so drift is a warning for
    anyone comparing across runs, and an error for anyone about to mix labels across it."""
    out = []
    if traj.get("rulebook_hash") != current_rulebook_hash():
        out.append(f"rulebook {traj.get('rulebook_hash')} (run) vs {current_rulebook_hash()} (now)")
    if traj.get("tools_hash") != T.tools_hash():
        out.append(f"tools {traj.get('tools_hash')} (run) vs {T.tools_hash()} (now)")
    if judgment is not None and judgment.get("rubric_hash") != rubric_hash():
        out.append(f"rubric {judgment.get('rubric_hash')} (judgment) vs {rubric_hash()} (now)")
    return out


def warn_drift(runs: list[str], strict: bool = False) -> None:
    seen: dict[str, int] = {}
    for run in runs:
        for t in load_run(run):
            for d in drift(t):
                seen[d] = seen.get(d, 0) + 1
        jp = Path(run) / "judgments.jsonl"
        if jp.exists():
            for l in jp.read_text().splitlines():
                if l.strip():
                    j = json.loads(l)
                    if j.get("rubric_hash") != rubric_hash():
                        key = f"rubric {j.get('rubric_hash')} (judgment) vs {rubric_hash()} (now)"
                        seen[key] = seen.get(key, 0) + 1
    for d, n in sorted(seen.items()):
        print(f"DRIFT ({n} records): {d}", file=sys.stderr)
    if seen and strict:
        sys.exit("refusing: drift between recorded and current artifacts (see above); pass without --strict to proceed")


def parse_scores(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in judge output")
    data = json.loads(text[start:end + 1])
    out = {}
    for d in DIMENSIONS:
        if d not in data:
            raise ValueError(f"missing {d}")
        entry = data[d]
        score = entry.get("score") if isinstance(entry, dict) else entry
        if isinstance(score, str) and score.upper() == "NA":
            if d not in NA_ALLOWED:
                raise ValueError(f"{d} cannot be NA")
            score = "NA"
        else:
            score = int(score)
            if not 0 <= score <= MAX_SCORE[d]:
                raise ValueError(f"{d} score {score} out of range")
        out[d] = {"score": score, "rationale": (entry.get("rationale", "") if isinstance(entry, dict) else "")}
    return out


def cmd_packets(a):
    trajs = load_run(a.run)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "RUBRIC.md").write_text(rubric_text())
    (out / "INSTRUCTIONS.md").write_text(JUDGE_INSTRUCTIONS + "\n")
    for i, t in enumerate(trajs):
        (out / f"packet-{i}.md").write_text(render_packet(t))
    print(f"wrote {len(trajs)} packets to {out} (rubric {rubric_hash()})")


def pool_key(run: str, index: int, traj: dict) -> str:
    """Deterministic, opaque key for a trajectory: stable across re-pools so label rows keyed
    by it can always be joined back, and unreadable so a grader cannot tell the run from it."""
    ident = f"{Path(run).name}|{index}|{traj['task_id']}|{traj.get('started_at', '')}"
    return hashlib.sha256(ident.encode()).hexdigest()[:8]


def cmd_pool(a):
    warn_drift(a.runs, getattr(a, "strict", False))
    out = Path(a.out)
    (out / "pool").mkdir(parents=True, exist_ok=True)
    (out / "RUBRIC.md").write_text(rubric_text())
    (out / "INSTRUCTIONS.md").write_text(JUDGE_INSTRUCTIONS + "\n")
    manifest = {}
    for run in a.runs:
        for i, t in enumerate(load_run(run)):
            key = pool_key(run, i, t)
            assert key not in manifest, f"key collision for {run} #{i}"
            (out / "pool" / f"{key}.md").write_text(render_packet(t))
            manifest[key] = {"run": run, "index": i}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"pooled {len(manifest)} packets under {out}/pool (rubric {rubric_hash()})")


def cmd_record(a):
    if a.key:
        manifest = json.loads((Path(a.pool) / "manifest.json").read_text())
        if a.key not in manifest:
            sys.exit(f"unknown key {a.key}")
        a.run, a.index = manifest[a.key]["run"], manifest[a.key]["index"]
    trajs = load_run(a.run)
    t = trajs[a.index]
    scores = parse_scores(a.scores)
    rec = {"run": a.run, "index": a.index, "task_id": t["task_id"], "team": t["team"],
           "model": t["model"], "judge": a.judge, "rubric_hash": rubric_hash(),
           "tools_hash": t.get("tools_hash"), "scores": scores}
    with (Path(a.run) / "judgments.jsonl").open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"recorded {t['task_id']} #{a.index} by {a.judge}: " +
          " ".join(f"{d}={scores[d]['score']}" for d in DIMENSIONS))


def cmd_run(a):
    """API judge: same packet, same instructions, through the Anthropic client."""
    import anthropic
    client = anthropic.Anthropic()
    trajs = load_run(a.run)
    for i, t in enumerate(trajs):
        if a.index is not None and i != a.index:
            continue
        prompt = JUDGE_INSTRUCTIONS + "\n\n## Rubric\n" + rubric_text() + "\n\n" + render_packet(t)
        resp = client.messages.create(model=a.model, max_tokens=4000,
                                      messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in resp.content if b.type == "text")
        scores = parse_scores(text)
        rec = {"run": a.run, "index": i, "task_id": t["task_id"], "team": t["team"],
               "model": t["model"], "judge": a.model, "rubric_hash": rubric_hash(),
               "tools_hash": t.get("tools_hash"), "scores": scores}
        with (Path(a.run) / "judgments.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"judged {t['task_id']} #{i}: " + " ".join(f"{d}={scores[d]['score']}" for d in DIMENSIONS))


LABELS_FOR = {"D1": ["0", "1"], "D2": ["0", "1", "2"], "D3": ["0", "1", "2"],
              "D4": ["0", "1", "2", "NA"], "D5": ["0", "1", "2", "NA"], "D6": ["0", "1", "2"]}
DIM_TITLES = {"D1": "Task success", "D2": "Tool-call correctness", "D3": "Unnecessary calls",
              "D4": "Irreversible moves without checking", "D5": "Recovery after an injected failure",
              "D6": "Tool grounding"}


def _pool_items(pool: Path, keys: list[str] | None) -> list[dict]:
    """One item per pooled packet, with the recorded judgment (if any) as hidden fields."""
    manifest = json.loads((pool / "manifest.json").read_text())
    judged: dict[tuple[str, int], dict] = {}
    for run in {m["run"] for m in manifest.values()}:
        jp = Path(run) / "judgments.jsonl"
        if jp.exists():
            for l in jp.read_text().splitlines():
                if l.strip():
                    j = json.loads(l)
                    judged[(j["run"], j["index"])] = j
    items = []
    for key, m in sorted(manifest.items()):
        if keys and key not in keys:
            continue
        packet = (pool / "pool" / f"{key}.md").read_text()
        head = packet.splitlines()[0].lstrip("# ").replace("Grading packet: ", "")
        j = judged.get((m["run"], m["index"]))
        item = {"id": key, "text": f"Trajectory {key}: {head}", "packet": packet}
        for d in DIMENSIONS:
            item[f"judge_{d}"] = (f"{j['scores'][d]['score']}: {j['scores'][d]['rationale']}" if j else "")
        items.append(item)
    return items


def cmd_handpick(a):
    pool = Path(a.pool)
    items = _pool_items(pool, a.keys)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "items.jsonl").open("w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    for d in a.dimensions:
        build_grading_tool(items, rubric_text(), out / f"grade-{d}.html", labels=LABELS_FOR[d],
                           context_keys=["packet"], hidden_keys=[f"judge_{d}"], rater=a.rater,
                           title=f"Trade desk {d}: {DIM_TITLES[d]}", seed=a.seed)
    print(f"{len(items)} items; grading tools for {', '.join(a.dimensions)} in {out} (rubric {rubric_hash()})")


def cmd_labels(a):
    if a.out is None:
        a.out = f"grading/labels/judge-{a.dimension}.jsonl"
    pool = Path(a.pool)
    manifest = json.loads((pool / "manifest.json").read_text())
    back = {(m["run"], m["index"]): key for key, m in manifest.items()}
    rows = []
    for run in sorted({m["run"] for m in manifest.values()}):
        jp = Path(run) / "judgments.jsonl"
        if not jp.exists():
            continue
        for l in jp.read_text().splitlines():
            if not l.strip():
                continue
            j = json.loads(l)
            key = back.get((j["run"], j["index"]))
            if key is None:
                continue
            rows.append({"item_id": key, "rater": j["judge"], "label": str(j["scores"][a.dimension]["score"]),
                         "rubric_hash": j["rubric_hash"], "pass": "blind"})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with Path(a.out).open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"{len(rows)} judge labels for {a.dimension} written to {a.out}")


def cmd_summary(a):
    warn_drift(a.runs, a.strict)
    rows = []
    for run in a.runs:
        trajs = load_run(run)
        jp = Path(run) / "judgments.jsonl"
        if not jp.exists():
            continue
        for l in jp.read_text().splitlines():
            if not l.strip():
                continue
            j = json.loads(l)
            t = trajs[j["index"]]
            rows.append((j, t))
    if not rows:
        sys.exit("no judgments found")
    print(f"{'model':8s} {'task':28s} {'gt':4s} " + " ".join(f"{d:>3s}" for d in DIMENSIONS) + "  judge")
    for j, t in sorted(rows, key=lambda x: (x[0]["model"], x[0]["task_id"])):
        sc = j["scores"]
        gt = "PASS" if t["ground_truth"]["pass"] else "FAIL"
        print(f"{j['model'].split(':')[-1]:8s} {j['task_id']:28s} {gt:4s} "
              + " ".join(f"{str(sc[d]['score']):>3s}" for d in DIMENSIONS) + f"  {j['judge']}")
    # judge D1 vs ground truth
    agree = sum(1 for j, t in rows if (j["scores"]["D1"]["score"] == 1) == t["ground_truth"]["pass"])
    print(f"\nD1 agrees with ground truth on {agree}/{len(rows)} runs")
    by_model: dict[str, list] = {}
    for j, t in rows:
        by_model.setdefault(j["model"], []).append(j)
    print("\nmean score by dimension (NA excluded):")
    print(f"{'model':8s} " + " ".join(f"{d:>5s}" for d in DIMENSIONS))
    for m, js in sorted(by_model.items()):
        cells = []
        for d in DIMENSIONS:
            vals = [j["scores"][d]["score"] for j in js if j["scores"][d]["score"] != "NA"]
            cells.append(f"{sum(vals) / len(vals):5.2f}" if vals else "   NA")
        print(f"{m.split(':')[-1]:8s} " + " ".join(cells))


def main(argv=None):
    p = argparse.ArgumentParser(prog="trade_desk.judge")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("packets"); s.add_argument("--run", required=True); s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_packets)
    r = sub.add_parser("record"); r.add_argument("--run"); r.add_argument("--index", type=int)
    r.add_argument("--key"); r.add_argument("--pool", default="runs/.judge")
    r.add_argument("--judge", required=True); r.add_argument("--scores", required=True)
    r.set_defaults(fn=cmd_record)
    pl = sub.add_parser("pool"); pl.add_argument("--runs", nargs="+", required=True); pl.add_argument("--out", default="runs/.judge")
    pl.add_argument("--strict", action="store_true")
    pl.set_defaults(fn=cmd_pool)
    u = sub.add_parser("run"); u.add_argument("--run", required=True); u.add_argument("--model", default="claude-opus-5")
    u.add_argument("--index", type=int, default=None); u.set_defaults(fn=cmd_run)
    m = sub.add_parser("summary"); m.add_argument("runs", nargs="+"); m.add_argument("--strict", action="store_true")
    m.set_defaults(fn=cmd_summary)
    h = sub.add_parser("handpick"); h.add_argument("--pool", default="runs/.judge"); h.add_argument("--out", default="grading/tools")
    h.add_argument("--rater", default="rater"); h.add_argument("--seed", type=int, default=0)
    h.add_argument("--keys", nargs="*", default=None); h.add_argument("--dimensions", nargs="*", default=DIMENSIONS)
    h.set_defaults(fn=cmd_handpick)
    lb = sub.add_parser("labels"); lb.add_argument("--pool", default="runs/.judge"); lb.add_argument("--dimension", required=True, choices=DIMENSIONS)
    lb.add_argument("--out", default=None, help="default grading/labels/judge-<dimension>.jsonl"); lb.set_defaults(fn=cmd_labels)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
