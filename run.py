"""
run.py — launcher for the Notion Wish List Price Updater.

Just run:   python run.py

It handles everything:
  - Stores your Notion API key in config.json (asks once, never again)
  - Discovers every database your integration can see
  - Lets you pick which one to update
  - Calls update_prices.main() with the right credentials
"""

import json
import os
import sys

from notion_client import Client

# ---------------------------------------------------------------------------
# Config file — lives next to this script, gitignored
# ---------------------------------------------------------------------------

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    """Return the parsed config dict, or {} if the file doesn't exist yet."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(config):
    """Write the config dict to config.json."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get_api_key(config):
    """
    Return the API key from config if it exists.
    Otherwise prompt the user, validate it, save it, and return it.
    """
    key = config.get("notion_api_key")
    if key:
        return key

    print("=" * 60)
    print("First-time setup — paste your Notion integration token below.")
    print("(It starts with 'ntn_')")
    print("=" * 60)
    key = input("\n  Token: ").strip()

    if not key.startswith("ntn_"):
        print("  ⚠️  That doesn't look like a valid token (should start with ntn_)")
        print("  Saving it anyway — you can delete config.json and re-run to fix it.")

    config["notion_api_key"] = key
    save_config(config)
    print(f"  ✅ Saved to config.json\n")
    return key


# ---------------------------------------------------------------------------
# Database discovery
# ---------------------------------------------------------------------------

def discover_databases(notion):
    """
    Ask Notion for every database the integration can see.
    Returns a list of dicts: [{ "id": ..., "title": ... }, ...]
    """
    try:
        response = notion.search(
            filter={"property": "object", "value": "data_source"}
        )
    except Exception as e:
        print(f"\n  ❌ Notion search failed: {e}")
        print("     Double-check your API key in config.json.")
        return []

    databases = []
    for db in response.get("results", []):
        # Search returns data_source objects.
        # Use the data source ID directly — that's what data_sources.query() expects.
        db_id = db.get("id")
        
        # Title can sit in different places depending on the object shape
        title = "Untitled"
        if db.get("title"):
            title = db["title"][0].get("plain_text", "Untitled")
        elif db.get("properties", {}).get("title"):
            title = db["properties"]["title"][0].get("plain_text", "Untitled")

        databases.append({"id": db_id, "title": title})

    return databases


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

def pick_database(databases):
    """
    Print a numbered list of databases and let the user choose one.
    Returns the chosen database dict, or None if they quit.
    """
    print()
    print("=" * 60)
    print("📋 Available databases")
    print("=" * 60)

    for i, db in enumerate(databases, 1):
        print(f"  {i}.  {db['title']}")
        print(f"      {db['id']}")

    print(f"\n  q.  Quit")
    print("-" * 60)

    choice = input("  Pick a number: ").strip()

    if choice.lower() == "q":
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(databases):
            return databases[idx]
    except ValueError:
        pass

    print("  ❌ Invalid choice.")
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    config = load_config()
    api_key = get_api_key(config)

    notion = Client(auth=api_key)

    # Discover databases
    print("  🔍 Searching for databases...", end=" ", flush=True)
    databases = discover_databases(notion)

    if not databases:
        print("\n  ❌ No databases found.")
        print("     Make sure your integration is shared with at least one database.")
        print("     (Open the database in Notion → ... → Add connections → pick your integration)")
        return

    print(f"found {len(databases)}.")

    # Let user pick
    chosen = pick_database(databases)
    if chosen is None:
        print("\n  Bye!")
        return

    # Hand off to the updater
    print()
    import update_prices
    update_prices.main(api_key, chosen["id"])


if __name__ == "__main__":
    main()