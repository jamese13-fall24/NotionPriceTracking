"""
Find your Notion database ID
This script will search for all databases you have access to
"""
import os
from notion_client import Client

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")

if not NOTION_API_KEY:
    print("ERROR: NOTION_API_KEY environment variable not set")
    exit(1)

notion = Client(auth=NOTION_API_KEY)

print("=" * 60)
print("🔍 Searching for accessible databases...")
print("=" * 60)
print()

try:
    # Search for all databases
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
        print("To fix:")
        print("  1. Open your Notion database")
        print("  2. Click '...' (three dots) in top right")
        print("  3. Click 'Add connections'")
        print("  4. Select your integration")
    else:
        print(f"✅ Found {len(databases)} database(s):\n")
        
        for i, db in enumerate(databases, 1):
            db_id = db['id']
            
            # Get title
            title_property = db.get('title', [])
            if title_property:
                title = title_property[0].get('plain_text', 'Untitled')
            else:
                title = 'Untitled'
            
            # Get URL
            url = db.get('url', 'N/A')
            
            print(f"Database {i}:")
            print(f"  Name: {title}")
            print(f"  ID:   {db_id}")
            print(f"  URL:  {url}")
            print()
            
            # If this looks like a wish list, highlight it
            if 'wish' in title.lower() or 'item' in title.lower():
                print(f"  👉 This looks like your wish list!")
                print(f"     Use this in your .env or environment:")
                print(f"     NOTION_DATABASE_ID={db_id}")
                print()
        
except Exception as e:
    print(f"❌ Error: {e}")
    print()
    import traceback
    traceback.print_exc()

print("=" * 60)
