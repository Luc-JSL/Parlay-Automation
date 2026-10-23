#!/usr/bin/env python3
"""Find PrizePicks props that are softer than the sportsbook market.

For every PrizePicks prop on the slate this pulls the same player/stat from the
sportsbooks (The Odds API, regions us + us_dfs), removes each book's margin, and
converts the book's line into a fair probability AT THE PRIZEPICKS LINE. When the
book line differs from the PrizePicks line, it fits a negative-binomial
distribution to the book's fair price and reads off the probability at the
PrizePicks number (dispersion per stat in DISPERSION below).

Usage
  ODDS_API_KEY=... python3 src/edge_scan.py basketball_nba [--hours 24] [--min 0.56]
  ODDS_API_KEY=... python3 src/edge_scan.py americanfootball_nfl --hours 96

Output columns: fair win% for the side (ties removed), number of books used,
spread of the books' estimates, and the books' lines. A pick needs to clear the
break-even rate for the entry (see prizepicks.py breakeven), ideally with room
to spare because the fitted distribution is only an approximation.
"""
import argparse
import json
import math
import os
import statistics
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://api.the-odds-api.com/v4"

MARKETS = {
    "basketball_nba": ["player_points", "player_rebounds", "player_assists", "player_threes",
                       "player_points_rebounds_assists", "player_points_rebounds",
                       "player_points_assists", "player_rebounds_assists"],
    "americanfootball_nfl": ["player_pass_yds", "player_pass_tds", "player_pass_completions",
                             "player_pass_attempts", "player_rush_yds", "player_rush_attempts",
                             "player_reception_yds", "player_receptions",
                             "player_rush_reception_yds", "player_pass_interceptions"],
}

# variance / mean of each stat, rough league-wide values
DISPERSION = {
    "player_points": 2.2, "player_rebounds": 1.25, "player_assists": 1.2, "player_threes": 1.1,
    "player_points_rebounds_assists": 2.4, "player_points_rebounds": 2.3,
    "player_points_assists": 2.3, "player_rebounds_assists": 1.4,
    "player_pass_yds": 17, "player_pass_tds": 1.0, "player_pass_completions": 1.6,
    "player_pass_attempts": 1.8, "player_rush_yds": 12, "player_rush_attempts": 1.6,
    "player_reception_yds": 14, "player_receptions": 1.0, "player_rush_reception_yds": 13,
    "player_pass_interceptions": 1.0,
}

DFS = {"prizepicks", "underdog", "betr_us_dfs", "pick6", "dabble_au"}


def get(path: str, **params):
    key = os.environ.get("ODDS_API_KEY") or sys.exit("Set ODDS_API_KEY")
    query = "&".join(f"{k}={v}" for k, v in {"apiKey": key, **params}.items())
    with urllib.request.urlopen(f"{BASE}/{path}?{query}", timeout=30) as r:
        return json.load(r)


def cdf(k: int, mean: float, disp: float) -> float:
    """P(X <= k) for a negative binomial (Poisson when disp <= 1)."""
    if k < 0:
        return 0.0
    if disp <= 1.0001:
        term = total = math.exp(-mean)
        for i in range(1, k + 1):
            term *= mean / i
            total += term
        return min(total, 1.0)
    p = 1 / disp
    r = mean / (disp - 1)
    term = total = math.exp(r * math.log(p))
    for i in range(1, k + 1):
        term *= (i - 1 + r) / i * (1 - p)
        total += term
    return min(total, 1.0)


def over_under_push(line: float, mean: float, disp: float) -> tuple[float, float, float]:
    if line == int(line):
        k = int(line)
        under, push = cdf(k - 1, mean, disp), cdf(k, mean, disp) - cdf(k - 1, mean, disp)
        return 1 - under - push, under, push
    under = cdf(math.floor(line), mean, disp)
    return 1 - under, under, 0.0


def fit_mean(line: float, p_over: float, disp: float) -> float:
    """Mean whose P(over line), ties removed, equals p_over."""
    lo, hi = 0.01, max(4 * line, 10)
    for _ in range(60):
        mid = (lo + hi) / 2
        o, u, _ = over_under_push(line, mid, disp)
        lo, hi = (mid, hi) if o / (o + u) < p_over else (lo, mid)
    return (lo + hi) / 2


