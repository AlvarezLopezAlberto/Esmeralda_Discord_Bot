"""
Document Decision Skill

Automatically documents important decisions made in Discord conversations
to Notion with full traceability.
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.skills.base import BaseSkill, SkillContext


class DocumentDecisionSkill(BaseSkill):
    """
    Skill to detect and document decisions in Notion.
    """
    
    def __init__(self, bot):
        super().__init__(
            name="document_decision",
            description="Detect and document decisions in Notion with project vital tag"
        )
        self.bot = bot
        
        # Keywords that indicate a decision
        self.decision_keywords = [
            r"\bdecidimos\b",
            r"\bse aprobó\b",
            r"\bse aprobo\b",
            r"\bcambiamos a\b",
            r"\bvamos con\b",
            r"\bfinal decision\b",
            r"\bdecided to\b",
            r"\bagreement\b",
            r"\bacuerdo\b",
            r"\bconfirmado\b",
            r"\bconfirmed\b"
        ]
    
    async def execute(self, context: SkillContext, **kwargs) -> Dict[str, Any]:
        """
        Detect and document a decision.
        
        Args:
            context: Skill context
            message_content: Message content to analyze
            conversation_history: Recent conversation history for context
            channel_name: Name of the channel where decision was made
            participants: List of participants in the discussion
            message_url: URL to the original Discord message
            
        Returns:
            Documentation result
        """
        message_content = kwargs.get("message_content", "")
        conversation_history = kwargs.get("conversation_history", [])
        channel_name = kwargs.get("channel_name", "Unknown Channel")
        participants = kwargs.get("participants", [])
        message_url = kwargs.get("message_url", "")
        
        # Check if this message contains a decision
        if not self._contains_decision(message_content):
            return {
                "success": False,
                "is_decision": False,
                "message": "No decision detected in message"
            }
        
        try:
            # Extract decision details
            decision_data = self._extract_decision_details(
                message_content,
                conversation_history
            )
            
            # Create Notion page for the decision
            notion_url = await self._create_decision_page(
                decision_data,
                channel_name,
                participants,
                message_url
            )
            
            return {
                "success": True,
                "is_decision": True,
                "decision": decision_data,
                "notion_url": notion_url,
                "message": f"Decisión documentada en Notion: {notion_url}"
            }
            
        except Exception as e:
            self.logger.error(f"Error documenting decision: {e}", exc_info=True)
            return {
                "success": False,
                "is_decision": True,
                "error": str(e)
            }
    
    def _contains_decision(self, content: str) -> bool:
        """
        Check if content contains decision keywords.
        
        Args:
            content: Message content to check
            
        Returns:
            True if decision detected
        """
        content_lower = content.lower()
        return any(re.search(pattern, content_lower) for pattern in self.decision_keywords)
    
    def _extract_decision_details(self, message: str, history: List[str]) -> Dict[str, Any]:
        """
        Extract decision details from message and context.
        
        Args:
            message: Main message containing the decision
            history: Conversation history for context
            
        Returns:
            Dictionary with decision details
        """
        # Combine for context
        full_context = "\n".join(history[-5:]) + "\n" + message if history else message
        
        # Use LLM to extract structured decision info
        try:
            prompt = f"""
            Analiza esta conversación y extrae la decisión que se tomó.
            
            Conversación:
            {full_context}
            
            Extrae:
            1. ¿Qué se decidió? (la decisión principal)
            2. ¿Por qué? (razón o contexto)
            3. ¿Sobre qué tema/proyecto? (si se menciona)
            
            Responde en JSON:
            {{
                "what": "descripción de la decisión",
                "why": "razón o contexto",
                "project": "nombre del proyecto o null",
                "summary": "resumen en una línea"
            }}
            """
            
            result = self.bot.llm.generate_completion(
                system_prompt="Eres un asistente experto en extraer decisiones de conversaciones.",
                user_prompt=prompt,
                json_mode=True
            )
            
            import json
            decision_data = json.loads(result)
            decision_data["timestamp"] = datetime.utcnow().isoformat()
            
            return decision_data
            
        except Exception as e:
            self.logger.warning(f"Error extracting decision with LLM: {e}")
            # Fallback to simple extraction
            return {
                "what": message,
                "why": "Ver contexto en Discord",
                "project": None,
                "summary": message[:100],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _create_decision_page(
        self,
        decision_data: Dict[str, Any],
        channel_name: str,
        participants: List[str],
        message_url: str
    ) -> str:
        """
        Create a Notion page to document the decision.
        
        Args:
            decision_data: Extracted decision information
            channel_name: Discord channel name
            participants: List of participant names
            message_url: URL to Discord message
            
        Returns:
            URL of created Notion page
        """
        # Note: The Notion URL provided by the user is a database view
        # We'll need to create a page in the appropriate location
        # For now, we'll use the MCP to create a page
        
        try:
            # Format the decision content
            content = f"""
# Decisión: {decision_data['summary']}

## ¿Qué se decidió?
{decision_data['what']}

## ¿Por qué?
{decision_data['why']}

## Contexto
- **Fecha**: {decision_data['timestamp']}
- **Canal**: {channel_name}
- **Participantes**: {', '.join(participants) if participants else 'N/A'}
- **Link a Discord**: {message_url}

## Proyecto
{decision_data.get('project', 'No especificado')}

---
*Documentado automáticamente por el PM Bot*
"""
            
            # Use Notion MCP to create the page
            # This is a placeholder - actual implementation depends on MCP API
            page = self.bot.notion_mcp.create_page(
                parent_id="1ecd14a8642b80f69f7df9a281d4e46b",  # From user's URL
                title=f"Decisión: {decision_data['summary']}",
                content=content,
                properties={
                    "Tags": {
                        "multi_select": [{"name": "project vital"}]
                    }
                }
            )
            
            return page.get("url", "")
            
        except Exception as e:
            self.logger.error(f"Error creating Notion page: {e}")
            raise
