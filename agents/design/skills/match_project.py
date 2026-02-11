"""
MatchProject Skill

Performs fuzzy matching of project names against valid Notion options.
"""

import re
import logging
import sys
import os
from typing import List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.skills.base import BaseSkill, SkillContext


class MatchProjectSkill(BaseSkill):
    """
    Matches project names using fuzzy logic and MCP-enhanced Notion queries.
    
    Can handle:
    - Exact matches
    - Case-insensitive matches
    - Canonical form matching (no spaces, special chars)
    - MCP-powered semantic matching (future enhancement)
    """
    
    def __init__(self, notion_mcp):
        """
        Initialize the skill.
        
        Args:
            notion_mcp: NotionMCPClient for fetching valid project options
        """
        super().__init__(
            name="match_project",
            description="Fuzzy matches project names against valid Notion options"
        )
        self.notion_mcp = notion_mcp
        self._fallback_projects = [
            "Comercial Sync",
            "Cooltech",
            "Solkos Intelligence",
            "Cobranza 360°",
            "Coolector iOS",
            "Cask'r app",
            "Coolservice",
            "Vexia",
            "Emerald",
            "Negocon",
            "MIDA",
            "HDI",
            "Other"
        ]
    
    @staticmethod
    def _canonical_project(value: str) -> str:
        """
        Normalize project name for fuzzy matching.
        
        - Lowercase
        - Remove spaces
        - Remove special characters
        
        Args:
            value: Raw project name
            
        Returns:
            Canonicalized project name
        """
        if not value:
            return ""
        
        # Remove special characters except letters/numbers
        normalized = re.sub(r'[^\w\s]', '', value.lower())
        # Remove all spaces
        normalized = normalized.replace(' ', '')
        return normalized
    
    async def get_valid_options(self, database_id: str) -> List[str]:
        """
        Get valid project options from Notion via MCP.
        
        Args:
            database_id: Notion database ID
            
        Returns:
            List of valid project names
        """
        try:
            # Try to get options via MCP
            options = await self.notion_mcp.get_select_options(database_id, "Proyecto")
            
            if options:
                self.logger.info(f"Loaded {len(options)} projects from Notion via MCP")
                return options
            
            # Fallback to hardcoded list
            self.logger.warning("Using fallback project list")
            return self._fallback_projects
            
        except Exception as e:
            self.logger.error(f"Failed to fetch project options: {e}")
            return self._fallback_projects
    
    async def execute(
        self,
        context: SkillContext,
        project_raw: str,
        database_id: str
    ) -> Optional[str]:
        """
        Match a project name against valid options.
        
        Args:
            context: Skill context
            project_raw: Raw project name from user/LLM
            database_id: Notion database ID to get valid options from
            
        Returns:
            Matched project name (canonical form) or None if no match
        """
        if not project_raw:
            self.logger.debug("No project provided")
            return None
        
        # Get valid options
        options = await self.get_valid_options(database_id)
        context.set("project_options", options)
        
        # Normalize input
        candidate = self._canonical_project(project_raw)
        
        # Check for explicit "no project" indicators
        if candidate in {"sinproyecto", "ninguno", "na", "none"}:
            self.logger.info(f"Project marked as N/A: {project_raw}")
            return None
        
        # Build canonical mapping
        by_canon = {self._canonical_project(opt): opt for opt in options}
        
        # Try exact canonical match
        matched = by_canon.get(candidate)
        
        if matched:
            self.logger.info(f"Matched '{project_raw}' -> '{matched}'")
            context.set("matched_project", matched)
            return matched
        
        # TODO: Add MCP semantic matching for even better fuzzy matching
        # e.g., "cask app" -> "Cask'r app"
        
        self.logger.info(f"No match found for project: {project_raw}")
        context.set("matched_project", None)
        return None
    
    async def validate_input(self, context: SkillContext, **kwargs) -> bool:
        """Validate that required parameters are provided."""
        if "project_raw" not in kwargs or "database_id" not in kwargs:
            self.logger.error("Missing required parameters")
            return False
        
        return True
