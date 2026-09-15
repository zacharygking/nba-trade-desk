"""Pull the 2025-26 league from ESPN's public API: who was under contract with whom, for what,
and what they produced. No key. Writes data/espn_2025-26.json with provenance.

  .venv/bin/python data/fetch_espn.py

Method
- Roster lists come from the current (2026-27 preseason) team rosters. ESPN does not serve past
  rosters, so 2025-26 team membership is taken from each player's 2025-26 contract record, which
  names the team that paid it. Players who left the league after 2025-26 are therefore missing.
  Players on a current roster with no 2025-26 contract (2026 draftees, camp invitees, summer
  signings) are kept in an "unsigned" list with their 2026-27 salary where ESPN has one. The
  league uses them to fill thin 2025-26 rosters to 15, flagging the salary as inferred, and loads
  the rest as free agents asking the minimum.
- Salary is the 2025-26 contract salary. Fields kept from the contract record: years remaining,
  minimum-salary exception, trade restriction, option type.
- Stats are 2025-26 regular season per-game averages plus PER.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

UA = {"User-Agent": "python-urllib/3.12"}   # ESPN's edge 403s spoofed browser UAs from scripts
SITE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
CORE = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
SEASON = 2026            # ESPN's year for 2025-26
OUT = Path(__file__).with_name("espn_2025-26.json")

CODE_FIX = {"GS": "GSW", "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}
STAT_KEYS = {"gamesPlayed", "avgMinutes", "avgPoints", "avgRebounds", "avgAssists", "PER",
             "avgPlusMinus", "fieldGoalPct"}


def get(url: str, tries: int = 3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                print(f"  ! {url} -> {e!r}", file=sys.stderr)
                return None
            time.sleep(1.5 * (i + 1))


def stats_for(athlete_id: str) -> dict:
    d = get(f"{CORE}/seasons/{SEASON}/types/2/athletes/{athlete_id}/statistics")
    out: dict = {}
    if not d:
        return out

    def walk(o):
        if isinstance(o, dict):
            if o.get("name") in STAT_KEYS and isinstance(o.get("value"), (int, float)):
                out[o["name"]] = o["value"]
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d)
    return out


def main() -> None:
    teams_raw = get(f"{SITE}/teams")["sports"][0]["leagues"][0]["teams"]
    id_to_code, espn_code = {}, {}
    for t in teams_raw:
        raw = t["team"]["abbreviation"]
        id_to_code[t["team"]["id"]] = CODE_FIX.get(raw, raw)
        espn_code[CODE_FIX.get(raw, raw)] = raw
    print(f"{len(id_to_code)} teams")

    seen: dict[str, dict] = {}
    for tid, code in sorted(id_to_code.items(), key=lambda kv: kv[1]):
        roster = get(f"{SITE}/teams/{espn_code[code].lower()}/roster")
        if not roster:
            continue
        for a in roster["athletes"]:
            if a["id"] in seen:
                continue
            seen[a["id"]] = {
                "espn_id": a["id"], "name": a["displayName"], "age": a.get("age"),
                "pos": a["position"]["abbreviation"],
                "experience": (a.get("experience") or {}).get("years"),
                "current_team": code,
                "contracts": {str(c["season"]["year"]): c["salary"] for c in (a.get("contracts") or [])},
            }
        print(f"  {code}: {len(roster['athletes'])} rostered, {len(seen)} unique so far")
        time.sleep(0.1)

    players = []
    unsigned = []
    for i, (aid, p) in enumerate(seen.items(), 1):
        sal = p["contracts"].get(str(SEASON))
        if not sal:
            unsigned.append({"espn_id": aid, "name": p["name"], "age": p["age"], "pos": p["pos"],
                             "experience": p["experience"], "current_team": p["current_team"],
                             "salary_2026_27": p["contracts"].get(str(SEASON + 1)),
                             "stats_2025_26": stats_for(aid)})
            continue
        c = get(f"{CORE}/athletes/{aid}/contracts/{SEASON}?lang=en&region=us") or {}
        team_ref = (c.get("team") or {}).get("$ref", "")
        m = re.search(r"/teams/(\d+)", team_ref)
        team_2526 = id_to_code.get(m.group(1)) if m else None
        st = stats_for(aid)
        players.append({
            "espn_id": aid, "name": p["name"], "age": p["age"], "pos": p["pos"],
            "experience": p["experience"], "team": team_2526 or p["current_team"],
            "team_source": "contract" if team_2526 else "current_roster",
            "salary_2025_26": sal,
            "years_remaining": c.get("yearsRemaining"),
            "min_exception": c.get("minimumSalaryException"),
            "trade_restriction": c.get("tradeRestriction"),
            "option_type": c.get("optionType"),
            "stats_2025_26": st,
        })
        if i % 50 == 0:
            print(f"  {i}/{len(seen)} athletes processed")
        time.sleep(0.05)

    snapshot = {
        "provenance": {
            "source": "ESPN public site and core APIs (unofficial, no key)",
            "endpoints": [f"{SITE}/teams", f"{SITE}/teams/{{code}}/roster",
                          f"{CORE}/athletes/{{id}}/contracts/{SEASON}",
                          f"{CORE}/seasons/{SEASON}/types/2/athletes/{{id}}/statistics"],
            "pulled_on": date.today().isoformat(),
            "season": "2025-26",
            "method": __doc__.strip(),
            "unsigned_count": len(unsigned),
        },
        "players": players,
        "unsigned": unsigned,
    }
    OUT.write_text(json.dumps(snapshot, indent=1))
    by_team: dict[str, list] = {}
    for p in players:
        by_team.setdefault(p["team"], []).append(p)
    print(f"\nwrote {OUT} with {len(players)} players under contract and {len(unsigned)} unsigned")
    for t in sorted(by_team):
        ps = by_team[t]
        print(f"  {t} n={len(ps):2d} payroll={sum(p['salary_2025_26'] for p in ps)/1e6:6.1f}M "
              f"restricted={sum(1 for p in ps if p['trade_restriction'])} "
              f"no_stats={sum(1 for p in ps if not p['stats_2025_26'])}")


if __name__ == "__main__":
    main()
