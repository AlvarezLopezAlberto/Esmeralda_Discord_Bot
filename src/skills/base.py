"""
Base classes for the Skills system.

Skills are modular, reusable components that perform specific tasks.
They can be used by agents to handle complex operations in a structured way.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class SkillContext:
    """
    Shared context that can be passed between skills.
    
    Attributes:
        data: Dictionary of contextual data
        agent: Reference to the calling agent
        message: Discord message that triggered the skill
    """
    data: Dict[str, Any] = field(default_factory=dict)
    agent: Optional[Any] = None
    message: Optional[Any] = None  # discord.Message
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the context."""
        self.data[key] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple values in the context."""
        self.data.update(updates)


class BaseSkill(ABC):
    """
    Abstract base class for all skills.
    
    Skills should:
    1. Have a unique name
    2. Declare their dependencies (other skills, services, etc.)
    3. Implement the execute() method
    4. Be stateless (use context for state)
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Initialize the skill.
        
        Args:
            name: Unique name for this skill
            description: Human-readable description of what the skill does
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"skill.{name}")
    
    @abstractmethod
    async def execute(self, context: SkillContext, **kwargs) -> Any:
        """
        Execute the skill's main logic.
        
        Args:
            context: Shared context for passing data between skills
            **kwargs: Additional arguments specific to this skill
            
        Returns:
            Result of the skill execution (type depends on skill)
        """
        pass
    
    async def validate_input(self, context: SkillContext, **kwargs) -> bool:
        """
        Validate inputs before execution.
        
        Override this method to add custom validation logic.
        
        Args:
            context: Skill context
            **kwargs: Arguments to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        return True
    
    def __str__(self) -> str:
        return f"Skill({self.name})"
    
    def __repr__(self) -> str:
        return f"<Skill name={self.name} desc='{self.description[:50]}'>"


class SkillRegistry:
    """
    Registry for managing and accessing skills.
    
    Provides:
    - Skill registration
    - Skill discovery
    - Dependency resolution
    """
    
    def __init__(self):
        """Initialize the skill registry."""
        self._skills: Dict[str, BaseSkill] = {}
        self.logger = logging.getLogger("skill.registry")
    
    def register(self, skill: BaseSkill) -> None:
        """
        Register a skill.
        
        Args:
            skill: Skill instance to register
            
        Raises:
            ValueError: If a skill with the same name already exists
        """
        if skill.name in self._skills:
            raise ValueError(f"Skill '{skill.name}' is already registered")
        
        self._skills[skill.name] = skill
        self.logger.info(f"Registered skill: {skill.name}")
    
    def get(self, name: str) -> Optional[BaseSkill]:
        """
        Get a skill by name.
        
        Args:
            name: Name of the skill
            
        Returns:
            Skill instance or None if not found
        """
        return self._skills.get(name)
    
    def get_all(self) -> List[BaseSkill]:
        """
        Get all registered skills.
        
        Returns:
            List of all skill instances
        """
        return list(self._skills.values())
    
    def list_names(self) -> List[str]:
        """
        Get names of all registered skills.
        
        Returns:
            List of skill names
        """
        return list(self._skills.keys())
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a skill.
        
        Args:
            name: Name of the skill to unregister
            
        Returns:
            True if skill was unregistered, False if not found
        """
        if name in self._skills:
            del self._skills[name]
            self.logger.info(f"Unregistered skill: {name}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all registered skills."""
        self._skills.clear()
        self.logger.info("Cleared all skills from registry")


class SkillExecutor:
    """
    Executes skills with proper error handling and logging.
    """
    
    def __init__(self, registry: SkillRegistry):
        """
        Initialize the executor.
        
        Args:
            registry: Skill registry to use
        """
        self.registry = registry
        self.logger = logging.getLogger("skill.executor")
    
    async def execute(
        self,
        skill_name: str,
        context: SkillContext,
        **kwargs
    ) -> Any:
        """
        Execute a skill by name.
        
        Args:
            skill_name: Name of the skill to execute
            context: Context to pass to the skill
            **kwargs: Additional arguments for the skill
            
        Returns:
            Result from the skill execution
            
        Raises:
            ValueError: If skill not found
            Exception: If skill execution fails
        """
        skill = self.registry.get(skill_name)
        if not skill:
            raise ValueError(f"Skill '{skill_name}' not found in registry")
        
        self.logger.debug(f"Executing skill: {skill_name}")
        
        try:
            # Validate input
            if not await skill.validate_input(context, **kwargs):
                raise ValueError(f"Input validation failed for skill '{skill_name}'")
            
            # Execute
            result = await skill.execute(context, **kwargs)
            
            self.logger.debug(f"Skill '{skill_name}' completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Skill '{skill_name}' failed: {e}", exc_info=True)
            raise
