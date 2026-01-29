import discord
from discord.ext import commands
from discord import app_commands
import re
import sys

class NotionIntegrationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="notion", description="Search and link a Notion page")
    @app_commands.describe(query="Page title to search used for autocomplete")
    async def notion_slash(self, interaction: discord.Interaction, query: str):
        """
        Slash command to search Notion and return an embed.
        """
        page_url = None
        page_title = query
        
        # 1. Try to fetch as ID first
        page_info = self.bot.notion.get_page_info(query)
        
        if page_info:
            page_url = page_info["url"]
            page_title = page_info["title"]
        else:
            # Search text
            if query.startswith("http"):
                 page_url = query
                 page_title = "Notion Page"
            else:
                 results = self.bot.notion.search_pages(query, limit=1)
                 if results:
                     page_url = results[0]["url"]
                     page_title = results[0]["title"]
                 else:
                     await interaction.response.send_message(f"No pages found for '{query}'", ephemeral=True)
                     return

        embed = discord.Embed(title=f"{page_title}", url=page_url, color=0x000000)
        embed.set_footer(text="Notion Page", icon_url="https://upload.wikimedia.org/wikipedia/commons/4/45/Notion_app_logo.png")
        
        await interaction.response.send_message(embed=embed)

    @notion_slash.autocomplete("query")
    async def notion_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        if not current:
            return []
        
        try:
            # Reduced limit to speed up processing
            results = self.bot.notion.search_pages(current, limit=10) 
            return [
                app_commands.Choice(name=r["title"], value=r["id"]) 
                for r in results
            ]
        except Exception:
            # If interaction times out (NotFound) or other error, just return empty list
            return []

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore own messages and Webhooks to avoid loops
        if message.author.id == self.bot.user.id or message.webhook_id:
            return

        sys.stderr.write(f"DEBUG: Message received from {message.author}: {message.content}\n")

        content = message.content
        
        if "notion.so" in content or "notion.site" in content:
            # Find all Notion URLs (including subdomains like emerald-dev.notion.site)
            urls = re.findall(r'(https?://(?:\S+\.)?notion\.(?:so|site)/[^\s]+)', content)
            
            if urls:
                replaced_content = content
                replacements_made = False
                
                for url in urls:
                    sys.stderr.write(f"DEBUG: Found Notion URL: {url}\n")
                    page_id = self.bot.notion.extract_page_id(url)
                    sys.stderr.write(f"DEBUG: Extracted Page ID: {page_id}\n")
                    
                    if page_id:
                        info = self.bot.notion.get_page_info(page_id)
                        if info:
                            title = info.get("title", "Notion Page")
                            # Replace URL with Markdown Link
                            replaced_content = replaced_content.replace(url, f"[{title}]({url})")
                            replacements_made = True
                        else:
                            sys.stderr.write(f"DEBUG: Failed to get page info for ID: {page_id}\n")
                    else:
                        sys.stderr.write(f"DEBUG: Failed to extract ID from URL: {url}\n")
                
                if replacements_made:
                    try:
                        # 1. Prepare Webhook
                        # Threads don't support webhooks, use parent channel
                        webhook_channel = message.channel
                        if isinstance(message.channel, discord.Thread):
                            webhook_channel = message.channel.parent
                        
                        # Check for existing webhook in channel
                        webhooks = await webhook_channel.webhooks()
                        webhook = None
                        for w in webhooks:
                            if w.name == "NotionFormatter":
                                webhook = w
                                break
                        
                        if not webhook:
                            webhook = await webhook_channel.create_webhook(name="NotionFormatter")
                        
                        # 2. Send as User
                        # If in a thread, send to the thread; otherwise send to the channel
                        send_kwargs = {
                            "content": replaced_content,
                            "username": message.author.display_name,
                            "avatar_url": message.author.display_avatar.url,
                            "files": [await a.to_file() for a in message.attachments]
                        }
                        
                        if isinstance(message.channel, discord.Thread):
                            send_kwargs["thread"] = message.channel
                        
                        await webhook.send(**send_kwargs)
                        
                        # 3. Delete Original
                        await message.delete()
                        return # Stop processing commands for this message since it's deleted
                        
                    except Exception as e:
                        sys.stderr.write(f"Error auto-formatting: {e}\n")

async def setup(bot):
    await bot.add_cog(NotionIntegrationCog(bot))
