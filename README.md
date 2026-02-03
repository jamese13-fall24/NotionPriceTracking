# 🛍️ Notion Wish List Price Updater

Automatically update product prices in your Notion wish list database using GitHub Actions. Completely free and runs daily!

## ✨ Features

- 🔄 **Automatic Updates:** Runs daily via GitHub Actions (free!)
- 🏪 **Multi-Retailer Support:** Works with Amazon, Walmart, Target, Best Buy, eBay, and more
- 💰 **Price Drop Detection:** Alerts you when prices decrease
- 📊 **Price History Tracking:** Keeps a log of price changes
- 🔒 **Secure:** Uses GitHub secrets to protect your credentials
- ⚡ **Easy Setup:** Step-by-step guide included

## 🚀 Quick Start

1. **Set up your Notion database** with required properties (Name, URL, Price, Status, Last Price Check)
2. **Create a Notion integration** and get your API key
3. **Fork this repository** or create a new one with these files
4. **Add secrets** to GitHub (NOTION_API_KEY and NOTION_DATABASE_ID)
5. **Run the workflow** manually to test
6. **Enjoy automatic price updates!**

👉 **[Full Setup Guide](SETUP_GUIDE.md)** - Detailed step-by-step instructions

## 📋 Requirements

### Notion Database Properties

Your database must have these properties:

| Property | Type | Description |
|----------|------|-------------|
| Name | Title | Product name |
| URL | URL | Product page link |
| Price | Number | Current price |
| Status | Select | Tracking status (Wishlist, Researching, Ready to Buy) |
| Last Price Check | Date | Last update timestamp |
| Price History | Text | Optional: Price change log |

### GitHub Secrets

Add these to your repository settings → Secrets and variables → Actions:

- `NOTION_API_KEY` - Your Notion integration token
- `NOTION_DATABASE_ID` - Your Notion database ID

## 🛠️ How It Works

1. **GitHub Actions** triggers the workflow daily at 9 AM UTC
2. Script fetches items from your Notion database with status: Wishlist, Researching, or Ready to Buy
3. For each item:
   - Scrapes the product URL
   - Extracts the current price
   - Updates the Notion database
   - Logs price changes
4. Prints a summary of updates and price drops

## 🏪 Supported Retailers

Currently supports:
- ✅ Amazon.ca
- ✅ UTdisguise
- ⏳ EBGames (cooldown between checks)
- ⏳ Manscaped (cooldown between checks)
- 🚫 Best Buy (blocked — update manually)
- ✅ Generic sites (attempts automatic detection)

Need to add a retailer? Check the [customization section](SETUP_GUIDE.md#add-more-retailers) in the setup guide!

## 📅 Schedule

By default, runs **daily at 9 AM UTC**. You can customize this in `.github/workflows/update-prices.yml`:

```yaml
schedule:
  - cron: '0 9 * * *'  # Change this line
```

Common schedules:
- `'0 9 * * *'` - Daily at 9 AM UTC
- `'0 */12 * * *'` - Every 12 hours  
- `'0 9 * * 1,4'` - Mondays and Thursdays
- `'0 0 * * 0'` - Every Sunday at midnight

Use [crontab.guru](https://crontab.guru/) to create custom schedules!

## 🎯 Example Output

```
============================================================
🚀 Starting Notion Wish List Price Update
⏰ Time: 2026-01-28 09:00:00
============================================================

📋 Fetching wish list items from Notion...
✅ Found 5 items to check

[1/5] Sony WH-1000XM5 Headphones
   🔍 Checking price at amazon.com...
   ✅ Updated: $349.99

[2/5] Nintendo Switch OLED
   🔍 Checking price at bestbuy.com...
💰 PRICE DROP: Nintendo Switch OLED
   Was: $349.99 → Now: $299.99 (Save $50.00!)

...

============================================================
📊 UPDATE SUMMARY
============================================================
Total items:              5
Successfully updated:     3
Failed to extract:        0
No URL provided:          0
Skipped (blocked domain): 1
Skipped (cooldown):       1
Price drops detected:     1

✨ Update complete!
============================================================
```

## 🔧 Customization

### Change Update Frequency
Edit the cron schedule in `.github/workflows/update-prices.yml`

### Add Price Drop Email Notifications
You can extend the workflow to send emails or Slack messages when prices drop

### Filter by Priority
Modify the Notion query to only update high-priority items

### Add More Retailers
Add custom price extraction functions for new websites

See the [Setup Guide](SETUP_GUIDE.md) for detailed customization instructions!

## ⚠️ Important Notes

- **Respect Websites:** The script includes delays between requests
- **Terms of Service:** Some websites prohibit scraping - use at your own discretion
- **Accuracy:** Prices may not extract correctly if websites change their design
- **Rate Limits:** Free GitHub Actions has usage limits (2,000 minutes/month for private repos)

## 🐛 Troubleshooting

**No items found?**
- Check that items have Status = "Wishlist", "Researching", or "Ready to Buy"
- Verify database is shared with your Notion integration

**Price not updating?**
- Check the workflow logs in GitHub Actions
- Website HTML may have changed (update selectors)
- Some sites actively block scraping

**Workflow not running?**
- Verify secrets are set correctly
- Check that workflow file is in `.github/workflows/`
- GitHub Actions must be enabled in repository settings

See the [Setup Guide](SETUP_GUIDE.md) for more troubleshooting tips!

## 📚 Files Included

- `update_prices.py` - Main Python script
- `requirements.txt` - Python dependencies
- `setup/` - Diagnostic scripts:
  - `find_database.py` - Find and verify your Notion database
  - `test_notion_api.py` - Test Notion API connectivity
  - `test_price_extraction.py` - Test new sites and get a verdict (blocked / cooldown / fine)
- `.gitignore` - Excludes `debug/` and `cooldowns.json`
- `SETUP_GUIDE.md` - Detailed setup instructions
- `TROUBLESHOOTING.md` - Diagnosing and fixing issues
- `QUICK_REFERENCE.md` - One-page cheat sheet
- `README.md` - This file

## 🤝 Contributing

Feel free to fork this repository and customize it for your needs! Some ideas:
- Add support for more retailers
- Implement price drop email notifications
- Add graphing/visualization of price history
- Support for other currencies

## 📄 License

This project is open source and available for personal use.

## 🙏 Credits

Built with:
- [Notion API](https://developers.notion.com/)
- [Playwright](https://playwright.dev/)
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)
- [Claude AI](https://claude.ai/)
---

**Happy price tracking! May all your wish list items go on sale! 🎉**