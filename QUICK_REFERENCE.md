# Quick Reference Card

## 🔑 Essential Information

### Notion Integration Setup
1. Go to: https://www.notion.so/my-integrations
2. Create integration: "Wish List Price Updater"
3. Copy token (starts with `secret_...`)
4. Share your database with the integration

### GitHub Secrets (Required)
- `NOTION_API_KEY` - Your integration token
- `NOTION_DATABASE_ID` - Your database ID (32 characters)

### Required Notion Properties
| Property | Type |
|----------|------|
| Name | Title |
| URL | URL |
| Price | Number |
| Status | Select (must include: Wishlist, Researching, Ready to Buy) |
| Last Price Check | Date |

### Files You Need
1. `update_prices.py` - Main script
2. `requirements.txt` - Dependencies
3. `.github/workflows/update-prices.yml` - Automation

---

## 🚀 Quick Start Checklist

- [ ] Create/configure Notion database with required properties
- [ ] Get Database ID from URL
- [ ] Create Notion integration at notion.so/my-integrations
- [ ] Copy integration token
- [ ] Share database with integration
- [ ] Create GitHub repository
- [ ] Upload files to repository
- [ ] Add NOTION_API_KEY secret in GitHub
- [ ] Add NOTION_DATABASE_ID secret in GitHub
- [ ] Test: Run workflow manually from Actions tab
- [ ] Verify: Check Notion database for updated prices

---

## 📍 Where to Find Things

### Database ID
In your Notion database URL:
```
https://www.notion.so/workspace/DATABASE_ID?v=...
                                ^^^^^^^^^^^
```

### Integration Token
1. Go to https://www.notion.so/my-integrations
2. Click your integration
3. Copy "Internal Integration Token"

### GitHub Secrets
Repository → Settings → Secrets and variables → Actions → New repository secret

### Workflow Logs
Repository → Actions → Click workflow run

---

## ⏰ Default Schedule

Runs **daily at 9 AM UTC**

Change in `.github/workflows/update-prices.yml`:
```yaml
schedule:
  - cron: '0 9 * * *'
```

---

## 🏪 Supported Sites

- Amazon (US, CA)
- Walmart (US, CA)
- Target
- Best Buy (US, CA)
- eBay (US, CA)
- Generic (auto-detect)

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| No items found | Check Status field = "Wishlist", "Researching", or "Ready to Buy" |
| Can't extract price | Check URL is valid, website may have changed |
| Workflow not running | Check secrets are set, Actions enabled |
| Database error | Verify Database ID, check integration is connected |

---

## 💡 Pro Tips

1. **Test First:** Run manually before relying on schedule
2. **Start Small:** Test with 2-3 items initially
3. **Monitor Logs:** Check first few runs in Actions tab
4. **Check Compatibility:** Not all sites work (test your retailers)
5. **Keep URLs Clean:** Use direct product page URLs

---

## 🔗 Useful Links

- Notion Integrations: https://www.notion.so/my-integrations
- GitHub Actions: https://github.com/YOUR_USERNAME/YOUR_REPO/actions
- Cron Schedule Tester: https://crontab.guru/
- Notion API Docs: https://developers.notion.com/

---

**For complete instructions, see SETUP_GUIDE.md**
