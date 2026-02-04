import sys
import os
import asyncio
import discord
from dotenv import load_dotenv

# Ensure we are in the project root for path resolution
# But we will run this from root via python3 src/trigger_design.py
# Add src to path
sys.path.append(os.path.abspath("src"))
sys.path.append(os.getcwd())

try:
    from services.notion import NotionHandler
    from services.llm import LLMHandler
    from agents.design.agent import DesignAgent
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
# The ID provided by user
TARGET_ID = 1468642052827779317

class OneOffBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        # Mimic the structure expected by DesignAgent
        self.notion = NotionHandler()
        self.llm = LLMHandler()

    async def on_ready(self):
        print(f"Logged in as {self.user} for Manual Trigger")
        try:
            # Fetch the thread (Forum Post)
            print(f"Fetching target {TARGET_ID}...")
            channel = await self.fetch_channel(TARGET_ID)
            
            if not isinstance(channel, discord.Thread):
                print(f"Target is not a Thread, it is {type(channel)}. Trying to fetch as message if possible context allows...")
                # Note: fetch_channel only returns channels/threads.
            
            print(f"Found Thread: {channel.name} ({channel.id})")
            
            # The starter message usually has the same ID as the thread in Forum channels
            print("Fetching starter message...")
            message = await channel.fetch_message(TARGET_ID)
            print(f"Message content: {message.content[:50]}...")

            # Initialize Agent
            print("Initializing DesignAgent...")
            agent_dir = os.path.abspath("agents/design")
            if not os.path.exists(agent_dir):
                print(f"Error: Agent dir {agent_dir} does not exist")
                await self.close()
                return

            agent = DesignAgent(self, "design", agent_dir)
            
            print("Executing agent.handle()...")
            await agent.handle(message)
            print("Execution finished successfully.")

        except discord.NotFound:
            print("Error: Target ID not found. Ensure the bot is in the server and has access.")
        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()
        
        await self.close()

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found.")
    else:
        bot = OneOffBot()
        bot.run(TOKEN)
