import sys
import os
import asyncio
import discord
from dotenv import load_dotenv

# Ensure we are in the project root for path resolution
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
TARGET_ID = 1470846699198222489

class OneOffBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.notion = NotionHandler()
        self.llm = LLMHandler()

    async def on_ready(self):
        print(f"Logged in as {self.user} for Manual Trigger")
        try:
            print(f"Fetching target {TARGET_ID}...")
            channel = await self.fetch_channel(TARGET_ID)
            
            if not isinstance(channel, discord.Thread):
                print(f"Target is not a Thread, it is {type(channel)}.")
                await self.close()
                return
            
            print(f"Found Thread: {channel.name} ({channel.id})")
            
            print("Fetching starter message...")
            message = await channel.fetch_message(TARGET_ID)
            print(f"Message content preview: {message.content[:100]}...")

            print("Initializing DesignAgent...")
            agent_dir = os.path.abspath("agents/design")
            agent = DesignAgent(self, "design", agent_dir)
            
            print("Executing agent.handle()...")
            # We trigger it as if the starter message was just sent or as if we are re-validating it
            await agent.handle(message)
            print("Execution finished successfully.")

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
