"""Design Agent Skills

Registry and exports for all Design Agent skills.
"""

import sys
import os
import importlib.util

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.skills.base import SkillRegistry


def _load_skill_module(skill_file):
    """Dynamically load a skill module from file path."""
    spec = importlib.util.spec_from_file_location(
        f"design_skill_{skill_file}",
        os.path.join(os.path.dirname(__file__), f"{skill_file}.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_design_skills_registry(bot) -> SkillRegistry:
    """
    Create and populate a skill registry for the Design Agent.
    
    Args:
        bot: Bot instance with llm, notion, and notion_mcp services
        
    Returns:
        Populated SkillRegistry
    """
    registry = SkillRegistry()
    
    # Load skill modules dynamically
    validate_intake_mod = _load_skill_module("validate_intake")
    extract_notion_url_mod = _load_skill_module("extract_notion_url")
    match_project_mod = _load_skill_module("match_project")
    create_notion_task_mod = _load_skill_module("create_notion_task")
    update_task_status_mod = _load_skill_module("update_task_status")
    conversation_memory_mod = _load_skill_module("conversation_memory")
    
    # Initialize skills with dependencies
    validate_intake = validate_intake_mod.ValidateIntakeSkill(bot.llm)
    extract_notion_url = extract_notion_url_mod.ExtractNotionURLSkill(getattr(bot, 'notion_mcp', None))
    match_project = match_project_mod.MatchProjectSkill(getattr(bot, 'notion_mcp', bot.notion))
    create_notion_task = create_notion_task_mod.CreateNotionTaskSkill(
        bot.notion,
        getattr(bot, 'notion_mcp', None)
    )
    update_task_status = update_task_status_mod.UpdateTaskStatusSkill(
        bot.notion,
        getattr(bot, 'notion_mcp', None)
    )
    conversation_memory = conversation_memory_mod.ConversationMemorySkill(bot.llm)
    
    # Register all skills
    registry.register(validate_intake)
    registry.register(extract_notion_url)
    registry.register(match_project)
    registry.register(create_notion_task)
    registry.register(update_task_status)
    registry.register(conversation_memory)
    
    return registry
