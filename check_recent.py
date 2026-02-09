import discord
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    thread_id = 1470470960841756837
    try:
        thread = await client.fetch_channel(thread_id)
        print(f"Checking thread: {thread.name}")
        async for m in thread.history(limit=10):
            print(f"[{m.author.name}] {m.content[:100]}...")
    except Exception as e:
        print(f"Error: {e}")
    await client.close()

client.run(TOKEN)
