import discord
import json
import logging
from adk.base import BaseAgent

class DesignAgent(BaseAgent):
    def __init__(self, bot, agent_name, agent_dir):
        super().__init__(bot, agent_name, agent_dir)
        self.target_channel_id = 1458858450355224709
        self.notion_db_id = "9b1d386dbae1401b8a58af5a792e8f1f"
        # Simple in-memory state: {thread_id: {"state": "...", "data": ...}}
        self.state_store = {}

    async def can_handle(self, message: discord.Message) -> bool:
        """
        Handle ANY message in a thread that belongs to the Intake Forum.
        """
        if message.author.bot:
            return False

        if not isinstance(message.channel, discord.Thread):
            return False

        if message.channel.parent_id != self.target_channel_id:
            return False
            
        return True

    async def handle(self, message: discord.Message):
        thread_id = message.channel.id
        is_starter = (message.id == thread_id)
        
        # Load Prompt
        prompt_template = self.load_prompt()
        
        # Context building
        # If it's the starter message, we treat it as a fresh validation
        current_state = self.state_store.get(thread_id, {}).get("state", "init")
        
        system_prompt = f"""
        {prompt_template}
        
        Current State: {current_state}
        Is Starter Message: {is_starter}
        """
        
        # If user replies, we feed that into the LLM logic
        user_prompt = f"Message: {message.content}"
        
        # If the user says "I edited it" or similar, we might need to fetch the starter message again
        # naive check or let LLM decide action="validate_edit"
        
        try:
            result_json = self.bot.llm.generate_completion(system_prompt, user_prompt, json_mode=True)
            response_data = json.loads(result_json)
        except Exception as e:
            self.logger.error(f"LLM Error: {e}")
            return

        action = response_data.get("action", "wait")
        feedback = response_data.get("feedback", "")
        extracted_data = response_data.get("data", {})

        # Execute Action
        if action == "approve":
            await self.send_status(message.channel, True, feedback)
            # Ask to clean up if conversations happened?
            if current_state != "init":
                 await message.channel.send("¿Quieres borrar el historial de nuestra conversación? (Responde 'borrar')")
                 self.state_store[thread_id] = {"state": "waiting_delete"}

        elif action == "offer_creation":
            await self.send_status(message.channel, False, feedback)
            await message.channel.send("¿Quieres que cree la tarea de Notion por ti? Responde con el **Nombre del Proyecto** y el **Título de la Tarea**.")
            self.state_store[thread_id] = {"state": "waiting_task_details"}

        elif action == "create_task":
            project = extracted_data.get("project")
            title = extracted_data.get("title")
            
            if project and title:
                url = self.bot.notion.create_task(self.notion_db_id, title, project)
                if url:
                    await message.channel.send(f"✅ Tarea creada: {url}\nPor favor edita tu post original para incluir este link y avísame cuando esté listo.")
                    self.state_store[thread_id] = {"state": "waiting_edit"}
                else:
                    await message.channel.send("❌ Error creando la tarea en Notion. Inténtalo manual.")
            else:
                await message.channel.send("No pude entender el nombre del proyecto o tarea. ¿Podrías repetirlo? (Formato: Proyecto - Tarea)")

        elif action == "validate_edit":
            # Fetch starter message
            try:
                starter = await message.channel.fetch_message(thread_id)
                # Recursively call handle but treat as starter?
                # Or just validate explicitly here.
                # Let's simple-recurse logic by sending the starter content to LLM again as if it was new
                user_prompt = f"STARTER MESSAGE CONTENT: {starter.content}"
                # Redo LLM call
                result_json_2 = self.bot.llm.generate_completion(prompt_template, user_prompt, json_mode=True)
                resp_2 = json.loads(result_json_2)
                
                if resp_2.get("es_valido"):
                    await self.send_status(message.channel, True, resp_2.get("feedback"))
                    await message.channel.send("¡Genial! ¿Quieres borrar nuestros mensajes de ayuda? (Responde 'sí')")
                    self.state_store[thread_id] = {"state": "waiting_delete"}
                else:
                    await self.send_status(message.channel, False, resp_2.get("feedback"))
            except:
                await message.channel.send("No pude leer el mensaje original.")

        elif action == "delete_history":
             # User said yes to delete
             await message.channel.purge(limit=100, check=lambda m: m.id != thread_id) # Delete all except starter
             self.state_store.pop(thread_id, None)

        elif action == "request_edit":
            await self.send_status(message.channel, False, feedback)
            self.state_store[thread_id] = {"state": "waiting_edit"}

        else:
            # Generic reply or wait
            if feedback:
                await message.channel.send(feedback)

    async def send_status(self, channel, is_valid, text):
        embed = discord.Embed(
            title="Design Intake Quality Gate",
            description=text,
            color=discord.Color.green() if is_valid else discord.Color.red()
        )
        if is_valid:
            embed.set_footer(text="✅ APROBADO")
        else:
            embed.set_footer(text="❌ REVISIÓN REQUERIDA")
        
        await channel.send(embed=embed)
