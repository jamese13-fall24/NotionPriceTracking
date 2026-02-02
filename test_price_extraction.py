"""
Final Price Extraction Script
Works around bot detection for Amazon and Best Buy
"""

import time
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def extract_price_from_html(html, url):
    """Extract price from HTML using multiple methods"""
    soup = BeautifulSoup(html, 'html.parser')
    domain = urlparse(url).netloc
    found_prices = []
    
    print("🔍 Analyzing page for prices...\n")
    
    # Method 1: JSON-LD structured data
    json_scripts = soup.find_all('script', {'type': 'application/ld+json'})
    for script in json_scripts:
        try:
            if script.string:
                data = json.loads(script.string)
                price = None
                
                if isinstance(data, dict):
                    # Direct price field
                    if 'price' in data:
                        price = data['price']
                    # Offers field
                    elif 'offers' in data:
                        offers = data['offers']
                        if isinstance(offers, dict):
                            price = offers.get('price') or offers.get('lowPrice')
                        elif isinstance(offers, list) and offers:
                            price = offers[0].get('price')
                
                if price:
                    found_prices.append(('JSON-LD', str(price)))
                    print(f"   ✓ JSON-LD: ${price}")
        except:
            pass
    
    # Method 2: Meta tags
    meta_selectors = [
        ('property', 'product:price:amount'),
        ('property', 'og:price:amount'),
        ('name', 'twitter:data1'),
    ]
    for attr, value in meta_selectors:
        meta = soup.find('meta', {attr: value})
        if meta and meta.get('content'):
            price = meta.get('content')
            found_prices.append(('Meta tag', price))
            print(f"   ✓ Meta tag ({value}): ${price}")
    
    # Method 3: Site-specific selectors
    if 'amazon' in domain:
        print("   🔍 Using Amazon-specific selectors...")
        
        # Amazon price selectors (in order of reliability)
        amazon_selectors = [
            ('span', {'class': 'a-price-whole'}),
            ('span', {'class': 'a-offscreen'}),
            ('span', {'id': 'priceblock_ourprice'}),
            ('span', {'id': 'priceblock_dealprice'}),
            ('div', {'id': 'corePrice_feature_div'}),
            ('span', {'class': 'priceToPay'}),
        ]
        
        for tag, attrs in amazon_selectors:
            elements = soup.find_all(tag, attrs)
            for elem in elements:
                text = elem.get_text().strip()
                # Extract price from text like "$699.99" or "699.99"
                price_match = re.search(r'[\$]?\s*([0-9,]+\.\d{2})', text)
                if price_match:
                    price = price_match.group(1).replace(',', '')
                    found_prices.append((f'Amazon {tag}.{attrs}', price))
                    print(f"   ✓ Amazon element: ${price}")
                    break
    
    elif 'bestbuy' in domain:
        print("   🔍 Using Best Buy-specific selectors...")
        
        # Best Buy selectors
        bestbuy_selectors = [
            ('span', {'class': re.compile('screenReaderOnly', re.IGNORECASE)}),
            ('span', {'class': re.compile('largePriceText', re.IGNORECASE)}),
            ('div', {'class': re.compile('price', re.IGNORECASE)}),
        ]
        
        for tag, attrs in bestbuy_selectors:
            elements = soup.find_all(tag, attrs)
            for elem in elements:
                text = elem.get_text().strip()
                price_match = re.search(r'[\$]?\s*([0-9,]+\.\d{2})', text)
                if price_match:
                    price = price_match.group(1).replace(',', '')
                    found_prices.append((f'Best Buy {tag}', price))
                    print(f"   ✓ Best Buy element: ${price}")
    
    # Method 4: Generic text pattern search (last resort)
    if not found_prices:
        print("   🔍 Searching for price patterns in text...")
        text = soup.get_text()
        
        # Look for currency amounts
        pattern = r'\$\s*([0-9,]+\.\d{2})'
        matches = re.findall(pattern, text)
        
        if matches:
            # Remove duplicates while preserving order
            seen = set()
            unique_matches = []
            for match in matches:
                clean = match.replace(',', '')
                if clean not in seen and 0.01 <= float(clean) <= 99999:  # Reasonable price range
                    seen.add(clean)
                    unique_matches.append(clean)
            
            if unique_matches:
                found_prices.append(('Text pattern', unique_matches[0]))
                print(f"   ✓ Text pattern: ${unique_matches[0]}")
                print(f"   (Also found: {unique_matches[1:6]})")
    
    return found_prices


