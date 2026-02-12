"""
Track Capacity Skill

Monitors team capacity and workload distribution.
Helps with capacity planning and identifying overload/idle team members.
"""

import logging
from typing import Dict, Any, List, Optional
from src.skills.base import BaseSkill, SkillContext


class TrackCapacitySkill(BaseSkill):
    """
    Skill to track team capacity and workload distribution.
    """
    
    def __init__(self, bot):
        super().__init__(
            name="track_capacity",
            description="Track team capacity and suggest workload distribution"
        )
        self.bot = bot
        self.critical_projects = ["Vexia"]  # Projects with higher priority
        self.max_tasks_per_person = 5  # Threshold for overload
    
    async def execute(self, context: SkillContext, **kwargs) -> Dict[str, Any]:
        """
        Analyze team capacity and provide recommendations.
        
        Args:
            context: Skill context
            database_id: Notion database ID (defaults to Growth & Strategy)
            team_members: Optional list of team member IDs to analyze
            
        Returns:
            Capacity analysis with recommendations
        """
        database_id = kwargs.get("database_id", "9b1d386dbae1401b8a58af5a792e8f1f")
        team_members = kwargs.get("team_members", [])
        
        try:
            # Query Notion for active tasks
            tasks = await self._get_active_tasks(database_id)
            
            # Group tasks by assignee
            workload = self._calculate_workload(tasks, team_members)
            
            # Analyze capacity
            analysis = self._analyze_capacity(workload)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(analysis)
            
            return {
                "success": True,
                "workload": workload,
                "analysis": analysis,
                "recommendations": recommendations
            }
            
        except Exception as e:
            self.logger.error(f"Error tracking capacity: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_active_tasks(self, database_id: str) -> List[Dict[str, Any]]:
        """
        Get active tasks from Notion database.
        
        Args:
            database_id: Notion database ID
            
        Returns:
            List of active tasks
        """
        try:
            # Use Notion MCP to query tasks
            # Filter for tasks that are not completed
            tasks = self.bot.notion_mcp.query_database(
                database_id=database_id,
                filter_params={
                    "property": "Status",
                    "status": {
                        "does_not_equal": "Completado"
                    }
                }
            )
            return tasks.get("results", [])
        except Exception as e:
            self.logger.warning(f"Could not fetch tasks from Notion: {e}")
            return []
    
    def _calculate_workload(self, tasks: List[Dict[str, Any]], team_members: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate workload per team member.
        
        Args:
            tasks: List of tasks from Notion
            team_members: List of team member IDs
            
        Returns:
            Dictionary mapping member ID to workload info
        """
        workload = {}
        
        for task in tasks:
            try:
                # Extract assignee from task properties
                assignee_prop = task.get("properties", {}).get("Asignado a", {})
                people = assignee_prop.get("people", [])
                
                # Extract project from task
                project_prop = task.get("properties", {}).get("Project", {})
                project = project_prop.get("select", {}).get("name", "Unknown")
                
                # Check if critical project
                is_critical = project in self.critical_projects
                
                for person in people:
                    person_id = person.get("id")
                    person_name = person.get("name", "Unknown")
                    
                    if person_id not in workload:
                        workload[person_id] = {
                            "name": person_name,
                            "total_tasks": 0,
                            "critical_tasks": 0,
                            "projects": set()
                        }
                    
                    workload[person_id]["total_tasks"] += 1
                    if is_critical:
                        workload[person_id]["critical_tasks"] += 1
                    workload[person_id]["projects"].add(project)
                    
            except Exception as e:
                self.logger.warning(f"Error parsing task: {e}")
                continue
        
        # Convert sets to lists for JSON serialization
        for person_id in workload:
            workload[person_id]["projects"] = list(workload[person_id]["projects"])
        
        return workload
    
    def _analyze_capacity(self, workload: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze capacity and identify issues.
        
        Args:
            workload: Workload per team member
            
        Returns:
            Analysis results
        """
        overloaded = []
        idle = []
        balanced = []
        
        for person_id, info in workload.items():
            total_tasks = info["total_tasks"]
            
            if total_tasks == 0:
                idle.append(info["name"])
            elif total_tasks >= self.max_tasks_per_person:
                overloaded.append({
                    "name": info["name"],
                    "tasks": total_tasks,
                    "critical_tasks": info["critical_tasks"]
                })
            else:
                balanced.append(info["name"])
        
        return {
            "overloaded": overloaded,
            "idle": idle,
            "balanced": balanced,
            "total_team_size": len(workload)
        }
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate actionable recommendations based on analysis.
        
        Args:
            analysis: Capacity analysis results
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Check for overloaded team members
        if analysis["overloaded"]:
            for person in analysis["overloaded"]:
                recommendations.append(
                    f"⚠️ {person['name']} está sobrecargado con {person['tasks']} tareas activas. "
                    f"Considerar redistribuir {person['tasks'] - self.max_tasks_per_person + 1} tareas."
                )
        
        # Check for idle team members
        if analysis["idle"]:
            idle_names = ", ".join(analysis["idle"])
            recommendations.append(
                f"💡 {idle_names} {'están' if len(analysis['idle']) > 1 else 'está'} sin tareas asignadas. "
                f"Revisar backlog para asignar nuevas tareas."
            )
        
        # General recommendation
        if analysis["balanced"]:
            balanced_names = ", ".join(analysis["balanced"])
            recommendations.append(
                f"✅ {balanced_names} {'tienen' if len(analysis['balanced']) > 1 else 'tiene'} una carga balanceada."
            )
        
        if not recommendations:
            recommendations.append("✅ El equipo tiene una distribución balanceada de tareas.")
        
        return recommendations
