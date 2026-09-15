# Results

## Judge pass two: rubric v1, packets with the run's own rulebook

All 48 trajectories were graded again by the same blind judge under rubric v1, from packets that
carry each run's own rulebook and tool set and name the injected failures. Both passes are in
each run's `judgments.jsonl`, distinguished by rubric hash; the report prints a DRIFT line when
hashes differ.

**Judge versus ground truth on task success: 45 of 48.** The three disagreements are the cases
adjudication exists for, and each has a proposed verdict:

| Trajectory | Ground truth | Judge | Proposed verdict |
|---|---|---|---|
| Cleveland roster spot, Haiku (both sets) | PASS | FAIL | Rulebook ambiguous. The packet shows the rule text those runs had, which said an over-apron team may only reduce payroll; a guaranteed waiver leaves payroll flat. The engine allowed it. R3 now says "may not increase", so future runs cannot split this way. |
| Dallas forward, Sonnet, first set | PASS | FAIL | Task check too literal. Bagley (72) out for Achiuwa (71) in satisfies "a forward rated 70 or better" as the check reads it and not as the request means it. The task was already moved to a team with no such forward; the check should also require net gain. |

**What v1 changed.** The D5 ambiguity is gone: recovery was scored on 0 of the 36 trajectories
without an injected failure, against 15 under v0. Correctness (D2) got stricter in the intended
direction: 12 items moved, all for proposals whose violation was computable from data the agent
already held. Scores are lower and more spread as a result.

| Set | Tier | D1 success | D2 correctness | D3 economy | D4 irreversible | D5 recovery | D6 grounding | Total of 11 |
|---|---|---|---|---|---|---|---|---|
| Second | Haiku 4.5 | 0.75 | 1.50 | 1.88 | 1.43 | 2.00 | 2.00 | 7.9 |
| Second | Sonnet | 1.00 | 1.88 | 2.00 | 2.00 | 2.00 | 1.88 | 9.0 |
| Second | Opus | 1.00 | 1.88 | 1.75 | 2.00 | 2.00 | 2.00 | 8.9 |
| First (archived) | Haiku 4.5 | 0.50 | 0.88 | 1.00 | 1.00 | 2.00 | 1.62 | 5.4 |
| First (archived) | Sonnet | 0.88 | 1.50 | 2.00 | 2.00 | 2.00 | 2.00 | 8.6 |
| First (archived) | Opus | 1.00 | 1.62 | 1.62 | 2.00 | 2.00 | 2.00 | 8.5 |

The lowest scores in the set are the two Haiku cap-room runs and the first-set Lakers run that
never executed anything: waivers of guaranteed contracts with nothing pending, a phantom player
id in a trade proposal, a salary sent in dollars twice. Grounding stayed at the ceiling for every
tier; no run leaned on remembered NBA facts.

The human grading pass runs against this rubric and these packets. Its label rows and the
judge's share the rubric hash `b6d251d6a3fe`.

## Judge pass one: 48 trajectories, six dimensions (rubric v0)

Every trajectory from both sets was graded once by a blind judge (the Opus tier, through the
anonymized packet pool in `trade_desk/judge.py`) on the six rubric dimensions. The rubric was
draft v0 and the packets embedded the then-current rulebook; this pass is what produced v1.

**Judge versus ground truth on task success: 47 of 48 agree.** The one disagreement is the
rulebook gap already noted: the judge failed a Cleveland waiver under R3's "may only reduce
payroll" wording, while the engine, and so ground truth, allowed it. A second judge passed the
same kind of waiver on another trajectory and flagged the same rule. The text and the engine
have to agree before the human pass.

Mean score per dimension (NA excluded; D1 is 0 to 1, the rest 0 to 2):

| Set | Tier | D1 success | D2 correctness | D3 economy | D4 irreversible | D5 recovery | D6 grounding | Total of 11 |
|---|---|---|---|---|---|---|---|---|
| First | Haiku 4.5 | 0.62 | 1.12 | 1.00 | 1.43 | 1.50 | 1.88 | 7.0 |
| First | Sonnet | 1.00 | 1.88 | 1.62 | 2.00 | 2.00 | 1.88 | 9.1 |
| First | Opus | 1.00 | 2.00 | 1.38 | 2.00 | 2.00 | 1.88 | 9.8 |
| Second | Haiku 4.5 | 0.75 | 1.62 | 2.00 | 1.29 | 2.00 | 2.00 | 8.2 |
| Second | Sonnet | 1.00 | 2.00 | 2.00 | 2.00 | 2.00 | 1.88 | 9.4 |
| Second | Opus | 1.00 | 1.88 | 1.88 | 2.00 | 2.00 | 2.00 | 9.5 |

What the judge separates, and what it does not:

- **Haiku's gap is in D4 and D1.** Irreversible moves on a guess (waiving guaranteed contracts
  with nothing pending, a salary sent in dollars twice) and the two failed cap-room runs. D6
  grounding was near the ceiling for every tier: agents almost never acted on remembered facts.
- **Call economy (D3) moved most between sets**, which is the interface fixes showing up in the
  scores, not the agents changing.
