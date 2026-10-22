#!/usr/bin/env python3
"""Print current h2h / spread / total odds from The Odds API.

Usage: ODDS_API_KEY=... python3 src/fetch_odds.py <sport_key> [region]
Sport keys: basketball_nba, americanfootball_nfl, tennis_atp_*, tennis_wta_*
(list them with: python3 src/fetch_odds.py sports)
"""
import json
import os
import sys
import urllib.request

BASE = "https://api.the-odds-api.com/v4"


def get(path: str, **params) -> list:
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        sys.exit("Set ODDS_API_KEY (free key at https://the-odds-api.com)")
    query = "&".join(f"{k}={v}" for k, v in {"apiKey": key, **params}.items())
    with urllib.request.urlopen(f"{BASE}/{path}?{query}", timeout=20) as r:
        return json.load(r)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sport = sys.argv[1]
    if sport == "sports":
        for s in get("sports"):
            print(f"{s['key']:40} {s['title']}")
        return
    region = sys.argv[2] if len(sys.argv) > 2 else "us"
    events = get(f"sports/{sport}/odds", regions=region,
                 markets="h2h,spreads,totals", oddsFormat="american")
    for ev in events:
        print(f"\n{ev['away_team']} @ {ev['home_team']}  ({ev['commence_time']})")
        book = ev["bookmakers"][0] if ev["bookmakers"] else None
        if not book:
            continue
        for m in book["markets"]:
            outs = ", ".join(
                f"{o['name']} {o.get('point', '')} {o['price']:+d}".replace("  ", " ")
                for o in m["outcomes"])
            print(f"  [{book['title']}] {m['key']}: {outs}")


if __name__ == "__main__":
    main()
