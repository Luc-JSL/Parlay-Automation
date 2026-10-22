# Parlay Lab: context for every session

Read this first. It covers what's built, how the user wants things done, and where everything lives.
The repo's working branch is **`claude/loving-heisenberg-pfretk`**.

## The user
- 19 years old, lives in **Arkansas**, plays **PrizePicks only** (pick'em More/Less). PrizePicks is 18+ in Arkansas.
- Never suggest sportsbooks (21+ there) or other apps. Sportsbooks are only a **price reference**.
- **No college sports.** PrizePicks doesn't offer them in Arkansas.
- Prefers questions as numbered choices they can answer with 1, 2 or 3 (use AskUserQuestion). Ask before building
  anything ambiguous.
- Wants short, plain answers, and honest numbers. Don't oversell picks.

## The board ("Parlay Lab")
- **URL:** https://claude.ai/artifact/SjmXUoyLEsLor7gpYGActL. The source is `site/index.html`. Republish with the Artifact
  tool and that `url` after reading the artifact first. It declares the `sample` (chat) and `db` capabilities.
- **Look:** the user's purple "Neural Matrix" design (Orbitron/Rajdhani fonts, glass panels, purple accents), PARLAYLAB
  wordmark with a pinging dot.
- **Features:**
  - **List and Cards views.** List is the default: all picks in one section, best first.
  - **Sport tabs**, plus a **Specials** section (PrizePicks promos) at the top.
  - **From X** section: what the last X check found (`x_feed` in `board/live`): injury news, capper picks checked with
    an ADDED/SKIPPED verdict, and promos.
  - **Entry slip:**
    - Load best entry (searches 2–6 pick entries from different games for the best expected return, Goblin cuts included), plus **Best 3 / Best 4 / Best 5** buttons for a fixed size; each says whether to play it as Power or Flex, **+ Add 1 / − Remove 1**, bankroll and stake fields, and a "Power payout in app" override.
    - Power vs Flex expected return, a payout breakdown per outcome, and a quarter-Kelly stake suggestion (max 2% of bankroll).
    - Same-game warning.
  - **Goblin (G) button** per pick:
    - The user types the Goblin line, and win prob is raised by a rule of thumb (+4 points per half point for count
      stats, +1.8 for others).
    - The payout is cut by **25% per Goblin**, from the app (a 3-pick Power paid 4.5x instead of 6x).
    - The slip shows the dollar cost and a ✓/✗ "worth it" check against the normal line.
  - **"Not in my app"** hides a pick. **Chat** ("Tell Claude what your app shows") edits the board with tools.
  - **My entries & profit:** "I played Power/Flex", settle by hits, and total profit.
  - The board also works on localhost (`python3 -m http.server 8000` → `/site/`) from `results/live_board.json`, but
    without chat or sync.
- **Payout table** (`src/prizepicks.py` and the page):
  - Power: 2-pick **3x**, 3-pick **6x**, 4-pick **10x**, 5-pick 20x, 6-pick 37.5x.
  - Flex: 3-pick 2.25/1.25, 4-pick 5/1.5, 5-pick 10/2/0.4, 6-pick 25/2/0.4.
  - Same-game picks or Goblins can cut the payout. The user once saw 8x on a 4-pick.
  - Break-even per pick: 3-pick Power **55.0%**, 4-pick Power 56.2%, 5/6-pick Flex about 54.2%.
- **Board database** (ArtifactData tool, same artifact URL):

  | Doc | What |
  |---|---|
  | `board/live` | Picks on the board: `picks[]`, `bans[]`, `specials_info[]`, `x_feed{}`, `updated` |
  | `board/staged` | Copy of the latest scan |
  | `board/edits` | The user's hides, overrides, added picks, `goblins[]`, `goblinLines{}`. Never overwrite. |
  | `entries/*` | The user's logged entries. Never overwrite. |
  | `state/bans` | Ban list (also `results/ban_list.json`) |
  | `state/tracker` | `{csv}`, the pick tracker |
  | `state/linelog` | `{jsonl}`, line log for CLV |
  | `state/summary` | `{md}`, results summary |
  | `state/cappers` | X accounts to watch (also `results/cappers.json`): `cappers`, `tennis`, `prizepicks_official`, `insiders` |

  Read a doc before writing it, and pin the write with `if_version`.

## How picks are made
1. `src/live_board.py` (Odds API) compares **real PrizePicks lines** (region `us_dfs`, standard two-sided lines only, no
   Goblins/Demons) to US sportsbooks, removes the vig, and converts the probability to the PrizePicks line:
   - a negative binomial for count stats;
   - a normal model for points and yards.

   It covers NBA, NFL, NHL and MLB, keeps picks at 54% or better, drops banned players, and merges with older picks.
2. News check: injuries, minutes, lineups. X via `src/twitter.py` (`TWITTERAPI_IO_KEY`) plus web search. Official
   reports beat X.
3. Tennis has no PrizePicks lines in the API. Tennis picks are estimates at the books' line from match odds and research
   (not "play if ≤ X": lower lines are usually Goblins in the app).
4. Capper picks from `results/cappers.json` go on the board **only if our check agrees** (54% or better at the posted
   line), labeled `"source": "@handle"`. Never add a pick just because a capper posted it.
5. PrizePicks specials (Taco Tuesday and the like) from @PrizePicks on X go on the board as picks with `"special"`, or as
   `specials_info` cards with a Worth it / Skip verdict.
6. **Line movement (CLV) and calibration:** `src/clv.py` updates `results/SUMMARY.md`. There are no graded picks yet,
   so the edge isn't proven. Keep stakes small.

A PLAY is 58% or better. A LEAN is 54–58% (5–6 pick Flex only). Avoid stacking more than 2 tennis "Over games" picks.

## Automation
- **Scheduled task** "Parlay board auto-update", trigger `trig_014WJzjL3EZJ2vM5Fm2YXUVf`. It runs at 9:38 AM, 3:38 PM
  and 10:38 PM Central, starts a fresh session each time, and follows **`RUNBOOK.md`**. It **publishes picks to the board
  automatically**, as the user chose.
- Scheduled sessions can read the repo but **can't push** (403). Their state lives in the board database above.
  Git is only a backup.
- **Ban list:** hidden players, refreshed in the morning run. The user chose to hide them automatically.
- **The user says "update the parlay lab"** for an extra scan:
  1. Pull, run `live_board.py` with a modest budget, and news-check the top picks.
  2. `set` `board/live` (pinned), then commit and push.
- **The user says "stop the board"**: disable the trigger with `update_trigger` (`enabled: false`).
- **Odds API free tier:** 500 requests a month, about 10 per game scanned. A paid plan (about $30 a month) is needed
  for full coverage. Quota left at last check (Oct 22): 240.

## Tools
- `python3 src/fetch_odds.py sports | events <sport> | <sport> | edges <sport> --apps prizepicks`
- `python3 src/live_board.py [--budget N] [--hours H]` writes `results/live_board.json`
- `python3 src/prizepicks.py breakeven | devig A B | ev p1 p2 ... [--payout X]`
- `python3 src/twitter.py news "<player>" | insiders [--sport NBA] | cappers | specials | search "<query>"`
- `python3 src/clv.py` (CLV and calibration into `SUMMARY.md`)
- `python3 src/stats.py nba|nfl|nhl "<player>" <stat> <line> More|Less [--opp ABBR] [--json]` (ESPN game logs: hit rates this season, last 10, last season, vs opponent)
- Network: ESPN, basketball-reference, hockey-reference, tennisabstract and pbs.twimg.com (X images) are allowed. NBA.com and pro-football-reference block bots.

## Lessons learned (don't repeat)
- One-sided PrizePicks lines are Goblins/Demons. They looked like 70%+ edges, and the scanner now skips them.
- Goblins also show up as two-sided lines in the feed. A More pick a full point (or 10%) under every book's line is
  treated as a likely Goblin and kept only at 75%+ (the payout cut needs about 1.33x the hit rate). The user saw most
  "best" picks turn out to be Goblins before this rule. Less picks are never Goblins, so favor them.
- A normal curve overstated pushes on whole-number lines for count stats. That's fixed with a negative binomial.
- "Parlay progressions" and ladders don't change EV, and they raise the risk of going broke. Don't recommend them.
- Many cappers sell picks and have unverified records. Use X for news; our math decides.
- After republishing the board, the user may need **Ctrl + Shift + R** to see the new version.
- Tacos keep full payout (seen on a slip: 3-pick Power with a Taco paid 6x). Goblins cut it. Don't confuse the two.
