"""
Test price extraction on one or more URLs.
Use this when evaluating a new site to decide whether to:
  - Add it to BLOCKED_DOMAINS (never works)
  - Add it to COOLDOWN_DOMAINS (works, but needs time between hits)
  - Leave it alone (works every time)

The script runs each URL twice with a short gap and compares results,
then prints a clear verdict for each.

Usage:
    python setup/test_price_extraction.py

To test a single URL quickly, edit the SINGLE_URL variable below
and set it to your URL string. Set it back to None when done.
"""

import os
import re
import json
import time
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------------------------
# Quick single-URL mode — paste a URL here to test just that one
# ---------------------------------------------------------------------------
SINGLE_URL = None
# SINGLE_URL = "https://www.example.com/some-product"


# ---------------------------------------------------------------------------
# Default test URLs (edit freely)
# ---------------------------------------------------------------------------
DEFAULT_URLS = [
    ("Amazon",       "https://www.amazon.ca/dp/B0FC5FJZ9Z"),
    ("Best Buy",     "https://www.bestbuy.ca/en-ca/product/beats-by-dr-dre-studio-pro-over-ear-noise-cancelling-bluetooth-headphones-grey-only-at-best-buy/19392064"),
    ("Manscaped",    "https://ca.manscaped.com/products/the-platinum-package-5"),
    ("UTdisguise",   "https://www.utdisguisemastermask.com/products/leo-drone-mask"),
    ("EBGames",      "https://www.ebgames.ca/Switch/Games/941077/super-mario-galaxy-super-mario-galaxy-2"),
]


# ---------------------------------------------------------------------------
# Price extraction — kept in sync with update_prices.py
# ---------------------------------------------------------------------------

def extract_price_from_html(html, url):
    """
    Same extraction logic as update_prices.py.
    Returns the first valid price as a float, or None.
    """
    soup = BeautifulSoup(html, 'html.parser')
    domain = urlparse(url).netloc

    # Method 1: JSON-LD
    for script in soup.find_all('script', {'type': 'application/ld+json'}):
        try:
            if not script.string:
                continue
            data = json.loads(script.string)
            price = None
            if isinstance(data, dict):
                if 'price' in data:
                    price = data['price']
                elif 'offers' in data:
                    offers = data['offers']
                    if isinstance(offers, dict):
                        price = offers.get('price') or offers.get('lowPrice')
                    elif isinstance(offers, list) and offers:
                        price = offers[0].get('price')
            if price is not None:
                return float(str(price).replace(',', '').replace('$', '').strip())
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            continue

    # Method 2: Meta tags
    for attr, value in [('property', 'product:price:amount'),
                        ('property', 'og:price:amount'),
                        ('name', 'twitter:data1')]:
        meta = soup.find('meta', {attr: value})
        if meta and meta.get('content'):
            try:
                return float(meta['content'].replace(',', '').replace('$', '').strip())
            except (ValueError, TypeError):
                continue

    # Method 3: Site-specific selectors
    if 'amazon' in domain:
        for tag, attrs in [('span', {'class': 'a-price-whole'}),
                           ('span', {'class': 'a-offscreen'}),
                           ('span', {'id': 'priceblock_ourprice'}),
                           ('span', {'id': 'priceblock_dealprice'}),
                           ('div',  {'id': 'corePrice_feature_div'}),
                           ('span', {'class': 'priceToPay'})]:
            for elem in soup.find_all(tag, attrs):
                match = re.search(r'[\$]?\s*([0-9,]+\.\d{2})', elem.get_text().strip())
                if match:
                    try:
                        return float(match.group(1).replace(',', ''))
                    except ValueError:
                        continue

    elif 'bestbuy' in domain:
        for tag, attrs in [('span', {'class': re.compile('screenReaderOnly', re.IGNORECASE)}),
                           ('span', {'class': re.compile('largePriceText', re.IGNORECASE)}),
                           ('div',  {'class': re.compile('price', re.IGNORECASE)})]:
            for elem in soup.find_all(tag, attrs):
                match = re.search(r'[\$]?\s*([0-9,]+\.\d{2})', elem.get_text().strip())
                if match:
                    try:
                        return float(match.group(1).replace(',', ''))
                    except ValueError:
                        continue

    # Method 4: Generic $ pattern
    seen = set()
    for match in re.findall(r'\$\s*([0-9,]+\.\d{2})', soup.get_text()):
        clean = match.replace(',', '')
        if clean in seen:
            continue
        seen.add(clean)
        try:
            price = float(clean)
            if 0.01 <= price <= 99999:
                return price
        except ValueError:
            continue

    return None


