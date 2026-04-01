"""
Test price extraction on one or more URLs.
Use this when evaluating a new site to decide whether to:
  - Add it to BLOCKED_DOMAINS (never works)
  - Add it to COOLDOWN_DOMAINS (works, but needs time between hits)
  - Leave it alone (works every time)

The script runs each URL twice with a short gap and compares results,
then prints a clear verdict for each. Automatically converts USD prices
to CAD using the current month's exchange rate.

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
SINGLE_URL = "https://kimurakami.com/collections/sukajan/products/dragon-souvenir-jacket"
# SINGLE_URL = "https://www.example.com/some-product"


# ---------------------------------------------------------------------------
# Default test URLs (edit freely)
# ---------------------------------------------------------------------------
DEFAULT_URLS = [
    ("Amazon CA",    "https://www.amazon.ca/dp/B0FC5FJZ9Z"),
    ("Amazon US",    "https://www.amazon.com/dp/B0FC5FJZ9Z"),
    ("Best Buy",     "https://www.bestbuy.ca/en-ca/product/beats-by-dr-dre-studio-pro-over-ear-noise-cancelling-bluetooth-headphones-grey-only-at-best-buy/19392064"),
    ("Manscaped",    "https://ca.manscaped.com/products/the-platinum-package-5"),
]


# ---------------------------------------------------------------------------
# USD to CAD conversion configuration
# ---------------------------------------------------------------------------

# Domains that display prices in USD (will be converted to CAD)
USD_DOMAINS = [
    "amazon.com",
    "walmart.com",
    "target.com",
    "newegg.com",
    "ufmunderwear.com",
    "goodfor.life",
    "lovense.com",
    "dungeon-lab.com",
    "smitizen.com",
    "bigcartel.com",
    "fsman.net",
    "kimurakami.com",
]
 
# Exchange rate: USD to CAD
# Update this monthly - format: YYYY-MM = rate
EXCHANGE_RATES = {
    "2026-01": 1.3778,  # January 2026
    "2026-02": 1.3651,  # February 2026
    "2026-03": 1.3717,  # March 2026
}

def get_current_exchange_rate():
    """
    Get the exchange rate for the current month.
    Falls back to the most recent rate if current month not defined.
    """
    current_month = datetime.now().strftime("%Y-%m")
    
    # Try current month first
    if current_month in EXCHANGE_RATES:
        return EXCHANGE_RATES[current_month]
    
    # Fall back to most recent rate
    if EXCHANGE_RATES:
        latest_month = sorted(EXCHANGE_RATES.keys(), reverse=True)[0]
        rate = EXCHANGE_RATES[latest_month]
        print(f"   💱 Using {latest_month} exchange rate: {rate} (current month not defined)")
        return rate
    
    # Ultimate fallback
    print("   ⚠️  No exchange rate defined, using 1.35 as default")
    return 1.35
 
 
def is_usd_domain(url):
    """Return True if the URL's host matches any entry in USD_DOMAINS."""
    domain = urlparse(url).netloc.lower()
    return any(usd in domain for usd in USD_DOMAINS)

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

            def extract_price_currency(obj):
                if isinstance(obj, dict):
                    # price key found
                    if 'price' in obj:
                        return obj.get('price'), obj.get('priceCurrency')

                    # price inside offers
                    if 'offers' in obj:
                        offers = obj['offers']

                        if isinstance(offers, dict):
                            price = offers.get('price') or offers.get('lowPrice')
                            currency = offers.get('priceCurrency')
                            if price is not None:
                                return price, currency
                        
                        elif isinstance(offers, list):
                            for offer in offers:
                                if isinstance(offer, dict):
                                    price = offer.get('price') or offer.get('lowPrice')
                                    currency = offer.get('priceCurrency')
                                    if price is not None:
                                        return price, currency
                        
                    # price inside @graph
                    if '@graph' in obj and isinstance(obj['@graph'], list):
                        for item in obj['@graph']:
                            result = extract_price_currency(item)
                            if result is not None:
                                return result
                            
                elif isinstance(obj, list):
                    for item in obj:
                        result = extract_price_currency(item)
                        if result is not None:
                            return result
                
                return None

            result = extract_price_currency(data)
            if result is not None:
                print("JSON Price")
                price, price_currency = result
                # Skip if explicitly USD and we're on a .ca or cad domain
                if price_currency == 'USD' and ('.ca' in domain or 'en-ca' in url):
                    continue  # Keep searching for CAD price
                
                return float(str(price).replace(',', '').replace('$', '').strip())
            
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            continue

    # Method 2: Meta tags
    for attr, value in [('property', 'product:price:amount'),
                        ('property', 'og:price:amount'),
                        ('name', 'twitter:data1')]:
        meta = soup.find('meta', {attr: value})
        if meta and meta.get('content'):
            # Check if there's a currency meta tag
            currency_meta = soup.find('meta', {'property': 'og:price:currency'})
            if currency_meta and currency_meta.get('content') == 'USD' and ('.ca' in domain or 'en-ca' in url):
                continue  # Skip USD on .ca domains

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

    elif 'furrjoi' in domain:  # Replace YOURDOMAIN with actual domain keyword
        # This site has a price breakdown with OriginPrice, Subtotal, Discount, Shipping, Total
        # We want the Total specifically
        
        # Strategy 1: Look for the "Total" label and get the next price value
        total_label = soup.find('div', class_='label', string=lambda s: s and 'Total' in s)
        if total_label:
            # Find the parent container
            parent = total_label.find_parent()
            if parent:
                # Look for the value div within the same container
                value_div = parent.find('div', class_='value')
                if value_div:
                    price_text = value_div.get_text().strip()
                    # Extract price from "CA$1,647.76"
                    match = re.search(r'CA\$\s*([0-9,]+\.\d{2})', price_text)
                    if match:
                        try:
                            return float(match.group(1).replace(',', ''))
                        except ValueError:
                            pass
        
        # Strategy 2: Look for div with "!text-lg" class (used for Total)
        # but exclude the one with "line-through" (OriginPrice)
        for elem in soup.find_all('div', class_='value'):
            # Skip if it has line-through (that's OriginPrice)
            if 'line-through' in elem.get('class', []) or elem.find_parent(attrs={'line-through': True}):
                continue
            
            # Check if this is the large text price (Total has !text-lg)
            if '!text-lg' in elem.get('class', []):
                price_text = elem.get_text().strip()
                match = re.search(r'CA\$\s*([0-9,]+\.\d{2})', price_text)
                if match:
                    try:
                        return float(match.group(1).replace(',', ''))
                    except ValueError:
                        continue

    # elif 'lastquarterstudios' in domain:
    #     # This site shows both USD (in meta) and CAD (visible)
    #     # Prioritize the CAD price
    #     cad_selectors = [
    #         ('span', {'class': 'cad-price'}),
    #         ('div', {'class': 'price-cad'}),
    #         ('span', {'data-currency': 'CAD'}),
    #     ]
    #     for tag, attrs in cad_selectors:
    #         for elem in soup.find_all(tag, attrs):
    #             text = elem.get_text().strip()
    #             # Match CA$599.99 or $599.99
    #             match = re.search(r'(?:CA)?\$\s*([0-9,]+\.\d{2})', text)
    #             if match:
    #                 try:
    #                     return float(match.group(1).replace(',', ''))
    #                 except ValueError:
    #                     continue

    # elif 'smitizen' in domain:
    #     # This site shows an regular price and a sale price (both in USD)
    #     cad_selectors = [
    #         ('span', {'class': 'sale_price'}),
    #     ]
    #     for tag, attrs in cad_selectors:
    #         for elem in soup.find_all(tag, attrs):
    #             text = elem.get_text().strip()
    #             # Match CA$599.99 or $599.99
    #             match = re.search(r'(?:CA)?\$\s*([0-9,]+\.\d{2})', text)
    #             if match:
    #                 try:
    #                     return float(match.group(1).replace(',', ''))
    #                 except ValueError:
    #                     continue

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
    update_prices.py.  Returns (price, html, is_usd).
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
                return None, html, False          # blocked / too small

            price = extract_price_from_html(html, url)
            is_usd = is_usd_domain(url)
            return price, html, is_usd

        except Exception as e:
            print(f"   ⚠️  Playwright error: {e}")
            return None, "", False

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
    print(f"   Exchange rate: {get_current_exchange_rate()} USD→CAD")
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
        results[name] = {"url": url, "attempts": [], "is_usd": False, "exchange_rate": None,}

        for attempt in (1, 2):
            print(f"\n   Attempt {attempt}...")
            price, html, is_usd = fetch(url)

            if price is not None:
                # Convert if USD
                if is_usd:
                    rate = get_current_exchange_rate()
                    cad_price = price * rate
                    results[name]["is_usd"] = True
                    results[name]["exchange_rate"] = rate
                    results[name][f"usd_price_attempt{attempt}"] = price
                    
                    print(f"   💱 Extracted USD: ${price:.2f}")
                    print(f"   💱 Exchange rate: {rate}")
                    print(f"   ✅ Converted CAD: ${cad_price:.2f}")
                    
                    results[name]["attempts"].append(cad_price)
                else:
                    print(f"   ✅ ${price:.2f} CAD")
                    results[name]["attempts"].append(price)
            else:
                print(f"   ❌ no price extracted")
                results[name]["attempts"].append(None)
                # Save HTML for inspection
                path = save_debug_html(f"attempt{attempt}_{name.lower()}", urlparse(url).netloc, html)
                print(f"   💾 debug HTML → {path}")


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
    print("-" * 110)
    print(f"  {'Site':<20} {'Attempt 1':<35} {'Attempt 2':<35} {'Verdict'}")
    print("-" * 110)

    for name, data in results.items():
        a1, a2 = data["attempts"]
        is_usd = data["is_usd"]

        # Format with currency indicator
        if is_usd:
            usd1 = data.get("usd_price_attempt1")
            usd2 = data.get("usd_price_attempt2")
            
            if a1:
                a1_str = f"${a1:.2f} CAD"
                if usd1:
                    a1_str += f" (${usd1:.2f} USD)"
            else:
                a1_str = "✗"
                
            if a2:
                a2_str = f"${a2:.2f} CAD"
                if usd2:
                    a2_str += f" (${usd2:.2f} USD)"
            else:
                a2_str = "✗"
        else:
            a1_str = f"${a1:.2f} CAD" if a1 else "✗"
            a2_str = f"${a2:.2f} CAD" if a2 else "✗"

        # Determine verdict
        if a1 and a2:
            verdict = "✅ Leave alone"
        elif a1 and not a2:
            verdict = "⏳ COOLDOWN_DOMAINS"
        elif not a1 and not a2:
            verdict = "🚫 BLOCKED_DOMAINS"
        else:
            # failed first, worked second — unusual, could be transient
            verdict = "⚠️  Rerun to confirm"

        print(f"  {name:<20} {a1_str:<35} {a2_str:<35} {verdict}")

    print("-" * 110)
    print()
    print("Debug HTML for failed attempts is in the project's debug/ folder.")
    print("=" * 70)


if __name__ == "__main__":
    main()