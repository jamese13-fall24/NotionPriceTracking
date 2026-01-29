"""
Notion Wish List Price Updater
Automatically scrapes product prices from URLs and updates your Notion database
"""

import os
import requests
from notion_client import Client
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
import json
from urllib.parse import urlparse

# Try to import selenium - it's optional but recommended
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️  Selenium not available - some sites may not work properly")
    print("   Install with: pip install selenium")

# Initialize Notion client
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

if not NOTION_API_KEY or not DATABASE_ID:
    raise ValueError("Missing required environment variables: NOTION_API_KEY or NOTION_DATABASE_ID")

notion = Client(auth=NOTION_API_KEY)

# Request headers to avoid being blocked
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}


def get_selenium_driver():
    """Create and return a Selenium WebDriver instance"""
    if not SELENIUM_AVAILABLE:
        return None
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"⚠️  Could not initialize Selenium: {e}")
        return None


def get_page_content_selenium(url, driver):
    """
    Fetch page content using Selenium (for JavaScript-heavy sites)
    """
    try:
        driver.get(url)
        # Wait for page to load (up to 10 seconds)
        time.sleep(3)  # Give JavaScript time to load
        
        # Get page source after JavaScript execution
        html = driver.page_source
        return BeautifulSoup(html, 'html.parser')
    except Exception as e:
        print(f"   Selenium error: {e}")
        return None


def extract_price_amazon(soup):
    """Extract price from Amazon product pages (US & Canada)"""
    
    # Try multiple selectors in order of reliability
    selectors = [
        # JSON-LD structured data (most reliable)
        ('script', {'type': 'application/ld+json'}),
        # Meta tags
        ('meta', {'property': 'product:price:amount'}),
        ('meta', {'name': 'twitter:data1'}),
        # Main price displays
        ('span', {'class': 'a-price-whole'}),
        ('span', 'a-price-whole'),
        ('span', {'class': 'a-offscreen'}),
        ('span', 'a-offscreen'),
        ('span', {'class': 'priceToPay'}),
        ('span', 'priceToPay'),
        # Kindle/Digital prices
        ('span', {'id': 'kindle-price'}),
        ('span', {'id': 'digital-list-price'}),
        # Deal prices
        ('span', {'class': 'a-size-base a-color-price'}),
        # Price block
        ('div', {'id': 'corePrice_desktop'}),
        ('div', {'id': 'corePriceDisplay_desktop_feature_div'}),
    ]
    
    # Try JSON-LD first
    json_scripts = soup.find_all('script', {'type': 'application/ld+json'})
    for script in json_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and 'offers' in data:
                price = data['offers'].get('price')
                if price:
                    # Handle both string and number formats
                    return float(str(price).replace(',', '').replace('$', '').strip())
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            continue
    
    # Try meta tags
    meta_price = soup.find('meta', {'property': 'product:price:amount'})
    if meta_price:
        try:
            return float(meta_price.get('content'))
        except (ValueError, TypeError):
            pass
    
    # Try twitter card price
    twitter_price = soup.find('meta', {'name': 'twitter:data1'})
    if twitter_price:
        content = twitter_price.get('content', '')
        match = re.search(r'(\d+[,.]?\d*\.?\d*)', content)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                pass
    
    # Try standard price elements
    for tag, attrs in selectors[4:]:
        elements = soup.find_all(tag, attrs)
        for element in elements:
            text = element.get_text()
            # Extract numeric value, handling both formats: "99.99" and "99,99"
            match = re.search(r'(\d+[,.]?\d*\.?\d*)', text)
            if match:
                price_str = match.group(1).replace(',', '')
                try:
                    price = float(price_str)
                    # Sanity check
                    if 0.01 <= price <= 50000:
                        return price
                except ValueError:
                    continue
    
    return None


