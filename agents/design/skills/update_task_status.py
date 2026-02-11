"""
UpdateTaskStatus Skill

Updates the status of existing Notion tasks.
"""

import logging
import sys
import os
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.skills.base import BaseSkill, SkillContext


class UpdateTaskStatusSkill(BaseSkill):
    """
    Updates status and properties of existing Notion tasks.
    
    Can find tasks by:
    - Discord thread URL
    - Page ID
    - Fuzzy title match (via MCP)
    """
    
    def __init__(self, notion_handler, notion_mcp=None):
        """
        Initialize the skill.
        
        Args:
            notion_handler: NotionHandler for task updates
            notion_mcp: Optional NotionMCPClient for enhanced search
        """
        super().__init__(
            name="update_task_status",
            description="Updates status of existing Notion tasks"
        )
        self.notion = notion_handler
        self.notion_mcp = notion_mcp
    
    async def find_task_by_thread(
        self,
        database_id: str,
        guild_id: int,
        thread_id: int
    ) -> Optional[str]:
        """
        Find a task by Discord thread ID.
        
        Args:
            database_id: Notion database ID
            guild_id: Discord guild ID
            thread_id: Discord thread ID
            
        Returns:
            Task URL if found, None otherwise
        """
        try:
            task_url = self.notion.find_task_by_discord_thread(
                database_id,
                guild_id,
                thread_id
            )
            
            if task_url:
                self.logger.info(f"Found task for thread {thread_id}: {task_url}")
                return task_url
            
            self.logger.info(f"No task found for thread {thread_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding task by thread: {e}")
            return None
    
    async def execute(
        self,
        context: SkillContext,
        page_id: Optional[str] = None,
        database_id: Optional[str] = None,
        guild_id: Optional[int] = None,
        thread_id: Optional[int] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a Notion task.
        
        Args:
            context: Skill context
            page_id: Optional page ID to update directly
            database_id: Database ID (for thread-based lookup)
            guild_id: Guild ID (for thread-based lookup)
            thread_id: Thread ID (for thread-based lookup)
            properties: Properties to update
            
        Returns:
            True if update successful, False otherwise
        """
        # If no page_id, try to find by thread
        if not page_id and all([database_id, guild_id, thread_id]):
            task_url = await self.find_task_by_thread(
                database_id,
                guild_id,
                thread_id
            )
            
            if task_url:
                # Extract page ID from URL
                page_id = self.notion.extract_page_id(task_url)
        
        if not page_id:
            self.logger.error("Cannot update task: no page_id provided or found")
            context.set("update_success", False)
            return False
        
        if not properties:
            self.logger.warning("No properties provided for update")
            context.set("update_success", False)
            return False
        
        try:
            # Update via notion_mcp if available
            if self.notion_mcp:
                success = await self.notion_mcp.update_page(page_id, properties)
            else:
                # Fallback to basic NotionHandler
                # Note: NotionHandler doesn't have a generic update method
                # We'd need to use set_page_property for each property
                success = False
                for prop_name, value in properties.items():
                    prop_type = "select"  # TODO: Detect type from schema
                    success = self.notion.set_page_property(
                        page_id,
                        prop_name,
                        prop_type,
                        value
                    )
                    if not success:
                        break
            
            context.set("update_success", success)
            
            if success:
                self.logger.info(f"Successfully updated task {page_id}")
            else:
                self.logger.error(f"Failed to update task {page_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating task: {e}", exc_info=True)
            context.set("update_success", False)
            context.set("update_error", str(e))
            return False
    
    async def validate_input(self, context: SkillContext, **kwargs) -> bool:
        """Validate that we have either page_id or thread lookup info."""
        has_page_id = "page_id" in kwargs and kwargs["page_id"]
        has_thread_info = all([
            kwargs.get("database_id"),
            kwargs.get("guild_id") is not None,
            kwargs.get("thread_id") is not None
        ])
        
        if not (has_page_id or has_thread_info):
            self.logger.error(
                "Must provide either page_id or (database_id, guild_id, thread_id)"
            )
            return False
        
        return True
