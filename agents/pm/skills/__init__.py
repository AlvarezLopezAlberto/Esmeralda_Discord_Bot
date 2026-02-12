"""
PM Agent Skills Registry

This module creates and registers all skills for the PM agent.
"""

import os
import importlib.util
from src.skills.base import SkillRegistry


def _load_skill_module(skill_file):
    """Dynamically load a skill module from file path."""
    spec = importlib.util.spec_from_file_location(
        f"pm_skill_{skill_file}",
        os.path.join(os.path.dirname(__file__), f"{skill_file}.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_pm_skills_registry(bot) -> SkillRegistry:
    """
    Creates and populates the skill registry for the PM agent.
    
    Args:
        bot: Discord bot instance with attached services
        
    Returns:
        SkillRegistry with all PM skills registered
    """
    registry = SkillRegistry()
    
    # Load skill modules dynamically
    parse_daily_sync_mod = _load_skill_module("parse_daily_sync")
    track_capacity_mod = _load_skill_module("track_capacity")
    manage_backlog_mod = _load_skill_module("manage_backlog")
    document_decision_mod = _load_skill_module("document_decision")
    translate_feedback_mod = _load_skill_module("translate_feedback")
    
    # Register all PM skills
    registry.register(parse_daily_sync_mod.ParseDailySyncSkill(bot))
    registry.register(track_capacity_mod.TrackCapacitySkill(bot))
    registry.register(manage_backlog_mod.ManageBacklogSkill(bot))
    registry.register(document_decision_mod.DocumentDecisionSkill(bot))
    registry.register(translate_feedback_mod.TranslateFeedbackSkill(bot))
    
    return registry
