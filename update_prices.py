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
# Configuration  (populated by main() before use — see bottom of file)
# ---------------------------------------------------------------------------

notion = None          # notion_client.Client instance
DATABASE_ID = None     # target database ID string

# Domains that are known to block automated requests or want to be skipped intentionally
# Any URL whose host contains one of these strings will be skipped entirely.
BLOCKED_DOMAINS = [
    "bestbuy.ca",
    "bestbuy.com",
    "gooeycandy.bigcartel.com",
    "manscaped.com",
]

# Domains that enforce a rate-limit cooldown between visits.
# Key: domain substring. Value: minimum minutes between successful checks.
# If the cooldown hasn't elapsed since the last successful check, the site is
# skipped automatically and retried next run.
COOLDOWN_DOMAINS = {
    "ebgames.ca": 15,
}


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
                price, price_currency = result
                # Skip if explicitly USD and we're on a .ca or cad domain
                if price_currency == 'USD' and ('.ca' in domain or 'en-ca' in url):
                    continue  # Keep searching for CAD price

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
            # Check if there's a currency meta tag
            currency_meta = soup.find('meta', {'property': 'og:price:currency'})
            if currency_meta and currency_meta.get('content') == 'USD' and ('.ca' in domain or 'en-ca' in url):
                continue  # Skip USD on .ca domains

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

            price = extract_price_from_html(html, url)
            
            # Debug: Save HTML when extraction fails
            if price is None:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                debug_dir = os.path.join(script_dir, "debug")
                os.makedirs(debug_dir, exist_ok=True)
                
                domain = urlparse(url).netloc.replace('.', '_')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                debug_file = os.path.join(debug_dir, f"failed_{domain}_{timestamp}.html")
                
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                print(f"   💾 Saved HTML to: {debug_file}")
                print(f"   Tip: Open this file to see what the page looked like")

            return price

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
# Cooldown tracker
# ---------------------------------------------------------------------------

COOLDOWN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cooldowns.json")

def load_cooldowns():
    """Read last-check timestamps from cooldowns.json. Returns {} if missing."""
    try:
        with open(COOLDOWN_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_cooldowns(cooldowns):
    """Write cooldown timestamps to cooldowns.json."""
    with open(COOLDOWN_FILE, 'w') as f:
        json.dump(cooldowns, f, indent=2)

def get_cooldown_domain(url):
    """
    If the URL matches a COOLDOWN_DOMAINS entry, return (domain_key, minutes).
    Otherwise return (None, None).
    """
    netloc = urlparse(url).netloc.lower()
    for domain, minutes in COOLDOWN_DOMAINS.items():
        if domain in netloc:
            return domain, minutes
    return None, None

def is_on_cooldown(url):
    """
    Check whether the URL's domain is still within its cooldown window.
    Returns (True/False, remaining_minutes_or_None).
    """
    domain_key, cooldown_minutes = get_cooldown_domain(url)
    if domain_key is None:
        return False, None                          # not a cooldown domain at all

    cooldowns = load_cooldowns()
    last_check = cooldowns.get(domain_key)
    if last_check is None:
        return False, None                          # never checked — no cooldown yet

    elapsed = (datetime.now() - datetime.fromisoformat(last_check)).total_seconds() / 60
    if elapsed < cooldown_minutes:
        return True, round(cooldown_minutes - elapsed, 1)
    return False, None

def record_cooldown(url):
    """Stamp the current time for this URL's cooldown domain."""
    domain_key, _ = get_cooldown_domain(url)
    if domain_key is None:
        return
    cooldowns = load_cooldowns()
    cooldowns[domain_key] = datetime.now().isoformat()
    save_cooldowns(cooldowns)

# ---------------------------------------------------------------------------
# Exchange Rate value
# ---------------------------------------------------------------------------

def get_current_exchange_rate():
    """
    Get the exchange rate for the current month.
    Falls back to the most recent rate if current month not defined.
    """
    from datetime import datetime
    current_month = datetime.now().strftime("%Y-%m")
    
    # Try current month first
    if current_month in EXCHANGE_RATES:
        return EXCHANGE_RATES[current_month]
    
    # Fall back to most recent rate
    if EXCHANGE_RATES:
        # Get the most recent month (sorted descending)
        latest_month = sorted(EXCHANGE_RATES.keys(), reverse=True)[0]
        rate = EXCHANGE_RATES[latest_month]
        print(f"   💱 Using {latest_month} exchange rate: {rate} (current month not defined)")
        return rate
    
    # Ultimate fallback
    print("   ⚠️  No exchange rate defined, using 1.35 as default")
    return 1.35

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main(api_key, database_id):
    """
    Run the full price-update loop.

    api_key      – Notion integration token (ntn_...)
    database_id  – target database ID
    """
    # Wire module-level globals so all helpers see the right client & DB
    global notion, DATABASE_ID
    notion = Client(auth=api_key)
    DATABASE_ID = database_id

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
        'skipped_cooldown': 0,
        'converted': 0,
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

        # --- current exchange ---
        def is_usd_domain(url):
            """Return True if the URL's host matches any entry in USD_DOMAINS."""
            domain = urlparse(url).netloc.lower()
            return any(usd in domain for usd in USD_DOMAINS)


        def convert_to_cad(usd_price, url):
            """
            Convert USD price to CAD using the current month's exchange rate.
            Returns (cad_price, exchange_rate).
            """
            rate = get_current_exchange_rate()
            cad_price = usd_price * rate
            
            domain = urlparse(url).netloc
            print(f"   💱 {domain} price in USD: ${usd_price:.2f}")
            print(f"   💱 Exchange rate: {rate}")
            print(f"   💱 Converted to CAD: ${cad_price:.2f}")
            
            return cad_price, rate

        # --- cooldown check ---
        on_cooldown, remaining = is_on_cooldown(url)
        if on_cooldown:
            print(f"   ⏳ Rate-limit cooldown — {remaining} min remaining, skipping")
            stats['skipped_cooldown'] += 1
            print()
            continue

        # --- fetch & extract ---
        print(f"   🔍 Checking price at {urlparse(url).netloc}...")
        extracted_price = fetch_price(url)

        if extracted_price is None:
            print("   ❌ Could not extract price")
            stats['failed'] += 1
            print()
            continue

        # Stamp cooldown now that we know this domain accepted the request
        record_cooldown(url)

        # --- USD to CAD conversion ---
        if is_usd_domain(url):
            new_price, exchange_rate = convert_to_cad(extracted_price, url)
            stats['converted'] += 1
        else:
            new_price = extracted_price

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
    print(f"Skipped (cooldown):       {stats['skipped_cooldown']}")
    print(f"USD→CAD converted:        {stats['converted']}")
    print(f"Price drops detected:     {stats['price_drops']}")
    print()
    print("✨ Update complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Standalone mode: reads from environment variables.
    # Preferred way to run is via run.py, but this still works if you
    # have the env vars set.
    _key = os.environ.get("NOTION_API_KEY")
    _db  = os.environ.get("NOTION_DATABASE_ID")
    if not _key or not _db:
        raise ValueError(
            "Missing env vars. Either run via run.py or set:\n"
            "  $env:NOTION_API_KEY='ntn_...'\n"
            "  $env:NOTION_DATABASE_ID='...'"
        )
    main(_key, _db)