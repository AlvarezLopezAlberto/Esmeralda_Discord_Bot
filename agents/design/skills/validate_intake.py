"""
ValidateIntake Skill

Validates design intake requests against required criteria using LLM analysis.
"""

import json
import logging
import sys
import os
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.skills.base import BaseSkill, SkillContext


class ValidateIntakeSkill(BaseSkill):
    """
    Validates design intake requests to ensure they contain required information.
    
    Required fields:
    - Notion link (URL to a Notion page)
    - Context (challenge description and target audience)
    - Deliverables (list of expected outputs)  
    - Deadline (specific date)
    """
    
    def __init__(self, llm_handler):
        """
        Initialize the skill.
        
        Args:
            llm_handler: LLMHandler instance for AI-powered validation
        """
        super().__init__(
            name="validate_intake",
            description="Validates design intake requests against required criteria"
        )
        self.llm = llm_handler
    
    async def execute(
        self,
        context: SkillContext,
        content: str,
        reference_date: str,
        prompt_template: str
    ) -> Dict[str, Any]:
        """
        Execute intake validation.
        
        Args:
            context: Skill context
            content: Content to validate (message or thread content)
            reference_date: Reference date for deadline validation (ISO format)
            prompt_template: LLM prompt template for validation
            
        Returns:
            Dictionary with:
                - es_valido (bool): Whether the intake is valid
                - feedback (str): Feedback message for the user
                - data (dict): Extracted data (project, title, deadline, etc.)
                - action (str): Recommended action
        """
        self.logger.debug(f"Validating intake content (length: {len(content)})")
        
        # Build system prompt
        system_prompt = f"""
        {prompt_template}
        
        Thread Date (UTC): {reference_date}
        """
        
        user_prompt = f"CONTENT TO VALIDATE:\n{content}"
        
        try:
            # Call LLM for validation
            result_json = self.llm.generate_completion(
                system_prompt,
                user_prompt,
                json_mode=True
            )
            
            response_data = json.loads(result_json)
            
            # Validate response structure
            if not isinstance(response_data, dict):
                raise ValueError("LLM response is not a dictionary")
            
            # Ensure required fields
            response_data.setdefault("es_valido", False)
            response_data.setdefault("feedback", "")
            response_data.setdefault("data", {})
            response_data.setdefault("action", "wait")
            
            # Store in context for other skills
            context.set("validation_result", response_data)
            context.set("is_valid", response_data["es_valido"])
            
            self.logger.info(
                f"Validation complete: valid={response_data['es_valido']}, "
                f"action={response_data['action']}"
            )
            
            return response_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM JSON response: {e}")
            return {
                "es_valido": False,
                "feedback": "Error técnico al procesar la validación. Por favor intenta de nuevo.",
                "data": {},
                "action": "wait"
            }
        
        except Exception as e:
            self.logger.error(f"Validation error: {e}", exc_info=True)
            return {
                "es_valido": False,
                "feedback": "Lo siento, estoy teniendo problemas técnicos. Por favor contacta a soporte.",
                "data": {},
                "action": "wait"
            }
    
    async def validate_input(self, context: SkillContext, **kwargs) -> bool:
        """Validate that required parameters are provided."""
        required = ["content", "reference_date", "prompt_template"]
        
        for param in required:
            if param not in kwargs:
                self.logger.error(f"Missing required parameter: {param}")
                return False
        
        return True
