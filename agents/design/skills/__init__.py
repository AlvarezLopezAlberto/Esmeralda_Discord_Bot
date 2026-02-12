"""Design Agent Skills

Registry and exports for all Design Agent skills.
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.skills.base import SkillRegistry
from .validate_intake import ValidateIntakeSkill
from .extract_notion_url import ExtractNotionURLSkill
from .match_project import MatchProjectSkill
from .create_notion_task import CreateNotionTaskSkill
from .update_task_status import UpdateTaskStatusSkill
from .conversation_memory import ConversationMemorySkill


def create_design_skills_registry(bot) -> SkillRegistry:
    """
    Create and populate a skill registry for the Design Agent.
    
    Args:
        bot: Bot instance with llm, notion, and notion_mcp services
        
    Returns:
        Populated SkillRegistry
    """
    registry = SkillRegistry()
    
    # Initialize skills with dependencies
    validate_intake = ValidateIntakeSkill(bot.llm)
    extract_notion_url = ExtractNotionURLSkill(getattr(bot, 'notion_mcp', None))
    match_project = MatchProjectSkill(getattr(bot, 'notion_mcp', bot.notion))
    create_notion_task = CreateNotionTaskSkill(
        bot.notion,
        getattr(bot, 'notion_mcp', None)
    )
    update_task_status = UpdateTaskStatusSkill(
        bot.notion,
        getattr(bot, 'notion_mcp', None)
    )
    conversation_memory = ConversationMemorySkill(bot.llm)
    
    # Register all skills
    registry.register(validate_intake)
    registry.register(extract_notion_url)
    registry.register(match_project)
    registry.register(create_notion_task)
    registry.register(update_task_status)
    registry.register(conversation_memory)
    
    return registry


__all__ = [
    "ValidateIntakeSkill",
    "ExtractNotionURLSkill",
    "MatchProjectSkill",
    "CreateNotionTaskSkill",
    "UpdateTaskStatusSkill",
    "ConversationMemorySkill",
    "create_design_skills_registry"
]
