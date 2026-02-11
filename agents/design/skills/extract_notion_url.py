"""
ExtractNotionURL Skill

Extracts and validates Notion URLs from thread starter messages.
"""

import re
import logging
import sys
import os
from typing import Optional
import discord

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.skills.base import BaseSkill, SkillContext


class ExtractNotionURLSkill(BaseSkill):
    """
    Extracts Notion URLs from Discord thread starter messages.
    
    Also validates that the URL is from the correct workspace/database.
    """
    
    def __init__(self, notion_mcp=None):
        """
        Initialize the skill.
        
        Args:
            notion_mcp: Optional NotionMCPClient for URL validation
        """
        super().__init__(
            name="extract_notion_url",
            description="Extracts and validates Notion URLs from thread messages"
        )
        self.notion_mcp = notion_mcp
    
    async def execute(
        self,
        context: SkillContext,
        thread: discord.Thread,
        thread_id: int,
        expected_database_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract Notion URL from thread starter message.
        
        Args:
            context: Skill context
            thread: Discord thread object
            thread_id: ID of the thread (same as starter message ID)
            expected_database_id: If provided, validate URL is from this database
            
        Returns:
            Notion URL if found and valid, None otherwise
        """
        try:
            # Fetch starter message
            starter = await thread.fetch_message(thread_id)
            content = starter.content or ""
            
            # Extract Notion URLs using regex
            notion_urls = re.findall(
                r'(https?://(?:\S+\.)?notion\.(?:so|site)/[^\s]+)',
                content
            )
            
            if not notion_urls:
                self.logger.debug(f"No Notion URLs found in thread {thread_id}")
                return None
            
            first_url = notion_urls[0]
            
            # Validate against expected database if provided
            if expected_database_id:
                # Check if URL contains the database ID
                # Database IDs in URLs are typically formatted without dashes
                db_id_clean = expected_database_id.replace("-", "")
                
                if db_id_clean not in first_url:
                    self.logger.info(
                        f"URL {first_url} is not from expected database {expected_database_id}"
                    )
                    return None
            
            # Optionally validate with MCP that the URL actually exists
            if self.notion_mcp:
                # TODO: Add MCP validation to check if page exists
                pass
            
            # Store in context
            context.set("notion_url", first_url)
            
            self.logger.info(f"Extracted Notion URL from thread {thread_id}: {first_url}")
            return first_url
            
        except discord.NotFound:
            self.logger.warning(f"Starter message not found for thread {thread_id}")
            return None
        
        except Exception as e:
            self.logger.error(f"Failed to extract Notion URL: {e}", exc_info=True)
            return None
    
    async def validate_input(self, context: SkillContext, **kwargs) -> bool:
        """Validate that required parameters are provided."""
        if "thread" not in kwargs or "thread_id" not in kwargs:
            self.logger.error("Missing required parameters: thread or thread_id")
            return False
        
        return True
