"""
Notion Wish List Price Updater
Automatically scrapes product prices from URLs and updates your Notion database.
Uses Playwright to render pages and extract prices.
"""

import os
import re
import json
import time
from datetime import datetime
from urllib.parse import urlparse

from notion_client import Client
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

if not NOTION_API_KEY or not DATABASE_ID:
    raise ValueError("Missing required environment variables: NOTION_API_KEY or NOTION_DATABASE_ID")

notion = Client(auth=NOTION_API_KEY)

# Domains that are known to block automated requests.
# Any URL whose host contains one of these strings will be skipped entirely.
BLOCKED_DOMAINS = [
    "bestbuy.ca",
    "bestbuy.com",
]

# ---------------------------------------------------------------------------
# Price extraction (ported from working test script)
# ---------------------------------------------------------------------------

def extract_price_from_html(html, url):
    """
    Extract price from rendered HTML using multiple methods in order of
    reliability: JSON-LD -> meta tags -> site-specific selectors -> generic
    text pattern search.

    Returns the first valid price found as a float, or None.
    """
    soup = BeautifulSoup(html, 'html.parser')
    domain = urlparse(url).netloc

    # ------------------------------------------------------------------
    # Method 1: JSON-LD structured data
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Method 2: Meta tags
    # ------------------------------------------------------------------
    meta_selectors = [
        ('property', 'product:price:amount'),
        ('property', 'og:price:amount'),
        ('name', 'twitter:data1'),
    ]
    for attr, value in meta_selectors:
        meta = soup.find('meta', {attr: value})
        if meta and meta.get('content'):
            try:
                return float(meta['content'].replace(',', '').replace('$', '').strip())
            except (ValueError, TypeError):
                continue

    # ------------------------------------------------------------------
    # Method 3: Site-specific selectors
    # ------------------------------------------------------------------
    if 'amazon' in domain:
        amazon_selectors = [
            ('span', {'class': 'a-price-whole'}),
            ('span', {'class': 'a-offscreen'}),
            ('span', {'id': 'priceblock_ourprice'}),
            ('span', {'id': 'priceblock_dealprice'}),
            ('div', {'id': 'corePrice_feature_div'}),
            ('span', {'class': 'priceToPay'}),
        ]
        for tag, attrs in amazon_selectors:
            for elem in soup.find_all(tag, attrs):
                match = re.search(r'[\$]?\s*([0-9,]+\.\d{2})', elem.get_text().strip())
                if match:
                    try:
                        return float(match.group(1).replace(',', ''))
                    except ValueError:
                        continue

    elif 'bestbuy' in domain:
        bestbuy_selectors = [
            ('span', {'class': re.compile('screenReaderOnly', re.IGNORECASE)}),
            ('span', {'class': re.compile('largePriceText', re.IGNORECASE)}),
            ('div', {'class': re.compile('price', re.IGNORECASE)}),
        ]
        for tag, attrs in bestbuy_selectors:
            for elem in soup.find_all(tag, attrs):
                match = re.search(r'[\$]?\s*([0-9,]+\.\d{2})', elem.get_text().strip())
                if match:
                    try:
                        return float(match.group(1).replace(',', ''))
                    except ValueError:
                        continue

    # ------------------------------------------------------------------
    # Method 4: Generic text pattern search (last resort)
    # ------------------------------------------------------------------
    text = soup.get_text()
    matches = re.findall(r'\$\s*([0-9,]+\.\d{2})', text)

    seen = set()
    for match in matches:
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
# Playwright page fetcher
# ---------------------------------------------------------------------------

def fetch_price(url):
    """
    Open *url* in a headless Chromium browser, wait for the page to settle,
    then run extract_price_from_html on the rendered HTML.

    Returns the extracted price as a float, or None.
    """
    with sync_playwright() as p:
        # Use a persistent context to maintain cookies between runs
        # This makes sites like Amazon less suspicious
        user_data_dir = os.path.expanduser("~/.playwright_notion_wishlist")
        
        browser = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
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
            page.wait_for_timeout(8000)  # let JS finish rendering

            html = page.content()

            # Quick sanity check — if the page is tiny it's probably a block page
            if len(html) < 5000:
                print(f"   ⚠️  Page too small ({len(html)} chars) — likely blocked")
                return None

            return extract_price_from_html(html, url)

        except Exception as e:
            print(f"   ❌ Playwright error: {e}")
            return None

        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Notion helpers
# ---------------------------------------------------------------------------

def get_wishlist_items():
    """Query Notion for items with an active status."""
    try:
        response = notion.data_sources.query(
            data_source_id=DATABASE_ID,
            filter={
                "or": [
                    {"property": "Status", "select": {"equals": "Wishlist"}},
                    {"property": "Status", "select": {"equals": "Researching"}},
                    {"property": "Status", "select": {"equals": "Ready to Buy"}},
                ]
            }
        )
        return response.get('results', [])
    except Exception as e:
        print(f"❌ Error querying Notion database: {e}")
        print(f"   Hint: Make sure the database is shared with your integration")
        return []


