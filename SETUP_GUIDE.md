# Notion Wish List Price Updater - Setup Guide

This guide will walk you through setting up automatic price updates for your Notion wish list using GitHub Actions (completely free!).

## 📋 What You'll Need

1. A GitHub account (free)
2. A Notion account with your wish list database
3. 15-20 minutes for setup

## 🎯 Overview

This system will:
- Run automatically every day at 9 AM UTC
- Check prices for items in your Notion wish list
- Update the prices in your database
- Track price changes and alert you to drops
- Work with Amazon, Walmart, Target, Best Buy, eBay, and more

---

## Step 1: Set Up Your Notion Database

### 1.1 Create the Required Properties

Your Notion database needs these properties (case-sensitive):

| Property Name | Type | Required? | Notes |
|---------------|------|-----------|-------|
| Name | Title | ✅ Yes | Item name (default property) |
| URL | URL | ✅ Yes | Product page URL |
| Price | Number | ✅ Yes | Current price |
| Status | Select | ✅ Yes | Must include: Wishlist, Researching, Ready to Buy |
| Last Price Check | Date | ✅ Yes | When price was last updated |
| Price History | Text | Optional | Tracks price changes |

### 1.2 Add Status Options

Edit the "Status" property and add these options:
- Wishlist
- Researching  
- Ready to Buy
- Ordered
- Received
- Not Buying

The script will only update items with status: **Wishlist**, **Researching**, or **Ready to Buy**.

### 1.3 Get Your Database ID

1. Open your Notion database as a full page
2. Look at the URL in your browser:
   ```
   https://www.notion.so/yourworkspace/1234567890abcdef1234567890abcdef?v=...
                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                      This is your Database ID
   ```
3. Copy the 32-character ID (the part after the last `/` and before the `?`)
4. Save this - you'll need it later!

---

## Step 2: Create a Notion Integration

### 2.1 Create the Integration

1. Go to https://www.notion.so/my-integrations
2. Click **"+ New integration"**
3. Fill in the details:
   - **Name:** Wish List Price Updater
   - **Associated workspace:** Select your workspace
   - **Capabilities:** Read content, Update content (both checked)
4. Click **"Submit"**
5. Copy the **Internal Integration Token** (starts with `secret_...`)
6. **IMPORTANT:** Save this token securely - you'll need it later!

### 2.2 Share Database with Integration

1. Open your Notion wish list database
2. Click the **"..."** (three dots) in the top right
3. Scroll down and click **"Add connections"**
4. Search for and select **"Wish List Price Updater"** (or whatever you named it)
5. Click **"Confirm"**

Your database is now accessible to the integration! ✅

---

## Step 3: Set Up GitHub Repository

### 3.1 Create a New Repository

1. Go to https://github.com/new
2. Fill in the details:
   - **Repository name:** `notion-wishlist-updater` (or any name you like)
   - **Description:** "Automatic price updates for my Notion wish list"
   - **Visibility:** Private (recommended) or Public
   - **Initialize with README:** ✅ Check this box
3. Click **"Create repository"**

### 3.2 Upload the Files

You have two options:

**Option A: Upload via Web Interface (Easiest)**

1. In your repository, click **"Add file"** → **"Upload files"**
2. Upload these files (all provided in this package):
   - `update_prices.py`
   - `requirements.txt`
   - `.github/workflows/update-prices.yml`
3. For the workflow file, you'll need to create the folder structure:
   - Click **"Add file"** → **"Create new file"**
   - Name it: `.github/workflows/update-prices.yml`
   - Paste the content from `update-prices.yml`
   - Click **"Commit new file"**

