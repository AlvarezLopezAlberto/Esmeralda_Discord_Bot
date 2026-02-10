import discord
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append(os.path.join(os.getcwd(), "src"))

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
THREAD_ID = 1470846699198222489

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    
    try:
        thread = await client.fetch_channel(THREAD_ID)
        print(f"Thread Name: {thread.name}")
        print(f"Parent Channel: {thread.parent}")
        
        async for message in thread.history(limit=10, oldest_first=True):
            print(f"[{message.created_at}] {message.author}: {message.content[:200]}...")
            if message.embeds:
                for embed in message.embeds:
                    print(f"Embed: {embed.title} - {embed.description[:200]}")
            print("-" * 20)
            
    except Exception as e:
        print(f"Error: {e}")
        
    await client.close()

client.run(TOKEN)
