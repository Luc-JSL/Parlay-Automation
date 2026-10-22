# Automated Board Runbook

Every scheduled run follows this file. Work on branch `claude/cool-edison-x9a8gv`.
The board lives at https://claude.ai/artifact/SjmXUoyLEsLor7gpYGActL and reads its picks from the
artifact database document `board/live` (collection `board`, doc id `live`).

## Who this is for
- The user is 19, lives in **Arkansas**, and plays **PrizePicks only**. Never suggest sportsbooks
  (21+ in Arkansas) or other apps. Sportsbooks are only a price reference.
- **No college sports.** PrizePicks doesn't offer them in Arkansas.
- The app pays **8x on a 4-pick Power**, so each pick needs 59.5% to break even. Other payouts follow
  `src/prizepicks.py` until the user reports what the app shows.

## Each run (keep it short; aim for under 20 minutes)
1. `git pull origin claude/cool-edison-x9a8gv`
2. **Scan.** Run `python3 src/live_board.py`. It spends a fair share of this month's Odds API quota,
   scans the soonest games in NBA, NFL, NHL and MLB, keeps only standard PrizePicks lines
   (no Goblins or Demons), and writes `results/live_board.json`. Picks from games it didn't rescan are kept
   until their game starts. If the quota is at 0, run it with `--budget 0` to drop games that have started.
3. **News check the top picks.** For the 6–8 highest picks that start within 12 hours, search for injury news,
   expected minutes or role, and lineup changes. Then for each pick:
   - Drop it if a key status is unknown close to lock, or the news cuts against it.
   - Adjust `p` by at most about 3 points, and only with a concrete reason.
   - Rewrite `note` in one or two plain sentences with the reason, and delete `"auto": true` once checked.

   Never invent stats, lines, or statuses.
4. **Tennis (optional).** No PrizePicks tennis lines come through the API. Add at most 4 tennis picks from match odds
   and research as "play if line ≤ X" (`"cond": "≤"`, `"tennis": true`, `"team": "ATP"` or `"WTA"`), each with
   a `start` time. Skip tennis if you can't find match odds.
5. **Publish to the board.** Save the final JSON to `results/live_board.json`. Then, with the ArtifactData tool, `get`
   `board/live` to read its `version`, and `set` it from that file (`file_path`) with `if_version`.
   Every pick needs `id`, `sport`, `player`, `game`, `game_id`, `start` (ISO UTC), `when` (Central time),
   `stat`, `side` (More/Less), `line`, `books`, `p` (0–1), and `note`. If ArtifactData isn't available, say so in the summary.
6. **Grade.** For rows in `results/tracker.csv` with an empty `result` whose game is final, fill in `actual`
   and `result` (W/L/P/void) from box scores. Append every pick that is new to the board this run, without duplicating rows.
   Update `results/SUMMARY.md` with the record, the hit rate by sport, and calibration by probability bucket.
7. Commit `Board update <date> <time CT>` and `git push -u origin claude/cool-edison-x9a8gv`.
8. Finish with 3 lines: the top 4 picks right now, picks graded, and API quota left.

## Rules
- A PLAY needs ≥ 58% (≥ 59.5% for a 4-pick Power at 8x). 54–58% is a LEAN for 5–6 pick Flex only.
- Avoid stacking negatively correlated picks. Don't put more than 2 tennis "Over games" picks on one entry.
- Sites blocked by network policy: note them in the summary and move on.
