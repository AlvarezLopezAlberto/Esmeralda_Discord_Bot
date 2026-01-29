import discord
from discord.ext import commands
import os
from datetime import datetime, timedelta
from utils import domain_context
import json

class DailyLogCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def gather_messages_last_24h(self, guild):
        """
        Scans all text channels for messages from the last 24h.
        """
        cutoff = datetime.now() - timedelta(hours=24)
        data = {}
        
        # 1. Scan Text Channels
        for channel in guild.text_channels:
            if not channel.permissions_for(guild.me).read_messages:
                continue
            try:
                messages = []
                async for msg in channel.history(after=cutoff, limit=500):
                    if not msg.author.bot:
                        messages.append(f"{msg.author.name}: {msg.content}")
                if messages:
                    data[channel.name] = messages
            except Exception:
                pass
                
        # 2. Scan Active Threads
        try:
            active_threads = await guild.active_threads()
            for thread in active_threads:
                try:
                    t_messages = []
                    async for msg in thread.history(after=cutoff, limit=500):
                        if not msg.author.bot:
                            t_messages.append(f"{msg.author.name}: {msg.content}")
                    
                    if t_messages:
                        data[f"Thread: {thread.name} (in #{thread.parent.name})"] = t_messages
                except Exception as e:
                    print(f"Error reading thread {thread.name}: {e}")
                    
        except Exception as e:
            print(f"Error fetching threads for guild {guild.name}: {e}")
            
        return data

    def generate_daily_digest_content(self, channels_data):
        """
        Generates a Daily Log + Graph Nodes using LLM with Domain Context.
        """
        if not channels_data:
            return None

        # Prepare input text
        start_text = "ACTIVITY LOG (Last 24h):\n"
        for source, msgs in channels_data.items():
            start_text += f"\n## Channel/Source: {source}\n" + "\n".join(msgs[:50])

        # Get Domain Context
        context_str = domain_context.get_full_context()
        
        # Load Prompt
        system_prompt = "Eres un asistente operativo experto. Respondes en JSON."
        prompt_template = self.bot.llm.load_prompt("daily_log")
        
        if not prompt_template:
            return f"# Error: Prompt 'daily_log' not found.\n\n{start_text}"

        user_prompt = prompt_template.format(context_str=context_str) + "\n\n" + start_text

        # Generate
        result = self.bot.llm.generate_completion(system_prompt, user_prompt, json_mode=True)
        
        try:
            data = json.loads(result)
            
            # 1. Process Topics (Create Nodes)
            topics = data.get("topics", [])
            for item in topics:
                project = item.get("project", "General")
                topic = item.get("topic")
                summary = item.get("summary", "")
                
                if project and topic:
                    self.bot.obsidian.ensure_topic_node(topic, project, summary)
            
            # 2. Return the Daily Log Markdown
            return data.get("summary_markdown", "# Error: No content.")

        except Exception as e:
            return f"Error generating digest: {str(e)}"

    def generate_note_content(self, message_content, author, project_context):
        """
        Uses LLM to generate formatted Markdown content.
        """
        system_prompt = "You are a helpful operational assistant."
        prompt_template = self.bot.llm.load_prompt("create_note")
        
        if not prompt_template:
            return f"Error: Prompt 'create_note' not found.\n\n{message_content}"

        user_prompt = prompt_template.format(
            project_context=", ".join(project_context),
            author=author,
            message_content=message_content
        )
        
        return self.bot.llm.generate_completion(system_prompt, user_prompt)

    @commands.command(name='update')
    async def local_update(self, ctx):
        """
        Generates Daily Log for CURRENT server only.
        """
        status_msg = await ctx.send("🔄 Escaneando servidor actual...")
        g_data = await self.gather_messages_last_24h(ctx.guild)
        
        if not g_data:
            await status_msg.edit(content="❌ No hay mensajes recientes.")
            return

        await status_msg.edit(content="🧠 Analizando con IA (Contexto Solkos)...")

        content = self.generate_daily_digest_content(g_data)
        
        if content:
            title = f"Daily Log {datetime.now().strftime('%Y-%m-%d')} (Local)"
            path = self.bot.obsidian.create_note(title, content, folder="Inbox")
            if path:
                await status_msg.edit(content=f"✅ Daily Log Local creado: `{os.path.basename(path)}`")
        else:
            await status_msg.edit(content="❌ Error generando contenido.")

    @commands.command(name='update-all')
    async def global_update(self, ctx):
        await self.run_global_update(ctx)

    async def run_global_update(self, ctx=None):
        status_msg = None
        if ctx:
            status_msg = await ctx.send("🌍 Escaneando todos los servidores...")
        
        aggregated_data = {}
        for guild in self.bot.guilds:
            g_data = await self.gather_messages_last_24h(guild)
            for ch, msgs in g_data.items():
                aggregated_data[f"{guild.name} - #{ch}"] = msgs
                
        if not aggregated_data:
            if ctx: await status_msg.edit(content="❌ No hay mensajes recientes.")
            return

        if ctx: await status_msg.edit(content="🧠 Analizando con IA (Contexto Solkos)...")

        content = self.generate_daily_digest_content(aggregated_data)
        
        if content:
            title = f"Daily Log {datetime.now().strftime('%Y-%m-%d')}"
            path = self.bot.obsidian.create_note(title, content, folder="Inbox")
            if ctx: await status_msg.edit(content=f"✅ Daily Log creado: `{os.path.basename(path)}`")
        else:
            if ctx: await status_msg.edit(content="❌ Error generando contenido.")

    @commands.command(name='note')
    async def create_note(self, ctx, *, content):
        """
        Command: !note <text>
        Manually triggers note creation from the message content.
        """
        projects = self.bot.obsidian.get_existing_projects()
        status_msg = await ctx.send("Thinking... 🧠")
        
        ai_output = self.generate_note_content(content, ctx.author.name, projects)
        
        title = f"Discord Note - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        body = ai_output
        
        file_path = self.bot.obsidian.create_note(title, body, folder="Inbox")
        
        if file_path:
            await status_msg.edit(content=f"✅ Note created: `{os.path.basename(file_path)}`")
        else:
            await status_msg.edit(content="❌ Failed to create note.")

async def setup(bot):
    await bot.add_cog(DailyLogCog(bot))
