#!/usr/bin/env python3
"""Build the live PrizePicks board: scan every sport we can play, keep the best standard lines.

Usage (needs ODDS_API_KEY):
  python3 src/live_board.py                     # budget = fair share of this month's remaining quota
  python3 src/live_board.py --budget 60 --hours 18
  python3 src/live_board.py --budget 0          # no API calls; just drop picks whose games started

Writes results/live_board.json. Picks from games not rescanned this run are kept until their
game starts, so a small budget still leaves a full board. College sports are excluded
(PrizePicks doesn't offer them in Arkansas). Players on results/ban_list.json are left out.
"""
import argparse
import calendar
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
import fetch_odds as fo  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results", "live_board.json")
LOG = os.path.join(os.path.dirname(__file__), "..", "results", "line_log.jsonl")
BANS = os.path.join(os.path.dirname(__file__), "..", "results", "ban_list.json")


def load_bans() -> set[str]:
    """Lower-cased names of players on the ban list (results/ban_list.json)."""
    if not os.path.exists(BANS):
        return set()
    with open(BANS) as f:
        players = json.load(f).get("players", [])
    return {n.strip().lower() for p in players for n in [p["name"], *p.get("aliases", [])]}
CENTRAL = ZoneInfo("America/Chicago")
RUNS_PER_DAY = 3

# Priority order and a compact set of markets per sport (each market costs 2 requests per game).
SPORTS = [
    ("basketball_nba", "NBA", ["player_points", "player_rebounds", "player_assists",
                               "player_points_rebounds_assists"]),
    ("americanfootball_nfl", "NFL", ["player_pass_yds", "player_rush_yds", "player_reception_yds",
                                     "player_receptions"]),
    ("icehockey_nhl", "NHL", ["player_shots_on_goal", "player_points"]),
    ("baseball_mlb", "MLB", ["pitcher_strikeouts", "batter_total_bases", "batter_hits"]),
]
STAT_NAMES = {
    "points": "Points", "rebounds": "Rebounds", "assists": "Assists", "threes": "3-Pt Made",
    "points_rebounds_assists": "Pts+Rebs+Asts", "pass_yds": "Pass Yds", "pass_tds": "Pass TDs",
    "rush_yds": "Rush Yds", "reception_yds": "Rec Yds", "receptions": "Receptions",
    "shots_on_goal": "Shots on Goal", "pitcher_strikeouts": "Pitcher Ks",
    "batter_total_bases": "Total Bases", "batter_hits": "Hits",
}


