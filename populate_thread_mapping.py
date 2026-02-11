#!/usr/bin/env python3
"""
Script to populate thread_notion_mapping.csv with existing threads from the intake forum.
This will fetch all threads and extract Notion links from starter messages where available.
"""
import os
import sys
import asyncio
import discord
import csv
import re
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
INTAKE_FORUM_ID = 1458858450355224709
MAPPING_FILE = "thread_notion_mapping.csv"

async def main():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f'Logged in as {client.user}')
        print(f'Fetching threads from intake forum...\n')
        
        try:
            # Get the intake forum
            forum = await client.fetch_channel(INTAKE_FORUM_ID)
            
            # Fetch all active and archived threads
            threads_data = []
            
            # Active threads
            print("Fetching active threads...")
            async for thread in forum.archived_threads(limit=None):
                threads_data.append(thread)
            
            # Also get currently active threads
            for thread in forum.threads:
                threads_data.append(thread)
            
            print(f"Found {len(threads_data)} threads total\n")
            
            # Process each thread
            mappings = []
            for i, thread in enumerate(threads_data, 1):
                print(f"[{i}/{len(threads_data)}] Processing: {thread.name[:50]}...")
                
                thread_id = thread.id
                thread_title = thread.name
                notion_url = ""
                status = "pending"
                notes = ""
                
                try:
                    # Fetch starter message
                    starter = await thread.fetch_message(thread_id)
                    content = starter.content or ""
                    
                    # Extract Notion URL
                    notion_urls = re.findall(r'(https?://(?:\S+\.)?notion\.(?:so|site)/[^\s]+)', content)
                    if notion_urls:
                        notion_url = notion_urls[0]
                        status = "approved"
                        print(f"  ✅ Found Notion link")
                    else:
                        print(f"  ⚠️  No Notion link in starter")
                        notes = "No Notion link in starter message"
                        
                except Exception as e:
                    print(f"  ❌ Error fetching starter: {e}")
                    notes = f"Error: {str(e)}"
                
                mappings.append({
                    "thread_id": thread_id,
                    "thread_title": thread_title,
                    "notion_url": notion_url,
                    "status": status,
                    "notes": notes
                })
            
            # Write to CSV
            print(f"\nWriting to {MAPPING_FILE}...")
            with open(MAPPING_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['thread_id', 'thread_title', 'notion_url', 'status', 'notes'])
                writer.writeheader()
                writer.writerows(mappings)
            
            print(f"✅ Complete! Wrote {len(mappings)} threads to {MAPPING_FILE}")
            print(f"\nSummary:")
            approved = sum(1 for m in mappings if m['status'] == 'approved')
            pending = sum(1 for m in mappings if m['status'] == 'pending')
            print(f"  - Approved (with Notion link): {approved}")
            print(f"  - Pending (no link): {pending}")
            print(f"\nPlease review and fill in any missing Notion URLs manually.")
            
        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()
        
        await client.close()
    
    await client.start(TOKEN)

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
        sys.exit(1)
    
    asyncio.run(main())
