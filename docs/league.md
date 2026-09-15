# The league

Players, teams, positions, salaries and contract flags are the real 2025-26 NBA, pulled from
ESPN's public API on the date recorded in `data/espn_2025-26.json`. No key, no scraping of HTML.

| What | Where it comes from |
|---|---|
| Who is on which team | Each player's 2025-26 contract record names the team that paid it |
| Salary | The 2025-26 contract salary |
| Years remaining, trade restriction, minimum-exception flag | The contract record |
| Position (G, F or C, as ESPN lists them), age, experience | The roster record |
| Cap $154.6M, tax $187.9M, apron $195.9M | The league's published 2025-26 figures; the first apron is the only hard ceiling here |
| Per-game averages for every season and for the career | The athlete stats page: games, starts, minutes, points, rebounds, assists, steals, blocks, turnovers, shooting percentages |
| **Rating** and **career rating**, the derived numbers | One formula over per-game averages, applied to the 2025-26 row and to the career row: `40 + 0.55 × minutes + 0.75 × points + 0.5 × rebounds + 0.9 × assists + 0.15 × (FG% − 45)`, clamped to 40–95. A row with fewer than 10 games rates 45, so a star who missed the season rates 45 for the season and keeps his career rating. |

## Simplifications

All deliberate:

- Rosters are capped at 15 by salary.
- Every contract is treated as guaranteed unless a task says otherwise.
- ESPN's trade-restriction flag is kept in the snapshot but not applied. It marks about 40% of
  contracts and its meaning is undocumented.
- Draft picks are each team's own firsts and seconds for the next two drafts.
- The rulebook is ten rules, not the collective bargaining agreement. See
  [`rulebook/RULEBOOK.md`](../rulebook/RULEBOOK.md). **The rulebook is the only authority in this
  league.** Real NBA rules do not apply, and that is stated to the agent and the grader.
- Five real teams sat above the first apron in 2025-26, so the rulebook lets an over-apron team
  make payroll-reducing moves and nothing else, which is roughly how the real apron behaves.

## Coverage, and the one inference that closes the gap

ESPN only serves current rosters, so 2025-26 teams are rebuilt from contract records, and players
who left the league over the summer are missing. Each thin team is filled to 14, or to 15 if it had 15 under contract, with its own
current players who have no 2025-26 contract (2026 draftees, camp invitees, summer signings),
priced from their 2026-27 contract when ESPN has one and at the minimum otherwise. The league
therefore keeps some open roster spots, as the real one does. Every such
player carries `salary_source: inferred:...` in tool results, so the agent and the grader can see
which numbers are real. The remaining unsigned players are free agents asking the minimum.

| Measure | Count |
|---|---|
| Players under a 2025-26 contract | 406 |
| Rostered after filling to 15 | 450 |
| Roster slots filled by inference | 46, of which 45 at the minimum |
| Free agents | 107 |

`data/fetch_espn.py` documents the method and re-pulls in about five minutes.

## The synthetic league

A league of invented players and contracts is kept alongside (`--league synthetic`). An agent
cannot know those rosters from memory, which makes the pair a test of tool grounding versus
recall. Same engine, same tasks, same rulebook.