def auto_budget(remaining: int) -> int:
    now = datetime.now(CENTRAL)
    days_left = calendar.monthrange(now.year, now.month)[1] - now.day + 1
    return max(0, remaining // (days_left * RUNS_PER_DAY))


def log_lines(sport_key: str, label: str, rows: list[dict], now: datetime) -> None:
    """Append every PrizePicks line seen this scan to results/line_log.jsonl (used by src/clv.py)."""
    with open(LOG, "a") as f:
        for r in rows:
            f.write(json.dumps({
                "t": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "id": slug(label, r["player"], r["market"]),
                "sport_key": sport_key, "market": "player_" + r["market"] if not r["market"].startswith(("pitcher", "batter")) else r["market"],
                "start": r["start"], "pp_line": r["pp_line"], "pick": r["pick"], "fair_prob": r["fair_prob"],
                "quotes": r["quotes"]}) + "\n")


def slug(*parts: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", "-".join(parts).lower()).strip("-")[:60]


def to_pick(sport_label: str, r: dict) -> dict:
    start = datetime.fromisoformat(r["start"].replace("Z", "+00:00"))
    away, home = r["event"].split(" @ ")
    books = "/".join(f"{x:g}" for x in r["book_lines"])
    return {
        "id": slug(sport_label, r["player"], r["market"]), "sport": sport_label, "player": r["player"],
        "team": "", "game": f"{away.split()[-1]} @ {home.split()[-1]}", "game_id": slug(r["event"]),
        "start": r["start"], "when": start.astimezone(CENTRAL).strftime("%a %-I:%M %p CT"),
        "stat": STAT_NAMES.get(r["market"], r["market"].replace("_", " ").title()),
        "side": r["pick"], "line": f"{r['pp_line']:g}", "books": f"Books {books} ({r['books']})",
        "p": r["fair_prob"], "auto": True,
        "note": f"Auto scan: PrizePicks line vs. {r['books']} sportsbooks with the margin removed. Not news-checked yet.",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, help="max API requests this run (default: auto)")
    ap.add_argument("--hours", type=float, default=16, help="scan games starting within this window")
    ap.add_argument("--min", type=float, default=0.54, help="lowest fair hit rate kept on the board")
    a = ap.parse_args()

    fo.get("sports")  # free call; fills fo.quota
    remaining = int(fo.quota.get("remaining") or 0)
    budget = a.budget if a.budget is not None else auto_budget(remaining)
    now = datetime.now(timezone.utc)

    old = []
    if os.path.exists(OUT):
        with open(OUT) as f:
            old = json.load(f).get("picks", [])

    queue = []  # (start, sport_key, label, markets, event)
    if budget > 0:
        for key, label, markets in SPORTS:
            for ev in fo.upcoming(fo.get(f"sports/{key}/events"), a.hours):
                queue.append((ev["commence_time"], key, label, markets, ev))
    queue.sort(key=lambda q: q[0])

    new, scanned, scanned_games, spent = [], set(), set(), 0
    for _, key, label, markets, ev in queue:
        cost = len(markets) * 2
        if spent + cost > budget:
            continue
        rows = fo.scan_event(key, ev, markets, {"prizepicks"})
        spent += cost
        log_lines(key, label, rows, now)
        scanned.add(slug(f"{ev['away_team']} @ {ev['home_team']}"))
        scanned_games.add((label, f"{ev['away_team'].split()[-1]} @ {ev['home_team'].split()[-1]}"))
        new += [to_pick(label, r) for r in rows if r["fair_prob"] >= a.min and r["books"] >= 2]

    # Fresh scan rows for the same player and stat replace older picks. A researched pick keeps its
    # note when its line is unchanged; if the line moved, the fresh row wins. Older picks from a
    # scanned game with no fresh row no longer clear the bar, so they drop off.
    fresh = {(p["player"], p["stat"]): p for p in new}
    kept = []
    for p in old:
        if not p.get("start") or datetime.fromisoformat(p["start"].replace("Z", "+00:00")) <= now:
            continue
        f = fresh.get((p["player"], p["stat"]))
        if f:
            if not p.get("auto") and f["line"] == p["line"] and f["side"] == p["side"]:
                new.remove(f)
                kept.append({**p, "p": f["p"], "books": f["books"]})
            continue
        if p.get("game_id") in scanned or (p.get("sport"), p.get("game")) in scanned_games:
            continue
        kept.append(p)
    bans = load_bans()
    merged = {p["id"]: p for p in kept + new}.values()
    banned = [p for p in merged if p["player"].strip().lower() in bans]
    picks = sorted((p for p in merged if p["player"].strip().lower() not in bans), key=lambda p: -p["p"])[:30]

    board = {"updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "quota_remaining": fo.quota.get("remaining"),
             "scanned_games": len(scanned), "bans": sorted(bans), "picks": picks}
    with open(OUT, "w") as f:
        json.dump(board, f, indent=1)
    print(f"budget {budget}, spent ~{spent}, scanned {len(scanned)} games, kept {len(kept)} older picks, "
          f"{len(picks)} on board, {len(banned)} hidden by ban list, quota left {fo.quota.get('remaining')}")
    for p in picks[:15]:
        print(f"  {p['p']:.1%} {p['sport']:4} {p['player']} {p['stat']} {p['side']} {p['line']}  ({p['game']}, {p['when']})")


if __name__ == "__main__":
    main()
