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
        
        # STATE RECOVERY: If state is init (e.g. restart), check if we were waiting for something based on chat history
        if current_state == "init" and not is_starter:
            try:
                async for m in message.channel.history(limit=5):
                    if m.author == self.bot.user:
                        if "borrar el historial" in m.content or "borrar nuestros mensajes" in m.content:
                            current_state = "waiting_delete"
                        elif "Nombre del Proyecto" in m.content:
                            current_state = "waiting_task_details"
                        break
            except Exception as e:
                self.logger.warning(f"Failed to recover state: {e}")
        
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
            # 1. Automate Task Creation
            project = extracted_data.get("project", "Sin Proyecto")
            title = extracted_data.get("title", "Nueva Tarea de Diseño")
            thread_url = message.jump_url
            
            # Create in Notion
            notion_url = self.bot.notion.create_task(
                self.notion_db_id, 
                title, 
                project, 
                sprint="Current Sprint", 
                content=f"Solicitud original en Discord: {thread_url}\n\nDescripción:\n{message.content}"
            )
            
            # 2. Notify Design Team
            request_channel_id = 1207375472955232266
            request_channel = self.bot.get_channel(request_channel_id)
            if request_channel:
                await request_channel.send(
                    f"<@&1458178611382325412> **Nueva Solicitud de Diseño Aprobada**\n"
                    f"📂 **Proyecto:** {project}\n"
                    f"📝 **Tarea:** {title}\n"
                    f"🔗 **Notion:** {notion_url if notion_url else 'Error creando Notion'}\n"
                    f"💬 **Hilo:** {thread_url}"
                )

            # 3. User Feedback
            final_feedback = feedback
            if notion_url:
                final_feedback += f"\n\n✅ He creado la tarea en Notion por ti: {notion_url}"

            await self.send_status(message.channel, True, final_feedback, final_approved=True)
            
            if current_state != "init":
                 await message.channel.send("¿Quieres borrar el historial de nuestra conversación para limpiar el hilo? (Responde 'sí')")
                 self.state_store[thread_id] = {"state": "waiting_delete"}

        elif action == "offer_creation":
            await self.send_status(message.channel, False, feedback)
            await message.channel.send("¿Quieres que cree la tarea de Notion por ti? Responde con el **Nombre del Proyecto** y el **Título de la Tarea**.")
            self.state_store[thread_id] = {"state": "waiting_task_details"}

        elif action == "create_task":
            # This action might become redundant if "approve" does it, 
            # but keep it for the flow where user explicitly asks after "offer_creation"
            project = extracted_data.get("project")
            title = extracted_data.get("title")
            
            if project and title:
                url = self.bot.notion.create_task(
                    self.notion_db_id, title, project, sprint="Current Sprint", content=f"Creado manualmente desde hilo: {message.jump_url}"
                )
                if url:
                    await message.channel.send(f"✅ Tarea creada: {url}\nPor favor edita tu post original para incluir este link y avísame cuando esté listo.")
                    self.state_store[thread_id] = {"state": "waiting_edit"}
                else:
                    # Increment failure count
                    current_errors = self.state_store.get(thread_id, {}).get("notion_errors", 0) + 1
                    
                    if current_errors >= 2:
                        await message.channel.send(
                            "❌ No he podido crear la tarea automáticamente tras varios intentos.\n"
                            "Por favor, usa este formulario manual para darla de alta:\n"
                            "https://www.notion.so/emerald-dev/2fdd14a8642b80edb194deed54c6449e?pvs=106\n\n"
                            "Una vez creada, pega el link aquí."
                        )
                        # Reset to waiting for the link (or some neutral state)
                        self.state_store[thread_id] = {"state": "waiting_edit", "notion_errors": 0} 
                    else:
                        await message.channel.send("❌ Error creando la tarea en Notion. Inténtalo de nuevo o revisa los datos.")
                        # Retain state but update errors
                        state_data = self.state_store.get(thread_id, {"state": "waiting_task_details"})
                        state_data["notion_errors"] = current_errors
                        self.state_store[thread_id] = state_data
            else:
                await message.channel.send("No pude entender el nombre del proyecto o tarea. ¿Podrías repetirlo? (Formato: Proyecto - Tarea)")

        elif action == "validate_edit":
            # Fetch starter message
            try:
                starter = await message.channel.fetch_message(thread_id)
                # Redo LLM call with FRESH content
                user_prompt = f"STARTER MESSAGE CONTENT: {starter.content}"
                
                result_json_2 = self.bot.llm.generate_completion(prompt_template, user_prompt, json_mode=True)
                resp_2 = json.loads(result_json_2)
                
                if resp_2.get("es_valido"):
                    # Success! 
                    # Extract Data from NEW response
                    data_2 = resp_2.get("data", {})
                    project = data_2.get("project", "Sin Proyecto")
                    title = data_2.get("title", "Nueva Tarea de Diseño")
                    thread_url = message.jump_url

                    # Create Notion
                    notion_url = self.bot.notion.create_task(
                        self.notion_db_id, 
                        title, 
                        project, 
                        sprint="Current Sprint", 
                        content=f"Solicitud original en Discord (Intake): {thread_url}\n\nContenido:\n{starter.content}"
                    )

                    # Notify Team
                    request_channel_id = 1207375472955232266
                    request_channel = self.bot.get_channel(request_channel_id)
                    if request_channel:
                         await request_channel.send(
                            f"<@&1458178611382325412> **Nueva Solicitud de Diseño Aprobada (Post Editado)**\n"
                            f"📂 **Proyecto:** {project}\n"
                            f"📝 **Tarea:** {title}\n"
                            f"🔗 **Notion:** {notion_url if notion_url else 'Error creando Notion'}\n"
                            f"💬 **Hilo:** {thread_url}"
                        )

                    feedback_text = resp_2.get("feedback")
                    if notion_url:
                        feedback_text += f"\n\n✅ He creado la tarea en Notion automáticamente: {notion_url}"

                    await self.send_status(message.channel, True, feedback_text, final_approved=True)
                    await message.channel.send("¡Genial! ¿Quieres borrar nuestros mensajes de ayuda? (Responde 'sí')")
                    self.state_store[thread_id] = {"state": "waiting_delete"}
                else:
                    # Still invalid, normal text feedback
                    await self.send_status(message.channel, False, resp_2.get("feedback"))
            except Exception as e:
                self.logger.error(f"Error fetching starter message: {e}")
                import traceback
                traceback.print_exc()
                await message.channel.send("No pude leer el mensaje original.")

        elif action == "delete_history":
             await message.channel.send("Limpiando conversación...")
             try:
                 # Delete messages in this thread that are NOT the starter message
                 # We need to fetch history first
                 messages_to_delete = []
                 async for m in message.channel.history(limit=100):
                     if m.id != thread_id:
                         messages_to_delete.append(m)
                 
                 if messages_to_delete:
                     if len(messages_to_delete) > 0:
                         # bulk_delete is for TextChannel, for Thread use delete() one by one or purge if supported
                         # Discord purge on threads often works.
                         await message.channel.delete_messages(messages_to_delete)
             except Exception as e:
                 self.logger.error(f"Delete Error: {e}")
                 # Fallback to simple purge which might be easier
                 await message.channel.purge(limit=100, check=lambda m: m.id != thread_id)
                 
             self.state_store.pop(thread_id, None)

        elif action == "request_edit":
            await self.send_status(message.channel, False, feedback)
            self.state_store[thread_id] = {"state": "waiting_edit"}

        else:
            # Generic reply or wait
            if feedback:
                await message.channel.send(feedback)

    async def send_status(self, channel, is_valid, text, final_approved=False):
        if final_approved and is_valid:
            # Show Green Embed ONLY for final approval
            embed = discord.Embed(
                title="Design Intake Quality Gate",
                description=text,
                color=discord.Color.green()
            )
            embed.set_footer(text="✅ APROBADO")
            await channel.send(embed=embed)
        else:
            # Standard conversational text
            await channel.send(text)
