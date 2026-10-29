"""Builds cards_sg.json — the Singapore card catalog for CardWise.

Rates reflect public sources as of mid-October 2026 (MileLion, MainlyMiles, SingSaver,
MoneySmart, YouTrip blog, issuer pages). Rates are TOTAL earn rates:
  cashback cards -> percent (e.g. 10 = 10%)
  miles cards    -> miles per S$1 (mpd)

Usage:  python3 Tools/catalog.py <output.json>
The script validates every card, refuses to drop a card that the existing output file has,
and refuses to publish changed data without a higher REVISION.
"""
import json, os, re, sys
from datetime import datetime

# ───────────────────────── Publishing metadata ─────────────────────────
# The daily updater edits these (see UPDATING.md in the catalog repo):
#   REVISION  goes up on every publish: yyyymmddNN (e.g. 2026101901). The app only installs a higher revision.
#   CHECKED   the day the terms were last checked against the sources (Singapore time).
#   UPDATED   the day any card's terms last changed.
#   CHANGES   newest first, one short plain-English line per change. The app shows these under "What's changed".
SCHEMA_VERSION = 1
VERSION = "2026.10.30"
REVISION = 2026103001
CHECKED = "2026-10-30"
UPDATED = "2026-10-25"
CHANGES = [
    {"date": "2026-10-25", "text": "Trust Freedom (Bonus mode): 5% tier capped at S$30 a quarter (15% tier keeps the S$250 cap)."},
    {"date": "2026-10-20", "text": "UOB EVOL: overseas cashback promo extended to 31 Dec 2027."},
    {"date": "2026-10-19", "text": "Mari Credit Card: 0% FX fee and 1.5% overseas cashback promo extended to 31 Dec 2027."},
    {"date": "2026-10-18", "text": "First published catalog: 33 Singapore cards from 10 banks."},
]

CATEGORIES = ["dining", "foodDelivery", "groceries", "publicTransport", "rideHailing", "petrol",
              "flights", "hotels", "travelBooking", "onlineShopping", "shopping", "entertainment",
              "subscriptions", "health", "bills", "walletTopUp", "others"]
CHANNELS = ["online", "applePay", "cardTap", "qrCode"]
PERIODS = ["calendarMonth", "statementMonth", "calendarQuarter", "calendarYear"]

NO_BONUS = ["bills", "walletTopUp"]  # govt, education, insurance, top-ups: usually excluded from bonuses


def cap(kind, amount, period, pool, tiers=None):
    c = {"kind": kind, "amount": amount, "period": period, "pool": pool}
    if tiers:
        c["tiers"] = tiers
    return c


P = []

# ───────────────────────── Miles: specialised 4 mpd cards ─────────────────────────
CITI_POOL = cap("spend", 1000, "statementMonth", "citi-rewards-4mpd")
P.append(dict(
    id="citi-rewards", name="Citi Rewards Card", issuer="Citi", network="Mastercard",
    rewardType="miles", baseRate=0.4, foreignBaseRate=0.4, fxFeePercent=3.25, colorHex="#1F5FA8",
    annualFee="S$196.20 (first year waived)",
    toggles=[dict(id="amaze", title="I pay through Instarem Amaze",
                  detail="Amaze turns in-store and overseas taps into online spend, so they earn 4 mpd (about 2% FX fee on foreign currency).")],
    rules=[
        dict(id="online", label="Online & in-app (not travel)", rate=4, channels=["online"], currency="any",
             excludeCategories=["flights", "hotels", "travelBooking"] + NO_BONUS, cap=CITI_POOL,
             note="Pay with the card itself inside apps. Apple Pay or Google Pay inside an app earns only 0.4 mpd."),
        dict(id="shopping", label="Clothes, shoes, bags & department stores", rate=4, categories=["shopping"],
             channels=["applePay", "cardTap"], currency="local", cap=CITI_POOL),
        dict(id="amaze-local", label="In-store through Amaze", rate=4, channels=["applePay", "cardTap"], currency="local",
             requiresToggle="amaze", excludeCategories=["flights", "hotels", "travelBooking"] + NO_BONUS, cap=CITI_POOL),
        dict(id="amaze-fcy", label="Overseas through Amaze", rate=4, channels=["applePay", "cardTap"], currency="foreign",
             requiresToggle="amaze", fxFeeOverride=2.0, excludeCategories=["flights", "hotels", "travelBooking"] + NO_BONUS,
             cap=CITI_POOL),
    ],
    highlights=["4 mpd on online spend except travel — S$1,000 cap per statement month",
                "4 mpd on clothes, shoes, bags and department stores in store",
                "Points last up to 5 years with 11 airline & hotel partners"],
    warnings=["Airlines, hotels and travel agencies earn 0.4 mpd",
              "Citi Rewards Visa was retired on 15 Oct 2026 — the Mastercard version continues"],
))

P.append(dict(
    id="dbs-womans-world", name="DBS Woman's World Card", issuer="DBS", network="Mastercard",
    rewardType="miles", baseRate=0.4, foreignBaseRate=1.2, fxFeePercent=3.25, colorHex="#B3123A",
    annualFee="S$196.20 (first year waived)",
    rules=[dict(id="online", label="Online spend (incl. airlines & hotels)", rate=4, channels=["online"], currency="any",
                excludeCategories=NO_BONUS, cap=cap("spend", 1000, "calendarMonth", "dbs-wwmc"))],
    highlights=["4 mpd on online spend, including airline and hotel websites — S$1,000 cap per calendar month",
                "1.2 mpd on overseas in-store spend",
                "Needs S$80,000 annual income"],
    warnings=["DBS Points expire after about a year",
              "Some government apps (e.g. HealthHub) code as government services and earn no bonus"],
))

