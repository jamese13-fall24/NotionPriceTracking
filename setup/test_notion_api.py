"""
Test the Notion API methods used by update_prices.py.
Run this to verify your integration token and database ID are correct,
and that the two operations the main script relies on actually work.

Usage:
    set NOTION_API_KEY=secret_your_key_here
    set NOTION_DATABASE_ID=your_32_char_id
    python setup/test_notion_api.py
"""

import os
from notion_client import Client

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

if not NOTION_API_KEY:
    print("❌ NOTION_API_KEY not set")
    exit(1)
if not DATABASE_ID:
    print("❌ NOTION_DATABASE_ID not set")
    exit(1)

print("=" * 60)
print("🧪 Notion API Test")
print("=" * 60)
print(f"  API Key:     {NOTION_API_KEY[:20]}...")
print(f"  Database ID: {DATABASE_ID}")
print()

notion = Client(auth=NOTION_API_KEY)

# ------------------------------------------------------------------
# 1. Retrieve the database (confirms ID + permissions)
# ------------------------------------------------------------------
print("1. notion.databases.retrieve()")
try:
    db = notion.databases.retrieve(database_id=DATABASE_ID)
    title = db.get('title', [{}])
    title_text = title[0].get('plain_text', 'N/A') if title else 'N/A'
    print(f"   ✅ OK — database name: {title_text}")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
print()

# ------------------------------------------------------------------
# 2. Query the database (the main read operation)
# ------------------------------------------------------------------
print("2. notion.data_sources.query()")
try:
    response = notion.data_sources.query(data_source_id=DATABASE_ID)
    results = response.get('results', [])
    print(f"   ✅ OK — returned {len(results)} item(s)")

    # Show the first item so you can verify it's the right database
    if results:
        first = results[0]
        props = first.get('properties', {})

        name = "?"
        if 'Name' in props:
            name_arr = props['Name'].get('title', [])
            name = name_arr[0]['text']['content'] if name_arr else '?'

        url = props.get('URL', {}).get('url', 'no URL')
        price = props.get('Price', {}).get('number', 'no price')

        print(f"   First item: {name}")
        print(f"     URL:   {url}")
        print(f"     Price: {price}")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
print()

# ------------------------------------------------------------------
# 3. Query with the same filter update_prices.py uses
# ------------------------------------------------------------------
print("3. notion.data_sources.query() with Status filter")
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
    results = response.get('results', [])
    print(f"   ✅ OK — {len(results)} item(s) match the active-status filter")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    print("   This is the filter update_prices.py uses — fix this before running the main script")
print()

# ------------------------------------------------------------------
# 4. pages.update (write test — updates Last Price Check on first item
#    only if you type 'y'; otherwise skipped)
# ------------------------------------------------------------------
print("4. notion.pages.update() — write permission check")
try:
    # Grab a page ID from the earlier query
    response = notion.data_sources.query(data_source_id=DATABASE_ID)
    results = response.get('results', [])
    if not results:
        print("   ⚠️  No items in database — can't test write. Skipped.")
    else:
        page_id = results[0]['id']
        props = results[0].get('properties', {})
        name_arr = props.get('Name', {}).get('title', [])
        name = name_arr[0]['text']['content'] if name_arr else '?'

        answer = input(f"   Write test on \"{name}\" — run it? (y/n): ").strip().lower()
        if answer == 'y':
            from datetime import datetime
            notion.pages.update(
                page_id=page_id,
                properties={
                    "Last Price Check": {"date": {"start": datetime.now().isoformat()}}
                }
            )
            print("   ✅ OK — Last Price Check updated")
        else:
            print("   ⏭️  Skipped")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
print()

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
print("=" * 60)
print("If everything shows ✅, update_prices.py should work.")
print("=" * 60)