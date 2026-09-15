"""Results: the tables the write-up cites, read back from datasets.

  python -m trade_desk.results --items datasets/trajectories-v5 [--graded datasets/trajectories-v5-graded]

From the items dataset alone: ground-truth passes per tier and task, call counts. With the graded
dataset: judge scores per tier and dimension, judge agreement with ground truth, and the
validation report if a human pass exists. Nothing here computes a statistic; motherlode did that
and wrote it into the graded dataset.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def read_dataset(path: str) -> tuple[dict, Path]:
    p = Path(path)
    return json.loads((p / "manifest.json").read_text()), p


def tier_name(t: str) -> str:
    return t.split(":")[-1]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="trade_desk.results")
    ap.add_argument("--items", required=True)
    ap.add_argument("--graded", default=None)
    a = ap.parse_args(argv)
    man, p = read_dataset(a.items)
    items = read_jsonl(p / "items.jsonl")
    print(f"items dataset {man['name']} ({man['dataset_sha256']}): {len(items)} trajectories, "
          f"tiers {[tier_name(t) for t in man['meta'].get('tiers', [])]}")
    tiers = sorted({it["meta"]["tier"] for it in items})
    tasks = sorted({it["meta"]["task_id"] for it in items})
    print("\n== ground truth by task ==")
    print(f"{'task':30s} " + " ".join(f"{tier_name(t):>8s}" for t in tiers))
    for task in tasks:
        cells = []
        for tier in tiers:
            hit = [it for it in items if it["meta"]["task_id"] == task and it["meta"]["tier"] == tier]
            cells.append(("PASS" if hit[0]["truth"]["D1"] == "1" else "FAIL") if hit else "-")
        print(f"{task:30s} " + " ".join(f"{c:>8s}" for c in cells))
    print(f"{'passes':30s} " + " ".join(f"{sum(1 for it in items if it['meta']['tier'] == t and it['truth']['D1'] == '1'):>8d}" for t in tiers))
    print(f"{'mean tool calls':30s} " + " ".join(
        f"{sum(it['meta']['n_tool_calls'] for it in items if it['meta']['tier'] == t) / max(1, sum(1 for it in items if it['meta']['tier'] == t)):8.1f}" for t in tiers))

    if not a.graded:
        return
    gman, gp = read_dataset(a.graded)
    src = gman["sources"][0]["dataset_sha256"] if gman.get("sources") else None
    print(f"\ngraded dataset {gman['name']} ({gman['dataset_sha256']}) grades items {src}"
          + ("" if src == man["dataset_sha256"] else "  WARNING: not this items dataset"))
    judgments = read_jsonl(gp / "judgments.jsonl") if (gp / "judgments.jsonl").exists() else []
    if not judgments:
        return
    by_item = {it["id"]: it for it in items}
    dims = sorted({j["dimension"] for j in judgments})
    judges = sorted({j["rater"] for j in judgments})
    for judge in judges:
        rows = [j for j in judgments if j["rater"] == judge and j["item_id"] in by_item]
        print(f"\n== judge {judge}: mean score by dimension (NA excluded) ==")
        print(f"{'tier':8s} " + " ".join(f"{d:>5s}" for d in dims) + "  total")
        for tier in tiers:
            cells, total = [], 0.0
            for d in dims:
                v = [int(j["label"]) for j in rows if j["dimension"] == d and by_item[j["item_id"]]["meta"]["tier"] == tier and j["label"] != "NA"]
                cells.append(f"{sum(v) / len(v):5.2f}" if v else "   NA")
                total += sum(v) / len(v) if v else 0
            print(f"{tier_name(tier):8s} " + " ".join(cells) + f"  {total:5.1f}")
        d1 = [j for j in rows if j["dimension"] == "D1"]
        agree = sum(1 for j in d1 if j["label"] == by_item[j["item_id"]]["truth"]["D1"])
        print(f"D1 agrees with ground truth on {agree}/{len(d1)}")
        dis = [j for j in d1 if j["label"] != by_item[j["item_id"]]["truth"]["D1"]]
        for j in dis:
            m = by_item[j["item_id"]]["meta"]
            print(f"  {tier_name(m['tier']):8s} {m['task_id']:26s} truth={by_item[j['item_id']]['truth']['D1']} judge={j['label']} :: {j.get('rationale', '')[:120]}")
    if (gp / "validation.json").exists():
        v = json.loads((gp / "validation.json").read_text())
        print(f"\n== validation (human {v.get('human_rater')} vs judge {v.get('judge_rater')}) ==")
        for d, entry in v["dimensions"].items():
            c = entry["human_vs_judge"]
            print(f"{d:4s} n={c['n']:3d} NA={c['na_excluded']:2d} kappa={c.get('kappa', float('nan')):5.2f} "
                  f"ci=[{c.get('kappa_ci95', [0, 0])[0]:5.2f},{c.get('kappa_ci95', [0, 0])[1]:5.2f}]")


if __name__ == "__main__":
    main()