def get_property_value(page, property_name, property_type):
    """Safely pull a typed value out of a Notion page's properties dict."""
    try:
        prop = page['properties'].get(property_name, {})

        if property_type == 'url':
            return prop.get('url')
        elif property_type == 'number':
            return prop.get('number')
        elif property_type == 'title':
            title_array = prop.get('title', [])
            return title_array[0]['text']['content'] if title_array else 'Untitled'
        elif property_type == 'rich_text':
            text_array = prop.get('rich_text', [])
            return text_array[0]['text']['content'] if text_array else ''
    except Exception:
        return None


def update_notion_price(page_id, item_name, new_price, old_price=None):
    """Update Price, Last Price Check, and (on change) Price History in Notion."""
    try:
        properties = {
            "Price": {"number": new_price},
            "Last Price Check": {"date": {"start": datetime.now().isoformat()}},
        }

        if old_price is not None and old_price != new_price:
            change_amount = new_price - old_price
            change_percent = (change_amount / old_price) * 100

            history_entry = (
                f"{datetime.now().strftime('%Y-%m-%d')}: "
                f"${new_price:.2f} ({change_percent:+.1f}%)"
            )
            properties["Price History"] = {
                "rich_text": [{"text": {"content": history_entry}}]
            }

            if change_amount < 0:
                print(f"   💰 PRICE DROP: ${old_price:.2f} → ${new_price:.2f} (Save ${abs(change_amount):.2f}!)")
            else:
                print(f"   📈 PRICE INCREASE: ${old_price:.2f} → ${new_price:.2f} (+${change_amount:.2f})")

        notion.pages.update(page_id=page_id, properties=properties)
        return True

    except Exception as e:
        print(f"   ❌ Error updating Notion for {item_name}: {e}")
        return False


# ---------------------------------------------------------------------------
# Blocked-domain check
# ---------------------------------------------------------------------------

def is_domain_blocked(url):
    """Return True if the URL's host matches any entry in BLOCKED_DOMAINS."""
    domain = urlparse(url).netloc.lower()
    return any(blocked in domain for blocked in BLOCKED_DOMAINS)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("🚀 Starting Notion Wish List Price Update")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if BLOCKED_DOMAINS:
        print(f"🚫 Blocked domains: {', '.join(BLOCKED_DOMAINS)}")
    print("=" * 60)
    print()

    # Fetch items
    print("📋 Fetching wish list items from Notion...")
    items = get_wishlist_items()

    if not items:
        print("⚠️  No items found to update")
        return

    print(f"✅ Found {len(items)} item(s) to check\n")

    stats = {
        'total': len(items),
        'updated': 0,
        'failed': 0,
        'no_url': 0,
        'skipped_blocked': 0,
        'price_drops': 0,
    }

    for i, item in enumerate(items, 1):
        item_name = get_property_value(item, 'Name', 'title')
        url = get_property_value(item, 'URL', 'url')
        old_price = get_property_value(item, 'Price', 'number')

        print(f"[{i}/{len(items)}] {item_name}")

        # --- no URL ---
        if not url:
            print("   ⚠️  No URL provided — skipping")
            stats['no_url'] += 1
            print()
            continue

        # --- blocked domain ---
        if is_domain_blocked(url):
            print(f"   🚫 {urlparse(url).netloc} is in the blocked list — skipping")
            stats['skipped_blocked'] += 1
            print()
            continue

        # --- fetch & extract ---
        print(f"   🔍 Checking price at {urlparse(url).netloc}...")
        new_price = fetch_price(url)

        if new_price is None:
            print("   ❌ Could not extract price")
            stats['failed'] += 1
            print()
            continue

        # --- update Notion ---
        if old_price is not None and new_price < old_price:
            stats['price_drops'] += 1

        success = update_notion_price(item['id'], item_name, new_price, old_price)

        if success:
            if old_price is None or old_price == new_price:
                print(f"   ✅ Price: ${new_price:.2f}")
            stats['updated'] += 1
        else:
            stats['failed'] += 1

        print()

        # Respectful delay between requests
        if i < len(items):
            time.sleep(2)

    # --- summary ---
    print("=" * 60)
    print("📊 UPDATE SUMMARY")
    print("=" * 60)
    print(f"Total items:              {stats['total']}")
    print(f"Successfully updated:     {stats['updated']}")
    print(f"Failed to extract:        {stats['failed']}")
    print(f"No URL provided:          {stats['no_url']}")
    print(f"Skipped (blocked domain): {stats['skipped_blocked']}")
    print(f"Price drops detected:     {stats['price_drops']}")
    print()
    print("✨ Update complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()