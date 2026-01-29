import os
import sys
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Add src directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.obsidian import ObsidianVaultHandler
from services.notion import NotionHandler
from services.llm import LLMHandler
from keep_alive import keep_alive

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
VAULT_PATH = os.getenv("VAULT_PATH", "./Emerald Digital Operation")

# Initialize Services
# We will attach these to the bot instance in the setup_hook or main block
obsidian_service = ObsidianVaultHandler(vault_path=VAULT_PATH)
notion_service = NotionHandler()
llm_service = LLMHandler()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        
        # Attach services
        self.obsidian = obsidian_service
        self.notion = notion_service
        self.llm = llm_service

    async def setup_hook(self):
        # Load Cogs
        cogs = ['cogs.daily_log', 'cogs.notion_integration', 'cogs.design_intake']
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"Loaded extension: {cog}")
            except Exception as e:
                print(f"Failed to load extension {cog}: {e}")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
        
        guild_id = os.getenv("DISCORD_GUILD_ID")
        try:
            if guild_id:
                guild = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"Synced {len(synced)} command(s) to Guild {guild_id} (Instant)")
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
