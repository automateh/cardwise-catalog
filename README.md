# CardWise card catalog

Public card data for **CardWise**, an iPhone app that tracks your spending and tells you which Singapore credit card or e-wallet to use for each purchase.

The app downloads [`catalog/cards_sg.json`](catalog/cards_sg.json) from this repo about once a day. Before using a download, the app checks that it:

- reads correctly;
- passes the same checks as `Tools/catalog.py`;
- has a higher `revision` than the data it already has.

If any check fails, the app keeps its current data. Only this public file is fetched; nothing about the person using the app is ever sent.

## What's here

| Path | What it is |
|---|---|
| `catalog/cards_sg.json` | The published catalog the app reads |
| `Tools/catalog.py` | The source of truth: every card's earn rules, plus validation. Running it regenerates the JSON. |
| `Tools/engine.py` | A Python copy of the app's rewards engine |
| `Tools/rankings.py` | Prints the best cards for common purchases (Grab, SimplyGo, Shopee, dining, flights, overseas…), so you can check what an edit changes |
| `UPDATING.md` | How the catalog is kept current. The daily update task follows it. |

## How updates happen

A scheduled task runs every morning (Singapore time). It:

1. checks the banks' card pages and trusted Singapore sources for changes;
2. edits `Tools/catalog.py`;
3. regenerates and validates the JSON;
4. compares the rankings before and after the edit;
5. pushes the result.

It changes a card only when the bank, or two independent reputable sources, confirm the change. Each publish raises `revision` and records the check date. Real changes are listed in `changes`, which the app shows under **What's changed**.

## Updating by hand

1. Edit `Tools/catalog.py`. Change the card, raise `REVISION` (format `yyyymmddNN`), set `CHECKED` (and `UPDATED` if terms changed), and add a line to `CHANGES`.
2. Run `python3 Tools/catalog.py catalog/cards_sg.json`. The script refuses to write if:
   - anything is invalid;
   - a card was removed;
   - the data changed without a higher revision.
3. Commit and push to `main`. The app picks the change up within a day.

## Format notes

- **Rates** are total earn rates: percent for cashback cards, miles per S$1 for miles cards.
- **Caps** have a `kind`: `spend` limits bonus-eligible spend, `reward` limits cashback paid out. Each cap counts over a `period`: `calendarMonth`, `statementMonth`, `calendarQuarter` or `calendarYear`.
- **Minimum spend:** `minSpend` on a rule overrides the card's own. Rules in the same `tierGroup` are alternatives, and only the highest tier the holder qualifies for applies.
- **Promos:** `validUntil` (`YYYY-MM-DD`, Singapore time) ends a promo rule automatically.
- **Card ids** never change and cards are never deleted, because people's saved cards point to them. A withdrawn card gets a warning instead.

These are estimates from public sources, not financial advice. Always check the bank's current terms and conditions.