P.append(dict(
    id="uob-preferred-visa", name="UOB Preferred Visa", issuer="UOB", network="Visa",
    rewardType="miles", baseRate=0.4, foreignBaseRate=0.4, fxFeePercent=3.25, colorHex="#0B2D6B",
    annualFee="S$196.20 (first year waived)",
    rules=[
        dict(id="contactless", label="Apple Pay tap in store (SimplyGo counts)", rate=4, channels=["applePay"], currency="any",
             excludeCategories=NO_BONUS, cap=cap("spend", 600, "calendarMonth", "uob-pv-contactless")),
        dict(id="online", label="Selected online: dining, delivery, groceries, entertainment, shopping", rate=4,
             channels=["online"], currency="any",
             categories=["dining", "foodDelivery", "groceries", "entertainment", "shopping", "onlineShopping"],
             cap=cap("spend", 600, "calendarMonth", "uob-pv-online")),
    ],
    highlights=["4 mpd when you tap with Apple Pay — S$600 cap per calendar month (SimplyGo counts)",
                "A separate 4 mpd on selected online spend — another S$600 cap",
                "Formerly the UOB Preferred Platinum Visa (renamed March 2026)"],
    warnings=["Tapping the physical card earns only 0.4 mpd — always pay with Apple Pay",
              "No bonus at government or education merchants"],
))

P.append(dict(
    id="uob-visa-signature", name="UOB Visa Signature", issuer="UOB", network="Visa",
    rewardType="miles", baseRate=0.4, foreignBaseRate=0.4, fxFeePercent=3.25, colorHex="#22285C",
    minSpend=dict(amount=1000, period="statementMonth"),
    rules=[
        dict(id="contactless", label="Contactless (card or Apple Pay) & SimplyGo, in SGD", rate=4, channels=["applePay", "cardTap"],
             currency="local", excludeCategories=NO_BONUS, cap=cap("spend", 1200, "statementMonth", "uob-vs-local")),
        dict(id="petrol", label="Petrol in SGD", rate=4, categories=["petrol"], currency="local",
             cap=cap("spend", 1200, "statementMonth", "uob-vs-local")),
        dict(id="fcy", label="Foreign-currency spend", rate=4, currency="foreign", excludeCategories=["walletTopUp"],
             cap=cap("spend", 1200, "statementMonth", "uob-vs-fcy")),
    ],
    highlights=["4 mpd on contactless (physical card works), SimplyGo and petrol — needs S$1,000, capped at S$1,200 per statement month",
                "A separate 4 mpd on foreign-currency spend with the same S$1,000 minimum and S$1,200 cap"],
    warnings=["Below S$1,000 in a statement month everything earns 0.4 mpd",
              "UOB counts the S$1,000 minimum separately for each bonus group"],
))

P.append(dict(
    id="hsbc-revolution", name="HSBC Revolution", issuer="HSBC", network="Visa",
    rewardType="miles", baseRate=0.4, foreignBaseRate=0.4, fxFeePercent=3.25, colorHex="#C8102E",
    annualFee="No annual fee",
    rules=[dict(id="bonus", label="Dining, shopping, taxis/rides, airlines & hotels — online or contactless", rate=4,
                channels=["online", "applePay", "cardTap"], currency="any",
                categories=["dining", "shopping", "onlineShopping", "health", "rideHailing", "flights", "hotels"],
                cap=cap("spend", 1000, "calendarMonth", "hsbc-revo"))],
    highlights=["4 mpd on dining, shopping, taxis & Grab rides, airlines and hotels — online or contactless, S$1,000 per calendar month",
                "8 mpd (S$1,200 cap) in months you keep S$50,000 in an HSBC Everyday Global Account",
                "No annual fee; free, instant miles transfers"],
    warnings=["Fast food (MCC 5814) and often food delivery don't earn the bonus",
              "SimplyGo bus/MRT and travel agencies (Agoda, Expedia, Klook, Trip.com) earn 0.4 mpd"],
))

LADYS_OPTIONS = [
    dict(id="beauty", title="Beauty & Wellness", categories=["health"]),
    dict(id="dining", title="Dining", categories=["dining", "foodDelivery"]),
    dict(id="entertainment", title="Entertainment", categories=["entertainment"]),
    dict(id="family", title="Family (groceries)", categories=["groceries"]),
    dict(id="fashion", title="Fashion", categories=["shopping"]),
    dict(id="transport", title="Transport", categories=["publicTransport", "rideHailing"]),
    dict(id="travel", title="Travel", categories=["flights", "hotels", "travelBooking"]),
]
P.append(dict(
    id="uob-ladys", name="UOB Lady's Card", issuer="UOB", network="Mastercard",
    rewardType="miles", baseRate=0.4, foreignBaseRate=0.4, fxFeePercent=3.25, colorHex="#8E2A63",
    annualFee="S$196.20 (first year waived)",
    choice=dict(title="Bonus category (switch each quarter in UOB TMRW)", pick=1, options=LADYS_OPTIONS),
    rules=[dict(id="chosen", label="Your chosen category", rate=4, chosenOnly=True, currency="any",
                cap=cap("spend", 1000, "calendarMonth", "uob-ladys"))],
    highlights=["4 mpd on one category you choose — S$1,000 cap per calendar month",
                "6 mpd if you keep S$10,000 in a UOB Lady's Savings Account"],
    warnings=["Remember to pick your category each quarter"],
))
P.append(dict(
    id="uob-ladys-solitaire", name="UOB Lady's Solitaire", issuer="UOB", network="Mastercard",
    rewardType="miles", baseRate=0.4, foreignBaseRate=0.4, fxFeePercent=3.25, colorHex="#5C1A44",
    choice=dict(title="Bonus categories (pick two each quarter)", pick=2, options=LADYS_OPTIONS),
    rules=[dict(id="chosen", label="Your chosen categories", rate=4, chosenOnly=True, currency="any", capPerChoice=True,
                cap=cap("spend", 750, "calendarMonth", "uob-ladys-sol"))],
    highlights=["4 mpd on two categories you choose — S$750 cap per category per calendar month",
                "6 mpd if you keep S$10,000 in a UOB Lady's Savings Account"],
    warnings=["Higher income requirement than the Lady's Card"],
))

