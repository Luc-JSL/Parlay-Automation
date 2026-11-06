#!/usr/bin/env python3
"""Budget and car-affordability calculator.

Estimates monthly take-home pay from gross income (2026 federal brackets,
Arkansas 2026 brackets, FICA), shows what is left after fixed bills, how long
a down payment takes to save, and what a car really costs per month once the
loan, insurance, fuel, tires, maintenance and Arkansas personal property tax
are added up. It also prints the gross income that common lender and
budgeting rules would require for that car.

Examples
--------
Monthly budget and savings timeline:
    python3 src/money_plan.py budget --income 2500 --rent 650 --utilities 150 \
        --car-payment 350 --insurance 300 --food 320 --gas 110 --misc 150

Months to save a down payment under several income scenarios:
    python3 src/money_plan.py timeline --rent 650 --utilities 150 \
        --car-payment 350 --insurance 300 --goal 11000 --incomes 2000 3000 4000 5000

Cost of owning a specific car:
    python3 src/money_plan.py car --price 55000 --down 11000 --apr 10 --months 72 \
        --insurance 600 --miles 10000 --mpg 18 --fuel-price 4.62

Tax figures are simplified (single filer, standard deduction, no credits) and
are estimates, not tax advice.
"""

from __future__ import annotations

import argparse

# 2026 federal brackets for a single filer (taxable income thresholds).
FED_STD_DEDUCTION = 16_100
FED_BRACKETS = [
    (12_400, 0.10),
    (50_400, 0.12),
    (105_700, 0.22),
    (201_775, 0.24),
    (256_225, 0.32),
    (640_600, 0.35),
    (float("inf"), 0.37),
]

# Arkansas 2026 (per DFA withholding formula effective 1 Jan 2026).
AR_STD_DEDUCTION = 2_470
AR_PERSONAL_CREDIT = 29
AR_BRACKETS = [
    (5_599, 0.00),
    (11_199, 0.02),
    (15_999, 0.03),
    (26_399, 0.034),
    (float("inf"), 0.037),
]

FICA_RATE = 0.0765           # employee share of Social Security + Medicare
SE_TAX_RATE = 0.153          # self-employment tax on 92.35% of net 1099 profit


def progressive_tax(taxable: float, brackets) -> float:
    tax, lower = 0.0, 0.0
    for upper, rate in brackets:
        if taxable <= lower:
            break
        tax += (min(taxable, upper) - lower) * rate
        lower = upper
    return tax


def annual_taxes(gross_w2: float, net_1099: float = 0.0) -> dict:
    se_tax = SE_TAX_RATE * net_1099 * 0.9235
    agi = gross_w2 + net_1099 - se_tax / 2
    fed_taxable = max(0.0, agi - FED_STD_DEDUCTION)
    federal = progressive_tax(fed_taxable, FED_BRACKETS) + se_tax
    ar_taxable = max(0.0, agi - AR_STD_DEDUCTION)
    arkansas = max(0.0, progressive_tax(ar_taxable, AR_BRACKETS) - AR_PERSONAL_CREDIT)
    fica = FICA_RATE * gross_w2
    return {"federal": federal, "arkansas": arkansas, "fica": fica,
            "total": federal + arkansas + fica}


def monthly_take_home(gross_monthly: float, net_1099_monthly: float = 0.0) -> float:
    t = annual_taxes(gross_monthly * 12, net_1099_monthly * 12)
    return gross_monthly + net_1099_monthly - t["total"] / 12


def loan_payment(principal: float, apr_pct: float, months: int) -> float:
    if principal <= 0:
        return 0.0
    r = apr_pct / 100 / 12
    if r == 0:
        return principal / months
    return principal * r / (1 - (1 + r) ** -months)


def fmt(x: float) -> str:
    return f"${x:,.0f}"


def cmd_budget(a: argparse.Namespace) -> None:
    take_home = monthly_take_home(a.income, a.side)
    fixed = a.rent + a.utilities + a.car_payment + a.insurance
    living = a.food + a.gas + a.phone + a.misc
    left = take_home - fixed - living
    print(f"Gross income            {fmt(a.income + a.side):>10}")
    print(f"Estimated take-home     {fmt(take_home):>10}")
    print(f"Fixed bills             {fmt(fixed):>10}   (rent, utilities, car payment, insurance)")
    print(f"Living costs            {fmt(living):>10}   (food, gas, phone, misc)")
    print(f"Left to save            {fmt(left):>10}")
    car_share = (a.car_payment + a.insurance) / max(a.income + a.side, 1)
    print(f"Car payment + insurance = {car_share:.0%} of gross income "
          f"(lenders usually cap this near 15 to 20%)")
    if left <= 0:
        print("This budget does not balance; nothing can be saved until income rises or a bill falls.")


def cmd_timeline(a: argparse.Namespace) -> None:
    print(f"Goal: {fmt(a.goal)} saved. Fixed bills {fmt(a.rent + a.utilities + a.car_payment + a.insurance)}, "
          f"living costs {fmt(a.living)} per month.")
    print(f"{'Gross/mo':>10} {'Take-home':>10} {'Saved/mo':>10} {'Months':>8}")
    for inc in a.incomes:
        th = monthly_take_home(inc)
        saved = th - (a.rent + a.utilities + a.car_payment + a.insurance) - a.living
        months = "never" if saved <= 0 else f"{a.goal / saved:.1f}"
        print(f"{fmt(inc):>10} {fmt(th):>10} {fmt(saved):>10} {months:>8}")


