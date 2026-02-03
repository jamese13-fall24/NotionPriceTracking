"""
Find your Notion database ID.
Run this if you're unsure of your DATABASE_ID or want to verify
the integration can see your databases.

Usage:
    set NOTION_API_KEY=secret_your_key_here
    python setup/find_database.py
"""

import os
from notion_client import Client

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")

if not NOTION_API_KEY:
    print("❌ NOTION_API_KEY environment variable not set")
    print("\nSet it first:")
    print("  Windows CMD:        set NOTION_API_KEY=secret_...")
    print("  Windows PowerShell: $env:NOTION_API_KEY='secret_...'")
    print("  Mac/Linux:          export NOTION_API_KEY='secret_...'")
    exit(1)

notion = Client(auth=NOTION_API_KEY)

print("=" * 60)
print("🔍 Searching for accessible databases...")
print("=" * 60)
print()

try:
    # notion-client 2.7.0: search filter uses "data_source" not "database"
    response = notion.search(
        filter={"property": "object", "value": "data_source"}
    )

    databases = response.get('results', [])

    if not databases:
        print("❌ No databases found!")
        print()
        print("This could mean:")
        print("  1. You haven't shared any databases with this integration")
        print("  2. The integration doesn't have the right permissions")
        print()
        print("To share a database:")
        print("  1. Open your Notion database")
        print("  2. Click '...' (three dots) in top right")
        print("  3. Click 'Add connections'")
        print("  4. Select your integration")
    else:
        print(f"✅ Found {len(databases)} database(s):\n")

        for i, db in enumerate(databases, 1):
            db_id = db['id']

            # Title can be nested differently depending on the object type
            title = "Untitled"
            if db.get('title'):
                # direct title array (from databases.retrieve style)
                title = db['title'][0].get('plain_text', 'Untitled')
            elif db.get('properties', {}).get('title'):
                # properties-based title
                title = db['properties']['title'][0].get('plain_text', 'Untitled')

            url = db.get('url', 'N/A')

            print(f"  Database {i}:")
            print(f"    Name: {title}")
            print(f"    ID:   {db_id}")
            print(f"    URL:  {url}")
            print()

            if 'wish' in title.lower() or 'item' in title.lower():
                print(f"    👉 Looks like your wish list! Set:")
                print(f"       NOTION_DATABASE_ID={db_id}")
                print()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)