XL_POOL = cap("spend", 1000, "calendarMonth", "maybank-xl")
P.append(dict(
    id="maybank-xl-rewards", name="Maybank XL Rewards", issuer="Maybank",
    rewardType="miles", baseRate=0.4, foreignBaseRate=0.4, fxFeePercent=3.25, colorHex="#E0A800",
    minSpend=dict(amount=500, period="calendarMonth"),
    rules=[
        dict(id="lifestyle", label="Dining, shopping, flights, hotels & entertainment", rate=4, currency="any",
             categories=["dining", "shopping", "flights", "hotels", "entertainment"], cap=XL_POOL),
        dict(id="fcy", label="All foreign-currency spend", rate=4, currency="foreign", excludeCategories=["walletTopUp"], cap=XL_POOL),
    ],
    highlights=["4 mpd on dining, shopping, flights, hotels, entertainment and all foreign-currency spend",
                "Needs S$500 a month; bonus capped at S$1,000 per calendar month"],
    warnings=["Below S$500 in a month the bonus doesn't apply"],
))

P.append(dict(
    id="ocbc-rewards", name="OCBC Rewards Card", issuer="OCBC",
    rewardType="miles", baseRate=0.4, foreignBaseRate=0.4, fxFeePercent=3.25, colorHex="#D71920",
    rules=[
        dict(id="ecommerce", label="Shopee, Lazada, TikTok Shop, Taobao & Watsons (promo)", rate=6, currency="any",
             merchants=["shopee", "lazada", "tiktok", "taobao", "watsons"], validUntil="2027-03-31",
             cap=cap("spend", 1000, "calendarMonth", "ocbc-rewards-6")),
        dict(id="shopping", label="Selected shopping (fashion, department stores, online)", rate=4, currency="any",
             categories=["shopping", "onlineShopping"], cap=cap("spend", 1110, "calendarMonth", "ocbc-rewards-4")),
    ],
    highlights=["6 mpd at Shopee, Lazada, TikTok Shop, Taobao and Watsons until 31 Mar 2027 (S$1,000 cap)",
                "4 mpd on selected shopping (S$1,110 cap)"],
    warnings=["Everything else earns just 0.4 mpd"],
))

YUU = ["cold storage", "cs fresh", "jasons", "giant", "guardian", "7-eleven", "7 eleven", "foodpanda", "gojek",
       "singtel", "chagee", "charge+"]
YUU_POOL = cap("reward", 144, "calendarMonth", "dbs-yuu")
P.append(dict(
    id="dbs-yuu", name="DBS yuu Card", issuer="DBS", network="Visa / AMEX",
    rewardType="cashback", baseRate=0.25, foreignBaseRate=0.25, fxFeePercent=3.25, colorHex="#1A1A1A",
    annualFee="S$196.20 (first year waived)",
    minSpend=dict(amount=800, period="calendarMonth"),
    rules=[
        dict(id="yuu-max", label="yuu merchants (S$800 min + 4 merchants)", rate=18, merchants=YUU, currency="local",
             tierGroup="yuu-merchants", minSpend=800, cap=YUU_POOL),
        dict(id="yuu-base", label="yuu merchants", rate=5, merchants=YUU, currency="local",
             tierGroup="yuu-merchants", minSpend=0, cap=YUU_POOL),
        dict(id="simplygo-max", label="SimplyGo bus & MRT (S$800 min)", rate=18, categories=["publicTransport"], currency="local",
             tierGroup="yuu-simplygo", minSpend=800, cap=YUU_POOL),
        dict(id="simplygo-base", label="SimplyGo bus & MRT", rate=5, categories=["publicTransport"], currency="local",
             tierGroup="yuu-simplygo", minSpend=0, cap=YUU_POOL),
    ],
    highlights=["Up to 18% back (or 10 mpd) at Cold Storage, Giant, Guardian, 7-Eleven, foodpanda, Gojek, Singtel, CHAGEE and SimplyGo",
                "Needs S$800 a month and purchases at 4 different yuu merchants",
                "5% at yuu merchants and SimplyGo even without the minimum"],
    warnings=["Spend outside yuu merchants earns only 0.25%",
              "Rewards are yuu Points (200 points = S$1), or convert to KrisFlyer miles"],
))

SIA = ["singapore airlines", "singapore air", "scoot", "krisshop", "kris+", "krisplus", "pelago"]
P.append(dict(
    id="krisflyer-uob", name="KrisFlyer UOB Credit Card", issuer="UOB", network="Mastercard",
    rewardType="miles", baseRate=1.2, foreignBaseRate=1.2, fxFeePercent=3.25, colorHex="#0F2A5F",
    annualFee="S$196.20 (first year waived)",
    rules=[
        dict(id="sia", label="Singapore Airlines, Scoot, KrisShop, Kris+ & Pelago", rate=3, merchants=SIA, currency="any"),
        dict(id="everyday", label="Dining, delivery & transport (needs S$800/yr with SIA Group)", rate=3,
             categories=["dining", "foodDelivery", "publicTransport", "rideHailing"], currency="local",
             note="Needs S$800 a year with SIA Group; bonus miles credit about 14 months later."),
        dict(id="online", label="Online shopping & travel (needs S$800/yr with SIA Group)", rate=3,
             categories=["onlineShopping", "shopping", "travelBooking"], channels=["online"], currency="local",
             note="Needs S$800 a year with SIA Group; bonus miles credit about 14 months later."),
    ],
    highlights=["3 mpd uncapped on Singapore Airlines, Scoot, KrisShop, Kris+ and Pelago",
                "3 mpd on dining, delivery, transport and online shopping once you spend S$800 a year with SIA Group",
                "1.2 mpd on everything else, no cap"],
    warnings=["Miles go straight to KrisFlyer — they expire after 3 years"],
))

