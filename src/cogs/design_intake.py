import discord
from discord.ext import commands
import json

class DesignIntakeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ID del canal FORO #design-intake
        self.target_channel_id = 1458858450355224709

    def is_design_intake_thread(self, channel):
        """Checks if the channel is a thread within the target forum channel."""
        # En foros, el "channel" del mensaje es el Hilo (Thread).
        # Su `parent` es el canal Foro.
        if isinstance(channel, discord.Thread):
            if channel.parent_id == self.target_channel_id:
                return True
        return False

    async def validate_intake(self, message):
        """Validates the content of the intake request using LLM."""
        prompt_template = self.bot.llm.load_prompt("intake_validation")
        if not prompt_template:
            print("Error: 'intake_validation' prompt not found.")
            return

        user_prompt = prompt_template.format(post_content=message.content)
        
        # System prompt is embedded in the template or we can add a simple one
        system_prompt = "You are a Quality Gate Validator."
        
        result_json = self.bot.llm.generate_completion(system_prompt, user_prompt, json_mode=True)
        
        try:
            return json.loads(result_json)
        except json.JSONDecodeError:
            print(f"Failed to decode JSON from LLM: {result_json}")
            return None

    async def process_message(self, message):
        """Processes the message (new or edited) to validate requirements."""
        if not message.content:
            return

        validation_result = await self.validate_intake(message)
        if not validation_result:
            return

        is_valid = validation_result.get("es_valido", False)
        feedback = validation_result.get("feedback", "")

        embed = discord.Embed(
            title="Design Intake Quality Gate",
            description=feedback,
            color=discord.Color.green() if is_valid else discord.Color.red()
        )
        
        if is_valid:
            embed.set_footer(text="✅ Status: APROBADO - Esperando Triaje")
        else:
            embed.set_footer(text="❌ Status: RECHAZADO - Por favor edita tu post")

        # Check if bot has already responded
        bot_message = None
        async for msg in message.channel.history(limit=20):
            if msg.author.id == self.bot.user.id:
                bot_message = msg
                break

        if bot_message:
            await bot_message.edit(embed=embed)
        else:
            await message.channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages
        if message.author.bot:
            return

        # Check if it's in the correct thread/channel context
        if not self.is_design_intake_thread(message.channel):
            return
        
        # We only care about the "Starter Message" of the thread.
        # In a Forum channel, the starter message is the first message in the thread.
        # Usually for Threads/Forums, the Thread ID IS the Starter Message ID.
        if message.id == message.channel.id:
             await self.process_message(message)
        elif message.channel.message_count <= 1:
             # Fallback: if message count is low, it's likely the first message 
             # (though message_count can be inaccurate in cached threads)
             await self.process_message(message)


    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        """
        Handles message edits even when messages aren't in cache.
        This is crucial for forum posts that may have been created before bot startup.
        """
        import sys
        
        # Get the channel
        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return
        
        sys.stderr.write(f"DEBUG INTAKE: Raw message edit in channel {channel.name}\n")
        
        # Check if it's in the design intake forum
        if not self.is_design_intake_thread(channel):
            sys.stderr.write(f"DEBUG INTAKE: Not in design intake thread\n")
            return
        
        # Fetch the message
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            sys.stderr.write(f"DEBUG INTAKE: Message not found\n")
            return
        except discord.Forbidden:
            sys.stderr.write(f"DEBUG INTAKE: No permission to fetch message\n")
            return
        
        sys.stderr.write(f"DEBUG INTAKE: Message edited by {message.author}\n")
        
        # Ignore bot edits
        if message.author.bot:
            sys.stderr.write(f"DEBUG INTAKE: Ignoring bot edit\n")
            return
        
        sys.stderr.write(f"DEBUG INTAKE: Message ID: {message.id}, Channel ID: {channel.id}\n")
        
        # Only re-validate if it's the STARTER message.
        if message.id == channel.id:
            sys.stderr.write(f"DEBUG INTAKE: Processing starter message edit\n")
            await self.process_message(message)
        else:
            sys.stderr.write(f"DEBUG INTAKE: Not starter message, skipping\n")
        
async def setup(bot):
    await bot.add_cog(DesignIntakeCog(bot))
