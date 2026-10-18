# Daily update playbook

The CardWise daily update task follows this every morning, and it works the same way for anyone updating by hand.

**Goal:** `catalog/cards_sg.json` matches what Singapore banks offer today, and nothing is published on a guess.

## 0. Get ready

```bash
git pull origin main
python3 Tools/rankings.py catalog/cards_sg.json > /tmp/before.txt
```

Read the metadata at the top of `Tools/catalog.py` (`REVISION`, `CHECKED`, `CHANGES`) to see when the catalog was last checked and what changed recently.

## 1. Look for changes since `CHECKED`

Search the web for Singapore credit-card news dated after `CHECKED`. Good places to start:

- The MileLion credit-card news: https://milelion.com/category/credit-cards/
- MainlyMiles (search "MainlyMiles" with the card or month)
- SingSaver blog: https://www.singsaver.com.sg/blog
- MoneySmart credit cards: https://www.moneysmart.sg/credit-cards
- YouTrip blog (cashback cards, Trust, MariBank): https://www.you.co/sg/blog/
- The banks' own card pages, notices and T&Cs: DBS/POSB, UOB, OCBC, Citi, HSBC, Maybank, Standard Chartered, American Express, Trust and MariBank.

Useful searches include "<bank> credit card changes <Month Year>", "devaluation", "earn rate", "bonus cap", "minimum spend" and "new credit card Singapore <Month Year>".

Also check:

- **Promos ending:** has any rule with `validUntil` ended or been extended?
- **New cards:** has a popular, widely available card launched that people would want compared?
- **Withdrawn cards:** has any card stopped taking new applicants?

## 2. Decide what to change

Change a card only when **both** of these hold:

- **The source is solid.** The bank's own page, T&Cs or notice says so, **or** two independent reputable sources agree (for example MileLion and MainlyMiles).
- **The change is in effect.** For an announced future change, leave the current rule alone, mention it in the summary, and apply it on or after the effective date. If a promo has a known end date, set `validUntil` instead.

When unsure, don't change it. List it in the run summary as **needs a human look**.

## 3. Edit `Tools/catalog.py`

- **Rates are total earn rates:** percent for cashback cards, miles per S$1 for miles cards. "4 mpd (0.4 base + 3.6 bonus)" is written as `rate=4`.
- **Never change an `id` or a cap `pool` name, and never delete a card.** People's saved cards point to them. For a withdrawn card, add a warning such as "No longer open to new applicants".
- **Promos:** add `validUntil="YYYY-MM-DD"`, the last valid day in Singapore time.
- **Caps:** `kind="spend"` limits bonus-eligible spend; `kind="reward"` limits cashback paid out. Match the bank's period: calendar month, statement month, quarter or year.
- **Minimum spends:** a rule's `minSpend` overrides the card's own. Use `tierGroup` for "higher rate at higher spend" tiers.
- **New card:** copy the structure of a similar card. Use an id of the form `issuer-card-name` (lower case, dashes). Add 2–3 short `highlights` and any `warnings`.
- **Style:** keep labels, notes and highlights short and in plain English.

## 4. Publish (every day, even when nothing changed)

1. At the top of `Tools/catalog.py`, set:
   - `REVISION`: today's date in Singapore as `yyyymmdd` plus a two-digit sequence. For example `2026101901`, then `2026101902` for a second publish the same day. It must be higher than the current value.
   - `VERSION`: today as `YYYY.MM.DD`.
   - `CHECKED`: today as `YYYY-MM-DD`, Singapore time.
   - If any terms changed:
     - set `UPDATED` to today;
     - add one entry per change to the **top** of `CHANGES`, e.g. `{"date": "2026-10-19", "text": "HSBC Revolution: bonus cap raised to S$1,500 a month."}`;
     - keep the most recent 20 entries.
2. Run `python3 Tools/catalog.py catalog/cards_sg.json`. It must end with `wrote N cards…`. If it prints `NOT WRITTEN`, fix the problem. Never weaken or bypass the checks.
3. Run `python3 Tools/rankings.py catalog/cards_sg.json > /tmp/after.txt && diff /tmp/before.txt /tmp/after.txt`. Every difference must come from an intended edit or an expired promo. If not, investigate before publishing.
4. Run `git add -A && git commit -m "Card data YYYY-MM-DD: <one-line summary, or 'checked, no changes'>" && git push origin main`.

## 5. Report

Finish with a short summary covering:

- what changed, with source links;
- anything that **needs a human look**;
- the new `REVISION`.
