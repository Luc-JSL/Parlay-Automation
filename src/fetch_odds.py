#!/usr/bin/env python3
"""Odds from The Odds API: game lines, upcoming events, and a PrizePicks edge scanner.

Usage (needs ODDS_API_KEY; free key at https://the-odds-api.com):
  python3 src/fetch_odds.py sports                    # list sport keys (free)
  python3 src/fetch_odds.py events <sport>            # upcoming events + ids (free)
  python3 src/fetch_odds.py <sport> [region]          # h2h / spread / total, games not started yet
  python3 src/fetch_odds.py edges <sport> [--hours 36] [--markets m1,m2] [--min 0.56] [--json out.json]

Sport keys: basketball_nba, americanfootball_nfl, tennis_atp_*, tennis_wta_*

`edges` pulls player props from US sportsbooks and from PrizePicks (region us_dfs) for every
event starting in the next --hours, removes each book's margin, converts the sportsbook fair
probability to the PrizePicks line, and lists the PrizePicks picks with the highest fair hit rate.
Cost: (number of markets) x 2 regions per event. Only games that have not started are included.
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from statistics import NormalDist, median

BASE = "https://api.the-odds-api.com/v4"
DFS_BOOKS = {"prizepicks", "underdog", "pick6", "betr_us_dfs", "dabble_au"}

DEFAULT_MARKETS = {
    "basketball_nba": ["player_points", "player_rebounds", "player_assists", "player_threes",
                       "player_points_rebounds_assists"],
    "americanfootball_nfl": ["player_pass_yds", "player_pass_tds", "player_rush_yds",
                             "player_reception_yds", "player_receptions"],
}

# Rough standard deviation of each stat, sd = a + b * line. Used only to move a sportsbook
# fair probability from the book's line to a nearby PrizePicks line.
SD = {
    "player_points": (2.5, 0.18), "player_rebounds": (1.2, 0.20), "player_assists": (1.0, 0.20),
    "player_threes": (0.8, 0.25), "player_points_rebounds_assists": (3.5, 0.15),
    "player_pass_yds": (20, 0.15), "player_pass_tds": (0.4, 0.40), "player_rush_yds": (8, 0.30),
    "player_reception_yds": (8, 0.35), "player_receptions": (0.8, 0.30),
}

quota = {}


def get(path: str, **params):
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        sys.exit("Set ODDS_API_KEY (free key at https://the-odds-api.com)")
    query = "&".join(f"{k}={v}" for k, v in {"apiKey": key, **params}.items())
    with urllib.request.urlopen(f"{BASE}/{path}?{query}", timeout=30) as r:
        quota["remaining"] = r.headers.get("x-requests-remaining")
        return json.load(r)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def upcoming(events: list, hours: float | None = None) -> list:
    """Drop events that have already started (and, with hours, ones too far out)."""
    now = datetime.now(timezone.utc)
    out = []
    for ev in events:
        start = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        if start > now and (hours is None or start <= now + timedelta(hours=hours)):
            out.append(ev)
    return out


def to_prob(american: float) -> float:
    return 100 / (american + 100) if american > 0 else -american / (-american + 100)


def over_prob_at(p_over: float, book_line: float, line: float, market: str) -> tuple[float, float]:
    """Fair P(over), P(under) at `line`, given fair P(over) at `book_line`. Normal model."""
    a, b = SD.get(market, (1.0, 0.25))
    sd = a + b * max(book_line, line)
    n = NormalDist()
    p_over = min(max(p_over, 0.01), 0.99)
    mu = book_line - sd * n.inv_cdf(1 - p_over)
    dist = NormalDist(mu, sd)
    if float(line).is_integer():  # whole-number line: a push is possible
        return 1 - dist.cdf(line + 0.5), dist.cdf(line - 0.5)
    return 1 - dist.cdf(line), dist.cdf(line)


def scan_event(sport: str, ev: dict, markets: list[str]) -> list[dict]:
    data = get(f"sports/{sport}/events/{ev['id']}/odds", regions="us,us_dfs",
               markets=",".join(markets), oddsFormat="american")
    pp, books = {}, {}
    for bk in data.get("bookmakers", []):
        for m in bk["markets"]:
            pairs = {}
            for o in m["outcomes"]:
                if "point" in o and o["name"] in ("Over", "Under"):
                    pairs.setdefault((o["description"], o["point"]), {})[o["name"]] = o["price"]
            for (player, point), sides in pairs.items():
                k = (player, m["key"])
                if bk["key"] == "prizepicks":
                    pp[k] = point
                elif bk["key"] not in DFS_BOOKS and len(sides) == 2:
                    po, pu = to_prob(sides["Over"]), to_prob(sides["Under"])
                    books.setdefault(k, []).append((bk["key"], point, po / (po + pu)))
    rows = []
    for (player, market), line in pp.items():
        quotes = books.get((player, market))
        if not quotes:
            continue
        overs, unders = zip(*(over_prob_at(p, pt, line, market) for _, pt, p in quotes))
        o, u = median(overs), median(unders)
        side, prob = ("More", o / (o + u)) if o >= u else ("Less", u / (o + u))
        rows.append({
            "event": f"{ev['away_team']} @ {ev['home_team']}", "start": ev["commence_time"],
            "player": player, "market": market.removeprefix("player_"), "pp_line": line,
            "book_lines": sorted({pt for _, pt, _ in quotes}), "books": len(quotes),
            "pick": side, "fair_prob": round(prob, 3), "push_prob": round(max(0.0, 1 - o - u), 3),
        })
    return rows


def edges(a) -> None:
    markets = a.markets.split(",") if a.markets else DEFAULT_MARKETS.get(a.sport)
    if not markets:
        sys.exit(f"No default prop markets for {a.sport}; pass --markets")
    events = upcoming(get(f"sports/{a.sport}/events"), a.hours)
    if not events:
        print(f"No {a.sport} events starting in the next {a.hours}h.")
        return
    rows = []
    for ev in events:
        rows += scan_event(a.sport, ev, markets)
    rows.sort(key=lambda r: -r["fair_prob"])
    print(f"{len(events)} events, {len(rows)} PrizePicks props matched to sportsbooks "
          f"(quota left: {quota.get('remaining')})\n")
    print(f"{'fair':>6} {'pick':5} {'PP':>6}  {'books@':12} {'n':>2}  player / stat / game")
    for r in rows:
        if r["fair_prob"] < a.min:
            break
        bl = "/".join(f"{x:g}" for x in r["book_lines"])
        print(f"{r['fair_prob']:6.1%} {r['pick']:5} {r['pp_line']:6g}  {bl:12} {r['books']:2}  "
              f"{r['player']} {r['market']} ({r['event']}, {r['start'][5:16]}Z)")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(rows, f, indent=1)
        print(f"\nAll {len(rows)} rows written to {a.json}")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "sports":
        for s in get("sports"):
            print(f"{s['key']:40} {s['title']}")
    elif cmd == "events":
        for ev in upcoming(get(f"sports/{sys.argv[2]}/events")):
            print(f"{ev['id']}  {ev['commence_time']}  {ev['away_team']} @ {ev['home_team']}")
    elif cmd == "edges":
        ap = argparse.ArgumentParser(prog="fetch_odds.py edges")
        ap.add_argument("sport")
        ap.add_argument("--hours", type=float, default=36)
        ap.add_argument("--markets")
        ap.add_argument("--min", type=float, default=0.56)
        ap.add_argument("--json")
        edges(ap.parse_args(sys.argv[2:]))
    else:
        region = sys.argv[2] if len(sys.argv) > 2 else "us"
        events = get(f"sports/{cmd}/odds", regions=region, markets="h2h,spreads,totals",
                     oddsFormat="american", commenceTimeFrom=iso(datetime.now(timezone.utc)))
        for ev in upcoming(events):
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
