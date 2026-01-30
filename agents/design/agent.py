import discord
import json
import logging
import asyncio
from adk.base import BaseAgent

class DesignAgent(BaseAgent):
    def __init__(self, bot, agent_name, agent_dir):
        super().__init__(bot, agent_name, agent_dir)
        self.target_channel_id = 1458858450355224709 # Could be redundant with config but keeping for logic

    async def can_handle(self, message: discord.Message) -> bool:
        """
        Custom routing logic for Design Intake.
        We care about:
        1. Messages in threads belonging to the Forum Channel.
        2. Specifically the Starter Message of the thread (first message).
        """
        if message.author.bot:
            return False

        # Check if channel is a Thread
        if not isinstance(message.channel, discord.Thread):
            return False

        # Check Parent ID (The Forum Channel)
        if message.channel.parent_id != self.target_channel_id:
            return False
            
        # Check if it's the starter message.
        # In forums, usually message.id == channel.id for the starter post?
        # Or we check message position.
        if message.id == message.channel.id:
            return True
        
        # Fallback for some cases where IDs might differ slightly (unlikely in new forums but possible)
        # or if it's an early message.
        # But per the logic being refactored: "if message.id == message.channel.id"
        return True

    async def handle(self, message: discord.Message):
        self.logger.info(f"DesignAgent handling message {message.id} in {message.channel.name}")
        
        # Preload memory (optional for this specific interactions, but good practice)
        # memory = await self.preload_memory(message.author.id, "intake")
        
        # Load Prompt
        prompt_template = self.load_prompt()
        
        # Prepare content
        user_prompt = prompt_template.format(post_content=message.content)
        system_prompt = "You are a Quality Gate Validator."

        # Call LLM
        # Assuming self.bot.llm is the contract
        try:
            result_json = self.bot.llm.generate_completion(system_prompt, user_prompt, json_mode=True)
            validation_result = json.loads(result_json)
        except Exception as e:
            self.logger.error(f"LLM Error: {e}")
            return # Silent fail or error message

        if not validation_result:
            return

        is_valid = validation_result.get("es_valido", False)
        feedback = validation_result.get("feedback", "")

        # Create Response
        embed = discord.Embed(
            title="Design Intake Quality Gate",
            description=feedback,
            color=discord.Color.green() if is_valid else discord.Color.red()
        )
        
        if is_valid:
            embed.set_footer(text="✅ Status: APROBADO - Esperando Triaje")
        else:
            embed.set_footer(text="❌ Status: RECHAZADO - Por favor edita tu post")

        # Log to memory (just an example of context dumping)
        await self.dump_memory(message.author.id, f"Intake Status: {is_valid}\nFeedback: {feedback}", "last_intake")

        # Send or Edit
        # Logic from old cog: Check if bot already responded
        bot_message = None
        async for msg in message.channel.history(limit=20):
            if msg.author.id == self.bot.user.id and msg.embeds and msg.embeds[0].title == "Design Intake Quality Gate":
                bot_message = msg
                break

        if bot_message:
            await bot_message.edit(embed=embed)
        else:
            await message.channel.send(embed=embed)
