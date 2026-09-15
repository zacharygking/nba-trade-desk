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

These runs used tasks v2 and the eight-tool set. What they exposed was fixed afterward (see
below); the trajectories keep their v2 label and their tool set is recorded. Tier comparisons on
the current tool set need a rerun.

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

Two task flaws surfaced first:

- The dead-money trap had flagged a top-six player as non-guaranteed. It now flags deals outside
  the protected group.
- The forward task landed on a roster that already had four qualifying forwards. It now lands on a
  team that has none.

Mining the trajectories then showed that most of the noise was the interface, not the agents:

- The call cap was advisory; 10 of 24 runs exceeded it, one reaching 77 calls. Session mode now
  enforces it and records the overrun.
- `read_rule` with no id returned titles only, so agents read the ten rules one call at a time
  (166 of 616 calls). It now returns the whole rulebook.
- Agents scanned cap sheets team by team to find partners (143 calls). `view_league` returns every
  team's books in one call.
- One agent sent a salary in dollars and got a garbled apron violation. Dollar amounts are now
  refused with the conversion spelled out.
- Protections were by season rating, so a star with zero games could be traded as a bench piece.
  Protections are now by value, a games-weighted blend of season and career rating, and every
  request says so.
- Filling every roster to 15 made one-for-nothing salary dumps illegal league-wide. Thin rosters
  now fill to 14 unless the team really had 15 under contract.

Discipline was good throughout: no agent executed a trade it had not first proposed and had
accepted, and all three tiers noticed the rulebook outage and worked around it.

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