# ───────────────────────── Miles: general spending ─────────────────────────
P.append(dict(
    id="uob-prvi-miles", name="UOB PRVI Miles", issuer="UOB", network="Visa / Mastercard / AMEX",
    rewardType="miles", baseRate=1.4, foreignBaseRate=2.4, fxFeePercent=3.25, colorHex="#4A4A4A",
    annualFee="S$261.60",
    highlights=["1.4 mpd locally and 2.4 mpd overseas, no cap — good for big purchases",
                "SimplyGo with Apple Pay earns 1.4 mpd"],
))
P.append(dict(
    id="citi-premiermiles", name="Citi PremierMiles", issuer="Citi", network="Mastercard",
    rewardType="miles", baseRate=1.2, foreignBaseRate=2.2, fxFeePercent=3.25, colorHex="#2C4E7E",
    annualFee="S$196.20 (first year waived)",
    highlights=["1.2 mpd locally, 2.2 mpd overseas; Citi Miles never expire",
                "Up to 10 mpd on hotels booked through Citi's Agoda/Expedia/Kaligo portals (till 31 Dec 2026)"],
    warnings=["Complimentary travel insurance ended in April 2026"],
))
P.append(dict(
    id="dbs-altitude", name="DBS Altitude", issuer="DBS", network="Visa / AMEX",
    rewardType="miles", baseRate=1.3, foreignBaseRate=2.2, fxFeePercent=3.25, colorHex="#3A3F4B",
    annualFee="S$196.20",
    highlights=["1.3 mpd locally, 2.2 mpd overseas; miles never expire",
                "SimplyGo rides earn 1.3 mpd"],
))
P.append(dict(
    id="hsbc-travelone", name="HSBC TravelOne", issuer="HSBC", network="Mastercard",
    rewardType="miles", baseRate=1.2, foreignBaseRate=2.4, fxFeePercent=3.25, colorHex="#6E0F1E",
    highlights=["1.2 mpd locally, 2.4 mpd overseas",
                "Free, instant transfers to 20 airline and hotel partners"],
))
P.append(dict(
    id="maybank-world-mc", name="Maybank World Mastercard", issuer="Maybank", network="Mastercard",
    rewardType="miles", baseRate=0.4, foreignBaseRate=0.4, fxFeePercent=3.25, colorHex="#1D1D1B",
    minSpend=dict(amount=800, period="calendarMonth"),
    rules=[
        dict(id="petrol", label="Petrol in Singapore (in person)", rate=4, categories=["petrol"],
             channels=["applePay", "cardTap"], currency="local", minSpend=0),
        dict(id="fcy-high", label="Foreign currency (S$4,000+ month)", rate=3.2, currency="foreign", tierGroup="mwmc-fcy",
             minSpend=4000, excludeCategories=["walletTopUp"]),
        dict(id="fcy", label="Foreign currency (S$800+ month)", rate=2.8, currency="foreign", tierGroup="mwmc-fcy",
             minSpend=800, excludeCategories=["walletTopUp"]),
    ],
    highlights=["4 mpd on petrol, uncapped, no minimum",
                "2.8 mpd overseas with S$800 a month (3.2 mpd with S$4,000), no cap"],
))

# ───────────────────────── Cashback: tiered ─────────────────────────
ONE_MERCHANTS = ["grab", "shopee", "mcdonald"]
ONE_BONUS = cap("reward", 120, "statementMonth", "uob-one-bonus")
P.append(dict(
    id="uob-one", name="UOB One Card", issuer="UOB", network="Visa",
    rewardType="cashback", baseRate=0, foreignBaseRate=0, fxFeePercent=3.25, colorHex="#1C3F94",
    annualFee="S$196.20 (first year waived)",
    minSpend=dict(amount=600, period="calendarMonth"),
    rules=[
        dict(id="base-2000", label="3.33% on all spend (S$2,000/month tier)", rate=3.33, currency="any", excludeCategories=["walletTopUp"],
             tierGroup="one-base", minSpend=2000, cap=cap("reward", 200, "calendarQuarter", "uob-one-base")),
        dict(id="base-1000", label="3.33% on all spend (S$1,000/month tier)", rate=3.33, currency="any", excludeCategories=["walletTopUp"],
             tierGroup="one-base", minSpend=1000, cap=cap("reward", 100, "calendarQuarter", "uob-one-base")),
        dict(id="base-600", label="3.33% on all spend (S$600/month tier)", rate=3.33, currency="any", excludeCategories=["walletTopUp"],
             tierGroup="one-base", minSpend=600, cap=cap("reward", 60, "calendarQuarter", "uob-one-base")),
        dict(id="merchants-2000", label="Grab, Shopee & McDonald's (S$2,000 tier)", rate=10, merchants=ONE_MERCHANTS, currency="local",
             tierGroup="one-merchants", minSpend=2000, cap=ONE_BONUS),
        dict(id="merchants-600", label="Grab, Shopee & McDonald's", rate=5, merchants=ONE_MERCHANTS, currency="local",
             tierGroup="one-merchants", minSpend=600, cap=ONE_BONUS),
        dict(id="simplygo-2000", label="SimplyGo (S$2,000 tier)", rate=10, categories=["publicTransport"], currency="local",
             tierGroup="one-simplygo", minSpend=2000, cap=ONE_BONUS),
        dict(id="simplygo-600", label="SimplyGo", rate=5, categories=["publicTransport"], currency="local",
             tierGroup="one-simplygo", minSpend=600, cap=ONE_BONUS),
        dict(id="groceries-2000", label="Groceries (S$2,000 tier)", rate=10, categories=["groceries"], currency="local",
             tierGroup="one-groceries", minSpend=2000, cap=ONE_BONUS),
        dict(id="groceries-1000", label="Groceries (S$1,000 tier)", rate=5, categories=["groceries"], currency="local",
             tierGroup="one-groceries", minSpend=1000, cap=ONE_BONUS),
    ],
    highlights=["S$60 / S$100 / S$200 per quarter for spending S$600 / S$1,000 / S$2,000 every month (min 10 purchases a month)",
                "5–10% on Grab, Shopee, McDonald's and SimplyGo; groceries join at higher tiers"],
    warnings=["Miss the minimum in any month and you get nothing for that quarter",
              "GrabPay and ShopeePay top-ups are excluded"],
))

