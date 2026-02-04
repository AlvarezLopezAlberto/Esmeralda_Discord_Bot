import discord
import os
import asyncio
from dotenv import load_dotenv

# Load .env
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ ERROR: No DISCORD_TOKEN found in .env")
    exit(1)

print(f"🔑 Token found: {TOKEN[:5]}...*****")

class TestBot(discord.Client):
    async def on_ready(self):
        print(f"✅ SUCCESS! Logged in as {self.user} (ID: {self.user.id})")
        print("Bot is ONLINE and connected to Discord Gateway.")
        await self.close()

    async def on_error(self, event, *args, **kwargs):
        print(f"❌ Error during {event}")
        import traceback
        traceback.print_exc()

intents = discord.Intents.default()
intents.message_content = True 

client = TestBot(intents=intents)

print("⏳ Attempting to connect to Discord...")
try:
    client.run(TOKEN)
except discord.errors.LoginFailure:
    print("❌ ERROR: Login failed. Check your Token.")
except discord.errors.PrivilegedIntentsRequired:
    print("❌ ERROR: Privileged Intents missing. Enable 'Message Content Intent' in Developer Portal.")
except Exception as e:
    print(f"❌ ERROR: Connection failed: {e}")
