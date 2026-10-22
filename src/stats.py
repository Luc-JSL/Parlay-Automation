#!/usr/bin/env python3
"""Check a prop against the player's real game logs (ESPN; needs the ESPN domains allowed).

Usage:
  python3 src/stats.py nba "Aaron Gordon" pra 22 More [--opp OKC] [--n 10]
  python3 src/stats.py nfl "TreVeyon Henderson" rush_rec_yds 30.5 More
  python3 src/stats.py --json nba "Joel Embiid" assists 3.5 More

Stats: NBA points rebounds assists threes blocks steals turnovers pra pr pa ra
       NFL pass_yds pass_tds completions pass_att rush_yds rush_att receptions rec_yds rush_rec_yds targets
       NHL sog points goals assists saves
Prints this season's games, the last --n regular/postseason games (this season first, then last season),
the hit rate on the chosen side, the average, and games against --opp. Preseason is ignored.
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

WEB = "https://site.web.api.espn.com/apis/common/v3"
PATHS = {"nba": "basketball/nba", "nfl": "football/nfl", "nhl": "hockey/nhl"}

NBA = {"points": ["points"], "rebounds": ["totalRebounds"], "assists": ["assists"], "threes": ["3PM"],
       "blocks": ["blocks"], "steals": ["steals"], "turnovers": ["turnovers"],
       "pra": ["points", "totalRebounds", "assists"], "pr": ["points", "totalRebounds"],
       "pa": ["points", "assists"], "ra": ["totalRebounds", "assists"]}
NFL = {"pass_yds": ["passingYards"], "pass_tds": ["passingTouchdowns"], "completions": ["completions"],
       "pass_att": ["passingAttempts"], "rush_yds": ["rushingYards"], "rush_att": ["rushingAttempts"],
       "receptions": ["receptions"], "rec_yds": ["receivingYards"], "targets": ["receivingTargets"],
       "rush_rec_yds": ["rushingYards", "receivingYards"]}
NHL = {"sog": ["shotsTotal"], "points": ["points"], "goals": ["goals"], "assists": ["assists"], "saves": ["saves"]}


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def find_player(name: str, league: str) -> str:
    q = urllib.parse.urlencode({"query": name, "type": "player", "limit": 10})
    for it in get(f"{WEB}/search?{q}").get("items", []):
        if it.get("league") == league:
            return it["id"]
    sys.exit(f"{name}: no {league.upper()} player found on ESPN")


def season_now(league: str) -> int:
    now = datetime.now(timezone.utc)
    if league == "nfl":
        return now.year if now.month >= 8 else now.year - 1
    return now.year + 1 if now.month >= 9 else now.year  # NBA/NHL seasons are named by their end year


def games(pid: str, league: str, season: int) -> list[dict]:
    d = get(f"{WEB}/sports/{PATHS[league]}/athletes/{pid}/gamelog?season={season}")
    names, events, out = d.get("names", []), d.get("events", {}), []
    for st in d.get("seasonTypes", []):
        if "Preseason" in st.get("displayName", ""):
            continue
        for cat in st.get("categories", []):
            for e in cat.get("events", []):
                row = dict(zip(names, e.get("stats", [])))
                made = row.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted", "")
                if "-" in made:
                    row["3PM"] = made.split("-")[0]
                if "completions/passingAttempts" in row:
                    c, a = row["completions/passingAttempts"].split("/")
                    row["completions"], row["passingAttempts"] = c, a
                ev = events.get(e.get("eventId"), {})
                out.append({"date": ev.get("gameDate", "")[:10], "opp": ev.get("opponent", {}).get("abbreviation", "?"),
                            "season": st.get("displayName", ""), "row": row})
    return sorted({g["date"] + g["opp"]: g for g in out}.values(), key=lambda g: g["date"], reverse=True)


def value(row: dict, keys: list[str]):
    try:
        return sum(float(row[k]) for k in keys)
    except (KeyError, ValueError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("league", choices=["nba", "nfl", "nhl"])
    ap.add_argument("player")
    ap.add_argument("stat")
    ap.add_argument("line", type=float)
    ap.add_argument("side", choices=["More", "Less"])
    ap.add_argument("--opp", help="opponent abbreviation, e.g. OKC")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    keys = {"nba": NBA, "nfl": NFL, "nhl": NHL}[a.league].get(a.stat)
    if not keys:
        sys.exit(f"Unknown stat {a.stat!r}")
    pid = find_player(a.player, a.league)
    now = season_now(a.league)
    cur = games(pid, a.league, now)
    prev = games(pid, a.league, now - 1)
    played = [dict(g, v=value(g["row"], keys)) for g in cur + prev]
    played = [g for g in played if g["v"] is not None]
    hit = (lambda v: v > a.line) if a.side == "More" else (lambda v: v < a.line)

    def summary(gs):
        if not gs:
            return {"n": 0}
        return {"n": len(gs), "hits": sum(hit(g["v"]) for g in gs), "avg": round(sum(g["v"] for g in gs) / len(gs), 1),
                "values": [g["v"] for g in gs]}

    res = {"player": a.player, "stat": a.stat, "line": a.line, "side": a.side,
           "this_season": summary([g for g in played if g in played[:len(cur)]]),
           "last_n": summary(played[:a.n]), "last_season": summary(played[len(cur):]),
           "vs_opp": summary([g for g in played if a.opp and g["opp"] == a.opp.upper()][:8])}
    if a.json:
        print(json.dumps(res))
        return
    print(f"{a.player} {a.side} {a.line:g} {a.stat}")
    for k, s in res.items():
        if isinstance(s, dict) and s.get("n"):
            vals = ", ".join(f"{v:g}" for v in s["values"][:12])
            print(f"  {k:12} {s['hits']}/{s['n']} hit  avg {s['avg']:g}   [{vals}]")
        elif isinstance(s, dict):
            print(f"  {k:12} no games")


if __name__ == "__main__":
    main()
