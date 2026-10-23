#!/usr/bin/env python3
"""NBA game logs from ESPN's public site API (no key).

  python3 src/espn_logs.py "Jalen Brunson" 2026 2027   # season = year it ends (2027 = 2026-27)
"""
import json
import sys
import urllib.parse
import urllib.request

SITE = "https://site.web.api.espn.com/apis/common/v3"


def get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def player_id(name: str) -> str:
    items = get(f"{SITE}/search?limit=5&type=player&query={urllib.parse.quote(name)}").get("items", [])
    for it in items:
        if it.get("league") == "nba" or "/nba/" in json.dumps(it.get("link", "")):
            return it["id"]
    if not items:
        raise LookupError(f"no ESPN player found for {name!r}")
    return items[0]["id"]


def game_log(name: str, season: int) -> list[dict]:
    """Regular-season and playoff games, oldest first: {date, opp, home, min, pts, reb, ast, fg3}."""
    d = get(f"{SITE}/sports/basketball/nba/athletes/{player_id(name)}/gamelog?season={season}")
    names, events, rows = d.get("names", []), d.get("events", {}), []
    for st in d.get("seasonTypes", []):
        if "Preseason" in st.get("displayName", ""):
            continue
        for cat in st.get("categories", []):
            for e in cat.get("events", []):
                g, s = events.get(e["eventId"], {}), dict(zip(names, e["stats"]))
                rows.append({
                    "date": g.get("gameDate", "")[:10], "opp": g.get("opponent", {}).get("abbreviation", ""),
                    "home": g.get("atVs") == "vs", "min": float(s.get("minutes") or 0),
                    "pts": float(s.get("points") or 0), "reb": float(s.get("totalRebounds") or 0),
                    "ast": float(s.get("assists") or 0),
                    "fg3": float((s.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted") or "0-0").split("-")[0]),
                })
    return sorted(rows, key=lambda r: r["date"])


if __name__ == "__main__":
    for season in sys.argv[2:]:
        for g in game_log(sys.argv[1], int(season)):
            print(g)