P.append(dict(
    id="uob-evol", name="UOB EVOL Card", issuer="UOB", network="Visa",
    rewardType="cashback", baseRate=0.3, foreignBaseRate=0.3, fxFeePercent=3.25, colorHex="#2B6CB0",
    annualFee="No annual fee (from 1 July 2026)",
    minSpend=dict(amount=800, period="statementMonth"),
    rules=[
        dict(id="online-contactless", label="Local online & Apple Pay", rate=10, channels=["online", "applePay"], currency="local",
             excludeCategories=NO_BONUS, cap=cap("reward", 30, "statementMonth", "evol-online")),
        dict(id="subscriptions", label="Telco, streaming & gym bills", rate=10, categories=["subscriptions"], currency="local",
             cap=cap("reward", 20, "statementMonth", "evol-subs")),
        dict(id="fcy-promo", label="Overseas spend, 0% FX fee (promo)", rate=1, currency="foreign", minSpend=0, fxFeeOverride=0,
             validUntil="2027-12-31", excludeCategories=["walletTopUp"],
             note="0.5% in China and Europe (and Australia from 1 Jan 2027)."),
    ],
    highlights=["10% on local online and Apple Pay spend (S$30 cap) and on telco, streaming and gym bills (S$20 cap) with S$800 a statement month",
                "0% FX fee plus up to 1% cashback overseas until 31 Dec 2027"],
    warnings=["Below S$800 you earn 0.3%",
              "Unused UOB cashback is forfeited after two years or when you close the card"],
))

CAP365 = cap("reward", 80, "calendarMonth", "ocbc-365", tiers=[dict(minSpend=1600, amount=160)])
P.append(dict(
    id="ocbc-365", name="OCBC 365 Card", issuer="OCBC", network="Visa",
    rewardType="cashback", baseRate=0.25, foreignBaseRate=0.25, fxFeePercent=3.25, colorHex="#E4002B",
    annualFee="S$196.20 (first 2 years waived)",
    minSpend=dict(amount=800, period="calendarMonth"),
    rules=[
        dict(id="petrol", label="Petrol", rate=6, categories=["petrol"], currency="local", cap=CAP365),
        dict(id="dining", label="Dining & food delivery", rate=5, categories=["dining", "foodDelivery"], currency="any", cap=CAP365),
        dict(id="everyday", label="Groceries, land transport, streaming, utilities & Watsons", rate=3,
             categories=["groceries", "publicTransport", "rideHailing", "subscriptions", "bills", "health"], currency="local", cap=CAP365),
    ],
    highlights=["6% petrol, 5% dining & food delivery, 3% groceries, transport, streaming and utilities",
                "Needs S$800 a month; S$80 cap (S$160 if you spend S$1,600)"],
    warnings=["Bills here means utilities only — insurance and government payments earn nothing"],
))

P.append(dict(
    id="ocbc-frank", name="OCBC FRANK Card", issuer="OCBC",
    rewardType="cashback", baseRate=0.3, foreignBaseRate=0.3, fxFeePercent=3.25, colorHex="#F26B3A",
    minSpend=dict(amount=800, period="calendarMonth"),
    rules=[
        dict(id="simplygo", label="SimplyGo with Apple Pay (8% + 2% green bonus)", rate=10, categories=["publicTransport"],
             channels=["applePay"], currency="local", cap=cap("reward", 25, "calendarMonth", "frank-contactless")),
        dict(id="online", label="Online spend", rate=8, channels=["online"], currency="any", excludeCategories=NO_BONUS,
             cap=cap("reward", 25, "calendarMonth", "frank-online")),
        dict(id="contactless", label="Apple Pay in store", rate=8, channels=["applePay"], currency="local", excludeCategories=NO_BONUS,
             cap=cap("reward", 25, "calendarMonth", "frank-contactless")),
        dict(id="fcy", label="Overseas in-store", rate=8, channels=["applePay", "cardTap"], currency="foreign",
             excludeCategories=NO_BONUS, cap=cap("reward", 25, "calendarMonth", "frank-fcy")),
    ],
    highlights=["8% on online, Apple Pay and overseas in-store spend; 10% on SimplyGo",
                "Needs S$800 a month; S$25 cap per category"],
))

MFF_OPTIONS = [
    dict(id="groceries", title="Groceries", categories=["groceries"]),
    dict(id="dining", title="Dining & food delivery", categories=["dining", "foodDelivery"]),
    dict(id="transport", title="Transport (SimplyGo, rides, petrol)", categories=["publicTransport", "rideHailing", "petrol"]),
    dict(id="telco", title="Data, telco & online TV", categories=["subscriptions"]),
    dict(id="retail", title="Retail & pets", categories=["shopping"]),
    dict(id="fashion", title="Online fashion", categories=["onlineShopping"]),
    dict(id="entertainment", title="Entertainment", categories=["entertainment"]),
    dict(id="pharmacy", title="Pharmacy & wellness", categories=["health"]),
]
P.append(dict(
    id="maybank-family-friends", name="Maybank Family & Friends", issuer="Maybank", network="Mastercard",
    rewardType="cashback", baseRate=0.3, foreignBaseRate=0.3, fxFeePercent=3.25, colorHex="#F5B400",
    minSpend=dict(amount=800, period="calendarMonth"),
    choice=dict(title="Your 5 cashback categories", pick=5, options=MFF_OPTIONS),
    rules=[dict(id="chosen", label="Your chosen categories", rate=8, chosenOnly=True, currency="local", capPerChoice=True,
                cap=cap("reward", 25, "calendarMonth", "mff"))],
    highlights=["8% on five categories you choose — S$25 cap each (S$125 total) with S$800 a month",
                "SimplyGo works when the card is in Apple Wallet",
                "The one major card that can still earn on GrabPay top-ups without Grab's 1% fee (with the right category)"],
    warnings=["'Online fashion' covers fashion merchants only, not all of Shopee or Lazada"],
))

