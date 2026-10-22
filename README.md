# Parlay Automation

Research-driven parlay picks for **NBA, NFL, and Tennis (ATP/WTA)**.

Each slate lives in `picks/YYYY-MM-DD.md` with the legs, the reasoning and sources
behind each one, the odds at the time of writing, and what would invalidate the pick.

## PrizePicks first

Picks are built for **PrizePicks** (player stat More/Less, Power and Flex Play entries).
Each pick on an entry has to hit about 54–59% just to break even:

| Picks | Power | Flex |
|---|---|---|
| 2 | 57.7% | – |
| 3 | 58.5% | 59.1% |
| 4 | 56.2% (59.5% if same-game picks cut it to 8x) | 56.9% |
| 5 | 54.9% | 54.3% |
| 6 | 54.7% | 54.2% |

(From the payout table in `src/prizepicks.py`. Check the in-app payouts, which change.)

So the process is: **find props where the PrizePicks line is softer than the sharp sportsbook line**,
remove the sportsbook's margin to get a fair probability, and only play picks that clear the
break-even rate for the entry size. 5–6 pick Flex entries have the lowest bar per pick.

## How picks are made

1. **Slate scan** – every NBA / NFL / ATP / WTA event on the date.
2. **Injury + lineup check** – official injury reports, beat writers, and team news.
   A leg is dropped if a key player's status is unknown close to lock.
3. **Market check** – opening vs. current line. If the line has already moved
   through the number we liked, the value is gone and the leg is dropped.
4. **Form / matchup** – recent results, head-to-head, situational spots
   (short week, back-to-back, travel, surface for tennis).
5. **Correlation + price** – legs should be independent (or positively
   correlated on purpose), and the combined price has to clear our
   estimated true probability. `src/parlay_calc.py` does the math.

Rules of thumb we follow:
- 2–3 legs max for the "core" parlay. Every extra leg compounds the book's margin.
- No coin-flip legs (spreads under 3 in the NBA with unknown injuries, etc.).
- Moneyline favorites are fine as anchors, but never pay worse than about -350.
- Re-check injuries 60 minutes before lock and confirm the live price.

## Tools

```bash
python3 src/prizepicks.py breakeven               # break-even % per entry type
python3 src/prizepicks.py devig -140 +115          # fair % of a sportsbook prop side
python3 src/prizepicks.py ev 0.60 0.59 0.61 --stake 10   # EV of a 3-pick entry
```

```bash
# Combined odds, implied probability, and EV for a parlay
python3 src/parlay_calc.py -160 -300 1.38 --true-probs 0.60 0.74 0.70

# Live odds (needs a free key from https://the-odds-api.com in ODDS_API_KEY)
# Only games that haven't started are shown.
python3 src/fetch_odds.py basketball_nba
python3 src/fetch_odds.py events americanfootball_nfl       # upcoming events + ids (free)

# PrizePicks edge scanner: real PrizePicks lines vs. de-vigged sportsbook consensus
python3 src/fetch_odds.py edges basketball_nba --hours 36 --min 0.56 --json /tmp/nba.json
```

`edges` costs (markets x 2 regions) API requests per event, about 10 per NBA/NFL game.

## Viewing the board

- **Full version:** https://claude.ai/artifact/SjmXUoyLEsLor7gpYGActL (sign in to claude.ai). The live feed, chat, Goblin marks,
  and saved entries all work here.
- **On your own computer:** from the repo folder run `python3 -m http.server 8000`, then open http://localhost:8000/site/.
  It shows the picks saved in `results/live_board.json` (run `git pull` for the newest). Chat and cloud saving don't
  work there, and your slip and entries stay in that browser only.

## Data sources / connectors

| Need | Source | How it connects |
|------|--------|-----------------|
| Live odds, line movement | [The Odds API](https://the-odds-api.com) (free tier) | `ODDS_API_KEY` environment variable |
| NBA stats | [balldontlie](https://www.balldontlie.io) / NBA.com | `BALLDONTLIE_API_KEY` env var |
| NFL stats / injuries | ESPN public endpoints, nflverse | no key needed (network allow-list) |
| Tennis stats / H2H | Tennis Abstract, ATP/WTA sites | no key needed (network allow-list) |
| Breaking news (X/Twitter) | X API (paid tier for search) | `X_BEARER_TOKEN` env var |

Never commit API keys. Store them as environment variables / secrets.

> Picks are analysis, not guarantees. Bet responsibly and within limits.