def cmd_car(a: argparse.Namespace) -> None:
    sales_tax = a.price * a.sales_tax_pct / 100
    financed = max(0.0, a.price + (sales_tax if a.finance_tax else 0) - a.down)
    payment = loan_payment(financed, a.apr, a.months)
    total_interest = payment * a.months - financed
    fuel = a.miles / a.mpg * a.fuel_price / 12
    tires = a.tire_set_cost * (a.miles / a.tire_life_miles) / 12
    maintenance = a.maintenance_per_year / 12
    prop_tax = a.price * 0.20 * a.millage / 1000 / 12
    all_in = payment + a.insurance + fuel + tires + maintenance + prop_tax

    print(f"Price {fmt(a.price)}, down {fmt(a.down)}, sales tax {fmt(sales_tax)} "
          f"({a.sales_tax_pct}%, {'financed' if a.finance_tax else 'paid in cash at registration'})")
    print(f"Loan {fmt(financed)} at {a.apr}% for {a.months} months")
    print()
    print(f"Loan payment            {fmt(payment):>10}")
    print(f"Insurance               {fmt(a.insurance):>10}")
    print(f"Fuel                    {fmt(fuel):>10}   ({a.miles:,.0f} mi/yr, {a.mpg} mpg, ${a.fuel_price:.2f}/gal)")
    print(f"Tires                   {fmt(tires):>10}   ({fmt(a.tire_set_cost)} per set every {a.tire_life_miles:,} mi)")
    print(f"Maintenance/repairs     {fmt(maintenance):>10}   ({fmt(a.maintenance_per_year)}/yr)")
    print(f"AR personal prop. tax   {fmt(prop_tax):>10}   (20% assessment x {a.millage} mills)")
    print(f"All-in per month        {fmt(all_in):>10}")
    print(f"Total loan interest     {fmt(total_interest):>10}")
    print()
    print("Gross monthly income needed:")
    print(f"  lender payment-to-income cap of 20% (payment + insurance) {fmt((payment + a.insurance) / 0.20):>10}")
    print(f"  lender payment-to-income cap of 15%                       {fmt((payment + a.insurance) / 0.15):>10}")
    print(f"  20/4/10 rule, all car costs under 10% of gross            {fmt(all_in / 0.10):>10}")
    print(f"  looser test, all car costs under 20% of take-home         ~{fmt(all_in / 0.20 / 0.80):>9}  (assumes ~80% take-home)")
    if a.months > 48:
        print("Note: 20/4/10 also says a loan term over 48 months is too long for the price.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("budget", help="monthly budget from gross income and bills")
    b.add_argument("--income", type=float, required=True, help="gross W-2 income per month")
    b.add_argument("--side", type=float, default=0, help="net 1099/self-employed profit per month")
    for name in ("rent", "utilities", "car-payment", "insurance"):
        b.add_argument(f"--{name}", type=float, default=0)
    b.add_argument("--food", type=float, default=320, help="USDA low-cost plan, single male 19-50, Sept 2026")
    b.add_argument("--gas", type=float, default=110)
    b.add_argument("--phone", type=float, default=25)
    b.add_argument("--misc", type=float, default=150)
    b.set_defaults(func=cmd_budget)

    t = sub.add_parser("timeline", help="months to save a goal under several income scenarios")
    t.add_argument("--goal", type=float, required=True)
    t.add_argument("--incomes", type=float, nargs="+", default=[2000, 3000, 4000, 5000])
    for name in ("rent", "utilities", "car-payment", "insurance"):
        t.add_argument(f"--{name}", type=float, default=0)
    t.add_argument("--living", type=float, default=605, help="food + gas + phone + misc per month")
    t.set_defaults(func=cmd_timeline)

    c = sub.add_parser("car", help="all-in monthly cost of a specific car and the income it needs")
    c.add_argument("--price", type=float, required=True)
    c.add_argument("--down", type=float, default=0)
    c.add_argument("--apr", type=float, required=True, help="loan APR in percent")
    c.add_argument("--months", type=int, default=72)
    c.add_argument("--insurance", type=float, required=True, help="full-coverage premium per month")
    c.add_argument("--miles", type=float, default=10000, help="miles per year")
    c.add_argument("--mpg", type=float, default=18)
    c.add_argument("--fuel-price", type=float, default=4.62, help="premium, Arkansas, Nov 2026")
    c.add_argument("--tire-set-cost", type=float, default=2000)
    c.add_argument("--tire-life-miles", type=float, default=12000)
    c.add_argument("--maintenance-per-year", type=float, default=1600)
    c.add_argument("--sales-tax-pct", type=float, default=9.0, help="6.5% state + local")
    c.add_argument("--finance-tax", action="store_true", help="roll sales tax into the loan")
    c.add_argument("--millage", type=float, default=55, help="county millage for personal property tax")
    c.set_defaults(func=cmd_car)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
