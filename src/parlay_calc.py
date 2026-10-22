#!/usr/bin/env python3
"""Parlay math: combine leg odds, show implied probability and expected value.

Odds may be American (-150, +120) or decimal (1.38). Optional --true-probs are
your own estimated win probabilities per leg, used to compute edge and EV.
"""
import argparse
import math


def to_decimal(odds: float) -> float:
    if 1.0 < odds < 100:  # already decimal
        return odds
    if odds >= 100:
        return 1 + odds / 100
    if odds <= -100:
        return 1 + 100 / abs(odds)
    raise ValueError(f"Unrecognised odds: {odds}")


def to_american(decimal: float) -> str:
    if decimal >= 2:
        return f"+{round((decimal - 1) * 100)}"
    return f"{round(-100 / (decimal - 1))}"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("odds", nargs="+", type=float, help="leg odds (American or decimal)")
    p.add_argument("--true-probs", nargs="+", type=float, help="your win probability per leg")
    p.add_argument("--stake", type=float, default=100.0)
    a = p.parse_args()

    decs = [to_decimal(o) for o in a.odds]
    combined = math.prod(decs)
    implied = 1 / combined

    for i, (o, d) in enumerate(zip(a.odds, decs), 1):
        print(f"Leg {i}: {o:g} -> decimal {d:.3f}, implied {1 / d:.1%}")
    print(f"\nParlay: decimal {combined:.2f} ({to_american(combined)}), "
          f"implied {implied:.1%}, ${a.stake:.0f} pays ${a.stake * combined:.2f}")

    if a.true_probs:
        if len(a.true_probs) != len(decs):
            p.error("--true-probs needs one value per leg")
        true_p = math.prod(a.true_probs)
        ev = true_p * (combined - 1) * a.stake - (1 - true_p) * a.stake
        print(f"Your estimated hit rate: {true_p:.1%}  (edge {true_p - implied:+.1%})")
        print(f"Expected value on ${a.stake:.0f}: {ev:+.2f}")


if __name__ == "__main__":
    main()