def scan_event(sport: str, ev: dict, markets: list[str]) -> list[dict]:
    data = get(f"sports/{sport}/events/{ev['id']}/odds", regions="us,us2,eu,us_dfs",
               markets=",".join(markets), oddsFormat="decimal")
    alts = get(f"sports/{sport}/events/{ev['id']}/odds", regions="us_dfs", bookmakers="prizepicks",
               markets=",".join(m + "_alternate" for m in markets), oddsFormat="decimal")
    # goblin (easier, pays less) and demon (harder, pays more) lines; PrizePicks prices demons higher
    ladder = {}
    for b in alts.get("bookmakers", []):
        for m in b["markets"]:
            for o in m["outcomes"]:
                tier = "demon" if o["price"] >= 1.9 else "goblin"
                ladder.setdefault((o["description"], m["key"].removesuffix("_alternate")), {}) \
                      .setdefault(tier, []).append(o["point"])
    pp, books, two_sided = {}, {}, {}
    for b in data.get("bookmakers", []):
        for m in b["markets"]:
            sides = {}
            for o in m["outcomes"]:
                sides.setdefault((o["description"], o.get("point")), {})[o["name"]] = o["price"]
            for (player, point), s in sides.items():
                key = (player, m["key"])
                if b["key"] == "prizepicks":
                    pp[key] = point
                    two_sided[key] = "Under" in s  # standard lines offer More and Less; goblins/demons only More
                elif b["key"] not in DFS and "Over" in s and "Under" in s:
                    books.setdefault(key, []).append((b["key"], point, s["Over"], s["Under"]))
    rows = []
    for (player, market), line in pp.items():
        quotes = books.get((player, market), [])
        disp = DISPERSION.get(market, 1.5)
        ests, exact = [], []
        for book, bline, o_px, u_px in quotes:
            po, pu = 1 / o_px, 1 / u_px
            fair_over = po / (po + pu)
            if abs(bline - line) > max(1.5, 0.12 * line):
                continue  # too far from the PrizePicks line to extrapolate safely
            mu = fit_mean(bline, fair_over, disp)
            o, u, push = over_under_push(line, mu, disp)
            ests.append(o / (o + u))
            if bline == line:
                exact.append(fair_over)
        if len(ests) < 2:
            continue
        p_over = statistics.median(ests)
        side, p = ("More", p_over) if p_over >= 0.5 else ("Less", 1 - p_over)
        tiers = ladder.get((player, market), {})
        # a "standard" line at or below a goblin, or at or above a demon, is probably mislabeled
        suspect = (line <= max(tiers.get("goblin", [-1])) or line >= min(tiers.get("demon", [1e9]))
                   or not two_sided.get((player, market), True))
        rows.append({
            "game": f"{ev['away_team']} @ {ev['home_team']}", "start": ev["commence_time"],
            "player": player, "market": market.replace("player_", ""), "pp_line": line,
            "side": side, "p": p, "n": len(ests), "spread": max(ests) - min(ests),
            "exact": len(exact), "lines": sorted({q[1] for q in quotes}),
            "gap": line - statistics.median(q[1] for q in quotes), "suspect": suspect,
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sport", choices=MARKETS)
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--min", type=float, default=0.55, help="only show picks at or above this win%%")
    ap.add_argument("--json", help="also write all rows to this file")
    a = ap.parse_args()

    now = datetime.now(timezone.utc)
    until = (now + timedelta(hours=a.hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = [e for e in get(f"sports/{a.sport}/events", commenceTimeTo=until)
              if e["commence_time"] > now.strftime("%Y-%m-%dT%H:%M:%SZ")]
    rows = []
    for ev in events:
        rows += scan_event(a.sport, ev, MARKETS[a.sport])
    rows.sort(key=lambda r: -r["p"])
    if a.json:
        with open(a.json, "w") as f:
            json.dump(rows, f, indent=1)
    print(f"{len(events)} events, {len(rows)} PrizePicks props matched to 2+ books\n")
    print("gap = PrizePicks line minus median book line. A gap of a full point or more is often a stale\n"
          "line or a goblin/demon mislabeled as standard: confirm the line in the app before playing it.\n")
    print(f"{'win%':>6} {'bk':>2} {'ex':>2} {'sprd':>5} {'gap':>5}  {'pick':32} {'stat':26} {'game'}")
    for r in rows:
        if r["p"] < a.min:
            break
        pick = f"{r['player']} {r['side']} {r['pp_line']:g}"
        print(f"{r['p']:6.1%} {r['n']:2} {r['exact']:2} {r['spread']:5.1%} {r['gap']:+5.1f}  {pick:32} "
              f"{r['market']:26} {r['game']}  books@{','.join(f'{x:g}' for x in r['lines'])}"
              + ("  SUSPECT: not between goblin and demon lines, skip" if r["suspect"] else ""))


if __name__ == "__main__":
    main()