def extract_price_walmart(soup):
    """Extract price from Walmart product pages"""
    selectors = [
        ('span', 'price-characteristic'),
        ('span', {'itemprop': 'price'}),
        ('span', 'price display-inline-block arrange-fit'),
    ]
    
    for tag, attrs in selectors:
        element = soup.find(tag, attrs)
        if element:
            # Check for content attribute
            if isinstance(attrs, dict) and 'itemprop' in attrs:
                content = element.get('content')
                if content:
                    try:
                        return float(content)
                    except ValueError:
                        pass
            
            # Otherwise parse text
            text = element.get_text()
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
    return None


def extract_price_target(soup):
    """Extract price from Target product pages"""
    selectors = [
        ('span', {'data-test': 'product-price'}),
        ('div', {'data-test': 'product-price'}),
    ]
    
    for tag, attrs in selectors:
        element = soup.find(tag, attrs)
        if element:
            text = element.get_text()
            match = re.search(r'\$?(\d+\.?\d*)', text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
    return None


def extract_price_bestbuy(soup):
    """Extract price from Best Buy product pages (US & Canada)"""
    
    # Best Buy Canada specific selectors (2026)
    selectors = [
        # Structured data (most reliable)
        ('meta', {'property': 'product:price:amount'}),
        ('meta', {'property': 'og:price:amount'}),
        # JSON-LD structured data
        ('script', {'type': 'application/ld+json'}),
        # Various price display elements
        ('div', {'class': re.compile(r'.*productPricing.*')}),
        ('div', {'class': re.compile(r'.*price.*', re.IGNORECASE)}),
        ('span', {'class': re.compile(r'.*screenReaderOnly.*price.*')}),
        ('div', {'data-automation': 'product-price'}),
        ('span', {'data-automation': 'product-price'}),
        # Fallback selectors
        ('div', 'priceView-hero-price priceView-customer-price'),
        ('div', 'priceView-customer-price'),
        ('span', {'aria-label': re.compile(r'Customer Price')}),
    ]
    
    # Try meta tags first (most reliable)
    for tag, attrs in selectors[:2]:
        element = soup.find(tag, attrs)
        if element:
            content = element.get('content')
            if content:
                try:
                    return float(content)
                except ValueError:
                    pass
    
    # Try JSON-LD structured data
    json_scripts = soup.find_all('script', {'type': 'application/ld+json'})
    for script in json_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                # Handle single product
                if 'offers' in data:
                    price = data['offers'].get('price') or data['offers'].get('lowPrice')
                    if price:
                        return float(price)
            elif isinstance(data, list):
                # Handle list of products
                for item in data:
                    if 'offers' in item:
                        price = item['offers'].get('price') or item['offers'].get('lowPrice')
                        if price:
                            return float(price)
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            continue
    
    # Try other HTML elements
    for tag, attrs in selectors[3:]:
        elements = soup.find_all(tag, attrs)
        for element in elements:
            text = element.get_text()
            # Look for price pattern with $ sign
            matches = re.findall(r'\$\s*([0-9,]+\.?\d{0,2})', text)
            if matches:
                price_str = matches[0].replace(',', '')
                try:
                    price = float(price_str)
                    # Sanity check: price should be reasonable (between $1 and $50,000)
                    if 1 <= price <= 50000:
                        return price
                except ValueError:
                    continue
    
    return None


def extract_price_ebay(soup):
    """Extract price from eBay product pages"""
    selectors = [
        ('span', 'ux-textspans--BOLD'),
        ('div', {'class': 'x-price-primary'}),
    ]
    
    for tag, attrs in selectors:
        elements = soup.find_all(tag, attrs)
        for element in elements:
            text = element.get_text()
            # Look for price pattern
            match = re.search(r'US\s*\$?(\d+\.?\d*)', text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
    return None


def extract_price_generic(soup):
    """
    Generic price extraction for unknown retailers
    Looks for common price patterns in the HTML
    """
    # Look for meta tags with price
    meta_price = soup.find('meta', {'property': 'product:price:amount'})
    if meta_price:
        try:
            return float(meta_price.get('content'))
        except (ValueError, TypeError):
            pass
    
    # Look for common price patterns in text
    text = soup.get_text()
    patterns = [
        r'\$(\d+,?\d*\.?\d{2})',  # $99.99 or $1,999.99
        r'USD\s*(\d+\.?\d*)',      # USD 99.99
        r'Price:\s*\$?(\d+\.?\d*)', # Price: $99.99
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                return float(price_str)
            except ValueError:
                continue
    
    return None


def extract_price_from_url(url, use_selenium=None):
    """
    Main function to extract price from any URL
    Detects retailer and uses appropriate extraction method
    """
    domain = urlparse(url).netloc.lower()
    
    # Sites that need Selenium (JavaScript-heavy)
    selenium_required_sites = ['bestbuy.ca', 'bestbuy.com', 'walmart.ca', 'walmart.com']
    needs_selenium = any(site in domain for site in selenium_required_sites)
    
    # Determine if we should use Selenium
    should_use_selenium = (use_selenium is not None and SELENIUM_AVAILABLE) or \
                         (needs_selenium and SELENIUM_AVAILABLE)
    
    try:
        soup = None
        
        if should_use_selenium and use_selenium is not None:
            # Use provided driver
            soup = get_page_content_selenium(url, use_selenium)
        elif should_use_selenium:
            # Create temporary driver
            driver = get_selenium_driver()
            if driver:
                soup = get_page_content_selenium(url, driver)
                driver.quit()
            else:
                print(f"   ⚠️  Selenium unavailable, trying standard request...")
                needs_selenium = False
        
        # Fallback to standard requests if Selenium didn't work
        if soup is None:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        
        # Detect retailer from URL and extract price
        if 'amazon.com' in domain or 'amazon.ca' in domain:
            price = extract_price_amazon(soup)
        elif 'walmart.com' in domain or 'walmart.ca' in domain:
            price = extract_price_walmart(soup)
        elif 'target.com' in domain:
            price = extract_price_target(soup)
        elif 'bestbuy.com' in domain or 'bestbuy.ca' in domain:
            price = extract_price_bestbuy(soup)
        elif 'ebay.com' in domain or 'ebay.ca' in domain:
            price = extract_price_ebay(soup)
        else:
            # Try generic extraction
            price = extract_price_generic(soup)
        
        return price
        
    except requests.exceptions.Timeout:
        print(f"   ⏱️  Timeout scraping {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error scraping {url}: {e}")
        return None
    except Exception as e:
        print(f"   ❌ Unexpected error scraping {url}: {e}")
        return None


def get_wishlist_items():
    """
    Query Notion database for items that need price updates
    Returns items with status 'Wishlist' or 'Researching'
    """
    try:
        results = notion.databases.query(
            database_id=DATABASE_ID,
            filter={
                "or": [
                    {"property": "Status", "select": {"equals": "Wishlist"}},
                    {"property": "Status", "select": {"equals": "Researching"}},
                    {"property": "Status", "select": {"equals": "Ready to Buy"}}
                ]
            }
        )
        return results['results']
    except Exception as e:
        print(f"❌ Error querying Notion database: {e}")
        return []


def get_property_value(page, property_name, property_type):
    """Helper function to safely extract property values from Notion pages"""
    try:
        prop = page['properties'].get(property_name, {})
        
        if property_type == 'url':
            return prop.get('url')
        elif property_type == 'number':
            return prop.get('number')
        elif property_type == 'title':
            title_array = prop.get('title', [])
            if title_array:
                return title_array[0]['text']['content']
            return 'Untitled'
        elif property_type == 'rich_text':
            text_array = prop.get('rich_text', [])
            if text_array:
                return text_array[0]['text']['content']
            return ''
        
    except Exception:
        return None


def update_notion_price(page_id, item_name, new_price, old_price=None):
    """
    Update price and last check date in Notion database
    Optionally append to price history
    """
    try:
        properties = {
            "Price": {"number": new_price},
            "Last Price Check": {"date": {"start": datetime.now().isoformat()}}
        }
        
        # Calculate price change if we have old price
        if old_price and old_price != new_price:
            change_amount = new_price - old_price
            change_percent = (change_amount / old_price) * 100
            
            # Update price history (if the field exists)
            history_entry = f"{datetime.now().strftime('%Y-%m-%d')}: ${new_price:.2f} ({change_percent:+.1f}%)"
            properties["Price History"] = {
                "rich_text": [{"text": {"content": history_entry}}]
            }
            
            # Print price change alert
            if change_amount < 0:
                print(f"💰 PRICE DROP: {item_name}")
                print(f"   Was: ${old_price:.2f} → Now: ${new_price:.2f} (Save ${abs(change_amount):.2f}!)")
            elif change_amount > 0:
                print(f"📈 PRICE INCREASE: {item_name}")
                print(f"   Was: ${old_price:.2f} → Now: ${new_price:.2f} (+${change_amount:.2f})")
        
        notion.pages.update(page_id=page_id, properties=properties)
        return True
        
    except Exception as e:
        print(f"❌ Error updating Notion for {item_name}: {e}")
        return False


def main():
    """Main execution function"""
    print("=" * 60)
    print("🚀 Starting Notion Wish List Price Update")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # Initialize Selenium driver once for all items (more efficient)
    driver = None
    if SELENIUM_AVAILABLE:
        print("🌐 Initializing Selenium WebDriver...")
        driver = get_selenium_driver()
        if driver:
            print("✅ Selenium ready for JavaScript-heavy sites")
        else:
            print("⚠️  Selenium initialization failed - will use standard requests")
        print()
    
    # Get items from Notion
    print("📋 Fetching wish list items from Notion...")
    items = get_wishlist_items()
    
    if not items:
        print("⚠️  No items found to update")
        if driver:
            driver.quit()
        return
    
    print(f"✅ Found {len(items)} items to check")
    print()
    
    # Track statistics
    stats = {
        'total': len(items),
        'updated': 0,
        'failed': 0,
        'no_url': 0,
        'price_drops': 0
    }
    
    # Process each item
    for i, item in enumerate(items, 1):
        # Get item details
        item_name = get_property_value(item, 'Name', 'title')
        url = get_property_value(item, 'URL', 'url')
        old_price = get_property_value(item, 'Price', 'number')
        
        print(f"[{i}/{len(items)}] {item_name}")
        
        # Check if URL exists
        if not url:
            print("   ⚠️  No URL provided - skipping")
            stats['no_url'] += 1
            print()
            continue
        
        # Extract price
        print(f"   🔍 Checking price at {urlparse(url).netloc}...")
        new_price = extract_price_from_url(url, use_selenium=driver)
        
        if new_price:
            # Check for price drop
            if old_price and new_price < old_price:
                stats['price_drops'] += 1
            
            # Update Notion
            success = update_notion_price(item['id'], item_name, new_price, old_price)
            
            if success:
                if not old_price or old_price == new_price:
                    print(f"   ✅ Updated: ${new_price:.2f}")
                stats['updated'] += 1
            else:
                stats['failed'] += 1
        else:
            print(f"   ❌ Could not extract price")
            stats['failed'] += 1
        
        print()
        
        # Be respectful - add delay between requests
        if i < len(items):
            time.sleep(2)  # 2 second delay between items
    
    # Clean up Selenium
    if driver:
        driver.quit()
        print("🌐 Selenium driver closed")
        print()
    
    # Print summary
    print("=" * 60)
    print("📊 UPDATE SUMMARY")
    print("=" * 60)
    print(f"Total items checked:     {stats['total']}")
    print(f"Successfully updated:    {stats['updated']}")
    print(f"Failed to update:        {stats['failed']}")
    print(f"No URL provided:         {stats['no_url']}")
    print(f"Price drops detected:    {stats['price_drops']}")
    print()
    print("✨ Update complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
