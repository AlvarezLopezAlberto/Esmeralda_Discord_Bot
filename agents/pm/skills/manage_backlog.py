"""
Manage Backlog Skill

Manages and prioritizes the backlog of design tasks.
Helps ensure the team always has work queued up but isn't overwhelmed.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from src.skills.base import BaseSkill, SkillContext


class ManageBacklogSkill(BaseSkill):
    """
    Skill to manage and prioritize the backlog.
    """
    
    def __init__(self, bot):
        super().__init__(
            name="manage_backlog",
            description="Manage and prioritize the backlog of design tasks"
        )
        self.bot = bot
    
    async def execute(self, context: SkillContext, **kwargs) -> Dict[str, Any]:
        """
        Analyze backlog and provide prioritization recommendations.
        
        Args:
            context: Skill context
            database_id: Notion database ID
            priority_projects: Optional list of priority project names
            
        Returns:
            Backlog analysis with prioritized tasks
        """
        database_id = kwargs.get("database_id", "9b1d386dbae1401b8a58af5a792e8f1f")
        priority_projects = kwargs.get("priority_projects", ["Vexia"])
        
        try:
            # Get unassigned or pending tasks
            backlog_tasks = await self._get_backlog_tasks(database_id)
            
            # Prioritize tasks
            prioritized = self._prioritize_tasks(backlog_tasks, priority_projects)
            
            # Generate recommendations
            recommendations = self._generate_backlog_recommendations(prioritized)
            
            return {
                "success": True,
                "backlog_size": len(backlog_tasks),
                "prioritized_tasks": prioritized,
                "recommendations": recommendations
            }
            
        except Exception as e:
            self.logger.error(f"Error managing backlog: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_backlog_tasks(self, database_id: str) -> List[Dict[str, Any]]:
        """
        Get tasks that are in the backlog (unassigned or pending).
        
        Args:
            database_id: Notion database ID
            
        Returns:
            List of backlog tasks
        """
        try:
            # Query for tasks that are not started or not assigned
            tasks = self.bot.notion_mcp.query_database(
                database_id=database_id,
                filter_params={
                    "or": [
                        {
                            "property": "Status",
                            "status": {
                                "equals": "Pendiente"
                            }
                        },
                        {
                            "property": "Asignado a",
                            "people": {
                                "is_empty": True
                            }
                        }
                    ]
                }
            )
            return tasks.get("results", [])
        except Exception as e:
            self.logger.warning(f"Could not fetch backlog from Notion: {e}")
            return []
    
    def _prioritize_tasks(self, tasks: List[Dict[str, Any]], priority_projects: List[str]) -> List[Dict[str, Any]]:
        """
        Prioritize tasks based on deadline, project, and other factors.
        
        Args:
            tasks: List of tasks to prioritize
            priority_projects: List of high-priority project names
            
        Returns:
            Sorted list of tasks with priority scores
        """
        prioritized = []
        
        for task in tasks:
            try:
                properties = task.get("properties", {})
                
                # Extract relevant information
                title = properties.get("Nombre", {}).get("title", [{}])[0].get("plain_text", "Untitled")
                project = properties.get("Project", {}).get("select", {}).get("name", "")
                deadline_prop = properties.get("Deadline", {}).get("date", {})
                deadline = deadline_prop.get("start") if deadline_prop else None
                
                # Calculate priority score
                score = self._calculate_priority_score(project, deadline, priority_projects)
                
                prioritized.append({
                    "title": title,
                    "project": project,
                    "deadline": deadline,
                    "priority_score": score,
                    "notion_id": task.get("id"),
                    "url": task.get("url")
                })
                
            except Exception as e:
                self.logger.warning(f"Error processing task: {e}")
                continue
        
        # Sort by priority score (descending)
        prioritized.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return prioritized
    
    def _calculate_priority_score(self, project: str, deadline: str, priority_projects: List[str]) -> float:
        """
        Calculate priority score for a task.
        
        Scoring:
        - Priority project: +50 points
        - Deadline within 7 days: +30 points
        - Deadline within 14 days: +15 points
        - No deadline: 0 points
        
        Args:
            project: Project name
            deadline: Deadline date string (ISO format)
            priority_projects: List of priority project names
            
        Returns:
            Priority score
        """
        score = 0.0
        
        # Check if priority project
        if project in priority_projects:
            score += 50
        
        # Check deadline urgency
        if deadline:
            try:
                deadline_date = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                days_until_deadline = (deadline_date - datetime.now(deadline_date.tzinfo)).days
                
                if days_until_deadline < 0:
                    # Overdue - highest priority
                    score += 100
                elif days_until_deadline <= 7:
                    score += 30
                elif days_until_deadline <= 14:
                    score += 15
                    
            except Exception as e:
                self.logger.warning(f"Error parsing deadline: {e}")
        
        return score
    
    def _generate_backlog_recommendations(self, prioritized_tasks: List[Dict[str, Any]]) -> List[str]:
        """
        Generate recommendations for backlog management.
        
        Args:
            prioritized_tasks: List of prioritized tasks
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if not prioritized_tasks:
            recommendations.append("✅ El backlog está vacío. Buen trabajo!")
            return recommendations
        
        # Recommend top 3 tasks to work on next
        top_tasks = prioritized_tasks[:3]
        recommendations.append("📋 **Tareas recomendadas para asignar:**")
        
        for i, task in enumerate(top_tasks, 1):
            deadline_str = f" (Deadline: {task['deadline']})" if task['deadline'] else ""
            recommendations.append(
                f"{i}. [{task['title']}]({task['url']}) - Proyecto: {task['project']}{deadline_str}"
            )
        
        # Warn about overdue tasks
        overdue_count = sum(1 for task in prioritized_tasks if task['priority_score'] >= 100)
        if overdue_count > 0:
            recommendations.append(f"⚠️ **{overdue_count} tarea(s) vencida(s)** - requieren atención inmediata!")
        
        # General backlog health
        if len(prioritized_tasks) > 20:
            recommendations.append(f"📊 El backlog tiene {len(prioritized_tasks)} tareas. Considerar refinar o cerrar tareas obsoletas.")
        
        return recommendations
