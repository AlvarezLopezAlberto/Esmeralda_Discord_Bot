import os
import sys
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Add src directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.notion import NotionHandler
from services.llm import LLMHandler
from keep_alive import keep_alive
from adk import AgentManager
from utilities.notion import process_notion_links

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Initialize Services
notion_service = NotionHandler()
llm_service = LLMHandler()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        
        # Attach services
        self.notion = notion_service
        self.llm = llm_service
        self.agent_manager = None

    async def setup_hook(self):
        # Initialize ADK Agent Manager
        self.agent_manager = AgentManager(self)
        self.agent_manager.load_agents()
        await self.agent_manager.register_cogs()
        
        print("ADK Framework Initialized.")

    async def on_message(self, message):
        # Prevent bot recursion
        if message.author.bot:
            return

        # 1. Utilities Layer (Deterministic)
        # Notion Link Utility
        handled_by_utility = await process_notion_links(message, self.notion)
        if handled_by_utility:
            # If utility replaced the message, stop processing this object.
            # The new webhook message is a bot message and will be ignored by recursion check.
            return

        # 2. Agent Layer (AI)
        if self.agent_manager:
            await self.agent_manager.route_message(message)

        # 3. Legacy Commands (if any)
        await self.process_commands(message)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
        
        # Sync Commands (Slash Commands from Agents)
        guild_id = os.getenv("DISCORD_GUILD_ID")
        try:
            if guild_id:
                guild = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"Synced {len(synced)} command(s) to Guild {guild_id}")
            else:
                synced = await self.tree.sync()
                print(f"Synced {len(synced)} command(s) Globally")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
        
        print("Bot is ready and listening.")

bot = MyBot()

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found in environment.")
    else:
        keep_alive()
        bot.run(DISCORD_TOKEN)
