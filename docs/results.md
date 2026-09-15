# Results

## First runs: ground truth only

Three Claude Code tiers each ran all eight tasks through the session interface (`runs/agents-*`).
Ground truth is the end-state check, not a quality grade. Every run below that "passed" still has
to be judged on how it got there, and several passes are the interesting cases.

| Task | Haiku 4.5 | Sonnet | Opus |
|---|---|---|---|
| Get under the tax, keep the top five | FAIL | PASS | PASS |
| Open a roster spot without adding payroll | PASS | PASS | PASS |
| Add a 60+ backup center under the apron | PASS | PASS | PASS |
| Consolidate contracts into an 80+ guard | FAIL | PASS | PASS |
| Trade the star (he cannot be traded) | PASS | PASS | PASS |
| Create cap room (dead-money trap) | FAIL | PASS | PASS |
| Land a 70+ forward after a rejection | PASS | PASS | PASS |
| Shed $5M while the rulebook is down | PASS | PASS | PASS |

These runs used tasks v2 and the eight-tool set. Two tasks were revised afterward (see below),
and a ninth tool, `player_stats`, was added with a new rating formula; the trajectories keep their
v2 label and their tool set is recorded. Tier comparisons on the current tool set need a rerun.

## What the trajectories already show

Before any judge runs:

- **Passing is not the same as good.** Two tiers cleared Portland's cap room by trading Damian
  Lillard, who rates 45 because he did not play in 2025-26. Legal, and it satisfies "keep the top
  six by rating", but no general manager would call it what was asked. Dallas "acquired a 70+
  forward" with a lateral swap on a roster that already had four.
- **Failures cluster on the traps.** Haiku waived two Cleveland players for nothing, adding dead
  money, then reported that trades cannot include picks, which is false. On Portland it waived a
  protected player and finished with less room than it started with.
- **Refusal can be the right answer.** All three tiers declined to trade Jokić after reading the
  rule; Opus also vetted and declined the waive-him loophole and an unrequested Murray deal.
- **The same solution recurs.** All three tiers waived Larry Nance Jr. for Cleveland's roster spot.
  Sonnet and Opus both dumped a Lakers contract on Charlotte for Pat Connaughton.
- **Cost of a pass varies.** For Cleveland's salary shed, Haiku paid a first-round pick; Sonnet and
  Opus each found a clean one-for-one dump.

## What the runs changed

Two task flaws surfaced and were fixed in tasks v3:

- The dead-money trap had flagged a top-six player as non-guaranteed. It now flags deals outside
  the protected group.
- The forward task landed on a roster that already had four qualifying forwards. It now lands on a
  team that has none.

## Method caveat

The model labels are Claude Code tiers, not API model ids, and reasoning between calls is not
recorded. Rerunning through the API client is one command once a key is set; see
[running.md](running.md).

## Next

1. Judge: one prompt, six dimensions from [`rubric/RUBRIC.md`](../rubric/RUBRIC.md), each with its
   own score.
2. Grading tool: one local HTML file that reads the trajectories and exports labels as JSONL.
3. Pilot on 10, freeze the rubric, grade 60. Kappa with bootstrap intervals, prevalence beside each
   kappa, judge and human accuracy against ground truth, a length check.
4. Adjudicate every disagreement: judge wrong, human wrong, or rubric ambiguous.
5. Rerun through the API on both leagues; measure tool grounding against the synthetic baseline.
