# Human grading

## The pilot

`pilot.json` lists ten trajectories from the second run set, chosen with a recorded seed: every
ground-truth failure plus passes spread across tasks and tiers. Grade them blind, one dimension
at a time, in the six tools under `tools/` (rebuilt by the commands below, so the HTML is not
tracked). The judge's score and rationale for that dimension appear only after you commit your
blind label; a revised label, if you change your mind after seeing it, is stored separately.

```
open grading/tools/grade-D1.html      # then D2 ... D6
```

Export from each tool when you finish it. The download is named `labels-zachary-<rubric hash>.jsonl`;
save it here as `labels/labels-zachary-D1.jsonl` and so on. Item ids carry the dimension suffix, so
files cannot be mixed up.

Then, per dimension:

```
.venv/bin/python -m trade_desk.judge labels --dimension D1     # writes labels/judge-D1.jsonl
.venv/bin/motherlode prospect --human grading/labels/labels-zachary-D1.jsonl --judge grading/labels/judge-D1.jsonl --adjudication grading/labels/adjudicate-D1.jsonl
```

The pilot's purpose is to fix the rubric: every disagreement with the judge is a question about
the rubric first and the judge second. After the pilot, the rubric freezes and the real pass grades
60 trajectories.

## Rebuilding the tools

```
KEYS=$(.venv/bin/python -c "import json; print(' '.join(r['key'] for r in json.load(open('grading/pilot.json'))['items']))")
.venv/bin/python -m trade_desk.judge items --dimension D1 --keys $KEYS --out grading/tools/items-D1.jsonl
.venv/bin/motherlode handpick --items grading/tools/items-D1.jsonl --rubric rubric/RUBRIC.md --out grading/tools/grade-D1.html \
  --labels 0 1 --context packet --hidden judge --rater zachary --seed 11 --title "Trade desk pilot D1: Task success"
```

`labels/` is tracked; `tools/` is generated and ignored. Every row's `item_id` is a deterministic
pool key plus the dimension, so rows join back to their run and index however many times the pool
is rebuilt.