def test_with_playwright(url):
    """Extract price using Playwright"""
    print(f"\n{'='*70}")
    print(f"URL: {url}")
    print(f"{'='*70}\n")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=False,  # Visible browser - less suspicious
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            
            # Create context with realistic settings
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-CA',
                timezone_id='America/Toronto',
            )
            
            page = context.new_page()
            
            # Navigate
            print(f"📥 Loading page...")
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for content
            print("⏳ Waiting for content to load...")
            page.wait_for_timeout(8000)  # 8 seconds
            
            # Check title
            title = page.title()
            html = page.content()
            
            print(f"📄 Page title: {title}")
            print(f"📏 Page size: {len(html):,} characters\n")
            
            # Check if blocked
            if 'access denied' in title.lower() or len(html) < 5000:
                print("❌ Page appears to be blocked or incomplete")
                print(f"   Title: {title}")
                
                # Save for manual inspection
                debug_file = f"blocked_{urlparse(url).netloc.replace('.', '_')}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"\n💾 Saved blocked page to: {debug_file}")
                print("\n⚠️  MANUAL WORKAROUND NEEDED:")
                print("   1. Open this URL in a regular browser")
                print("   2. Right-click → Inspect → Network tab")
                print("   3. Refresh the page")
                print("   4. Look for the main document request")
                print("   5. Copy the price from the page or API response\n")
                
                browser.close()
                return None
            
            print("✅ Page loaded successfully!\n")
            
            # Save HTML
            debug_file = f"success_{urlparse(url).netloc.replace('.', '_')}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"💾 Saved page to: {debug_file}\n")
            
            # Extract prices
            prices = extract_price_from_html(html, url)
            
            print(f"\n{'='*70}")
            if prices:
                print("🎯 FOUND PRICES:")
                print(f"{'='*70}")
                for method, price in prices:
                    print(f"   {method:25} → ${price}")
                
                # Determine the most likely actual price
                print(f"\n{'='*70}")
                print("💡 MOST LIKELY PRICE:")
                print(f"{'='*70}")
                
                # Prefer JSON-LD and meta tags over text patterns
                for method, price in prices:
                    if 'JSON-LD' in method or 'Meta' in method:
                        print(f"   ${price} (from {method})")
                        break
                else:
                    # Fall back to first found price
                    if prices:
                        print(f"   ${prices[0][1]} (from {prices[0][0]})")
            else:
                print("❌ NO PRICES FOUND")
                print(f"{'='*70}")
                print("\nThis could mean:")
                print("   - Page is blocked/incomplete")
                print("   - Price requires JavaScript/user interaction")
                print("   - Selectors need updating")
                print("\nCheck the saved HTML file to debug.")
            
            print(f"\n{'='*70}\n")
            
            browser.close()
            return prices
        
    except ImportError:
        print("❌ Playwright not installed")
        print("\nInstall with:")
        print("   pip install playwright")
        print("   playwright install chromium\n")
        return None
    
    except Exception as e:
        print(f"❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        try:
            browser.close()
        except:
            pass
        return None


def manual_price_check_instructions():
    """Print instructions for manual price checking"""
    print("\n" + "="*70)
    print("BEST BUY WORKAROUND (Manual Method)")
    print("="*70)
    print("""
Best Buy has very aggressive bot protection. Here's the manual method:

1. Open the URL in your regular browser (Chrome/Firefox)

2. Right-click on the page → Inspect → Network tab

3. Filter by 'Fetch/XHR' or 'All'

4. Refresh the page

5. Look for API calls like:
   - /api/product/...
   - /graphql
   - Any JSON responses

6. Click on them and check the Response/Preview tab

7. The price data should be in JSON format, something like:
   {
     "salePrice": 399.99,
     "regularPrice": 499.99,
     ...
   }

8. You can then use this API endpoint in your code instead of scraping HTML

ALTERNATIVE: Use Best Buy's unofficial API or RSS feeds if available.
    """)
    print("="*70 + "\n")


if __name__ == "__main__":
    test_urls = [
        ("Amazon", "https://www.amazon.ca/dp/B0FC5FJZ9Z"),
        ("Best Buy", "https://www.bestbuy.ca/en-ca/product/beats-by-dr-dre-studio-pro-over-ear-noise-cancelling-bluetooth-headphones-grey-only-at-best-buy/19392064"),
        ("Manscaped", "https://ca.manscaped.com/products/the-platinum-package-5"),
        ("UTdisguised", "https://www.utdisguisemastermask.com/products/leo-drone-mask"),
        ("EBGames", "https://www.ebgames.ca/Switch/Games/941077/super-mario-galaxy-super-mario-galaxy-2")
    ]
    
    print("\n" + "="*70)
    print("PRICE EXTRACTION TEST")
    print("="*70)
    print("\nUsing Playwright with anti-detection measures")
    print("Browser will open visibly (less suspicious to websites)\n")
    
    input("Press Enter to start...")
    
    results = {}
    
    for name, url in test_urls:
        prices = test_with_playwright(url)
        results[name] = prices
        time.sleep(3)  # Brief pause between tests
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for name, prices in results.items():
        print(f"\n{name}:")
        if prices:
            print(f"   ✅ Found {len(prices)} price(s)")
            for method, price in prices:
                print(f"      ${price} ({method})")
        else:
            print("   ❌ Failed to extract price")
    
    # Show manual instructions if Best Buy failed
    if not results.get("Best Buy"):
        manual_price_check_instructions()
    
    print("\n" + "="*70)
    print("Check the success_*.html and blocked_*.html files for details")
    print("="*70 + "\n")