"""Prints the best cards for common Singapore purchases, using the same rules as the app.

Run it before and after editing the catalog and diff the output: every change in the rankings
should be explained by an edit you meant to make.

    python3 Tools/rankings.py catalog/cards_sg.json > /tmp/before.txt
    ... edit Tools/catalog.py, regenerate the JSON ...
    python3 Tools/rankings.py catalog/cards_sg.json > /tmp/after.txt
    diff /tmp/before.txt /tmp/after.txt
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import Ctx, UserCard, evaluate, load  # noqa: E402


def sample_holder(product, ctx):
    """A holder at the card's highest minimum spend who picked the best bonus categories for this purchase."""
    minimums = [r.get("minSpend", 0) or 0 for r in product.get("rules", [])]
    minimums.append((product.get("minSpend") or {}).get("amount", 0))
    chosen = []
    if "choice" in product:
        options = product["choice"]["options"]
        hits = [o["id"] for o in options if ctx.category in o["categories"]]
        rest = [o["id"] for o in options if o["id"] not in hits]
        chosen = (hits + rest)[: product["choice"]["pick"]]
    return UserCard(product["id"], expected=max(minimums), chosen=chosen, toggles=[])


def show(products, title, ctx, top=6):
    rows = []
    for product in products.values():
        result = evaluate(product, sample_holder(product, ctx), ctx, {}, ctx.amount, True)
        rows.append((result["net"], product, result))
    rows.sort(key=lambda row: (-row[0], row[1]["id"]))
    extras = ", foreign" if ctx.foreign else ""
    print(f"\n== {title} (S${ctx.amount:.0f}, {ctx.category}, {ctx.channel}{extras})")
    for net, product, result in rows[:top]:
        unit = "mpd" if product["rewardType"] == "miles" else "%"
        print(f"  {net / ctx.amount * 100:6.2f}%  {product['id']:<28} {result['rate']}{unit:<4} {result['label'][:50]}")


SCENARIOS = [
    ("Grab ride", dict(category="rideHailing", channel="online", merchant="Grab")),
    ("SimplyGo bus & MRT", dict(category="publicTransport", channel="applePay", merchant="SimplyGo")),
    ("Shopee", dict(category="onlineShopping", channel="online", merchant="Shopee")),
    ("Food delivery", dict(category="foodDelivery", channel="online", merchant="foodpanda", amount=30)),
    ("Dining with Apple Pay", dict(category="dining", channel="applePay", amount=80)),
    ("Groceries with Apple Pay", dict(category="groceries", channel="applePay", merchant="FairPrice", amount=120)),
    ("Flights online", dict(category="flights", channel="online", merchant="Singapore Airlines", amount=800)),
    ("Agoda", dict(category="travelBooking", channel="online", merchant="Agoda", amount=300)),
    ("Overseas with Apple Pay", dict(category="shopping", channel="applePay", foreign=True, amount=200)),
    ("Petrol", dict(category="petrol", channel="cardTap", merchant="Shell", amount=80)),
    ("Insurance & bills", dict(category="bills", channel="online", amount=300)),
]

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 Tools/rankings.py catalog/cards_sg.json")
        sys.exit(2)
    catalog = load(sys.argv[1])
    # Evaluate as of today in Singapore, so promos past their end date drop out.
    today = datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None, hour=12, minute=0, second=0, microsecond=0)
    print(f"Rankings as of {today:%Y-%m-%d}")
    for name, spec in SCENARIOS:
        spec = dict(spec)
        spec.setdefault("amount", 100)
        spec["when"] = today
        show(catalog, name, Ctx(**spec))
