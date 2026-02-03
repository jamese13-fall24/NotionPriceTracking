# Troubleshooting Guide

---

## How the script handles difficult sites

Not every retailer lets bots in. The script has three tiers for dealing with that, and a tool for figuring out which tier a new site belongs to.

**BLOCKED_DOMAINS** — sites that consistently refuse automated access (e.g. Best Buy). The script skips them entirely; no request is made. You update these manually.

**COOLDOWN_DOMAINS** — sites that allow one visit, then lock you out for a while before resetting (e.g. EBGames, Manscaped). The script records when it last successfully checked each of these in `cooldowns.json` and skips them until the cooldown window has passed.

**Everything else** — sites that work every time. No special handling needed.

Both lists live at the top of `update_prices.py`:

```python
BLOCKED_DOMAINS = [
    "bestbuy.ca",
    "bestbuy.com",
]

COOLDOWN_DOMAINS = {
    "ebgames.ca": 15,       # minutes between checks
    "manscaped.com": 15,
}
```

---

## Testing a new site

Before adding a product from an unfamiliar retailer, run the test script to find out how the site behaves:

```bash
python setup/test_price_extraction.py
```

It opens each URL twice with a short gap and prints a verdict at the end:

```
  Site                 Attempt 1      Attempt 2      Verdict
  Amazon               $699.99        $699.99        ✅ Leave alone
  Best Buy             ✗              ✗              🚫 BLOCKED_DOMAINS
  EBGames              $99.99         ✗              ⏳ COOLDOWN_DOMAINS
```

To test a single URL quickly, open the script and set `SINGLE_URL` at the top to your link, then run it. Set it back to `None` when you're done.

---

## Reading the debug HTML

When extraction fails, the script saves the raw HTML it received into the `debug/` folder:

```
debug/failed_www_ebgames_ca_20260203_143022.html
```

Open that file in your browser. If you see a "verify you're human" page, that site needs to go in `BLOCKED_DOMAINS` or `COOLDOWN_DOMAINS`. If you see the real product page but no price was extracted, the selectors need updating — inspect the price element on the live site and add its tag/class to the site-specific section in `extract_price_from_html()`.

---

## Common issues

**"No items found to update"**
Check that your items have Status set to Wishlist, Researching, or Ready to Buy. Verify the database is shared with your Notion integration. Run `python setup/find_database.py` to confirm the script can see it.

**"Could not extract price"**
Check `debug/` for the saved HTML. Either the site blocked you (add to BLOCKED or COOLDOWN), or the page structure changed and the selectors need updating.

**"Page too small — likely blocked"**
The site returned a tiny response, usually a 403 or captcha page. Add the domain to BLOCKED_DOMAINS.

**Notion API errors**
Run `python setup/test_notion_api.py` — it tests each operation the main script uses and tells you exactly which one fails.

**Price is wrong / different from what you see in the browser**
Some sites show different prices based on geography. The script is locked to `en-CA` locale and `America/Toronto` timezone to keep prices consistent. If you're seeing a different price, make sure you're comparing against the Canadian version of the site.

---

## The cooldowns.json file

This file is auto-managed — you don't need to edit it. It records the last time each cooldown domain was successfully checked:

```json
{
  "ebgames.ca": "2026-02-03T14:30:22.481200",
  "manscaped.com": "2026-02-03T14:30:25.103400"
}
```

If you want to force a re-check of a cooldown site right now, delete the file (or just delete that domain's line) and run the script again. It's in `.gitignore` so it won't get committed.

---

## When to just update manually

If a site consistently fails even after debugging, it's not worth the fight. Add it to BLOCKED_DOMAINS and update that price by hand when you visit the product page anyway. A blocked site costs you nothing — a broken scrape just wastes a run.