import discord
from discord import app_commands
from adk.base import BaseAgent
import sys

class NotionAgent(BaseAgent):
    
    async def can_handle(self, message: discord.Message) -> bool:
        # This agent only operates via Slash Commands
        return False

    async def handle(self, message: discord.Message):
        pass

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
            return []
