#!/usr/bin/env python3
"""Build the Parlay Labs board: scan PrizePicks vs. the books, check game logs, rate each leg,
and search for the best slip.

  ODDS_API_KEY=... python3 src/lab_board.py basketball_nba --hours 24 --out lab/out

Writes board.json (every leg rated), slips.json (best entry per size and type) and
status.json (one row: when, verdict, best slip) to --out. Analyst notes from injury and
matchup research go in lab/notes.json, keyed "Player|stat" (stat as in edge_scan, e.g.
"rebounds_assists"): {"reject": true, "reason": "...", "risk": "...", "adjust": -0.01}.

How a leg is rated
  market  = de-vigged book consensus at the PrizePicks line (edge_scan), ties removed,
            minus 1 pt when it had to be extrapolated from a different book line,
            minus 0.5 pt when only 2 books post it
  history = how often the player beat this exact line: last 20 games and last season,
            each shrunk toward 50% (10 games of prior weight), averaged
  est     = 75% market + 25% history + any analyst adjustment
Tiers: play >= 58%, lean >= 55.5%, else pass. Rejected: mislabeled line, game logs
disagree (history under 45%), or an analyst note.

A slip qualifies when its expected return is at least 1.05x under the LOWER of the two
payout tables below (PrizePicks payouts could not be verified) and every leg clears the
entry's per-pick break-even by at least 1.5 points. The best slip is the top qualifying 2-3 pick entry; a 4-6 pick
entry is offered only when no 2-3 pick qualifies and it returns at least 1.15x.
"""
import argparse
import itertools
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import edge_scan  # noqa: E402
from prizepicks import breakeven, expected_return, hit_distribution  # noqa: E402

PAYOUTS = {
    "most sources (Sep 2026)": {
        "Power": {2: {2: 3}, 3: {3: 6}, 4: {4: 10}, 5: {5: 20}, 6: {6: 37.5}},
        "Flex": {3: {3: 3, 2: 1}, 4: {4: 6, 3: 1.5}, 5: {5: 10, 4: 2, 3: 0.4}, 6: {6: 25, 5: 2, 4: 0.4}},
    },
    "older table": {
        "Power": {2: {2: 3}, 3: {3: 5}, 4: {4: 10}, 5: {5: 20}, 6: {6: 37.5}},
        "Flex": {3: {3: 2.25, 2: 1.25}, 4: {4: 5, 3: 1.5}, 5: {5: 10, 4: 2, 3: 0.4}, 6: {6: 25, 5: 2, 4: 0.4}},
    },
}
MARGIN = 0.015  # every leg must clear the per-pick break-even by 1.5 points
STAT_KEYS = {
    "points": ("pts",), "rebounds": ("reb",), "assists": ("ast",), "threes": ("fg3",),
    "points_rebounds_assists": ("pts", "reb", "ast"), "points_rebounds": ("pts", "reb"),
    "points_assists": ("pts", "ast"), "rebounds_assists": ("reb", "ast"),
}
STAT_NAMES = {
    "points": "Points", "rebounds": "Rebounds", "assists": "Assists", "threes": "3-pointers made",
    "points_rebounds_assists": "Pts+Reb+Ast", "points_rebounds": "Pts+Reb", "points_assists": "Pts+Ast",
    "rebounds_assists": "Reb+Ast", "pass_yds": "Pass yards", "pass_tds": "Pass TDs",
    "pass_completions": "Completions", "pass_attempts": "Pass attempts", "rush_yds": "Rush yards",
    "rush_attempts": "Rush attempts", "reception_yds": "Receiving yards", "receptions": "Receptions",
    "rush_reception_yds": "Rush+Rec yards", "pass_interceptions": "Interceptions",
}


def shrink(wins: int, n: int, k: float = 10) -> float:
    return (wins + 0.5 * k) / (n + k)


def beat_rate(games: list[dict], keys: tuple, line: float, side: str) -> tuple[int, int]:
    wins = losses = 0
    for g in games:
        if g["min"] < 10:
            continue
        v = sum(g[k] for k in keys)
        if v == line:
            continue
        won = v > line if side == "More" else v < line
        wins, losses = wins + won, losses + (not won)
    return wins, wins + losses


def season_now() -> int:
    now = datetime.now(timezone.utc)
    return now.year + 1 if now.month >= 9 else now.year


def rate_legs(rows: list[dict], sport: str, notes: dict) -> list[dict]:
    logs = {}
    if sport == "basketball_nba":
        import espn_logs
    out = []
    for r in rows:
        if r["market"] == "rush_yds" and r["pp_line"] < 10:
            continue  # QB rush yards: kneel-downs break the count model
        key = f"{r['player']}|{r['market']}"
        note = notes.get(key, {})
        market = r["p"] - (0.01 if r["exact"] == 0 else 0) - (0.005 if r["n"] < 3 else 0)
        hist = l20 = seas = None
        h20 = hs = (0, 0)
        if sport == "basketball_nba" and r["p"] >= 0.53 and r["market"] in STAT_KEYS:
            if r["player"] not in logs:
                try:
                    s = season_now()
                    logs[r["player"]] = (espn_logs.game_log(r["player"], s - 1), espn_logs.game_log(r["player"], s))
                except Exception:
                    logs[r["player"]] = ([], [])
            last, cur = logs[r["player"]]
            keys = STAT_KEYS[r["market"]]
            h20 = beat_rate((last + cur)[-20:], keys, r["pp_line"], r["side"])
            hs = beat_rate(last, keys, r["pp_line"], r["side"])
            if h20[1] + hs[1]:
                l20, seas = shrink(*h20), shrink(*hs)
                hist = (l20 + seas) / 2
        est = market if hist is None else 0.75 * market + 0.25 * hist
        est += note.get("adjust", 0)
        reason = note.get("reason", "")
        if r["suspect"]:
            tier, reason = "rejected", reason or "Line sits outside PrizePicks' own goblin/demon ladder: probably mislabeled."
        elif note.get("reject"):
            tier = "rejected"
        elif hist is not None and h20[1] >= 8 and hist < 0.45:
            tier, reason = "rejected", reason or "Game logs disagree with the market."
        else:
            tier = "play" if est >= 0.58 else "lean" if est >= 0.555 else "pass"
        out.append({
            "id": key, "player": r["player"], "game": r["game"], "start": r["start"],
            "stat": STAT_NAMES.get(r["market"], r["market"]), "side": r["side"], "line": r["pp_line"],
            "book_lines": ", ".join(f"{x:g}" for x in r["lines"]), "books": r["n"],
            "market_pct": round(100 * r["p"], 1), "l20": f"{h20[0]}/{h20[1]}" if h20[1] else "",
            "l20_pct": round(100 * h20[0] / h20[1], 1) if h20[1] else None,
            "season_pct": round(100 * hs[0] / hs[1], 1) if hs[1] else None,
            "est_pct": round(100 * est, 1), "tier": tier, "reason": reason, "risk": note.get("risk", ""),
            "_est": est,
        })
    out.sort(key=lambda x: -x["_est"])
    return out


