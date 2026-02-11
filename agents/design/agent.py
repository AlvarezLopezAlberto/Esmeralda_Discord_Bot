import discord
import json
import logging
import os
import datetime
import calendar
from adk.base import BaseAgent

class DesignAgent(BaseAgent):
    def __init__(self, bot, agent_name, agent_dir):
        super().__init__(bot, agent_name, agent_dir)
        self.target_channel_id = 1458858450355224709
        self.notion_db_id = "9b1d386dbae1401b8a58af5a792e8f1f"
        self.existing_exception_thread_ids = {1470846699198222489}
        # Persistent state: {thread_id: {"state": "...", "notion_url": "...", "updated_at": "..."}}
        # Ensure memory directory exists
        os.makedirs(os.path.dirname(self._state_path()), exist_ok=True)
        self.state_store = self._load_state()
        self.boot_time = datetime.datetime.now(datetime.timezone.utc)
        self.mapping_file = os.path.join(os.getcwd(), "thread_notion_mapping.csv")
        self.logger.info(f"DesignAgent initialized. Boot time: {self.boot_time}. State loaded: {len(self.state_store)} threads.")

    def _state_path(self):
        return os.path.join(os.getcwd(), "memory", "design_intake_state.json")
    
    def _get_notion_url_from_csv(self, thread_id: int) -> tuple[Optional[str], Optional[str]]:
        """Read thread-Notion mapping from CSV file. Returns (notion_url, status)."""
        import csv
        
        if not os.path.exists(self.mapping_file):
            self.logger.warning(f"Mapping file not found: {self.mapping_file}")
            return None, None
        
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['thread_id'] == str(thread_id):
                        notion_url = row.get('notion_url', '').strip()
                        status = row.get('status', '').strip()
                        if notion_url:
                            return notion_url, status
                        return None, status
        except Exception as e:
            self.logger.error(f"Error reading mapping file: {e}")
        
        return None, None

    def _load_state(self):
        path = self._state_path()
        if not os.path.exists(path):
            self.logger.info(f"State file does not exist yet: {path}")
            return {}
        try:
            with open(path, "r") as f:
                state = json.load(f)
                self.logger.info(f"Loaded state from {path}: {len(state)} threads")
                return state
        except Exception as e:
            self.logger.error(f"Failed to load state store from {path}: {e}")
            return {}

    def _save_state(self):
        path = self._state_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump(self.state_store, f, indent=2)
            self.logger.debug(f"State saved to {path}: {len(self.state_store)} threads")
        except Exception as e:
            self.logger.error(f"Failed to save state store to {path}: {e}", exc_info=True)

    def _get_thread_state(self, thread_id: int):
        return self.state_store.get(str(thread_id), {})

    def _set_thread_state(self, thread_id: int, data: dict):
        data = dict(data or {})
        data["updated_at"] = datetime.datetime.utcnow().isoformat()
        self.state_store[str(thread_id)] = data
        self._save_state()

    def _clear_thread_state(self, thread_id: int):
        self.state_store.pop(str(thread_id), None)
        self._save_state()

    def _thread_link(self, message: discord.Message, thread_id: int) -> str:
        if message.guild:
            return f"https://discord.com/channels/{message.guild.id}/{thread_id}/{thread_id}"
        return message.jump_url

    def _reference_datetime(self, message: discord.Message) -> datetime.datetime:
        if isinstance(message.channel, discord.Thread) and message.channel.created_at:
            return message.channel.created_at
        if message.created_at:
            return message.created_at
        return datetime.datetime.now(datetime.timezone.utc)

    def _parse_iso_date(self, value: str):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except Exception:
            try:
                return datetime.datetime.fromisoformat(value).date()
            except Exception:
                return None

    def _safe_date(self, year: int, month: int, day: int) -> datetime.date:
        last_day = calendar.monthrange(year, month)[1]
        return datetime.date(year, month, min(day, last_day))

    def _normalize_deadline(self, deadline: str, reference_dt: datetime.datetime):
        """
        Normalizes a deadline string to ensure it's not in the past.
        If the LLM extracts a date with a past year, adjusts it to current or next year.
        """
        if not deadline:
            return None
        
        parsed = self._parse_iso_date(deadline)
        if not parsed:
            return deadline  # Return as-is if can't parse

        reference_date = reference_dt.date()
        
        # If parsed year is in the past, adjust to current/next year
        if parsed.year < reference_date.year:
            # Try with current year
            candidate = self._safe_date(reference_date.year, parsed.month, parsed.day)
            if candidate < reference_date:
                # If that date already passed this year, use next year
                candidate = self._safe_date(reference_date.year + 1, parsed.month, parsed.day)
        elif parsed.year == reference_date.year:
            # Same year - check if date already passed
            candidate = self._safe_date(parsed.year, parsed.month, parsed.day)
            if candidate < reference_date:
                candidate = self._safe_date(reference_date.year + 1, parsed.month, parsed.day)
        elif parsed.year == reference_date.year + 1:
            # Next year is fine
            candidate = parsed
        else:
            # More than 1 year in future - likely an error, use current year logic
            self.logger.warning(f"Deadline year {parsed.year} is far in future. Using fallback logic.")
            candidate = self._safe_date(reference_date.year, parsed.month, parsed.day)
            if candidate < reference_date:
                candidate = self._safe_date(reference_date.year + 1, parsed.month, parsed.day)
        
        return candidate.isoformat()

    def _get_project_options(self):
        try:
            if not self.bot.notion or not self.bot.notion.is_enabled():
                return []
            return self.bot.notion.get_multi_select_options(self.notion_db_id, "Proyecto")
        except Exception as e:
            self.logger.warning(f"Failed to load project options: {e}")
            return []

    @staticmethod
    def _canonical_project(value: str) -> str:
        return " ".join((value or "").strip().lower().split())

    def _match_project_option(self, project_raw: str, options):
        if not project_raw:
            return None
        candidate = self._canonical_project(project_raw)
        if not candidate or candidate in {"sin proyecto", "ninguno", "n/a"}:
            return None
        by_canon = {self._canonical_project(opt): opt for opt in (options or [])}
        return by_canon.get(candidate)

    async def _request_project(self, channel, thread_id: int, project_raw: str, options):
        base = "Necesito el Nombre del Proyecto exacto en Notion para crear la tarea."
        if project_raw:
            base = f"No encontré el proyecto \"{project_raw}\" en Notion. Necesito el Nombre del Proyecto exacto."

        message = base
        if options:
            preview = ", ".join(options[:20])
            if len(options) > 20:
                preview += f" (+{len(options) - 20} más)"
            message += f"\n\nProyectos disponibles: {preview}"

        message += "\n\nTip: la próxima vez incluye el nombre exacto del proyecto en tu mensaje para evitar demoras."
        await channel.send(message)
        self._set_thread_state(thread_id, {"state": "waiting_task_details"})

    async def _extract_notion_url_from_starter(self, channel: discord.Thread, thread_id: int) -> Optional[str]:
        """Extract Notion URL from the thread starter message if present."""
        try:
            import re
            starter = await channel.fetch_message(thread_id)
            content = starter.content or ""
            
            # Look for Notion URLs
            notion_urls = re.findall(r'(https?://(?:\S+\.)?notion\.(?:so|site)/[^\s]+)', content)
            if notion_urls:
                # Validate that it's from the correct database (emerald-dev workspace)
                first_url = notion_urls[0]
                
                # Check if it's NOT from our workspace (contains a different database ID)
                # Our database: 9b1d386dbae1401b8a58af5a792e8f1f
                if '/9b1d386dbae1' not in first_url and 'emerald-dev' in first_url:
                    # Return None and let the agent handle the user-provided link
                    self.logger.info(f"Found Notion link but it's not from the correct database: {first_url}")
                    return None
                
                # Return the first Notion URL found
                return first_url
        except Exception as e:
            self.logger.warning(f"Failed to extract Notion URL from starter: {e}")
        return None

    async def _recover_state_from_history(self, channel: discord.Thread, thread_id: int) -> str:
        try:
            async for m in channel.history(limit=10):
                if m.author == self.bot.user:
                    if "borrar el historial" in m.content or "borrar nuestros mensajes" in m.content:
                        return "waiting_delete"
                    if "Nombre del Proyecto" in m.content:
                        return "waiting_task_details"
                    if "He creado la tarea en Notion" in m.content:
                        return "approved"
                    break
        except Exception as e:
            self.logger.warning(f"Failed to recover state: {e}")
        return "init"

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

        state_entry = self._get_thread_state(thread_id)
        current_state = state_entry.get("state", "init")
        
        self.logger.debug(f"Thread {thread_id}: current_state='{current_state}', state_entry={state_entry}")

        # If thread was already handled, do nothing to avoid re-processing after restarts
        if current_state in {"approved", "ignored_existing"}:
            if current_state == "ignored_existing" and thread_id in self.existing_exception_thread_ids:
                self._clear_thread_state(thread_id)
                current_state = "init"
            else:
                self.logger.info(f"Thread {thread_id} already processed (state: {current_state}). Exiting.")
                return

        # If no state, try recovery and Notion double-check
        if current_state == "init":
            # Recover from history (bot already interacted)
            recovered_state = await self._recover_state_from_history(message.channel, thread_id)
            if recovered_state != "init":
                current_state = recovered_state
                self._set_thread_state(thread_id, {"state": current_state})
                if current_state == "approved":
                    return

            # PRIMARY CHECK: CSV mapping file (single source of truth)
            csv_notion_url, csv_status = self._get_notion_url_from_csv(thread_id)
            if csv_notion_url:
                self.logger.info(f"Thread {thread_id} found in CSV mapping with status '{csv_status}': {csv_notion_url}")
                self._set_thread_state(thread_id, {"state": "approved", "notion_url": csv_notion_url})
                return
            elif csv_status == "ignored":
                self.logger.info(f"Thread {thread_id} marked as 'ignored' in CSV mapping")
                self._set_thread_state(thread_id, {"state": "ignored_existing"})
                return

            # FALLBACK: Notion API check (for new threads not in CSV yet)
            # This must happen BEFORE the boot-time check to avoid missing already-processed threads
            if message.guild:
                existing_url = self.bot.notion.find_task_by_discord_thread(
                    self.notion_db_id,
                    message.guild.id,
                    thread_id
                )
                if existing_url:
                    self.logger.info(f"Thread {thread_id} found via Notion API (Discord Thread property): {existing_url}")
                    self._set_thread_state(thread_id, {"state": "approved", "notion_url": existing_url})
                    return
            
            # FALLBACK: Look for Notion link in the starter message itself
            # This handles old threads not yet in CSV
            notion_url_from_starter = await self._extract_notion_url_from_starter(message.channel, thread_id)
            if notion_url_from_starter:
                self.logger.info(f"Thread {thread_id} has Notion link in starter message: {notion_url_from_starter}")
                self._set_thread_state(thread_id, {"state": "approved", "notion_url": notion_url_from_starter})
                return

            # Ignore pre-existing threads on boot (except for exception threads)
            try:
                if (
                    message.channel.created_at
                    and message.channel.created_at < self.boot_time
                    and thread_id not in self.existing_exception_thread_ids
                ):
                    self.logger.info(f"Ignoring pre-existing thread {thread_id} (created before boot)")
                    self._set_thread_state(thread_id, {"state": "ignored_existing"})
                    return
            except Exception:
                pass
        
        # Load Prompt
        prompt_template = self.load_prompt()
        
        # Context building
        # If it's the starter message, we treat it as a fresh validation
        
        starter_content, recent_history = await self._build_thread_context(message.channel, thread_id)

        reference_dt = self._reference_datetime(message)
        system_prompt = f"""
        {prompt_template}
        
        Current State: {current_state}
        Is Starter Message: {is_starter}
        Thread Date (UTC): {reference_dt.date().isoformat()}
        """
        
        # If user replies, we feed that into the LLM logic
        user_prompt = (
            f"STARTER MESSAGE CONTENT:\n{starter_content}\n\n"
            f"RECENT THREAD HISTORY (newest last):\n{recent_history}\n\n"
            f"LATEST USER MESSAGE:\n{message.content}"
        )
        
        # If the user says "I edited it" or similar, we might need to fetch the starter message again
        # naive check or let LLM decide action="validate_edit"
        
        try:
            result_json = self.bot.llm.generate_completion(system_prompt, user_prompt, json_mode=True)
            response_data = json.loads(result_json)
        except Exception as e:
            self.logger.error(f"LLM Error: {e}")
            await message.channel.send("⚠️ Lo siento, estoy teniendo problemas técnicos para procesar tu solicitud en este momento. Por favor, inténtalo más tarde o contacta a soporte.")
            return

        action = response_data.get("action", "wait")
        feedback = response_data.get("feedback", "")
        extracted_data = response_data.get("data", {})

        # Execute Action
        if action == "approve":
            # Check if this thread already has a Notion task
            existing_notion_url = self._get_thread_state(thread_id).get("notion_url")
            
            if existing_notion_url:
                # Task already exists, don't create duplicate
                await self.send_status(
                    message.channel, 
                    True, 
                    f"Mi trabajo aquí está completo. La tarea ya fue creada en Notion: {existing_notion_url}\n\nEl equipo de diseño pronto comenzará a trabajar en tu solicitud usando este hilo. ¡Gracias!",
                    final_approved=True
                )
                # Update state to prevent further processing
                self._set_thread_state(thread_id, {"state": "approved", "notion_url": existing_notion_url})
                return
            
            # 1. Automate Task Creation
            project_raw = extracted_data.get("project")
            title = extracted_data.get("title", "Nueva Tarea de Diseño")
            deadline = extracted_data.get("deadline")  # ISO format YYYY-MM-DD or None
            thread_url = self._thread_link(message, thread_id)
            reference_dt = self._reference_datetime(message)
            deadline = self._normalize_deadline(deadline, reference_dt)

            project_options = self._get_project_options()
            project = self._match_project_option(project_raw, project_options)
            if not project:
                await self._request_project(message.channel, thread_id, project_raw, project_options)
                return
            
            # Fetch starter message for full context
            try:
                starter = await message.channel.fetch_message(thread_id)
                full_content = starter.content
            except:
                full_content = message.content
            
            # Create in Notion
            notion_url = self.bot.notion.create_task(
                self.notion_db_id, 
                title, 
                project,
                deadline=deadline,
                content=f"Solicitud original en Discord: {thread_url}\n\nDescripción:\n{full_content}",
                thread_url=thread_url
            )
            
            # Verify creation was successful
            if not notion_url:
                await message.channel.send(
                    "❌ Hubo un error al crear la tarea en Notion. Por favor intenta de nuevo o contacta al equipo de soporte."
                )
                return
            
            # Store the notion_url in state to prevent duplicates
            self._set_thread_state(thread_id, {"state": "approved", "notion_url": notion_url})
            
            # 2. Notify Design Team
            request_channel_id = 1207375472955232266
            request_channel = self.bot.get_channel(request_channel_id)
            if request_channel:
                await request_channel.send(
                    f"<@&1458178611382325412> **Nueva Solicitud de Diseño Aprobada**\n"
                    f"📂 **Proyecto:** {project}\n"
                    f"📝 **Tarea:** {title}\n"
                    f"🔗 **Notion:** {notion_url}\n"
                    f"💬 **Hilo:** {thread_url}"
                )

            # 3. User Feedback
            final_feedback = feedback
            final_feedback += f"\n\n✅ He creado la tarea en Notion por ti: {notion_url}"

            await self.send_status(message.channel, True, final_feedback, final_approved=True)

        elif action == "synthesize":
            # LLM has synthesized the information from chat history
            # Present it to the user for copy/paste
            await message.channel.send(feedback)
            self._set_thread_state(thread_id, {"state": "waiting_edit"})

        elif action == "create_task":
            # This action might become redundant if "approve" does it, 
            # but keep it for the flow where user explicitly asks after "offer_creation"
            project_raw = extracted_data.get("project")
            title = extracted_data.get("title")
            deadline = extracted_data.get("deadline")
            
            reference_dt = self._reference_datetime(message)
            deadline = self._normalize_deadline(deadline, reference_dt)

            project_options = self._get_project_options()
            project = self._match_project_option(project_raw, project_options)

            if project and title:
                thread_url = self._thread_link(message, thread_id)
                url = self.bot.notion.create_task(
                    self.notion_db_id,
                    title,
                    project,
                    deadline=deadline,
                    content=f"Creado manualmente desde hilo: {thread_url}",
                    thread_url=thread_url
                )
                if url:
                    await message.channel.send(f"✅ Tarea creada: {url}\nPor favor edita tu post original para incluir este link y avísame cuando esté listo.")
                    self._set_thread_state(thread_id, {"state": "waiting_edit"})
                else:
                    # Increment failure count
                    current_errors = self._get_thread_state(thread_id).get("notion_errors", 0) + 1
                    
                    if current_errors >= 2:
                        await message.channel.send(
                            "❌ No he podido crear la tarea automáticamente tras varios intentos.\n"
                            "Por favor, usa este formulario manual para darla de alta:\n"
                            "https://www.notion.so/emerald-dev/2fdd14a8642b80edb194deed54c6449e?pvs=106\n\n"
                            "Una vez creada, pega el link aquí."
                        )
                        # Reset to waiting for the link (or some neutral state)
                        self._set_thread_state(thread_id, {"state": "waiting_edit", "notion_errors": 0})
                    else:
                        await message.channel.send("❌ Error creando la tarea en Notion. Inténtalo de nuevo o revisa los datos.")
                        # Retain state but update errors
                        state_data = self._get_thread_state(thread_id) or {"state": "waiting_task_details"}
                        state_data["notion_errors"] = current_errors
                        self._set_thread_state(thread_id, state_data)
            else:
                if not project:
                    await self._request_project(message.channel, thread_id, project_raw, project_options)
                else:
                    await message.channel.send("No pude entender el título de la tarea. ¿Podrías repetirlo?")
                    self._set_thread_state(thread_id, {"state": "waiting_task_details"})

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
                    project_raw = data_2.get("project")
                    title = data_2.get("title", "Nueva Tarea de Diseño")
                    deadline = data_2.get("deadline")
                    thread_url = self._thread_link(message, thread_id)
                    reference_dt = self._reference_datetime(message)
                    deadline = self._normalize_deadline(deadline, reference_dt)

                    project_options = self._get_project_options()
                    project = self._match_project_option(project_raw, project_options)
                    if not project:
                        await self._request_project(message.channel, thread_id, project_raw, project_options)
                        return

                    # Create Notion
                    notion_url = self.bot.notion.create_task(
                        self.notion_db_id, 
                        title, 
                        project,
                        deadline=deadline,
                        content=f"Solicitud original en Discord (Intake): {thread_url}\n\nContenido:\n{starter.content}",
                        thread_url=thread_url
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
                    self._set_thread_state(thread_id, {"state": "waiting_delete"})
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
                 
             self._clear_thread_state(thread_id)

        elif action == "request_edit":
            await self.send_status(message.channel, False, feedback)
            self._set_thread_state(thread_id, {"state": "waiting_edit"})

        elif action == "handoff":
            # Post-approval handoff - bot is done, hand over to design team
            await message.channel.send(feedback)
            # Keep state as approved to prevent further processing

        else:
            # Generic reply or wait
            if feedback:
                await message.channel.send(feedback)

    async def _build_thread_context(self, channel: discord.Thread, thread_id: int, limit: int = 20):
        """Builds a compact context payload so the LLM can synthesize across the full conversation."""
        starter_content = ""
        recent_messages = []

        try:
            starter = await channel.fetch_message(thread_id)
            starter_content = starter.content or ""
        except Exception as e:
            self.logger.warning(f"Failed to fetch starter message: {e}")

        try:
            history_items = []
            async for m in channel.history(limit=limit, oldest_first=True):
                author = "BOT" if m.author == self.bot.user else "USER"
                content = (m.content or "").strip()

                if not content:
                    continue

                history_items.append(f"[{author}] {content}")

            recent_messages = history_items
        except Exception as e:
            self.logger.warning(f"Failed to read thread history: {e}")

        return starter_content, "\n".join(recent_messages)

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
