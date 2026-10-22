#!/usr/bin/env python3
"""Did the market move our way? Closing line value (CLV) and calibration report.

Usage:
  python3 src/clv.py            # print the report and update results/SUMMARY.md

CLV: for every pick that reached the board (fair >= 54% when first seen in results/line_log.jsonl),
compare our fair hit rate when first seen with the sportsbooks' fair hit rate for the SAME side and
line at the last scan before the game started. Positive CLV means the books moved toward our pick,
which is the earliest sign the picks have a real edge (win/loss records take hundreds of picks).

Calibration: picks graded in results/tracker.csv, grouped by our estimated hit rate.
"""
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from statistics import median

sys.path.insert(0, os.path.dirname(__file__))
from fetch_odds import COUNT_SPORTS, over_prob_at  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
LOG = os.path.join(ROOT, "results", "line_log.jsonl")
TRACKER = os.path.join(ROOT, "results", "tracker.csv")
SUMMARY = os.path.join(ROOT, "results", "SUMMARY.md")
BOARD_MIN = 0.54
START, END = "<!-- clv:start -->", "<!-- clv:end -->"


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def side_prob(entry: dict, side: str, line: float) -> float:
    """Sportsbook fair probability of `side` at `line`, from one scan's quotes (pushes excluded)."""
    count = entry["sport_key"].startswith(COUNT_SPORTS)
    overs, unders = zip(*(over_prob_at(p, pt, line, entry["market"], count) for pt, p in entry["quotes"]))
    o, u = median(overs), median(unders)
    return o / (o + u) if side == "More" else u / (o + u)


def clv_rows() -> list[dict]:
    if not os.path.exists(LOG):
        return []
    seen = defaultdict(list)
    with open(LOG) as f:
        for line in f:
            if line.strip():
                e = json.loads(line)
                seen[e["id"]].append(e)
    rows = []
    for pid, entries in seen.items():
        entries.sort(key=lambda e: e["t"])
        first = entries[0]
        if first["fair_prob"] < BOARD_MIN:
            continue
        before = [e for e in entries if ts(e["t"]) < ts(e["start"])]
        if len(before) < 2:
            continue
        last = before[-1]
        side, line = first["pick"], first["pp_line"]
        close = side_prob(last, side, line)
        moved = last["pp_line"] - line
        rows.append({"id": pid, "pick": f"{side} {line:g}", "open": first["fair_prob"], "close": round(close, 3),
                     "clv": round(close - first["fair_prob"], 3),
                     "pp_move": moved if side == "More" else -moved})  # >0 = PrizePicks moved toward our side
    return rows


def calibration() -> list[tuple]:
    buckets = [(0.50, 0.55), (0.55, 0.58), (0.58, 0.62), (0.62, 1.0)]
    out = []
    if not os.path.exists(TRACKER):
        return out
    with open(TRACKER) as f:
        graded = [r for r in csv.DictReader(f) if r.get("result") in ("W", "L") and r.get("est_prob")]
    for lo, hi in buckets:
        rs = [r for r in graded if lo <= float(r["est_prob"]) < hi]
        if rs:
            pred = sum(float(r["est_prob"]) for r in rs) / len(rs)
            hit = sum(r["result"] == "W" for r in rs) / len(rs)
            out.append((f"{lo:.0%}–{min(hi, 1):.0%}", len(rs), pred, hit))
    return out


def main() -> None:
    rows = clv_rows()
    cal = calibration()
    lines = [START, "## Line movement (CLV)", ""]
    if rows:
        avg = sum(r["clv"] for r in rows) / len(rows)
        pos = sum(r["clv"] > 0 for r in rows)
        lines += [f"{len(rows)} board picks seen at least twice before lock. Average CLV **{avg:+.1%}**; "
                  f"{pos} of {len(rows)} moved our way.", "",
                  "| Pick | Line | Fair when found | Fair at close | CLV | PrizePicks line moved our way |",
                  "|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda r: -r["clv"]):
            lines.append(f"| {r['id']} | {r['pick']} | {r['open']:.1%} | {r['close']:.1%} | {r['clv']:+.1%} | "
                         f"{'yes' if r['pp_move'] > 0 else 'no' if r['pp_move'] < 0 else 'unchanged'} |")
    else:
        lines.append("No board pick has been scanned twice before its game yet.")
    lines += ["", "## Calibration", ""]
    if cal:
        lines += ["| Our estimate | Picks | Predicted | Actual |", "|---|---|---|---|"]
        lines += [f"| {b} | {n} | {p:.1%} | {h:.1%} |" for b, n, p, h in cal]
        lines.append("")
        lines.append("Fewer than ~300 graded picks is too few to trust these numbers.")
    else:
        lines.append("No graded picks yet.")
    lines.append(END)
    block = "\n".join(lines)
    print(block)

    text = open(SUMMARY).read() if os.path.exists(SUMMARY) else "# Results Summary\n"
    if START in text:
        text = text[:text.index(START)] + block + text[text.index(END) + len(END):]
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    with open(SUMMARY, "w") as f:
        f.write(text)


if __name__ == "__main__":
    main()
