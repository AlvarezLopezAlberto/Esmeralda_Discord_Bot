import discord
from discord.ext import commands
import yaml
import os
import aiofiles
import logging

class BaseAgent(commands.Cog):
    def __init__(self, bot, agent_name, agent_dir):
        self.bot = bot
        self.agent_name = agent_name
        self.agent_dir = agent_dir
        self.config = self.load_config()
        self.memory_root = os.path.join(os.getcwd(), 'memory')
        self.setup_logging()

    def load_config(self):
        config_path = os.path.join(self.agent_dir, 'config.yaml')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config for agent {self.agent_name} not found at {config_path}")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate mandatory config keys
        required = ['channels', 'allowed_tools', 'memory_policy', 'prompt_path']
        for key in required:
            if key not in config:
                raise ValueError(f"Agent {self.agent_name} missing required config key: {key}")
        
        return config

    def setup_logging(self):
        self.logger = logging.getLogger(f"agent.{self.agent_name}")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def load_prompt(self):
        """Loads the prompt from the configured path."""
        # Config path should be relative to project root or absolute. 
        # Requirement: ./prompts/{agent_name}.txt
        prompt_rel_path = self.config['prompt_path']
        prompt_path = os.path.abspath(prompt_rel_path)
        
        if not os.path.exists(prompt_path):
            self.logger.error(f"Prompt file not found: {prompt_path}")
            return "You are a helpful assistant." # Fallback or Raise
            
        with open(prompt_path, 'r') as f:
            return f.read()

    async def can_handle(self, message: discord.Message) -> bool:
        """
        Logic to determine if this agent should handle the message.
        Can be overridden, but default checks configured channels.
        """
        # Default check: Channel ID or Name in config
        if str(message.channel.id) in map(str, self.config.get('channels', [])):
            return True
        if message.channel.name in self.config.get('channels', []):
            return True
        return False

    async def handle(self, message: discord.Message):
        """
        Main execution method. Must be implemented by subclass.
        """
        raise NotImplementedError("Agents must implement handle()")

    # --- Memory Management ---
    
    def get_memory_path(self, user_id, topic="default"):
        path = os.path.join(self.memory_root, str(user_id), self.agent_name)
        os.makedirs(path, exist_ok=True)
        return os.path.join(path, f"{topic}.md")

    async def preload_memory(self, user_id, topic="default"):
        path = self.get_memory_path(user_id, topic)
        if not os.path.exists(path):
            return ""
        
        async with aiofiles.open(path, mode='r') as f:
            content = await f.read()
        self.logger.info(f"Memory read: {path}")
        return content

    async def dump_memory(self, user_id, content, topic="default"):
        path = self.get_memory_path(user_id, topic)
        async with aiofiles.open(path, mode='w') as f:
            await f.write(content)
        self.logger.info(f"Memory written: {path}")

