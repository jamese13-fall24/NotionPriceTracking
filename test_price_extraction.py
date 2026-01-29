"""
Test Price Extraction Script
Run this to test price extraction from specific URLs without updating Notion
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urlparse

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def test_extract_price(url):
    """Test price extraction from a URL"""
    print(f"\n{'='*60}")
    print(f"Testing: {url}")
    print(f"{'='*60}\n")
    
    try:
        # Fetch page
        print("📥 Fetching page...")
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        print("✅ Page fetched successfully\n")
        
        # Try to find JSON-LD data
        print("🔍 Looking for JSON-LD structured data...")
        json_scripts = soup.find_all('script', {'type': 'application/ld+json'})
        if json_scripts:
            print(f"   Found {len(json_scripts)} JSON-LD script(s)")
            for i, script in enumerate(json_scripts):
                try:
                    data = json.loads(script.string)
                    print(f"\n   Script {i+1}:")
                    print(f"   {json.dumps(data, indent=2)[:500]}...")
                    
                    # Try to extract price
                    if isinstance(data, dict) and 'offers' in data:
                        price = data['offers'].get('price') or data['offers'].get('lowPrice')
                        if price:
                            print(f"   💰 Found price in JSON-LD: ${price}")
                except:
                    print(f"   Script {i+1}: Could not parse")
        else:
            print("   No JSON-LD scripts found\n")
        
        # Try meta tags
        print("🔍 Looking for meta tags...")
        meta_tags = [
            ('property', 'product:price:amount'),
            ('property', 'og:price:amount'),
            ('name', 'twitter:data1'),
        ]
        for attr_name, attr_value in meta_tags:
            meta = soup.find('meta', {attr_name: attr_value})
            if meta:
                content = meta.get('content')
                print(f"   Found <meta {attr_name}='{attr_value}' content='{content}'>")
        
        # Search for price patterns in text
        print("\n🔍 Looking for price patterns in page text...")
        text = soup.get_text()
        
        # Common price patterns
        patterns = [
            (r'\$\s*([0-9,]+\.?\d{0,2})', 'Dollar sign format'),
            (r'CAD\s*\$?\s*([0-9,]+\.?\d{0,2})', 'CAD format'),
            (r'USD\s*\$?\s*([0-9,]+\.?\d{0,2})', 'USD format'),
            (r'Price:\s*\$?\s*([0-9,]+\.?\d{0,2})', 'Price: format'),
        ]
        
        for pattern, desc in patterns:
            matches = re.findall(pattern, text)
            if matches:
                print(f"   {desc}: {matches[:5]}")  # Show first 5 matches
        
        # Try to find common price element classes
        print("\n🔍 Looking for common price elements...")
        price_classes = [
            'price', 'Price', 'product-price', 'productPrice',
            'priceView', 'a-price', 'priceToPay'
        ]
        
        for class_name in price_classes:
            elements = soup.find_all(class_=re.compile(class_name, re.IGNORECASE))
            if elements:
                print(f"   Found {len(elements)} elements with class matching '{class_name}'")
                for elem in elements[:2]:  # Show first 2
                    text = elem.get_text().strip()[:100]
                    print(f"      - {text}")
        
        print(f"\n{'='*60}")
        print("✅ Test complete!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}\n")

# Test URLs
if __name__ == "__main__":
    test_urls = [
        "https://www.bestbuy.ca/en-ca/product/beats-by-dr-dre-studio-pro-over-ear-noise-cancelling-bluetooth-headphones-grey-only-at-best-buy/19392064",
        "https://www.amazon.ca/dp/B0FC5FJZ9Z",
    ]
    
    for url in test_urls:
        test_extract_price(url)
        print("\n" + "="*60 + "\n")
