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

## Step 5: Test the Automation

### 5.1 Manual Test Run

Let's test before setting up the schedule:

1. Go to the **"Actions"** tab in your repository
2. Click **"Update Notion Wish List Prices"** in the left sidebar
3. Click **"Run workflow"** button (top right)
4. Click the green **"Run workflow"** button in the dropdown
5. Wait 30-60 seconds, then refresh the page
6. Click on the workflow run to see the output

### 5.2 Check the Results

The workflow will show you:
- How many items were checked
- Which prices were updated
- Any price drops detected
- Any errors encountered

Go to your Notion database and verify:
- Prices have been updated ✅
- "Last Price Check" shows today's date ✅
- "Price History" has an entry (if the field exists) ✅

---

## Step 6: Customize (Optional)

### 6.1 Change Update Schedule

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

### 6.2 Add More Retailers

To add support for a new retailer, edit `update_prices.py`:

1. Find the section with retailer-specific extractors
2. Add a new function like:

```python
def extract_price_YOUR_RETAILER(soup):
    """Extract price from Your Retailer product pages"""
    # Find the price element (inspect the website's HTML)
    element = soup.find('span', {'class': 'price-class-name'})
    if element:
        text = element.get_text()
        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            return float(match.group(1))
    return None
```

3. Add it to the `extract_price_from_url()` function:

```python
elif 'yourretailer.com' in domain:
    price = extract_price_YOUR_RETAILER(soup)
```

### 6.3 Add Email Notifications

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

**Issue: "Could not extract price"**
- ✅ Verify the URL is correct and accessible
- ✅ The website may have changed its HTML structure
- ✅ Some sites may block automated scraping

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
2. **Check Compatibility:** Not all websites allow scraping - test each retailer
3. **Monitor Initially:** Watch the first few runs to catch any issues
4. **Update Selectors:** If a website redesigns, you may need to update the price selectors
5. **Be Patient:** Price updates may take a minute or two to appear in Notion

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
results = notion.databases.query(
    database_id=DATABASE_ID,
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