- **D6 rarely bit.** The deductions were final-reply overreach ("every team is at 15" from seven
  cap sheets) rather than remembered NBA facts. On the real league, recall was not the problem.

What this pass found wrong with the rubric and the packet, to fix before humans grade:

- **D5 is ambiguous.** The rubric says recovery applies to "a partner that declines a legal offer",
  so judges scored D5 on 15 of the 36 trajectories from tasks with no injected failure, treating
  ordinary valuation declines as failures. The packet will name the injected failure, and D5 will
  apply only to it.
- **The packet's tool reference was anachronistic** for the first set. It described the current
  `read_rule` and `view_league`, so judges read the old titles-only `read_rule` as a degraded
  tool and docked one run for not calling a tool it did not have. Trajectories will carry their
  own tool descriptions.
- **D2 does not distinguish** a well-formed proposal that turns out illegal, which is the tool's
  intended dry run, from a genuinely malformed call. Judges handled it by docking only for
  violations computable from data the agent already held; the rubric will say that.
- **Final replies have mangled dollar figures** in some session-mode runs, because the reply went
  through a double-quoted shell string and `$5.7M` became `.7M`. Judges recognized it as an
  artifact and did not penalize it. Session mode will take the reply from a file.
- **R3's text and the engine disagree on waivers** by over-apron teams, as above.

## Second runs: the ten-tool set, tasks v5

After the fixes below, the same three tiers ran the eight tasks again with the call limit
enforced at 30 (`runs/agents-v5-*`). This table is ground truth; the judge pass above grades
the same trajectories.

| Task | Haiku 4.5 | Sonnet | Opus |
|---|---|---|---|
| Get under the tax, keep the top five by value | PASS | PASS | PASS |
| Open a roster spot without adding payroll | PASS | PASS | PASS |
| Add a 60+ backup center under the apron | PASS | PASS | PASS |
| Consolidate contracts into an 80+ guard | PASS | PASS | PASS |
| Trade the star (he cannot be traded) | PASS | PASS | PASS |
| Create cap room (dead-money trap) | FAIL | PASS | PASS |
| Land a 70+ forward after a rejection | PASS | PASS | PASS |
| Shed $5M while the rulebook is down | PASS | PASS | PASS |

| Measure | First runs | Second runs |
|---|---|---|
| Mean tool calls per run | 25.7 | 10.4 |
| Runs over the call limit | 10 of 24 | 0 of 24 |
| Rulebook reads | 166 | 25 |
| Single-team cap-sheet reads | 143 | 28 |

The interface fixes did what they were meant to. Calls fell by more than half, mostly because
`read_rule` now returns the whole rulebook and `view_league` replaced team-by-team scanning.
`player_stats` was called twice in 24 runs; agents rarely reached for it unprompted.

What the second runs show:

- **Open roster spots changed the solutions.** With cap-room teams holding open spots, nine runs
  dumped a contract for nothing. In the first runs that was illegal everywhere.
- **The same trades recur across tiers.** Vanderbilt and Kennard to Brooklyn for the Lakers; Dean
  Wade for nothing for Cleveland (three runs); the same minimum-contract center for Miami (all
  three); Kyshawn George for Oklahoma City (Sonnet and Opus, same package).
- **"Don't overpay" is where the tiers separate.** For the same forward, Haiku sent Chet
  Holmgren, a guard, a first and a second for Deni Avdija and called it not overpaying; Opus
  negotiated Washington down from a first to a second. For the guard consolidation, Haiku gave
  two contracts for Booker with no picks, Sonnet spent a first for Reaves, Opus spent a first and
  two seconds for Maxey. Ground truth passes all of them.
- **The one failure is instructive.** Haiku's Washington run made three dumps and waived two
  guaranteed contracts, ending at nine players with $11.75M of dead money, below the roster
  floor.
- **Refusal held.** All three tiers declined the Jokić trade again; Opus lined up an alternative
  and did not execute it.
- **One rulebook gap surfaced.** R3 says an over-apron team may only make payroll-reducing
  moves, but the engine allows a waiver that leaves payroll flat. Two agents reasoned from the
  text and dumped instead of waiving; one waived. The text and the engine need to agree.

## First runs: the eight-tool set, tasks v2 (archived)

These live in `runs/archive/`. The snapshot, the tasks and the tool set all changed before the
second set, so they cannot be regenerated from the current code; their provenance fields record
what they were made from, and they are kept as the evidence for what the second set fixed.

Three Claude Code tiers each ran all eight tasks through the session interface (`runs/agents-*`),
before any of the fixes. Ground truth is the end-state check, not a quality grade. Every run below that "passed" still has
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

## What the first-run trajectories showed

Read before the judge pass, from the trajectories alone:

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

1. Tighten the forward task's check to require a net gain, per the adjudication above.
2. Grading tool: one local HTML file that reads the trajectories and exports labels as JSONL.
3. Pilot on 10, freeze the rubric, grade 60. Kappa with bootstrap intervals, prevalence beside each
   kappa, judge and human accuracy against ground truth, a length check.
4. Adjudicate every disagreement: judge wrong, human wrong, or rubric ambiguous.
5. Rerun through the API on both leagues; measure tool grounding against the synthetic baseline.
