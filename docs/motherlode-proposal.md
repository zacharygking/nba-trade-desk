# Proposal: multi-dimension rubrics and the division of labor, for motherlode v0.2.0

Written after adopting v0.1.0 (`rubric_hash`, `handpick`). Everything below is a proposal for the
generic library, not trade-desk code.

## 0. Division of labor: files, not imports

Motherlode ends at paydirt and never imports a downstream project. A downstream project never
imports motherlode either; it invokes motherlode's commands and reads the files they write. The
boundary is three file contracts:

1. **The project writes packets and truth.** A directory with one text file per item to grade,
   plus a labels file whose rater is `ground_truth` for any dimension a checker can settle.
2. **Motherlode reads text and rubric, writes scores.** `judge` takes the packets directory and a
   rubric spec, does its own blinding, and writes `judgments.jsonl`. `handpick` takes an items
   file and writes the grading tool; the person's labels come back as a file. `prospect` takes
   label files, including the judge's and ground truth's, and writes the validation report.
3. **The project reads scores and labels back** for its own tables.

Under this rule the trade desk keeps everything about basketball: the sandbox the agent acts in
(league, rules, tools, tasks), the runner that produces trajectories, the packet renderer, and
the ground-truth check exported as labels. The generic parts of `trade_desk/judge.py` today (the
anonymized pool, the score parser, the API judge loop, the judgments report) are on loan and
become motherlode's `judge` command rather than library functions the trade desk imports. The
trade desk's one import, `rubric_hash`, goes away too: motherlode writes the hash into every file
it produces.

Only one step needs a live environment: an agent acting in a sandbox. That stays in the project
and is not a `mine`. For `mine` itself to obey the same rule, it should take a prompts file and a
model name rather than load a teacher and a spec from the project's Python.

Two shared conventions remain, and they are schemas, not code: the rubric spec format and the
shapes of a packets directory and a label row. They are the right place for agreement to live,
because both sides can version them and test them with fixtures.

## 1. A rubric spec, so labels can have dimensions

One JSON object describes the rubric's structure. It is what `handpick` renders and what
`prospect` validates against, so the two can never disagree.

```json
{
  "rubric_hash": "b6d251d6a3fe",
  "dimensions": [
    {"id": "D1", "name": "Task success", "scale": [0, 1], "ordinal": true, "na_allowed": false},
    {"id": "D2", "name": "Tool-call correctness", "scale": [0, 1, 2], "ordinal": true, "na_allowed": false},
    {"id": "D3", "name": "Unnecessary calls", "scale": [0, 1, 2], "ordinal": true, "na_allowed": false},
    {"id": "D4", "name": "Irreversible moves without checking", "scale": [0, 1, 2], "ordinal": true, "na_allowed": true},
    {"id": "D5", "name": "Recovery after an injected failure", "scale": [0, 1, 2], "ordinal": true, "na_allowed": true},
    {"id": "D6", "name": "Tool grounding", "scale": [0, 1, 2], "ordinal": true, "na_allowed": false}
  ]
}
```

A single-label rubric is the one-dimension case: `{"id": "label", "scale": ["sound", "unsupported", ...], "ordinal": false}`.
So v0.1.0 files stay valid, and `--labels a b c` on the command line is sugar for that spec.

## 2. Label rows gain a `dimension` field

```json
{"item_id": "63ec71a0", "rater": "zachary", "dimension": "D4", "label": "2", "rubric_hash": "b6d251d6a3fe", "pass": "blind"}
```

- One row per item, rater, dimension and pass. A file with no `dimension` field is read as the
  single dimension `label`, so nothing existing breaks.
- `label` is a string; `NA` is a label value only where the spec allows it. The reader rejects an
  `NA` on a dimension that does not allow it, the same way the trade desk's parser does today.
- A `rationale` field is optional and never used by the statistics; it is what adjudication reads.

This is exactly what the trade desk's `judgments.jsonl` flattens to. Its current shape, for
reference, is one row per judged item:

```json
{"run": "runs/agents-v5-opus", "index": 3, "task_id": "...", "team": "MIA", "model": "claude-code:opus",
 "judge": "claude-code:opus", "rubric_hash": "3026736c9678", "tools_hash": "b2c067ca9f6c",
 "scores": {"D1": {"score": 1, "rationale": "..."}, "D4": {"score": "NA", "rationale": "..."}, ...}}
```

`trade_desk.judge labels` already flattens that to the row above per dimension. If v0.2.0 reads
the long form natively, the trade desk switches its judge output to it and drops the flattening.

## 3. `handpick` renders every dimension on one item

- One page per item: the text, the context fields, then one row of buttons per dimension with the
  scale and `NA` where allowed. Commit commits all dimensions at once; the hidden fields for that
  item (one per dimension, e.g. `judge_D1` ... `judge_D6`) reveal together; the revised pass is
  per dimension.
- Export writes one row per dimension, as in section 2.
- Everything else stays as v0.1.0: rubric hashed into every row, seeded shuffle, browser storage,
  no server.

## 4. `prospect` validates per dimension

For each dimension in the spec:

- **Ordinal scales get weighted kappa**, linear by default with a quadratic option, plus the
  unweighted kappa beside it. Nominal scales keep Cohen's kappa. Both with the paired bootstrap
  interval already in `stats`.
- **`NA` is excluded pairwise** and the count of excluded items is reported per dimension, so a
  dimension that is mostly `NA` (D5 here: 36 of 48 trajectories inject no failure) shows how thin
  its evidence is instead of hiding it.
- **Prevalence per dimension** and the raw-agreement field with its existing unfriendly name.
- **Krippendorff's alpha at the interval level** for ordinal dimensions when there are two or more
  humans, nominal otherwise.
- A one-table summary across dimensions, since six separate reports is what nobody reads.
- The adjudication template gains a `dimension` column.

## 5. Ground truth as a rater

Some items have a checkable answer for one dimension (here, D1 has an end-state check). Proposal:
a label file whose `rater` is `ground_truth` is treated as any other rater, and `prospect`
reports every rater's agreement with it where it exists. That gives judge-versus-truth and
human-versus-truth per dimension for free, with no special casing, and it generalizes to any
task where a checker settles one axis and humans grade the rest.

## 6. Two generic pieces the trade desk would hand over

- **The anonymized pool.** `pool(items, out_dir)` writes each item's text under a random key and
  a `manifest.json` mapping key to the caller's identity; `resolve(key)` reads it back. The trade
  desk uses this so a grader cannot tell which model produced a packet from the path. Rendering
  the item text stays in the project.
- **The score parser.** `parse_scores(text, spec)` finds the JSON object in a model's reply,
  checks every dimension is present, in range, and `NA` only where allowed, and returns the row
  set from section 2. It is the same function whether the judge is an API call or a subagent.

## Order of value to the trade desk

Section 2 and 4 first (the trade desk can then run `prospect` per dimension on its existing
judgments the day they land), then 3, then 5 and 6.
