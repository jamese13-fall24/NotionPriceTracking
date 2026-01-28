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

# Initialize Notion client
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

if not NOTION_API_KEY or not DATABASE_ID:
    raise ValueError("Missing required environment variables: NOTION_API_KEY or NOTION_DATABASE_ID")

notion = Client(auth=NOTION_API_KEY)

# Request headers to avoid being blocked
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}


def extract_price_amazon(soup):
    """Extract price from Amazon product pages"""
    selectors = [
        ('span', 'a-price-whole'),
        ('span', 'a-offscreen'),
        ('span', 'priceToPay'),
    ]
    
    for tag, class_name in selectors:
        elements = soup.find_all(tag, class_=class_name)
        for element in elements:
            text = element.get_text()
            # Extract numeric value
            match = re.search(r'(\d+[,.]?\d*\.?\d*)', text)
            if match:
                price_str = match.group(1).replace(',', '')
                try:
                    return float(price_str)
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
    """Extract price from Best Buy product pages"""
    selectors = [
        ('div', 'priceView-hero-price priceView-customer-price'),
        ('div', 'priceView-customer-price'),
        ('span', {'aria-label': re.compile(r'Customer Price')}),
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


def extract_price_from_url(url):
    """
    Main function to extract price from any URL
    Detects retailer and uses appropriate extraction method
    """
    try:
        # Make request
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Detect retailer from URL
        domain = urlparse(url).netloc.lower()
        
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
        print(f"⏱️  Timeout scraping {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error scraping {url}: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error scraping {url}: {e}")
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
    
    # Get items from Notion
    print("📋 Fetching wish list items from Notion...")
    items = get_wishlist_items()
    
    if not items:
        print("⚠️  No items found to update")
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
        new_price = extract_price_from_url(url)
        
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
