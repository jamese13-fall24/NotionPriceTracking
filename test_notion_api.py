"""
Quick test to see what Notion API methods are available
"""
import os
from notion_client import Client

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

if not NOTION_API_KEY:
    print("ERROR: NOTION_API_KEY not set")
    exit(1)

print(f"API Key: {NOTION_API_KEY[:20]}...")
print(f"Database ID: {DATABASE_ID}")
print()

# Create client
notion = Client(auth=NOTION_API_KEY)

print("=== Checking notion.databases ===")
print(f"Type: {type(notion.databases)}")
print(f"Dir: {[m for m in dir(notion.databases) if not m.startswith('_')]}")
print()

# Try different ways to query
print("=== Attempting different query methods ===")

# Method 1: Direct query
try:
    print("1. Trying: notion.databases.query(database_id=...)")
    result = notion.databases.query(database_id=DATABASE_ID)
    print(f"   ✅ SUCCESS! Got {len(result.get('results', []))} items")
except Exception as e:
    print(f"   ❌ FAILED: {e}")

# Method 2: With filter
try:
    print("2. Trying: notion.databases.query(database_id=..., filter=...)")
    result = notion.databases.query(
        database_id=DATABASE_ID,
        filter={"property": "Status", "select": {"equals": "Wishlist"}}
    )
    print(f"   ✅ SUCCESS! Got {len(result.get('results', []))} items")
except Exception as e:
    print(f"   ❌ FAILED: {e}")

# Method 3: Check if there's a different endpoint
try:
    print("3. Trying: notion.search()")
    result = notion.search(filter={"property": "object", "value": "database"})
    print(f"   ✅ SUCCESS! Got {len(result.get('results', []))} databases")
except Exception as e:
    print(f"   ❌ FAILED: {e}")

# Method 4: Retrieve database
try:
    print("4. Trying: notion.databases.retrieve(database_id=...)")
    result = notion.databases.retrieve(database_id=DATABASE_ID)
    print(f"   ✅ SUCCESS! Database: {result.get('title', [{}])[0].get('plain_text', 'N/A')}")
except Exception as e:
    print(f"   ❌ FAILED: {e}")

print()
print("=== Checking for other endpoints ===")
print(f"Has 'blocks': {hasattr(notion, 'blocks')}")
print(f"Has 'pages': {hasattr(notion, 'pages')}")
print(f"Has 'users': {hasattr(notion, 'users')}")
print(f"Has 'search': {hasattr(notion, 'search')}")

if hasattr(notion, 'pages'):
    print(f"\nnotion.pages methods: {[m for m in dir(notion.pages) if not m.startswith('_')]}")
