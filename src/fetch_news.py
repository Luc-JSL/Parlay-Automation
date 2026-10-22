#!/usr/bin/env python3
"""Pull recent X/Twitter posts for injury, lineup and line-move news.

Uses twitterapi.io (key in TWITTERAPI_IO_KEY, sent as the X-API-Key header).

Usage:
  python3 src/fetch_news.py insiders nba [--hours 12] [--grep out,questionable]
  python3 src/fetch_news.py search "LeBron injury" [--hours 24] [--limit 40]
  python3 src/fetch_news.py user ShamsCharania [--hours 24]

Sports for `insiders`: nba, nfl, tennis (handle lists below).
--grep keeps only posts containing any of the comma-separated words (case-insensitive).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://api.twitterapi.io/twitter/tweet/advanced_search"

INSIDERS = {
    "nba": ["ShamsCharania", "ChrisBHaynes", "Underdog__NBA", "FantasyLabsNBA"],
    "nfl": ["AdamSchefter", "RapSheet", "TomPelissero", "Underdog__NFL", "FieldYates"],
    "tennis": ["josemorgado", "TennisTV", "WTA", "atptour"],
}

INJURY_WORDS = ["out", "questionable", "doubtful", "probable", "ruled", "injury",
                "injured", "available", "status", "starting", "lineup", "rest",
                "withdraw", "withdrawn", "retire", "inactive", "limited", "dnp"]


def search(query: str, limit: int) -> list:
    key = os.environ.get("TWITTERAPI_IO_KEY")
    if not key:
        sys.exit("Set TWITTERAPI_IO_KEY (key from https://twitterapi.io)")
    tweets, cursor = [], ""
    while len(tweets) < limit:
        params = {"query": query, "queryType": "Latest", "cursor": cursor}
        req = urllib.request.Request(f"{BASE}?{urllib.parse.urlencode(params)}",
                                     headers={"X-API-Key": key})
        with urllib.request.urlopen(req, timeout=30) as r:
            page = json.load(r)
        tweets += page.get("tweets", [])
        cursor = page.get("next_cursor") or ""
        if not page.get("has_next_page") or not cursor:
            break
    return tweets[:limit]


def since_clause(hours: float) -> str:
    return f"since_time:{int(time.time() - hours * 3600)}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["insiders", "search", "user"])
    ap.add_argument("target", help="sport (insiders), query (search) or handle (user)")
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--grep", help="comma-separated keywords; 'injury' = built-in list")
    a = ap.parse_args()

    if a.mode == "insiders":
        handles = INSIDERS.get(a.target.lower())
        if not handles:
            sys.exit(f"Unknown sport {a.target!r}; pick from {', '.join(INSIDERS)}")
        query = "(" + " OR ".join(f"from:{h}" for h in handles) + ")"
    elif a.mode == "user":
        query = f"from:{a.target.lstrip('@')}"
    else:
        query = a.target
    query += f" {since_clause(a.hours)}"

    words = None
    if a.grep:
        words = INJURY_WORDS if a.grep == "injury" else [w.strip().lower() for w in a.grep.split(",")]

    for t in search(query, a.limit):
        text = " ".join(t.get("text", "").split())
        if not re.sub(r"https://t\.co/\S+", "", text).strip():
            continue  # media-only post
        if words and not any(w in text.lower() for w in words):
            continue
        when = time.strftime("%m-%d %H:%M", time.strptime(t["createdAt"], "%a %b %d %H:%M:%S %z %Y"))
        print(f"[{when} UTC] @{t['author']['userName']}: {text}\n    {t.get('url', '')}")


if __name__ == "__main__":
    main()
