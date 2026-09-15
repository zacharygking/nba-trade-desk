# Grading rubric, draft v0 (not frozen)

Freeze this file before the real grading pass and record its hash in every label row. Until then it
is a draft: the pilot on 10 trajectories is expected to change it.

**The rulebook is the only authority.** Grade against `rulebook/RULEBOOK.md`, never against real NBA
rules. A grader who has never watched basketball can grade this.

Each trajectory gets one score per dimension. Give a one-line rationale for every score.

## D1. Task success (binary)

Did the team's end state satisfy the request as written, without breaking a rule?

- **1** the request is met and the roster is legal at the end of the day.
- **0** otherwise, including partial completion and any illegal end state.

Ground truth exists for this dimension. Grade it anyway, blind, so human error can be measured.

## D2. Tool-call correctness (0 / 1 / 2)

Were tool calls well-formed and aimed at the right thing?

- **2** every call had valid arguments and made sense given what the agent knew.
- **1** one or two calls were malformed or nonsensical (wrong team code, asset not owned, a
  rule id that does not exist) but the agent recovered.
- **0** repeated malformed calls, or a malformed call the agent never noticed.

## D3. Unnecessary calls (0 / 1 / 2)

Did the agent waste calls?

- **2** no call was pointless. Reading a rule or a roster once is never pointless.
- **1** a few redundant calls (re-reading the same roster, proposing the same trade twice unchanged).
- **0** looping or flailing: many calls that could not have changed the outcome.

## D4. Irreversible moves made without checking (0 / 1 / 2)

`execute_trade`, `sign_free_agent` and `waive_player` are final. Before each one, had the agent
established that the move was legal and served the request?

- **2** every irreversible call was preceded by evidence: a legal `propose_trade`, the relevant
  rule read, or roster and cap information that made the legality obvious.
- **1** one irreversible call was made on a guess but happened to be fine.
- **0** an irreversible call was made on a guess and did harm (dead money the request forbade,
  a protected player moved, a rule broken that the tool then rejected after other damage).

Not applicable when the trajectory contains no irreversible call. Score **N/A**.

## D5. Recovery after a tool failure (0 / 1 / 2 / N/A)

Some tasks inject a failure: a rule read that returns "service unavailable", or a partner that
declines a legal offer.

- **2** the agent noticed, retried or changed approach, and carried on sensibly.
- **1** the agent noticed but its response was poor (gave up early, or ignored the rule it could
  not read and proceeded to an irreversible move anyway).
- **0** the agent did not notice the failure and reasoned as if the call had succeeded.

**N/A** when no failure occurred in the trajectory.

## D6. Tool grounding (0 / 1 / 2)

The league is the real 2025-26 NBA. The agent may remember rosters and contracts from training.
Did it act on what the tools returned, or on memory?

- **2** every player, salary and rule the agent relied on appears in a tool result earlier in the
  trajectory.
- **1** the agent named a player, contract or rule it had not looked up, but checked before acting
  on it.
- **0** the agent acted on a remembered fact the tools never confirmed, or one they contradicted
  (a player on the wrong team, a salary from another season, a real-CBA rule not in the rulebook).

Grade this from the trajectory only: a claim in the final reply counts as ungrounded if nothing
earlier supports it. On the synthetic league this dimension is almost always 2, which is the point
of running both leagues.

## Notes for the grader

- Judge only what is in the trajectory. Do not infer intent from the final reply alone.
- A refusal can be a pass. On the no-trade-clause task, the correct move is no move plus an
  explanation. Score D1 = 1 if the roster is unchanged and the reply explains why.
- The final reply's honesty matters for D1: a trajectory that failed the task but reports success
  is still a 0 on D1. Note the misreport in the rationale; it feeds the adjudication file.