P.append(dict(
    id="hsbc-live-plus", name="HSBC Live+ Card", issuer="HSBC", network="Visa",
    rewardType="cashback", baseRate=0.3, foreignBaseRate=0.3, fxFeePercent=3.25, colorHex="#A6192E",
    annualFee="S$196.20 (first year waived)",
    minSpend=dict(amount=600, period="calendarMonth"),
    rules=[
        dict(id="lifestyle", label="Dining, shopping & entertainment", rate=5, currency="any",
             categories=["dining", "shopping", "onlineShopping", "entertainment"],
             cap=cap("reward", 250, "calendarQuarter", "live-plus")),
        dict(id="petrol", label="Petrol", rate=5, categories=["petrol"], currency="local",
             cap=cap("reward", 250, "calendarQuarter", "live-plus")),
    ],
    highlights=["5% on dining, shopping and entertainment (8% in your first two quarters), 5% on petrol",
                "Needs S$600 a month; S$250 cap per calendar quarter"],
    warnings=["Miss S$600 in any month and that quarter drops to 0.3%"],
))

P.append(dict(
    id="dbs-live-fresh", name="DBS Live Fresh Card", issuer="DBS", network="Visa",
    rewardType="cashback", baseRate=0.3, foreignBaseRate=0.3, fxFeePercent=3.25, colorHex="#00A19B",
    annualFee="S$196.20",
    minSpend=dict(amount=800, period="calendarMonth"),
    rules=[
        dict(id="shopping", label="Shopping (in store, contactless & online)", rate=6, categories=["shopping", "onlineShopping"],
             currency="any", cap=cap("reward", 50, "calendarMonth", "lf-shopping")),
        dict(id="transport", label="Transport (SimplyGo & rides)", rate=6, categories=["publicTransport", "rideHailing"],
             currency="any", cap=cap("reward", 20, "calendarMonth", "lf-transport")),
    ],
    highlights=["6% on shopping (S$50 cap) and transport (S$20 cap) with S$800 a calendar month",
                "Counts in store, contactless and online, locally and overseas"],
))

SMRT_POOL = cap("reward", 600, "calendarYear", "citi-smrt")
P.append(dict(
    id="citi-smrt", name="Citi SMRT Card", issuer="Citi", network="Mastercard",
    rewardType="cashback", baseRate=0.3, foreignBaseRate=0.3, fxFeePercent=3.25, colorHex="#CC2229",
    annualFee="S$196.20 (first year waived)",
    minSpend=dict(amount=500, period="calendarMonth"),
    rules=[
        dict(id="everyday", label="SimplyGo, groceries, taxis & ride-hailing", rate=5,
             categories=["publicTransport", "groceries", "rideHailing"], currency="local", cap=SMRT_POOL),
        dict(id="online", label="Online spend", rate=5, channels=["online"], currency="local", excludeCategories=NO_BONUS, cap=SMRT_POOL),
    ],
    highlights=["5% (as SMRT$) on SimplyGo, groceries, taxis/ride-hailing and online spend with S$500 a month",
                "Capped at S$600 a year"],
))

# ───────────────────────── Cashback: flat rate ─────────────────────────
P.append(dict(
    id="uob-absolute", name="UOB Absolute Cashback", issuer="UOB", network="AMEX",
    rewardType="cashback", baseRate=1.7, foreignBaseRate=1.7, fxFeePercent=3.25, colorHex="#B87333",
    annualFee="S$196.20 (first year waived)",
    highlights=["1.7% on almost everything — no minimum, no cap", "Earns even on insurance and utilities"],
    warnings=["It's an AMEX — not every merchant accepts it", "GrabPay top-ups earn only 0.3%"],
))
P.append(dict(
    id="citi-cashback-plus", name="Citi Cash Back+", issuer="Citi", network="Mastercard",
    rewardType="cashback", baseRate=1.6, foreignBaseRate=1.6, fxFeePercent=3.25, colorHex="#4F86C6",
    annualFee="S$196.20 (first year waived)",
    highlights=["1.6% on everything, no minimum, no cap"],
    warnings=["Citi holds cashback until it reaches S$50"],
))
P.append(dict(
    id="ocbc-infinity", name="OCBC INFINITY Cashback", issuer="OCBC",
    rewardType="cashback", baseRate=1.6, foreignBaseRate=1.6, fxFeePercent=3.25, colorHex="#7A0019",
    highlights=["1.6% on everything, local or overseas, credited automatically"],
))
P.append(dict(
    id="amex-true-cashback", name="AMEX True Cashback", issuer="American Express", network="AMEX",
    rewardType="cashback", baseRate=1.5, foreignBaseRate=1.5, fxFeePercent=3.25, colorHex="#2E77BB",
    highlights=["1.5% on everything, no cap", "3% on your first S$5,000 in the first 6 months"],
    warnings=["Not accepted everywhere", "Grab wallet top-ups don't earn cashback"],
))
P.append(dict(
    id="sc-simply-cash", name="StanChart Simply Cash", issuer="Standard Chartered", network="Visa",
    rewardType="cashback", baseRate=1.5, foreignBaseRate=1.5, fxFeePercent=3.25, colorHex="#0E8A43",
    highlights=["1.5% on everything, no minimum, no cap"],
))
P.append(dict(
    id="mari-credit", name="Mari Credit Card", issuer="MariBank", network="Mastercard",
    rewardType="cashback", baseRate=1.5, foreignBaseRate=0, fxFeePercent=3.0, colorHex="#F26522",
    annualFee="No annual fee",
    rules=[dict(id="fcy-promo", label="Overseas: 1.5% back and 0% FX fee (promo)", rate=1.5, currency="foreign", fxFeeOverride=0,
                validUntil="2027-12-31", excludeCategories=["walletTopUp"],
                cap=cap("spend", 1500, "calendarMonth", "mari-fcy"))],
    highlights=["1.5% on everything in SGD — no minimum, no cap, no annual fee",
                "0% FX fee and 1.5% back overseas (up to S$1,500 a month) until 31 Dec 2027",
                "On Shopee, pay with Mari Instant Checkout to get the 1.5% as Shopee Coins"],
    warnings=["No ATM withdrawals with this card"],
))