# ---------------------------------------------------------------------------
# Playwright fetcher — mirrors update_prices.py's persistent context
# ---------------------------------------------------------------------------

def fetch(url):
    """
    Fetch the page using the same persistent-context settings as
    update_prices.py.  Returns (price_or_None, html_string).
    """
    with sync_playwright() as p:
        user_data_dir = os.path.expanduser("~/.playwright_notion_wishlist")

        browser = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,   # visible — less suspicious for testing
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ],
            viewport={'width': 1920, 'height': 1080},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            locale='en-CA',
            timezone_id='America/Toronto',
        )

        page = browser.new_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(8000)
            html = page.content()

            if len(html) < 5000:
                return None, html          # blocked / too small

            price = extract_price_from_html(html, url)
            return price, html

        except Exception as e:
            print(f"   ⚠️  Playwright error: {e}")
            return None, ""

        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Save debug HTML
# ---------------------------------------------------------------------------

def save_debug_html(label, domain, html):
    """Save HTML into the project's debug/ folder for manual inspection."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    debug_dir = os.path.join(script_dir, "..", "debug")
    os.makedirs(debug_dir, exist_ok=True)

    safe_domain = domain.replace('.', '_')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(debug_dir, f"{label}_{safe_domain}_{timestamp}.html")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if SINGLE_URL:
        urls = [("Custom", SINGLE_URL)]
    else:
        urls = DEFAULT_URLS

    print("=" * 70)
    print("🧪 Price Extraction Test")
    print("=" * 70)
    print(f"   Testing {len(urls)} URL(s), 2 attempts each (3 s gap)")
    print(f"   Browser will open visibly (less suspicious to sites)")
    print("=" * 70)
    print()

    input("Press Enter to start...\n")

    # results[name] = [ (attempt_number, price_or_None), ... ]
    results = {}

    for name, url in urls:
        print("-" * 70)
        print(f"🔍 {name}")
        print(f"   {url}")
        print("-" * 70)
        results[name] = {"url": url, "attempts": []}

        for attempt in (1, 2):
            print(f"\n   Attempt {attempt}...")
            price, html = fetch(url)

            if price is not None:
                print(f"   ✅ ${price}")
            else:
                print(f"   ❌ no price extracted")
                # Save HTML for inspection
                path = save_debug_html(f"attempt{attempt}_{name.lower()}", urlparse(url).netloc, html)
                print(f"   💾 debug HTML → {path}")

            results[name]["attempts"].append(price)

            if attempt == 1:
                print(f"\n   ⏳ Waiting 3 s before attempt 2...")
                time.sleep(3)

        print()

    # ------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------
    print()
    print("=" * 70)
    print("📊 VERDICT")
    print("=" * 70)
    print()
    print("  Add to BLOCKED_DOMAINS   → site never returns a price")
    print("  Add to COOLDOWN_DOMAINS  → works once, then needs a break")
    print("  Leave alone              → works every time")
    print()
    print("-" * 70)
    print(f"  {'Site':<20} {'Attempt 1':<14} {'Attempt 2':<14} {'Verdict'}")
    print("-" * 70)

    for name, data in results.items():
        a1, a2 = data["attempts"]
        a1_str = f"${a1}" if a1 else "✗"
        a2_str = f"${a2}" if a2 else "✗"

        if a1 and a2:
            verdict = "✅ Leave alone"
        elif a1 and not a2:
            verdict = "⏳ COOLDOWN_DOMAINS"
        elif not a1 and not a2:
            verdict = "🚫 BLOCKED_DOMAINS"
        else:
            # failed first, worked second — unusual, could be transient
            verdict = "⚠️  Rerun to confirm"

        print(f"  {name:<20} {a1_str:<14} {a2_str:<14} {verdict}")

    print("-" * 70)
    print()
    print("Debug HTML for failed attempts is in the project's debug/ folder.")
    print("=" * 70)


if __name__ == "__main__":
    main()