**Option B: Upload via Git (If you're familiar with Git)**

```bash
# Clone your repository
git clone https://github.com/YOUR_USERNAME/notion-wishlist-updater.git
cd notion-wishlist-updater

# Copy the files into the repository
# (copy update_prices.py, requirements.txt, and .github/workflows/update-prices.yml)

# Create the workflows directory
mkdir -p .github/workflows
# Move update-prices.yml into .github/workflows/

# Commit and push
git add .
git commit -m "Add price updater script"
git push
```

---

## Step 4: Add Secrets to GitHub

GitHub Actions needs your Notion credentials. We'll store them securely as "secrets".

### 4.1 Navigate to Settings

1. In your GitHub repository, click **"Settings"** (top menu)
2. In the left sidebar, click **"Secrets and variables"** → **"Actions"**

### 4.2 Add NOTION_API_KEY

1. Click **"New repository secret"**
2. Name: `NOTION_API_KEY`
3. Value: Paste your Integration Token from Step 2.1 (starts with `secret_...`)
4. Click **"Add secret"**

### 4.3 Add NOTION_DATABASE_ID

1. Click **"New repository secret"** again
2. Name: `NOTION_DATABASE_ID`
3. Value: Paste your Database ID from Step 1.3 (32-character string)
4. Click **"Add secret"**

You should now see two secrets listed! ✅

---

## Step 5: Install Playwright Locally (For Testing)

Before setting up GitHub Actions, let's test locally:

### 5.1 Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### 5.2 Set Environment Variables

**On Mac/Linux:**
```bash
export NOTION_API_KEY="secret_your_key_here"
export NOTION_DATABASE_ID="your_database_id_here"
```

**On Windows (PowerShell):**
```powershell
$env:NOTION_API_KEY="secret_your_key_here"
$env:NOTION_DATABASE_ID="your_database_id_here"
```

**On Windows (Command Prompt):**
```cmd
set NOTION_API_KEY=secret_your_key_here
set NOTION_DATABASE_ID=your_database_id_here
```

### 5.3 Run Local Test

```bash
python update_prices.py
```

You should see output like:
```
============================================================
🚀 Starting Notion Wish List Price Update
⏰ Time: 2026-02-01 10:30:00
🚫 Blocked domains: bestbuy.ca, bestbuy.com
============================================================

📋 Fetching wish list items from Notion...
✅ Found 3 item(s) to check

[1/3] Nintendo Switch 2 Bundle
   🔍 Checking price at www.amazon.ca...
   ✅ Price: $649.99

[2/3] Beats Studio Pro Headphones
   🚫 www.bestbuy.ca is in the blocked list — skipping
...
```

### 5.4 Check Results in Notion

Go to your Notion database and verify:
- Prices have been updated ✅
- "Last Price Check" shows today's date ✅
- Blocked domains were skipped (not marked as failed) ✅

---

## Step 6: Set Up GitHub Actions (Automated Daily Updates)

Now that local testing works, set up GitHub Actions for daily automation.

### 6.1 Manual Test Run on GitHub

1. Go to the **"Actions"** tab in your repository
2. Click **"Update Notion Wish List Prices"** in the left sidebar
3. Click **"Run workflow"** button (top right)
4. Click the green **"Run workflow"** button in the dropdown
5. Wait 30-60 seconds, then refresh the page
6. Click on the workflow run to see the output

### 6.2 Check the Results

The workflow will show you:
- How many items were checked
- Which prices were updated
- Which domains were blocked/skipped
- Any price drops detected
- Any errors encountered

Go to your Notion database and verify everything updated correctly.

---

## Step 7: Customize (Optional)

### 7.1 Manage Blocked Domains

Some websites block automated requests. Edit the `BLOCKED_DOMAINS` list in `update_prices.py`:

```python
# Domains that are known to block automated requests.
BLOCKED_DOMAINS = [
    "bestbuy.ca",
    "bestbuy.com",
    # Add more domains here if they consistently fail
    # "example.com",
]
```

**How it works:**
- URLs containing any blocked domain are skipped entirely
- No request is made (saves time and avoids errors)
- Logged separately in the summary as "Skipped (blocked domain)"
- You can still manually update these prices in Notion

**When to add a domain:**
- If a site consistently returns 403 Forbidden
- If extraction always fails for a particular retailer
- If a site uses heavy anti-bot protection

### 7.2 Manage Cooldown Domains

Some sites allow one visit, then block you for a while before resetting. These go in `COOLDOWN_DOMAINS` instead of being blocked outright:

```python
# Key: domain substring. Value: minimum minutes between successful checks.
COOLDOWN_DOMAINS = {
    "ebgames.ca": 15,
    "manscaped.com": 15,
}
```

**How it works:**
- On a successful check, the script writes the timestamp to `cooldowns.json`
- On the next run, if less than the specified minutes have passed, the site is skipped automatically
- Once the cooldown elapses, it checks again and the cycle repeats
- `cooldowns.json` is in `.gitignore` — it's local state, not committed

**When to use this instead of BLOCKED_DOMAINS:**
- The site works sometimes but not every time
- You notice it fails on back-to-back runs but works after 10–15 minutes
- The debug HTML shows a human-verification page on the second hit

**Not sure which list a new site belongs in?** Run `python setup/test_price_extraction.py` — it tests each URL twice and gives you a verdict.

### 7.3 Change Update Schedule

Edit `.github/workflows/update-prices.yml`:

```yaml
schedule:
  - cron: '0 9 * * *'  # Daily at 9 AM UTC
```

Common schedules:
- `'0 9 * * *'` - Daily at 9 AM UTC
- `'0 */12 * * *'` - Every 12 hours
- `'0 9 * * 1,4'` - Mondays and Thursdays at 9 AM
- `'0 0 * * 0'` - Every Sunday at midnight

Use https://crontab.guru/ to create custom schedules!

### 7.4 Add More Retailers

Price extraction is handled by the `extract_price_from_html()` function in `update_prices.py`.

It tries these methods in order:
1. **JSON-LD structured data** (most reliable)
2. **Meta tags** (`product:price:amount`, etc.)
3. **Site-specific selectors** (Amazon, Best Buy)
4. **Generic price patterns** (looks for `$XX.XX` in text)

**To improve extraction for a specific retailer:**

Find the site-specific selectors section (around line 95) and add your retailer:

```python
elif 'yourstore.com' in domain:
    your_selectors = [
        ('span', {'class': 'product-price'}),
        ('div', {'id': 'price-display'}),
    ]
    for tag, attrs in your_selectors:
        for elem in soup.find_all(tag, attrs):
            match = re.search(r'[\$]?\s*([0-9,]+\.\d{2})', elem.get_text().strip())
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    continue
```

**Tips:**
- Right-click the price on the website → Inspect Element
- Note the HTML tag and class/id
- Add it to the selectors list

### 7.5 Email Notifications

To get emails when prices drop, you can use GitHub's notification features or add a notification step to the workflow.

---

## 🎉 You're All Set!

Your wish list will now update automatically every day!

## 📊 Monitoring

### View Update History
- Go to **Actions** tab in GitHub
- See all past runs and their results
- Click any run to see detailed logs

### What the Script Does
1. Fetches items from Notion (Status = Wishlist, Researching, or Ready to Buy)
2. For each item with a URL:
   - Scrapes the product page
   - Extracts the current price
   - Updates Notion with the new price
   - Records the last check date
   - Logs price changes
3. Waits 2 seconds between items (to be respectful to websites)
4. Prints a summary of updates

### Common Issues and Solutions

**Issue: "No items found to update"**
- ✅ Check that items have Status = "Wishlist", "Researching", or "Ready to Buy"
- ✅ Verify the database is shared with your integration

**Issue: "No module named 'playwright'"**
- ✅ Install Playwright: `pip install playwright`
- ✅ Install browser: `playwright install chromium`

**Issue: "Could not extract price"**
- ✅ Verify the URL is correct and accessible
- ✅ Check if domain is in `BLOCKED_DOMAINS` list (won't even try)
- ✅ The website may have changed its HTML structure
- ✅ Some sites block automated scraping (add to `BLOCKED_DOMAINS`)

**Issue: "Page too small - likely blocked"**
- ✅ Website is blocking the request (403 Forbidden, etc.)
- ✅ Add the domain to `BLOCKED_DOMAINS` list in `update_prices.py`
- ✅ Update prices manually for these items

**Issue: Workflow not running automatically**
- ✅ Check that the workflow file is in `.github/workflows/`
- ✅ GitHub Actions must be enabled in repository settings
- ✅ Free GitHub accounts may have limits on Actions minutes

**Issue: "Error querying Notion database"**
- ✅ Verify your NOTION_DATABASE_ID is correct (32 characters)
- ✅ Confirm the database is shared with your integration
- ✅ Check that NOTION_API_KEY is correct

---

## 🔒 Security Notes

- Your Notion API key is stored as a GitHub secret (encrypted)
- The repository can be private
- Never commit secrets directly to code
- You can revoke the Notion integration anytime at https://www.notion.so/my-integrations

---

## 💡 Tips

1. **Start Small:** Begin with 3-5 items to test
2. **Use Blocked Domains List:** If a site consistently fails, add it to `BLOCKED_DOMAINS`
3. **Monitor Initially:** Watch the first few runs to catch any issues
4. **Check the Summary:** Look at "Skipped (blocked domain)" count to see what's being ignored
5. **Manual Updates:** For blocked domains, update prices manually in Notion when checking
6. **Be Patient:** Price updates may take a minute or two to appear in Notion

---

## 🚀 Advanced Features

### Price Drop Alerts

The script already detects price drops and shows them in the console output. To get notified:

1. Enable GitHub Actions notifications in your account settings
2. Or add email/Slack/Discord notifications to the workflow

### Track Price History

If you added a "Price History" text field, it will automatically log:
- Date of price change
- New price
- Percentage change

### Filter by Priority

To only update high-priority items, modify the Notion query in `update_prices.py`:

```python
response = notion.data_sources.query(
    data_source_id=DATABASE_ID,
    filter={
        "and": [
            {
                "or": [
                    {"property": "Status", "select": {"equals": "Wishlist"}},
                    {"property": "Status", "select": {"equals": "Researching"}}
                ]
            },
            {"property": "Priority", "select": {"equals": "High"}}
        ]
    }
)
results = response.get('results', [])
```

---

## 📚 Additional Resources

- [Notion API Documentation](https://developers.notion.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Beautiful Soup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Cron Schedule Creator](https://crontab.guru/)

---

## 🤝 Need Help?

If you run into issues:
1. Check the workflow logs in the Actions tab
2. Verify all secrets are set correctly
3. Make sure your Notion database has the required properties
4. Test with a simple retailer like Amazon first

---

**Congratulations! You now have a free, automated price tracking system for your Notion wish list!** 🎊