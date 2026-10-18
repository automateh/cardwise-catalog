"""Python prototype of the CardWise rewards engine (mirrors RewardsEngine.swift)."""
import json, calendar
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta

MONTHS_IN = {"calendarMonth": 1, "statementMonth": 1, "calendarQuarter": 3, "calendarYear": 12}


def clamp_day(y, m, d):
    return min(d, calendar.monthrange(y, m)[1])


def add_months(y, m, k):
    m2 = m - 1 + k
    return y + m2 // 12, m2 % 12 + 1


def period_interval(period, when: datetime, statement_day=None):
    d = when.date() if isinstance(when, datetime) else when
    if period == "statementMonth" and statement_day:
        end_this = date(d.year, d.month, clamp_day(d.year, d.month, statement_day))
        if d <= end_this:
            py, pm = add_months(d.year, d.month, -1)
            start = date(py, pm, clamp_day(py, pm, statement_day)) + timedelta(days=1)
            end = end_this + timedelta(days=1)
        else:
            start = end_this + timedelta(days=1)
            ny, nm = add_months(d.year, d.month, 1)
            end = date(ny, nm, clamp_day(ny, nm, statement_day)) + timedelta(days=1)
        return start, end
    if period == "calendarQuarter":
        qm = (d.month - 1) // 3 * 3 + 1
        start = date(d.year, qm, 1)
        ey, em = add_months(d.year, qm, 3)
        return start, date(ey, em, 1)
    if period == "calendarYear":
        return date(d.year, 1, 1), date(d.year + 1, 1, 1)
    start = date(d.year, d.month, 1)
    ey, em = add_months(d.year, d.month, 1)
    return start, date(ey, em, 1)


@dataclass
class Ctx:
    category: str
    channel: str
    foreign: bool = False
    merchant: str = None
    amount: float = 100.0
    when: datetime = field(default_factory=lambda: datetime(2026, 10, 18, 12))


@dataclass
class UserCard:
    product_id: str
    expected: float = 0.0
    statement_day: int = None
    chosen: list = field(default_factory=list)
    toggles: list = field(default_factory=list)
    cid: str = None


def units_per_dollar(product, rate):
    return rate / 100.0 if product["rewardType"] == "cashback" else rate


def to_sgd(product, units, cpm):
    return units if product["rewardType"] == "cashback" else units * cpm / 100.0


def rule_matches(rule, product, card, ctx):
    """returns (ok, option_id)"""
    vu = rule.get("validUntil")
    if vu and ctx.when.date() > date.fromisoformat(vu):
        return False, None
    cats = rule.get("categories")
    if cats is not None and ctx.category not in cats:
        return False, None
    if ctx.category in rule.get("excludeCategories", []):
        return False, None
    chans = rule.get("channels")
    if chans is not None and ctx.channel not in chans:
        return False, None
    cur = rule.get("currency", "any")
    if cur == "local" and ctx.foreign:
        return False, None
    if cur == "foreign" and not ctx.foreign:
        return False, None
    m = rule.get("merchants")
    if m is not None:
        if not ctx.merchant:
            return False, None
        low = ctx.merchant.lower()
        if not any(k in low for k in m):
            return False, None
    tog = rule.get("requiresToggle")
    if tog and tog not in card.toggles:
        return False, None
    opt = None
    if rule.get("chosenOnly"):
        options = {o["id"]: o for o in product.get("choice", {}).get("options", [])}
        hit = [oid for oid in card.chosen if oid in options and ctx.category in options[oid]["categories"]]
        if not hit:
            return False, None
        opt = hit[0]
    return True, opt


def rule_min(rule, product):
    if "minSpend" in rule:
        return rule["minSpend"] or 0
    return (product.get("minSpend") or {}).get("amount", 0)


