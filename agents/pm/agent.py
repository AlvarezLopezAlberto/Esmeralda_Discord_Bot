"""
PM Agent - Project Manager Agent

Manages design team capacity, backlog, daily syncs, decision documentation,
and feedback translation.
"""

import discord
import json
import logging
import os
import sys
import datetime
import importlib.util
from typing import Optional

# Add paths for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from adk.base import BaseAgent
from src.skills.base import SkillContext, SkillExecutor


class PMAgent(BaseAgent):
    """
    Project Manager Agent with Skills-based architecture.
    
    Responsibilities:
    1. Capacity Planning - Track team workload and availability
    2. Backlog Management - Prioritize and manage task queue
    3. Daily Sync Monitoring - Parse and track team updates
    4. Decision Documentation - Auto-document decisions to Notion
    5. Feedback Translation - Convert vague feedback to action items
    """
    
    def __init__(self, bot, agent_name, agent_dir):
        super().__init__(bot, agent_name, agent_dir)
        
        # Configuration
        self.daily_sync_channel_id = 1304569263293468682
        self.notion_db_id = "9b1d386dbae1401b8a58af5a792e8f1f"  # Growth & Strategy
        
        # State management
        self.memory_root = os.path.join(os.getcwd(), 'memory', 'pm')
        os.makedirs(self.memory_root, exist_ok=True)
        
        # Initialize skills with dynamic import
        skills_init_path = os.path.join(agent_dir, 'skills', '__init__.py')
        spec = importlib.util.spec_from_file_location("pm_skills", skills_init_path)
        skills_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(skills_module)
        
        self.skills_registry = skills_module.create_pm_skills_registry(bot)
        self.skills_executor = SkillExecutor(self.skills_registry)
        
        self.logger.info(
            f"PMAgent initialized with {len(self.skills_registry.list_names())} skills."
        )
    
    # ==================== MAIN HANDLER ====================
    
    async def can_handle(self, message: discord.Message) -> bool:
        """
        Determine if PM agent should handle this message.
        
        Handles:
        - Messages in daily sync channel
        - DMs or mentions with PM-related keywords
        - Messages with decision keywords
        """
        if message.author.bot:
            return False
        
        # Check if in daily sync channel
        if message.channel.id == self.daily_sync_channel_id:
            return True
        
        # Check for PM mentions or keywords
        if self.bot.user.mentioned_in(message):
            pm_keywords = ["capacity", "backlog", "feedback", "decision", "task"]
            content_lower = message.content.lower()
            if any(keyword in content_lower for keyword in pm_keywords):
                return True
        
        return False
    
    async def handle(self, message: discord.Message):
        """
        Main handler using skills-based architecture.
        
        Flow:
        1. Detect message type (daily sync, feedback, decision, query)
        2. Route to appropriate skill
        3. Execute skill and respond
        """
        context = SkillContext(agent=self, message=message)
        
        # Load prompt for LLM-based routing
        prompt_template = self.load_prompt()
        
        try:
            # Determine action using LLM
            action_data = await self._determine_action(message, prompt_template)
            action = action_data.get("action", "wait")
            
            # Route to appropriate handler
            if action == "parse_daily_sync":
                await self._handle_daily_sync(message, context)
            
            elif action == "track_capacity":
                await self._handle_capacity_check(message, context)
            
            elif action == "manage_backlog":
                await self._handle_backlog_query(message, context)
            
            elif action == "document_decision":
                await self._handle_decision(message, context)
            
            elif action == "translate_feedback":
                await self._handle_feedback(message, context, action_data)
            
            else:
                # Generic response
                feedback = action_data.get("feedback", "")
                if feedback:
                    await message.channel.send(feedback)
                    
        except Exception as e:
            self.logger.error(f"Error handling message: {e}", exc_info=True)
            await message.channel.send(
                "⚠️ Lo siento, tuve un problema procesando tu mensaje. "
                "Por favor intenta de nuevo o contacta a soporte."
            )
    
    # ==================== ACTION DETERMINERS ====================
    
    async def _determine_action(self, message: discord.Message, prompt: str) -> dict:
        """
        Use LLM to determine what action to take.
        
        Args:
            message: Discord message
            prompt: System prompt
            
        Returns:
            Dictionary with action and data
        """
        # Build context
        content = message.content
        channel_name = getattr(message.channel, 'name', 'DM')
        
        user_prompt = f"""
        Canal: {channel_name}
        Mensaje: {content}
        
        Determina qué acción debe tomar el PM basándote en este mensaje.
        """
        
        try:
            result = self.bot.llm.generate_completion(
                system_prompt=prompt,
                user_prompt=user_prompt,
                json_mode=True
            )
            return json.loads(result)
        except Exception as e:
            self.logger.error(f"Error determining action: {e}")
            return {"action": "wait", "feedback": ""}
    
    # ==================== SKILL HANDLERS ====================
    
    async def _handle_daily_sync(self, message: discord.Message, context: SkillContext):
        """Handle daily sync message parsing."""
        try:
            result = await self.skills_executor.execute(
                "parse_daily_sync",
                context,
                message_content=message.content,
                author=message.author
            )
            
            if not result["success"]:
                await message.channel.send(
                    f"❌ {result.get('error', 'Error parseando daily sync')}\\n\\n"
                    f"Formato esperado:\\n"
                    f"¿Qué hice? ...\\n"
                    f"¿Qué haré? ...\\n"
                    f"¿Qué me bloquea? ..."
                )
                return
            
            # Acknowledge the sync
            sync_data = result["data"]
            response = f"✅ Daily sync registrado para {sync_data['author']}"
            
            # Alert if critical blocker
            if result.get("has_critical_blocker"):
                response += f"\\n\\n⚠️ **Blocker crítico detectado**: {sync_data['blockers']}"
                response += "\\nNotificando al equipo..."
            
            await message.add_reaction("✅")
            
            # Store sync data for capacity tracking
            await self._store_sync_data(sync_data)
            
            if result.get("has_critical_blocker"):
                await message.channel.send(response)
                
        except Exception as e:
            self.logger.error(f"Error handling daily sync: {e}", exc_info=True)
            await message.channel.send("Error procesando daily sync")
    
    async def _handle_capacity_check(self, message: discord.Message, context: SkillContext):
        """Handle capacity planning query."""
        try:
            result = await self.skills_executor.execute(
                "track_capacity",
                context,
                database_id=self.notion_db_id
            )
            
            if not result["success"]:
                await message.channel.send(f"❌ Error: {result.get('error')}")
                return
            
            # Format capacity report
            analysis = result["analysis"]
            recommendations = result["recommendations"]
            
            embed = discord.Embed(
                title="📊 Reporte de Capacidad del Equipo",
                color=discord.Color.blue()
            )
            
            # Add workload summary
            if analysis["overloaded"]:
                overloaded_list = "\\n".join([
                    f"- {p['name']}: {p['tasks']} tareas"
                    for p in analysis["overloaded"]
                ])
                embed.add_field(
                    name="⚠️ Sobrecargados",
                    value=overloaded_list,
                    inline=False
                )
            
            if analysis["idle"]:
                embed.add_field(
                    name="💡 Disponibles",
                    value="\\n".join([f"- {name}" for name in analysis["idle"]]),
                    inline=False
                )
            
            if analysis["balanced"]:
                embed.add_field(
                    name="✅ Carga Balanceada",
                    value="\\n".join([f"- {name}" for name in analysis["balanced"]]),
                    inline=False
                )
            
            # Add recommendations
            embed.add_field(
                name="💡 Recomendaciones",
                value="\\n".join(recommendations),
                inline=False
            )
            
            await message.channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error handling capacity check: {e}", exc_info=True)
            await message.channel.send("Error generando reporte de capacidad")
    
    async def _handle_backlog_query(self, message: discord.Message, context: SkillContext):
        """Handle backlog management query."""
        try:
            result = await self.skills_executor.execute(
                "manage_backlog",
                context,
                database_id=self.notion_db_id
            )
            
            if not result["success"]:
                await message.channel.send(f"❌ Error: {result.get('error')}")
                return
            
            # Format backlog report
            recommendations = result["recommendations"]
            backlog_size = result["backlog_size"]
            
            embed = discord.Embed(
                title=f"📋 Backlog Management ({backlog_size} tareas)",
                color=discord.Color.green()
            )
            
            embed.description = "\\n".join(recommendations)
            
            await message.channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error handling backlog query: {e}", exc_info=True)
            await message.channel.send("Error consultando backlog")
    
    async def _handle_decision(self, message: discord.Message, context: SkillContext):
        """Handle decision documentation."""
        try:
            # Get conversation history for context
            history = []
            if hasattr(message.channel, 'history'):
                async for msg in message.channel.history(limit=10):
                    if not msg.author.bot:
                        history.append(msg.content)
            history.reverse()
            
            # Get participants
            participants = list(set([
                msg.author.name
                async for msg in message.channel.history(limit=20)
                if not msg.author.bot
            ]))
            
            result = await self.skills_executor.execute(
                "document_decision",
                context,
                message_content=message.content,
                conversation_history=history,
                channel_name=getattr(message.channel, 'name', 'Unknown'),
                participants=participants,
                message_url=message.jump_url
            )
            
            if result.get("is_decision"):
                if result["success"]:
                    await message.add_reaction("📝")
                    await message.channel.send(
                        f"✅ Decisión documentada en Notion:\\n{result['notion_url']}"
                    )
                else:
                    await message.channel.send(
                        f"⚠️ Detecté una decisión pero hubo un error documentándola: {result.get('error')}"
                    )
                    
        except Exception as e:
            self.logger.error(f"Error handling decision: {e}", exc_info=True)
    
    async def _handle_feedback(
        self,
        message: discord.Message,
        context: SkillContext,
        action_data: dict
    ):
        """Handle feedback translation."""
        try:
            feedback = message.content
            project_context = action_data.get("data", {}).get("project", "")
            
            result = await self.skills_executor.execute(
                "translate_feedback",
                context,
                feedback=feedback,
                project_context=project_context,
                feedback_source=message.author.name,
                discord_link=message.jump_url
            )
            
            if result.get("needs_clarification"):
                questions = result["clarification_questions"]
                response = "Necesito más información para crear una tarea técnica clara:\\n\\n"
                response += "\\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
                await message.channel.send(response)
            elif result["success"]:
                await message.add_reaction("✅")
                await message.channel.send(result["message"])
            else:
                await message.channel.send(f"❌ Error: {result.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Error handling feedback: {e}", exc_info=True)
            await message.channel.send("Error procesando feedback")
    
    # ==================== HELPER METHODS ====================
    
    async def _store_sync_data(self, sync_data: dict):
        """Store daily sync data for historical tracking."""
        try:
            # Store in memory directory
            author_id = sync_data.get("author_id", "unknown")
            date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
            
            sync_file = os.path.join(self.memory_root, f"sync_{author_id}_{date}.json")
            
            with open(sync_file, 'w') as f:
                json.dump(sync_data, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Error storing sync data: {e}")
