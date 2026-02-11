"""
CreateNotionTask Skill

Creates tasks in Notion with proper schema validation and MCP support.
"""

import logging
import sys
import os
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.skills.base import BaseSkill, SkillContext


class CreateNotionTaskSkill(BaseSkill):
    """
    Creates tasks in Notion databases with schema validation.
    
    Uses MCP for:
    - Schema validation
    - Property formatting
    - Enhanced error handling
    """
    
    def __init__(self, notion_handler, notion_mcp=None):
        """
        Initialize the skill.
        
        Args:
            notion_handler: NotionHandler for task creation
            notion_mcp: Optional NotionMCPClient for enhanced operations
        """
        super().__init__(
            name="create_notion_task",
            description="Creates tasks in Notion with validation"
        )
        self.notion = notion_handler
        self.notion_mcp = notion_mcp
    
    async def execute(
        self,
        context: SkillContext,
        database_id: str,
        title: str,
        project: str,
        deadline: Optional[str] = None,
        content: Optional[str] = None,
        thread_url: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a Notion task.
        
        Args:
            context: Skill context
            database_id: Notion database ID
            title: Task title
            project: Project name
            deadline: Deadline in ISO format (YYYY-MM-DD)
            content: Task description/content
            thread_url: Discord thread URL to link
            
        Returns:
            URL of created task or None on failure
        """
        self.logger.info(
            f"Creating Notion task: title='{title}', project='{project}', "
            f"deadline={deadline}"
        )
        
        try:
            # Validate schema (if MCP is available)
            if self.notion_mcp:
                schema = await self.notion_mcp.get_database_schema(database_id)
                context.set("notion_schema", schema)
                
                # TODO: Validate properties against schema
                # For now, proceed with NotionHandler which handles this
            
            # Create the task using existing NotionHandler
            notion_url = self.notion.create_task(
                database_id=database_id,
                title=title,
                project=project,
                deadline=deadline,
                content=content,
                thread_url=thread_url,
                thread_property_name="Discord Thread"
            )
            
            if notion_url:
                self.logger.info(f"Successfully created task: {notion_url}")
                context.set("notion_url", notion_url)
                context.set("task_created", True)
                return notion_url
            else:
                self.logger.error("Failed to create task (no URL returned)")
                context.set("task_created", False)
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating Notion task: {e}", exc_info=True)
            context.set("task_created", False)
            context.set("creation_error", str(e))
            return None
    
    async def validate_input(self, context: SkillContext, **kwargs) -> bool:
        """Validate that required parameters are provided."""
        required = ["database_id", "title", "project"]
        
        for param in required:
            if param not in kwargs or not kwargs[param]:
                self.logger.error(f"Missing or empty required parameter: {param}")
                return False
        
        return True
