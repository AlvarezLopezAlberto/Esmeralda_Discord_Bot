"""
Translate Feedback Skill

Translates vague client feedback into clear, technical action items
and creates tasks in Notion.
"""

import logging
import json
from typing import Dict, Any, Optional
from src.skills.base import BaseSkill, SkillContext


class TranslateFeedbackSkill(BaseSkill):
    """
    Skill to translate vague feedback into actionable tasks.
    """
    
    def __init__(self, bot):
        super().__init__(
            name="translate_feedback",
            description="Translate vague feedback into clear action items and create Notion tasks"
        )
        self.bot = bot
        self.database_id = "9b1d386dbae1401b8a58af5a792e8f1f"  # Growth & Strategy DB
    
    async def execute(self, context: SkillContext, **kwargs) -> Dict[str, Any]:
        """
        Translate feedback into action item and create task.
        
        Args:
            context: Skill context
            feedback: The vague feedback to translate
            project_context: Optional project name or context
            feedback_source: Who provided the feedback
            discord_link: Link to the original feedback message
            
        Returns:
            Translation result with Notion task URL
        """
        feedback = kwargs.get("feedback", "")
        project_context = kwargs.get("project_context", "")
        feedback_source = kwargs.get("feedback_source", "Cliente interno")
        discord_link = kwargs.get("discord_link", "")
        
        if not feedback:
            return {
                "success": False,
                "error": "No feedback provided"
            }
        
        try:
            # Step 1: Analyze if feedback is clear enough
            clarity_check = await self._check_feedback_clarity(feedback)
            
            if not clarity_check["is_clear"]:
                return {
                    "success": False,
                    "needs_clarification": True,
                    "clarification_questions": clarity_check["questions"],
                    "message": "Necesito más información para crear una tarea técnica clara."
                }
            
            # Step 2: Get project context from Notion if needed
            project = await self._infer_project(project_context, feedback)
            
            # Step 3: Translate feedback into action item
            action_item = await self._translate_to_action_item(feedback, project)
            
            # Step 4: Create Notion task
            notion_url = await self._create_notion_task(
                action_item,
                project,
                feedback_source,
                discord_link
            )
            
            return {
                "success": True,
                "action_item": action_item,
                "notion_url": notion_url,
                "message": f"✅ He creado la tarea técnica en Notion: {notion_url}"
            }
            
        except Exception as e:
            self.logger.error(f"Error translating feedback: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _check_feedback_clarity(self, feedback: str) -> Dict[str, Any]:
        """
        Check if feedback is clear enough to create an action item.
        
        Args:
            feedback: The feedback to analyze
            
        Returns:
            Dictionary with clarity assessment
        """
        prompt = f"""
        Analiza este feedback de un cliente y determina si es suficientemente claro para crear una tarea técnica.
        
        Feedback: "{feedback}"
        
        Un feedback claro debe especificar:
        1. QUÉ elemento necesita cambios (ej: botón, color, layout)
        2. CUÁL es el problema específico
        3. QUÉ se espera como resultado
        
        Si NO es claro, genera preguntas específicas para obtener más información.
        
        Responde en JSON:
        {{
            "is_clear": boolean,
            "questions": ["pregunta 1", "pregunta 2", ...] o []
        }}
        """
        
        try:
            result = self.bot.llm.generate_completion(
                system_prompt="Eres un PM experto en clarificar feedback vago de clientes.",
                user_prompt=prompt,
                json_mode=True
            )
            return json.loads(result)
        except Exception as e:
            self.logger.warning(f"Error checking clarity: {e}")
            # Default to assuming it's clear enough
            return {"is_clear": True, "questions": []}
    
    async def _infer_project(self, project_context: str, feedback: str) -> Optional[str]:
        """
        Infer the project name from context or Notion.
        
        Args:
            project_context: Provided project context
            feedback: Feedback content
            
        Returns:
            Project name or None
        """
        if project_context:
            # Try to match with existing Notion projects
            try:
                # Query Notion for projects
                projects = self.bot.notion_mcp.query_database(
                    database_id=self.database_id,
                    filter_params={}
                )
                
                # Extract unique project names
                project_names = set()
                for task in projects.get("results", []):
                    project_prop = task.get("properties", {}).get("Project", {})
                    project_name = project_prop.get("select", {}).get("name")
                    if project_name:
                        project_names.add(project_name)
                
                # Fuzzy match project context
                project_context_lower = project_context.lower()
                for name in project_names:
                    if name.lower() in project_context_lower or project_context_lower in name.lower():
                        return name
                        
            except Exception as e:
                self.logger.warning(f"Error querying Notion for projects: {e}")
        
        return project_context if project_context else None
    
    async def _translate_to_action_item(self, feedback: str, project: Optional[str]) -> Dict[str, Any]:
        """
        Use LLM to translate vague feedback into clear action item.
        
        Args:
            feedback: Original feedback
            project: Project context
            
        Returns:
            Dictionary with action item details
        """
        prompt = f"""
        Convierte este feedback vago en una tarea técnica clara y accionable para un diseñador.
        
        Feedback original: "{feedback}"
        Proyecto: {project or "No especificado"}
        
        Crea una tarea con:
        1. Título claro y específico (máx 60 caracteres)
        2. Descripción técnica detallada que un diseñador pueda ejecutar
        3. Criterios de aceptación claros
        
        Responde en JSON:
        {{
            "title": "título de la tarea",
            "description": "descripción técnica detallada",
            "acceptance_criteria": ["criterio 1", "criterio 2", ...]
        }}
        """
        
        try:
            result = self.bot.llm.generate_completion(
                system_prompt="Eres un PM experto en convertir feedback vago en tareas técnicas claras para diseñadores.",
                user_prompt=prompt,
                json_mode=True
            )
            return json.loads(result)
        except Exception as e:
            self.logger.error(f"Error translating feedback: {e}")
            # Fallback to basic translation
            return {
                "title": f"Feedback: {feedback[:50]}...",
                "description": feedback,
                "acceptance_criteria": ["Implementar cambio solicitado", "Validar con cliente"]
            }
    
    async def _create_notion_task(
        self,
        action_item: Dict[str, Any],
        project: Optional[str],
        feedback_source: str,
        discord_link: str
    ) -> str:
        """
        Create task in Notion Growth & Strategy database.
        
        Args:
            action_item: Translated action item
            project: Project name
            feedback_source: Who gave the feedback
            discord_link: Link to original Discord message
            
        Returns:
            URL of created Notion task
        """
        # Format description with all context
        description = f"""
## Feedback Original
Fuente: {feedback_source}
Link a Discord: {discord_link}

## Descripción Técnica
{action_item['description']}

## Criterios de Aceptación
"""
        for i, criterion in enumerate(action_item.get('acceptance_criteria', []), 1):
            description += f"{i}. {criterion}\n"
        
        description += "\n---\n*Tarea creada automáticamente por PM Bot desde feedback*"
        
        try:
            # Use Notion MCP to create task
            task = self.bot.notion_mcp.create_page(
                parent_database_id=self.database_id,
                properties={
                    "Nombre": {
                        "title": [{"text": {"content": action_item["title"]}}]
                    },
                    "Project": {
                        "select": {"name": project} if project else None
                    },
                    "Status": {
                        "status": {"name": "Pendiente"}
                    },
                    "Discord Thread": {
                        "url": discord_link
                    }
                },
                content=description
            )
            
            return task.get("url", "")
            
        except Exception as e:
            self.logger.error(f"Error creating Notion task: {e}")
            raise
