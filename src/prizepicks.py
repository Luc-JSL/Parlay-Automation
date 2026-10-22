#!/usr/bin/env python3
"""PrizePicks entry math: break-even rates, de-vigged sportsbook probabilities, EV.

Examples
  # Break-even hit rate per pick for every entry type
  python3 src/prizepicks.py breakeven

  # Fair probability of one side of a sportsbook prop (both sides' odds)
  python3 src/prizepicks.py devig -122 -102

  # EV of a 3-pick entry, given your win probability for each pick
  python3 src/prizepicks.py ev 0.60 0.61 0.59 --stake 10
  python3 src/prizepicks.py ev 0.58 0.571 0.63 0.63 --payout 8   # use the payout the app shows

Payout multipliers change. PAYOUTS below mirror PrizePicks' help-center table
(https://intercom.help/prizepicks/en/articles/9047668-payouts-explained).
Check the payout shown in the app before entering and update this table if it differs.
These are the rates for picks from different games with no Goblins or Demons. Same-game picks can pay
less (a 4-pick Power with picks sharing a game showed 8x instead of 10x); pass --payout for those.
"""
import argparse

# picks -> {hits: multiplier}
POWER = {2: {2: 3}, 3: {3: 6}, 4: {4: 10}, 5: {5: 20}, 6: {6: 37.5}}
FLEX = {
    3: {3: 2.25, 2: 1.25},
    4: {4: 5, 3: 1.5},
    5: {5: 10, 4: 2, 3: 0.4},
    6: {6: 25, 5: 2, 4: 0.4},
}


def to_prob(american: float) -> float:
    return 100 / (american + 100) if american > 0 else -american / (-american + 100)


def hit_distribution(probs: list[float]) -> list[float]:
    """P(exactly k hits) for independent picks with different probabilities."""
    dist = [1.0]
    for p in probs:
        nxt = [0.0] * (len(dist) + 1)
        for k, q in enumerate(dist):
            nxt[k] += q * (1 - p)
            nxt[k + 1] += q * p
        dist = nxt
    return dist


def expected_return(probs: list[float], table: dict) -> float:
    dist = hit_distribution(probs)
    return sum(dist[k] * mult for k, mult in table.items())


def breakeven(n: int, table: dict) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if expected_return([mid] * n, table) < 1 else (lo, mid)
    return hi


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("breakeven")
    d = sub.add_parser("devig")
    d.add_argument("side", type=float, help="American odds of the side you want")
    d.add_argument("other", type=float, help="American odds of the opposite side")
    e = sub.add_parser("ev")
    e.add_argument("probs", nargs="+", type=float)
    e.add_argument("--stake", type=float, default=10.0)
    e.add_argument("--payout", type=float, help="Power payout the app shows for this entry, e.g. 8 (overrides the table)")
    a = ap.parse_args()

    if a.cmd == "breakeven":
        print("Picks  Power  Flex   (per-pick hit rate needed to break even)")
        for n in range(2, 7):
            flex = f"{breakeven(n, FLEX[n]):.1%}" if n in FLEX else "  -  "
            print(f"  {n}    {breakeven(n, POWER[n]):.1%}  {flex}")
    elif a.cmd == "devig":
        p, q = to_prob(a.side), to_prob(a.other)
        print(f"Raw implied {p:.1%} / {q:.1%} (hold {p + q - 1:.1%}) -> fair {p / (p + q):.1%}")
    else:
        n = len(a.probs)
        power = dict(POWER)
        if a.payout:
            power[n] = {n: a.payout}
        for name, tables in (("Power", power), ("Flex", FLEX)):
            if n in tables:
                r = expected_return(a.probs, tables[n])
                print(f"{name} {n}-pick: expected return {r:.3f}x -> EV {(r - 1) * a.stake:+.2f} "
                      f"on ${a.stake:.0f} (break-even {breakeven(n, tables[n]):.1%}/pick)")


if __name__ == "__main__":
    main()
