# Automated Board Runbook

Every scheduled run follows this file. Work on branch `claude/cool-edison-x9a8gv`.
The board lives at https://claude.ai/artifact/SjmXUoyLEsLor7gpYGActL and reads its picks from the
artifact database document `board/live` (collection `board`, doc id `live`).

## Who this is for
- The user is 19, lives in **Arkansas**, and plays **PrizePicks only**. Never suggest sportsbooks
  (21+ in Arkansas) or other apps. Sportsbooks are only a price reference.
- **No college sports.** PrizePicks doesn't offer them in Arkansas.
- Payouts follow `src/prizepicks.py` (4-pick Power 10x) when every pick is from a different game with no Goblins or Demons.
  Same-game picks can cut the payout (the user saw 8x, which needs 59.5% per pick), so recommend entries from different games.

## Where state lives
Scheduled sessions can read the repo but **can't push to it**, because it isn't attached to the scheduled task. So the
working state lives in the board's artifact database (ArtifactData tool, artifact URL above), and git is only a backup:

| Database doc (collection/doc) | Field | Repo file |
|---|---|---|
| `board/staged` | whole document | `results/live_board.json` (staged picks, not yet on the board) |
| `board/live` | whole document | what the board shows; each run publishes its picks here |
| `state/bans` | whole document | `results/ban_list.json` |
| `state/tracker` | `csv` | `results/tracker.csv` |
| `state/linelog` | `jsonl` | `results/line_log.jsonl` (drop lines older than 14 days before saving) |
| `state/summary` | `md` | `results/SUMMARY.md` |

## Each run (keep it short; aim for under 20 minutes)
1. `git pull origin claude/cool-edison-x9a8gv`, then **load state**: `get` each database doc above (except `board/live`),
   write each one to its repo file, and remember each doc's `version`.
2. **Ban list (morning run only, the one before noon CT).** Keep `results/ban_list.json` current. Search Reddit, X,
   TikTok and YouTube for players bettors call parlay killers or "never bet on". Add a player only when current stats
   back it up: volatile minutes or snaps, a role change, active injury, blowout benching, or retirement risk in tennis.
   Remove a player when that reason no longer holds, for example a stable role for 2+ weeks or a return from injury.
   Each entry needs `name` (sportsbook spelling), `sport`, `team`, a `reason` (one sentence), `mentions`, and `sources`.
   Note the adds and removes in the summary. `live_board.py` hides these players automatically.
3. **Scan.** Run `python3 src/live_board.py`. It spends a fair share of this month's Odds API quota,
   scans the soonest games in NBA, NFL, NHL and MLB, keeps only standard PrizePicks lines
   (no Goblins or Demons), and writes `results/live_board.json`. Picks from games it didn't rescan are kept
   until their game starts. If the quota is at 0, run it with `--budget 0` to drop games that have started.
4. **News check the top picks.** For the 6–8 highest picks that start within 12 hours, search for injury news,
   expected minutes or role, and lineup changes. Then for each pick:
   - Drop it if a key status is unknown close to lock, or the news cuts against it.
   - Adjust `p` by at most about 3 points, and only with a concrete reason.
   - Rewrite `note` in one or two plain sentences with the reason, and delete `"auto": true` once checked.

   Never invent stats, lines, or statuses.
5. **Tennis (optional).** No PrizePicks tennis lines come through the API. Add at most 4 tennis picks from match odds
   and research as "play if line ≤ X" (`"cond": "≤"`, `"tennis": true`, `"team": "ATP"` or `"WTA"`), each with
   a `start` time. Skip tennis if you can't find match odds.
6. **Publish to the board.** Save the final JSON to `results/live_board.json`. Then put it on the board: `get` `board/live`
   to read its `version`, and `set` it from the file with `if_version`. Also `set` `board/staged` to the same file so the
   two match. Every pick needs `id`, `sport`, `player`, `game`, `game_id`, `start` (ISO UTC), `when` (Central time),
   `stat`, `side` (More/Less), `line`, `books`, `p` (0–1), and `note`. Only picks at 54% or better go on the board.
7. **Grade.** For rows in `results/tracker.csv` with an empty `result` whose game is final, fill in `actual`
   and `result` (W/L/P/void) from box scores. Append every pick that is new to the board this run, without duplicating rows.
   Update `results/SUMMARY.md` with the record and the hit rate by sport, then run `python3 src/clv.py`. It rewrites the
   line-movement (CLV) and calibration sections from `results/line_log.jsonl` and the tracker. If average CLV over
   30+ picks is negative, write that down as a lesson and raise the bar for picks of that type.
8. **Save state** with one ArtifactData `batch`: `set` each doc from its repo file, wrapping text files in their field
   (for example `{"csv": "<tracker text>"}`), each with the `if_version` you loaded. Then commit
   `Board update <date> <time CT>` and try `git push -u origin claude/cool-edison-x9a8gv`. If the push is refused (403),
   that's expected: say so in one line and stop. Don't retry, and don't look for a way around it.
9. Finish with 5 lines: the top 4 picks now on the board, picks graded, ban-list changes, average CLV so far, and API quota left.

## Rules
- A PLAY needs ≥ 58%. 54–58% is a LEAN for 5–6 pick Flex only.
- Avoid stacking negatively correlated picks. Don't put more than 2 tennis "Over games" picks on one entry.
- Sites blocked by network policy: note them in the summary and move on.