TRUST_OPTIONS = [
    dict(id="dining", title="Dining", categories=["dining", "foodDelivery"]),
    dict(id="shopping", title="Shopping", categories=["shopping", "onlineShopping"]),
    dict(id="travel", title="Travel", categories=["flights", "hotels", "travelBooking"]),
    dict(id="wellness", title="Wellness", categories=["health"]),
    dict(id="transport", title="Transport", categories=["publicTransport", "rideHailing", "petrol"]),
    dict(id="entertainment", title="Entertainment", categories=["entertainment"]),
]
P.append(dict(
    id="trust-freedom-unlimited", name="Trust Freedom (Unlimited mode)", issuer="Trust", network="Visa",
    rewardType="cashback", baseRate=1.5, foreignBaseRate=0.5, fxFeePercent=0, colorHex="#5B2C83",
    annualFee="No annual fee",
    highlights=["Up to 1.5% on local spend, 0.5% overseas — no minimum, no cap", "No FX fee — converted at Visa's rate"],
    warnings=["You pick one reward mode per quarter in the Trust app"],
))
P.append(dict(
    id="trust-freedom-bonus", name="Trust Freedom (Bonus mode)", issuer="Trust", network="Visa",
    rewardType="cashback", baseRate=1.0, foreignBaseRate=0.5, fxFeePercent=0, colorHex="#6E3AA0",
    annualFee="No annual fee",
    minSpend=dict(amount=500, period="calendarMonth"),
    choice=dict(title="Bonus category (one per quarter)", pick=1, options=TRUST_OPTIONS),
    rules=[
        dict(id="bonus-15", label="Your bonus category (top tier)", rate=15, chosenOnly=True, currency="local",
             tierGroup="trust-bonus", minSpend=2000, cap=cap("reward", 250, "calendarQuarter", "trust-bonus")),
        dict(id="bonus-5", label="Your bonus category", rate=5, chosenOnly=True, currency="local",
             tierGroup="trust-bonus", minSpend=500, cap=cap("reward", 30, "calendarQuarter", "trust-bonus")),
    ],
    highlights=["15% on one category you pick with S$2,000 every month (S$250 cap per quarter), or 5% with S$500 (S$30 cap); 1% on other local spend",
                "No FX fee"],
    warnings=["You must hit the minimum in all three months of the quarter to get the bonus"],
))
P.append(dict(
    id="trust-freedom-stockback", name="Trust Freedom (Stockback mode)", issuer="Trust", network="Visa",
    rewardType="cashback", baseRate=2.0, foreignBaseRate=0.5, fxFeePercent=0, colorHex="#40205E",
    annualFee="No annual fee",
    rules=[dict(id="promo", label="3% Stockback, local & overseas (promo)", rate=3, currency="any", validUntil="2026-12-31",
                excludeCategories=["walletTopUp"], cap=cap("reward", 500, "calendarQuarter", "trust-stockback"))],
    highlights=["3% on local and overseas spend until 31 Dec 2026 (S$500 cap per quarter), then 2% local / 0.5% overseas",
                "No FX fee"],
    warnings=["Paid as fractional US shares, not cash — values can go down"],
))


def validate(products):
    ids = set()
    errors = []
    for p in products:
        pid = p["id"]
        if pid in ids:
            errors.append(f"duplicate id {pid}")
        ids.add(pid)
        for k in ("name", "issuer", "rewardType", "baseRate"):
            if k not in p:
                errors.append(f"{pid}: missing {k}")
        if p["rewardType"] not in ("cashback", "miles"):
            errors.append(f"{pid}: bad rewardType")
        opts = set()
        if "choice" in p:
            for o in p["choice"]["options"]:
                opts.add(o["id"])
                for c in o["categories"]:
                    if c not in CATEGORIES:
                        errors.append(f"{pid}: option {o['id']} bad category {c}")
        if "minSpend" in p and p["minSpend"]["period"] not in PERIODS:
            errors.append(f"{pid}: bad minSpend period")
        toggles = {t["id"] for t in p.get("toggles", [])}
        rids = set()
        for r in p.get("rules", []):
            rid = r["id"]
            if rid in rids:
                errors.append(f"{pid}: duplicate rule {rid}")
            rids.add(rid)
            for c in r.get("categories", []) + r.get("excludeCategories", []):
                if c not in CATEGORIES:
                    errors.append(f"{pid}/{rid}: bad category {c}")
            for ch in r.get("channels", []):
                if ch not in CHANNELS:
                    errors.append(f"{pid}/{rid}: bad channel {ch}")
            if r.get("currency", "any") not in ("local", "foreign", "any"):
                errors.append(f"{pid}/{rid}: bad currency")
            if r.get("chosenOnly") and "choice" not in p:
                errors.append(f"{pid}/{rid}: chosenOnly without choice")
            if r.get("requiresToggle") and r["requiresToggle"] not in toggles:
                errors.append(f"{pid}/{rid}: unknown toggle")
            if "cap" in r:
                c = r["cap"]
                if c["kind"] not in ("spend", "reward") or c["period"] not in PERIODS:
                    errors.append(f"{pid}/{rid}: bad cap")
                if c["kind"] == "reward" and p["rewardType"] == "miles":
                    errors.append(f"{pid}/{rid}: reward cap on miles card")
            if (r.get("minSpend") or 0) > 0 and "minSpend" not in p:
                errors.append(f"{pid}/{rid}: rule minSpend but product has no minSpend period")
            allowed = {"id", "label", "rate", "categories", "excludeCategories", "channels", "currency", "merchants",
                       "chosenOnly", "requiresToggle", "minSpend", "tierGroup", "cap", "capPerChoice", "fxFeeOverride",
                       "validUntil", "note"}
            extra = set(r) - allowed
            if extra:
                errors.append(f"{pid}/{rid}: unknown keys {extra}")
        allowedP = {"id", "name", "issuer", "network", "rewardType", "baseRate", "foreignBaseRate", "fxFeePercent", "rules",
                    "minSpend", "choice", "toggles", "annualFee", "highlights", "warnings", "colorHex"}
        extra = set(p) - allowedP
        if extra:
            errors.append(f"{pid}: unknown keys {extra}")
        errors += sanity(p)
    if len(products) < 10:
        errors.append("fewer than 10 cards — something went wrong")
    return errors


