# Automated Research Runbook

Every scheduled run follows this file. Work on branch `claude/sports-parlay-picker-hxrtt8`.

## Each run
1. `git pull origin claude/sports-parlay-picker-hxrtt8`
2. **Grade first.** For every pick in `results/tracker.csv` with `result` empty whose game is final,
   look up the box score and fill in `actual` and `result` (W/L/P/void). DNP/retired = void.
3. **Research the next slate** (today + tomorrow, US Eastern dates) for NBA, NFL, ATP/WTA tennis:
   - Injury reports, starting lineups, rest/back-to-back, tennis withdrawals and fatigue
   - Real PrizePicks lines vs. sportsbook fair odds: `python3 src/fetch_odds.py edges basketball_nba` and
     `... edges americanfootball_nfl` (if `ODDS_API_KEY` is set). Start from its `fair` %, then adjust for news the market
     hasn't priced. Each scan costs ~10 requests per game, so scan once per run.
   - News from beat writers / X, recent form, matchups, head-to-head
4. **Pick only what clears break-even.** De-vig sportsbook props with
   `python3 src/prizepicks.py devig`. A pick needs an estimated **≥ 58%** hit rate.
   Record the PrizePicks line threshold where it becomes a play. Never invent stats, lines, or statuses.
   If something can't be verified, write "not found" and lower confidence.
5. Write or update `picks/YYYY-MM-DD.md` (one file per date) with the card, reasoning, and sources.
   Append each new pick to `results/tracker.csv` (one row per pick; don't duplicate an existing pick on re-runs,
   update its line/prob instead).
6. Update `results/SUMMARY.md`: overall and per-sport hit rate, last 7 days, and calibration
   (predicted vs. actual hit rate by probability bucket). If a bucket underperforms, write down the lesson
   and apply it to future picks.
7. Commit with message `Picks/grading update <date> <time ET>` and `git push -u origin claude/sports-parlay-picker-hxrtt8`.
8. Finish with a 5-line summary: new picks, picks graded, current record.

## Rules
- PrizePicks payouts (verify in app): 2-pick Power 3x, 3 = 5x, 4 = 10x, 5 = 20x, 6 = 37.5x.
- Break-even per pick ≈ 54–59%. A -115 sportsbook prop at the same line is NOT a play.
- Avoid stacking negatively correlated picks on one entry.
- Sites blocked by network policy: note them in the run summary and move on.
