# Troubleshooting Guide - Price Extraction Issues

## The Problem

Modern e-commerce websites (especially Best Buy Canada, Amazon, Walmart) load prices dynamically using JavaScript. This means when you fetch the HTML with a simple HTTP request, the price hasn't loaded yet - it only appears after JavaScript runs in a browser.

## The Solution

We've updated the script to use **Selenium**, which actually runs a real browser in the background and waits for JavaScript to execute before extracting the price.

---

## Quick Fix for Best Buy Canada & Amazon

### Option 1: Install Selenium (Recommended)

#### On Your Local Computer:

1. **Install Chrome or Chromium browser** (if not already installed)
   
2. **Install Selenium and ChromeDriver:**
   ```bash
   pip install selenium==4.16.0
   pip install webdriver-manager==4.0.1
   ```

3. **Run the script again:**
   ```bash
   python update_prices.py
   ```

The script will now automatically use Selenium for Best Buy Canada and other JavaScript-heavy sites!

#### For GitHub Actions:

Update your `.github/workflows/update-prices.yml` file:

```yaml
name: Update Notion Wish List Prices

on:
  schedule:
    - cron: '0 9 * * *'
  workflow_dispatch:

jobs:
  update-prices:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Chrome
        run: |
          wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
          echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
          sudo apt-get update
          sudo apt-get install -y google-chrome-stable
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run price update script
        env:
          NOTION_API_KEY: ${{ secrets.NOTION_API_KEY }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
        run: |
          python update_prices.py
```

---

### Option 2: Use the Test Script (Debugging Only)

If you want to see what the script is finding, run the test script:

```bash
python test_price_extraction.py
```

This will show you:
- What data the script can see
- Where it's looking for prices
- What it's finding (or not finding)

---

## Why This Happens

### Traditional Web Scraping (What Doesn't Work):
```
You → HTTP Request → Server → Returns HTML → Parse HTML → No price found!
```
The price is missing because it's added by JavaScript AFTER the HTML loads.

### With Selenium (What Works):
```
You → Selenium → Opens Real Browser → Loads Page → JavaScript Runs → Price Appears → Extract Price ✓
```

---

## Understanding the Updated Script

The new script:

1. **Detects if a site needs Selenium:**
   - Best Buy (US & Canada)
   - Walmart (US & Canada)
   - Amazon (US & Canada)

2. **Uses one browser instance for all items** (efficient)

3. **Falls back to simple requests** if Selenium isn't available

4. **Provides clear error messages** when Selenium is needed but unavailable

---

## Alternative: API-Based Solutions

Some retailers offer APIs for price data:

### Amazon Product Advertising API
- Requires approval
- Free for affiliates
- More reliable than scraping
- Documentation: https://webservices.amazon.com/paapi5/documentation/

### Best Buy API
- Best Buy US has an API
- Best Buy Canada does NOT have a public API
- https://developer.bestbuy.com/

---

## Testing Your Setup

### Test 1: Check if Selenium is installed

```python
try:
    from selenium import webdriver
    print("✅ Selenium is installed")
except ImportError:
    print("❌ Selenium is NOT installed")
```

### Test 2: Check if Chrome/Chromium is installed

```bash
# On Linux/Mac
which google-chrome
which chromium

# On Windows
where chrome
```

### Test 3: Run the test script

```bash
python test_price_extraction.py
```

---

## Common Errors and Fixes

### Error: "selenium not found"
**Fix:** Install selenium
```bash
pip install selenium==4.16.0 webdriver-manager==4.0.1
```

### Error: "chromedriver not found" or "chrome not found"
**Fix:** Install Chrome browser
- **Ubuntu/Debian:**
  ```bash
  wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo apt install ./google-chrome-stable_current_amd64.deb
  ```
- **Mac:** Download from https://www.google.com/chrome/
- **Windows:** Download from https://www.google.com/chrome/

### Error: "Could not extract price" (with Selenium installed)
**Possible causes:**
1. Website changed their HTML structure
2. Product is out of stock
3. Region restrictions (some prices only show in certain countries)
4. Bot detection (website blocking automated access)

**Fix:** Run the test script to see what data is available:
```bash
python test_price_extraction.py
```

---

## Performance Considerations

### Selenium is Slower
- Simple request: ~1-2 seconds per item
- Selenium: ~5-8 seconds per item

For a 10-item wishlist:
- Without Selenium: ~15 seconds total
- With Selenium: ~60 seconds total

This is normal - you're launching a real browser for each update.

### GitHub Actions Limits
- Free tier: 2,000 minutes/month (private repos)
- With Selenium: Each run takes longer but still well within limits
- Running daily: ~30 runs × 1 minute = 30 minutes/month (plenty of room)

---

## Best Practices

1. **Start with a few items** - Test with 2-3 products first

2. **Check compatibility** - Not all retailers work well with scraping
   - ✅ Amazon (with Selenium)
   - ✅ Best Buy Canada (with Selenium)
   - ✅ Walmart
   - ✅ Target
   - ⚠️ Some smaller retailers may work inconsistently

3. **Monitor your runs** - Check GitHub Actions logs for the first week

4. **Have a backup plan** - For critical price tracking, manually verify

5. **Respect rate limits** - The script has 2-second delays built in

---

## When to Manually Update Prices

Despite automation, you should manually check prices when:
- About to make a purchase (always verify current price)
- Item shows as out of stock
- Price seems suspiciously high or low
- Website has changed recently

---

## Need More Help?

1. **Run the test script** to see what data is available
2. **Check GitHub Actions logs** for detailed error messages
3. **Try the URL in your browser** to verify the page loads
4. **Check if the product is in stock** on the retailer's website

---

## Summary

- **Best Buy Canada & Amazon need Selenium** to extract prices
- **Install Selenium locally:** `pip install selenium webdriver-manager`
- **Update GitHub Actions workflow** to install Chrome
- **Test your setup** with the test script before relying on automation
- **Expect slower performance** with Selenium (5-8 seconds per item vs 1-2 seconds)

The updated script handles all of this automatically - just install the dependencies!