def evaluate(product, card, ctx, ledger, min_progress, assume_expected, cpm=1.5):
    base = product.get("foreignBaseRate", product["baseRate"]) if ctx.foreign else product["baseRate"]
    fx_default = product.get("fxFeePercent", 3.25)
    amount = ctx.amount

    def mk(label, rate, units, fx_pct, notes, consumption=None, cap_left=None, bonus=False):
        val = to_sgd(product, units, cpm)
        fee = amount * fx_pct / 100 if ctx.foreign else 0.0
        return dict(label=label, rate=rate, units=units, value=val, fee=fee, net=val - fee, notes=notes,
                    consumption=consumption, cap_left=cap_left, bonus=bonus)

    if ctx.category == "walletTopUp":
        return mk("E-wallet top-up", 0, 0, 0, ["Top-ups usually earn no card rewards"])
    if ctx.channel == "qrCode":
        return mk("QR payment", 0, 0, 0, ["Cards can't pay SGQR codes directly"])

    best = mk("Base rate", base, amount * units_per_dollar(product, base), fx_default, [])
    min_period = (product.get("minSpend") or {}).get("period", "calendarMonth")
    expected = card.expected * MONTHS_IN[min_period]

    qualified, locked = [], []
    for rule in product.get("rules", []):
        ok, opt = rule_matches(rule, product, card, ctx)
        if not ok:
            continue
        mn = rule_min(rule, product)
        if mn > 0:
            if min_progress >= mn:
                qualified.append((rule, opt, False, mn))
            elif assume_expected and expected >= mn:
                qualified.append((rule, opt, True, mn))
            else:
                locked.append((rule, mn))
        else:
            qualified.append((rule, opt, False, 0))

    # tier groups: keep the qualified rule with the highest minimum in each group
    best_in_group = {}
    for q in qualified:
        g = q[0].get("tierGroup")
        if g and (g not in best_in_group or q[3] > best_in_group[g][3]):
            best_in_group[g] = q
    qualified = [q for q in qualified if not q[0].get("tierGroup") or best_in_group[q[0]["tierGroup"]] is q]

    for rule, opt, assumed, mn in qualified:
        rate = rule["rate"]
        per_bonus = units_per_dollar(product, rate)
        per_base = units_per_dollar(product, base)
        eligible = amount
        notes = []
        cons = None
        cap_left = None
        c = rule.get("cap")
        if c:
            pool = c.get("pool") or rule["id"]
            if rule.get("capPerChoice") and opt:
                pool += ":" + opt
            start, _ = period_interval(c["period"], ctx.when, card.statement_day)
            key = f"{pool}|{start.isoformat()}"
            used = ledger.get(key, (0.0, 0.0))
            cap_amt = c["amount"]
            for t in c.get("tiers", []):
                if max(min_progress, expected) >= t["minSpend"]:
                    cap_amt = max(cap_amt, t["amount"])
            if c["kind"] == "spend":
                left = max(0.0, cap_amt - used[0])
            else:
                left = max(0.0, cap_amt - used[1]) / per_bonus if per_bonus > 0 else 0.0
            eligible = min(amount, left)
            cap_left = left - eligible
            cons = (key, eligible, eligible * per_bonus)
            if eligible < amount:
                notes.append(f"Bonus cap hit: S${amount - eligible:.2f} earns the base rate")
        units = eligible * per_bonus + (amount - eligible) * per_base
        fx = rule.get("fxFeeOverride", fx_default)
        if assumed:
            notes.append(f"Assumes you reach S${mn:,.0f} this period (S${min_progress:,.0f} so far)")
        if rule.get("note"):
            notes.append(rule["note"])
        cand = mk(rule["label"], rate, units, fx, notes, cons, cap_left, True)
        if cand["net"] > best["net"] + 1e-9:
            best = cand

    hint = None
    for rule, mn in locked:
        if rule["rate"] > (best["rate"] if best["bonus"] else base):
            short = mn - min_progress
            if hint is None or rule["rate"] > hint[0]:
                hint = (rule["rate"], f"Spend S${short:,.0f} more this period to unlock {rule['rate']}")
    if hint:
        best["notes"].append(hint[1])
    return best


def simulate(product, card, txns, now, cpm=1.5):
    txns = sorted(txns, key=lambda t: t["when"])
    min_period = (product.get("minSpend") or {}).get("period", "calendarMonth")
    totals = {}
    for t in txns:
        s, _ = period_interval(min_period, t["when"], card.statement_day)
        totals[s] = totals.get(s, 0) + t["ctx"].amount
    ledger, results = {}, []
    for t in txns:
        s, e = period_interval(min_period, t["when"], card.statement_day)
        current = s <= now.date() < e
        r = evaluate(product, card, t["ctx"], ledger, totals[s], current, cpm)
        if r["consumption"]:
            k, sp, rw = r["consumption"]
            u = ledger.get(k, (0.0, 0.0))
            ledger[k] = (u[0] + sp, u[1] + rw)
        results.append(r)
    return ledger, results


def load(path):
    with open(path) as f:
        data = json.load(f)
    return {p["id"]: p for p in data["products"]}
