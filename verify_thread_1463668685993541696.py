#!/usr/bin/env python3
"""
Verification script to test that Esmeralda correctly handles thread 1463668685993541696.
This script checks if a Notion task exists for this thread.
"""
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), "src"))
from services.notion import NotionHandler

load_dotenv()

THREAD_ID = 1463668685993541696
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
NOTION_DB_ID = "9b1d386dbae1401b8a58af5a792e8f1f"

if __name__ == "__main__":
    print(f"Checking if thread {THREAD_ID} has an existing Notion task...")
    print(f"Guild ID: {GUILD_ID}")
    print(f"Database ID: {NOTION_DB_ID}")
    print()
    
    notion = NotionHandler()
    
    if not notion.is_enabled():
        print("❌ Notion is not enabled (missing NOTION_TOKEN)")
        sys.exit(1)
    
    existing_url = notion.find_task_by_discord_thread(
        NOTION_DB_ID,
        GUILD_ID,
        THREAD_ID
    )
    
    if existing_url:
        print(f"✅ Found existing Notion task for this thread:")
        print(f"   URL: {existing_url}")
        print()
        print("This means Esmeralda should NOT re-process this thread.")
        print("The Notion double-check will mark it as 'approved' immediately.")
    else:
        print(f"❌ No existing Notion task found for this thread.")
        print()
        print("This thread may need manual intervention.")
        print("You can create a task and link it to the thread URL.")
