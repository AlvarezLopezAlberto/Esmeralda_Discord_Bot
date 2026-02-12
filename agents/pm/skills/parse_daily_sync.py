"""
Parse Daily Sync Skill

Parses daily sync messages from designers to extract:
- What did I do?
- What will I do?
- What blocks me?
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional
from src.skills.base import BaseSkill, SkillContext


class ParseDailySyncSkill(BaseSkill):
    """
    Skill to parse daily sync messages from team members.
    """
    
    def __init__(self, bot):
        super().__init__(
            name="parse_daily_sync",
            description="Parse daily sync messages to extract what was done, what will be done, and blockers"
        )
        self.bot = bot
    
    async def execute(self, context: SkillContext, **kwargs) -> Dict[str, Any]:
        """
        Parse a daily sync message.
        
        Args:
            context: Skill context
            message_content: The message content to parse
            author: Discord member who sent the message
            
        Returns:
            Dictionary with parsed sync data
        """
        message_content = kwargs.get("message_content", "")
        author = kwargs.get("author")
        
        if not message_content:
            return {"success": False, "error": "No message content provided"}
        
        # Parse the three key sections
        sync_data = {
            "author": author.name if author else "Unknown",
            "author_id": str(author.id) if author else None,
            "timestamp": datetime.utcnow().isoformat(),
            "what_did": self._extract_section(message_content, r"¿[Qq]ué hice\?|[Ww]hat did"),
            "what_will": self._extract_section(message_content, r"¿[Qq]ué haré\?|[Ww]hat will"),
            "blockers": self._extract_section(message_content, r"¿[Qq]ué me bloquea\?|[Ww]hat blocks|[Bb]lockers"),
            "raw_message": message_content
        }
        
        # Validate that at least one section was found
        if not any([sync_data["what_did"], sync_data["what_will"], sync_data["blockers"]]):
            return {
                "success": False,
                "error": "Could not parse daily sync format. Expected sections: ¿Qué hice?, ¿Qué haré?, ¿Qué me bloquea?"
            }
        
        # Check for critical blockers
        has_critical_blocker = self._has_critical_blocker(sync_data["blockers"])
        
        return {
            "success": True,
            "data": sync_data,
            "has_critical_blocker": has_critical_blocker,
            "needs_attention": has_critical_blocker or not sync_data["what_will"]
        }
    
    def _extract_section(self, content: str, pattern: str) -> Optional[str]:
        """
        Extract content after a section header.
        
        Args:
            content: Full message content
            pattern: Regex pattern to match section header
            
        Returns:
            Extracted section content or None
        """
        # Find the section header
        match = re.search(pattern, content, re.IGNORECASE)
        if not match:
            return None
        
        # Extract everything after the header until next section or end
        start = match.end()
        # Look for next section (another question mark pattern)
        next_section = re.search(r'¿[Qq]ué|[Ww]hat|[Bb]lockers', content[start:], re.IGNORECASE)
        
        if next_section:
            end = start + next_section.start()
            section_content = content[start:end]
        else:
            section_content = content[start:]
        
        # Clean up the content
        section_content = section_content.strip()
        # Remove common prefixes like ":", "-", etc.
        section_content = re.sub(r'^[:\-\s]+', '', section_content)
        
        return section_content if section_content else None
    
    def _has_critical_blocker(self, blockers: Optional[str]) -> bool:
        """
        Check if blockers contain critical keywords.
        
        Args:
            blockers: Blocker section content
            
        Returns:
            True if critical blocker detected
        """
        if not blockers:
            return False
        
        critical_keywords = [
            "urgente", "critical", "blocked", "bloqueado",
            "no puedo", "can't continue", "stuck",
            "necesito ayuda", "need help"
        ]
        
        blockers_lower = blockers.lower()
        return any(keyword in blockers_lower for keyword in critical_keywords)
