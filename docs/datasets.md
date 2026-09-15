# Datasets, and where the gate runs

The trade desk and [motherlode](https://github.com/zacharygking/motherlode) never import each
other. They share datasets: directories with a manifest and hashes, written by one and read by
the other.

| Direction | Dataset | Producer | Contents |
|---|---|---|---|
| Trade desk to motherlode | `datasets/trajectories-v5` | `nba-trade-desk publish` | One item per trajectory: an opaque id, the packet as text, ground truth for D1, meta the trade desk needs later. Plus the rubric text and its spec. Sealed by `motherlode dataset seal`. |
| Motherlode to trade desk | `datasets/trajectories-v5-graded` | `motherlode paydirt` | The judge's label rows per item and dimension, human label files, ground truth as label rows, the validation report, hashed to the items dataset they grade. |

`datasets/trajectories-v2-archive` and its graded twin are the first run set, kept as evidence
and not replayable (see [results.md](results.md)).

## The gate, on this project

```
# the trade desk publishes
nba-trade-desk publish --runs runs/agents-v5-haiku runs/agents-v5-sonnet runs/agents-v5-opus --out datasets/trajectories-v5 --name trajectories-v5

# motherlode judges (blind packets under opaque keys; a subagent or a person records scores, or an API model does)
motherlode mask  --dataset datasets/trajectories-v5 --out work/masked
motherlode survey --masked work/masked --key <key> --rater claude-code:opus --scores '<json>'
motherlode survey --masked work/masked --model claude-opus-5

# a person grades a sample blind, every dimension on one page, the judge revealed after commit
motherlode handpick --dataset datasets/trajectories-v5 --masked work/masked --ids <pilot ids> --rater zachary --out work/grade.html

# validate per dimension, with ground truth as a third rater
motherlode prospect --dataset datasets/trajectories-v5 --human work/labels-zachary.jsonl --judge work/masked/judgments.jsonl --adjudication work/adjudicate.jsonl

# the graded dataset, back to the trade desk
motherlode paydirt --dataset datasets/trajectories-v5 --masked work/masked --human work/labels-zachary.jsonl --out datasets/trajectories-v5-graded

# the trade desk reads it back
nba-trade-desk results --items datasets/trajectories-v5 --graded datasets/trajectories-v5-graded
```

`work/` holds the masked items and the grading tools; it is scratch and ignored. Everything that matters ends up in `datasets/`.

## What each side owns

- **Trade desk:** the sandbox (league, rules, tools, tasks), the runner and session mode, the
  packet renderer, the ground-truth check, publishing, and the write-up.
- **Motherlode:** masking, the judge loop, the score parser, the grading tool, kappa and its
  intervals, adjudication, and the dataset format itself.

The two conventions they share are formats, not code: the rubric spec
(`rubric/RUBRIC.json`) and motherlode's dataset and label-row formats.

## Rubric hashes

Motherlode hashes the rubric text and its spec together. The judgments in the graded datasets
were made under rubric v1 text and migrated when the spec was added, so their hash is the
text-plus-spec hash `38daa3c66210`; each migrated row says so. Any human labels graded now share
that hash, which is what `prospect` checks.
