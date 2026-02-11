#!/usr/bin/env python3
"""
Test the new _extract_notion_url_from_starter logic with the problematic thread.
"""
import os
import sys
import asyncio
import discord
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), "agents", "design"))
from agent import DesignAgent

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
THREAD_ID = 1463668685993541696

class TestBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        
        class MockNotionHandler:
            def is_enabled(self):
                return True
            def find_task_by_discord_thread(self, db_id, guild_id, thread_id):
                # Simulate not finding via property
                return None
        
        class MockLLM:
            pass
        
        self.notion = MockNotionHandler()
        self.llm = MockLLM()

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        try:
            # Create agent
            agent_dir = os.path.abspath("agents/design")
            agent = DesignAgent(self, "design", agent_dir)
            
            # Fetch thread
            thread = await self.fetch_channel(THREAD_ID)
            print(f'Testing thread: {thread.name}')
            print()
            
            # Test the extraction method
            notion_url = await agent._extract_notion_url_from_starter(thread, THREAD_ID)
            
            if notion_url:
                print(f'✅ SUCCESS: Extracted Notion URL from starter:')
                print(f'   {notion_url}')
                print()
                print('This thread should now be marked as "approved" and Esmeralda won\'t re-process it.')
            else:
                print(f'❌ FAILED: Could not extract Notion URL from starter message')
                
        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()
        
        await self.close()

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found.")
    else:
        bot = TestBot()
        bot.run(TOKEN)