def conservative(probs: list[float], kind: str) -> tuple[float, float]:
    """Lowest expected return and highest per-pick break-even across the payout tables."""
    n = len(probs)
    tables = [t[kind][n] for t in PAYOUTS.values() if n in t[kind]]
    return min(expected_return(probs, t) for t in tables), max(breakeven(n, t) for t in tables)


def build_slips(legs: list[dict]) -> list[dict]:
    pool = [x for x in legs if x["tier"] in ("play", "lean") or (x["tier"] == "pass" and x["_est"] >= 0.55)][:14]
    best = {}
    for n in range(2, 7):
        for combo in itertools.combinations(pool, n):
            games = [c["game"] for c in combo]
            if any(games.count(g) > 2 for g in games) or len({c["player"] for c in combo}) < n:
                continue
            probs = [c["_est"] for c in combo]
            for kind in ("Power", "Flex"):
                if kind == "Flex" and n < 3:
                    continue
                ev, be = conservative(probs, kind)
                if (n, kind) not in best or ev > best[(n, kind)][0]:
                    best[(n, kind)] = (ev, be, combo, probs)
    slips = []
    for (n, kind), (ev, be, combo, probs) in best.items():
        dist = hit_distribution(probs)
        slips.append({
            "slip_id": f"{n}{kind[0].lower()}", "label": f"{n}-pick {kind}", "type": kind, "picks": n,
            "legs": " · ".join(f"{c['player']} {c['side']} {c['line']:g} {c['stat']}" for c in combo),
            "leg_ids": ";".join(c["id"] for c in combo),
            "est_all_pct": round(100 * dist[n], 1), "exp_return": round(ev, 2),
            "breakeven_pct": round(100 * be, 1),
            "qualifies": "yes" if ev >= 1.05 and min(probs) >= be + MARGIN else "no", "is_best": "no",
        })
    small = [s for s in slips if s["qualifies"] == "yes" and s["picks"] <= 3]
    big = [s for s in slips if s["qualifies"] == "yes" and s["picks"] > 3 and s["exp_return"] >= 1.15]
    pick = max(small or big, key=lambda s: s["exp_return"], default=None)
    if pick:
        pick["is_best"] = "yes"
    slips.sort(key=lambda s: (s["is_best"] != "yes", -s["exp_return"]))
    for i, s in enumerate(slips, 1):
        s["rank"] = i
    return slips


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sport", choices=edge_scan.MARKETS)
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--out", default="lab/out")
    ap.add_argument("--notes", default="lab/notes.json")
    ap.add_argument("--next-check", default="", help="when the next re-scan is planned, shown on the board")
    a = ap.parse_args()

    now = datetime.now(timezone.utc)
    until = (now + timedelta(hours=a.hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = [e for e in edge_scan.get(f"sports/{a.sport}/events", commenceTimeTo=until)
              if e["commence_time"] > now.strftime("%Y-%m-%dT%H:%M:%SZ")]
    rows = []
    for ev in events:
        rows += edge_scan.scan_event(a.sport, ev, edge_scan.MARKETS[a.sport])
    notes = json.load(open(a.notes)) if os.path.exists(a.notes) else {}
    legs = rate_legs(rows, a.sport, notes)
    slips = build_slips(legs)
    best = next((s for s in slips if s["is_best"] == "yes"), None)
    status = [{
        "scanned_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "sport": a.sport, "games": len(events),
        "props_scanned": len(rows), "plays": sum(x["tier"] == "play" for x in legs),
        "verdict": "Best slip ready" if best else "No strong plays", "best_slip_id": best["slip_id"] if best else "",
        "payouts_note": "PrizePicks payouts unverified: slips are rated on the lower of two published tables.",
        "next_check": a.next_check,
    }]
    os.makedirs(a.out, exist_ok=True)
    board = [{k: v for k, v in x.items() if not k.startswith("_")} for x in legs if x["market_pct"] >= 52 or x["tier"] == "rejected"]
    for name, data in (("board", board), ("slips", slips), ("status", status)):
        with open(os.path.join(a.out, f"{name}.json"), "w") as f:
            json.dump(data, f, indent=1)
    print(f"{status[0]['verdict']}: {len(board)} legs on the board, {len(slips)} slips")
    for s in slips[:6]:
        print(f"  {s['label']:14} {s['exp_return']:.2f}x qualifies={s['qualifies']} best={s['is_best']}  {s['legs']}")


if __name__ == "__main__":
    main()