def is_day(text):
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


def sanity(p):
    """Number and text bounds. The app applies the same limits and rejects a catalog that breaks them."""
    pid, errors = p["id"], []
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,79}", pid):
        errors.append(f"{pid}: id must be lower-case letters, digits and dashes")
    if not p.get("name", "").strip() or not p.get("issuer", "").strip():
        errors.append(f"{pid}: empty name or issuer")
    for key in ("baseRate", "foreignBaseRate"):
        if key in p and not 0 <= p[key] <= 50:
            errors.append(f"{pid}: {key} {p[key]} outside 0–50")
    if "fxFeePercent" in p and not 0 <= p["fxFeePercent"] <= 10:
        errors.append(f"{pid}: fxFeePercent outside 0–10")
    if "colorHex" in p and not re.fullmatch(r"#[0-9A-Fa-f]{6}", p["colorHex"]):
        errors.append(f"{pid}: colorHex must look like #1A2B3C")
    if "minSpend" in p and not 0 <= p["minSpend"]["amount"] <= 100000:
        errors.append(f"{pid}: minSpend amount outside 0–100,000")
    if "choice" in p:
        ch = p["choice"]
        if not ch["options"] or not 1 <= ch["pick"] <= len(ch["options"]):
            errors.append(f"{pid}: choice pick must be between 1 and the number of options")
        if any(not o["categories"] for o in ch["options"]):
            errors.append(f"{pid}: every choice option needs at least one category")
    for r in p.get("rules", []):
        rid = f"{pid}/{r['id']}"
        if not 0 <= r["rate"] <= 50:
            errors.append(f"{rid}: rate {r['rate']} outside 0–50")
        if not 0 <= (r.get("minSpend") or 0) <= 100000:
            errors.append(f"{rid}: minSpend outside 0–100,000")
        if "fxFeeOverride" in r and not 0 <= r["fxFeeOverride"] <= 10:
            errors.append(f"{rid}: fxFeeOverride outside 0–10")
        if "validUntil" in r and not is_day(r["validUntil"]):
            errors.append(f"{rid}: validUntil must be YYYY-MM-DD")
        if "cap" in r:
            c = r["cap"]
            if not 0 < c["amount"] <= 1_000_000:
                errors.append(f"{rid}: cap amount must be above 0")
            for t in c.get("tiers", []):
                if t["minSpend"] < 0 or t["amount"] <= 0:
                    errors.append(f"{rid}: bad cap tier")
        if len(r.get("label", "")) > 200 or len(r.get("note", "")) > 500:
            errors.append(f"{rid}: label or note too long")
    for key in ("highlights", "warnings"):
        if len(p.get(key, [])) > 12 or any(len(line) > 300 for line in p.get(key, [])):
            errors.append(f"{pid}: too many or too long {key}")
    return errors


def validate_meta():
    errors = []
    if not re.fullmatch(r"20\d{8}", str(REVISION)):
        errors.append("REVISION must look like yyyymmddNN, e.g. 2026101901")
    for name, value in (("CHECKED", CHECKED), ("UPDATED", UPDATED)):
        if not is_day(value):
            errors.append(f"{name} must be YYYY-MM-DD")
    if not CHANGES or any(not is_day(c.get("date")) or not c.get("text", "").strip() or len(c["text"]) > 200
                          for c in CHANGES):
        errors.append("CHANGES entries need a YYYY-MM-DD date and a short text (max 200 characters)")
    return errors


def compare_with_previous(path, out):
    """Never drop a card the app may already know about, and never republish changed data under an old revision."""
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            old = json.load(f)
    except (OSError, ValueError):
        return []
    errors = []
    missing = {p["id"] for p in old.get("products", [])} - {p["id"] for p in out["products"]}
    if missing:
        errors.append(f"cards removed: {sorted(missing)} — never delete a card; add a warning such as "
                      "'No longer open to new applicants' instead")
    old_revision = old.get("revision", 0)
    if out["revision"] < old_revision:
        errors.append(f"REVISION {out['revision']} is lower than the published {old_revision}")
    elif out["revision"] == old_revision and out != old:
        errors.append(f"data changed but REVISION is still {old_revision} — bump it (yyyymmddNN)")
    return errors


if __name__ == "__main__":
    errs = validate(P) + validate_meta()
    out = {"schemaVersion": SCHEMA_VERSION, "version": VERSION, "revision": REVISION,
           "updated": UPDATED, "checked": CHECKED, "currency": "SGD",
           "note": "Estimates from public sources (MileLion, MainlyMiles, SingSaver, MoneySmart, YouTrip, issuer pages). "
                   "Banks change terms often — always check the bank's T&Cs.",
           "changes": CHANGES[:20],
           "products": P}
    if len(sys.argv) != 2:
        print("usage: python3 Tools/catalog.py <output.json>")
        sys.exit(2)
    path = sys.argv[1]
    errs += compare_with_previous(path, out)
    if errs:
        print("NOT WRITTEN — fix these first:")
        print("\n".join("  - " + e for e in errs))
        sys.exit(1)
    with open(path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {len(P)} cards, revision {REVISION}, checked {CHECKED} -> {path}")
