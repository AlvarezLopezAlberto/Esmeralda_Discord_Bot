import os
import importlib.util
import sys
import logging
from .base import BaseAgent
import discord

class AgentManager:
    def __init__(self, bot):
        self.bot = bot
        self.agents = {} # name -> instance
        self.logger = logging.getLogger("adk.manager")
        logging.basicConfig(level=logging.INFO)

    def load_agents(self):
        """
        Dynamically loads agents from ./agents/ directory.
        """
        agents_root = os.path.join(os.getcwd(), 'agents')
        if not os.path.exists(agents_root):
            self.logger.warning("No 'agents' directory found.")
            return

        for agent_name in os.listdir(agents_root):
            agent_dir = os.path.join(agents_root, agent_name)
            if not os.path.isdir(agent_dir):
                continue
            
            # Check for required files
            if not os.path.exists(os.path.join(agent_dir, 'agent.py')):
                self.logger.warning(f"Skipping {agent_name}: Missing agent.py")
                continue
            if not os.path.exists(os.path.join(agent_dir, 'config.yaml')):
                self.logger.warning(f"Skipping {agent_name}: Missing config.yaml")
                continue

            # Import module
            try:
                spec = importlib.util.spec_from_file_location(f"agents.{agent_name}", os.path.join(agent_dir, 'agent.py'))
                module = importlib.util.module_from_spec(spec)
                sys.modules[f"agents.{agent_name}"] = module
                spec.loader.exec_module(module)
                
                # Find agent class
                agent_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BaseAgent) and attr is not BaseAgent:
                        agent_class = attr
                        break
                
                if not agent_class:
                    self.logger.error(f"No valid BaseAgent subclass found in {agent_name}/agent.py")
                    continue

                # Instantiate and Register
                # We assume the agent class allows __init__(bot, name, dir) matching BaseAgent
                # But if the user overrides init, they must match signature or forward args.
                # To be safe, we expect standard signature or kwargs.
                agent_instance = agent_class(self.bot, agent_name, agent_dir)
                self.agents[agent_name] = agent_instance
                self.logger.info(f"Registered agent: {agent_name}")

            except Exception as e:
                self.logger.error(f"Failed to load agent {agent_name}: {e}", exc_info=True)

    async def register_cogs(self):
        """Registers all loaded agent instances as Cogs to the bot."""
        for name, agent in self.agents.items():
            await self.bot.add_cog(agent)
            self.logger.info(f"Added Cog for agent: {name}")

    async def route_message(self, message: discord.Message):
        """
        Routes the message to the first agent that says "can_handle".
        """
        selected_agent = None
        for name, agent in self.agents.items():
            try:
                if await agent.can_handle(message):
                    selected_agent = agent
                    break
            except Exception as e:
                self.logger.error(f"Error checking can_handle for {name}: {e}")

        if selected_agent:
            self.logger.info(f"Routing message to agent: {selected_agent.agent_name}")
            try:
                # Execute handle
                await selected_agent.handle(message)
            except Exception as e:
                self.logger.error(f"Agent {selected_agent.agent_name} failed to handle: {e}", exc_info=True)
        else:
            # self.logger.debug("No agent handled the message.")
            pass
