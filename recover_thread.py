import discord
import os
import sys
import asyncio
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append(os.path.join(os.getcwd(), "src"))
from services.notion import NotionHandler

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
NOTION_DB_ID = "9b1d386dbae1401b8a58af5a792e8f1f"
THREAD_ID = 1470470960841756837

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

client = discord.Client(intents=intents)
notion = NotionHandler()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    
    try:
        thread = await client.fetch_channel(THREAD_ID)
        print(f"Working on thread: {thread.name}")
        
        # 1. Create Notion Task
        title = "Optimizar la UI de la versión mobile para las vistas de Jugadores y DTs."
        project = "Caskrapp"  # Inferred from content
        deadline = "2026-02-18"  # Extracted from the bot message: "18 de febrero"
        content = f"Creado manualmente por Esmeralda para recuperar solicitud.\n\nHilo original: {thread.jump_url}"
        
        print(f"Creating Notion task: {title}")
        notion_url = notion.create_task(
            NOTION_DB_ID,
            title,
            project,
            deadline=deadline,
            content=content
        )
        
        if notion_url:
            print(f"✅ Notion task created: {notion_url}")
            
            # 2. Re-trigger validation message to user
            # We want them to edit the starter message.
            msg = f"""✅ **¡He creado la tarea en Notion por ti!**
🔗 Link: {notion_url}

⚠️ **IMPORTANTE**: Debido a un conflicto previo con el bot de links, el mensaje original de este hilo fue reemplazado. 

**Para que el registro sea perfecto, por favor @Alberto Alvarez:**
1. Copia el contenido de arriba (Contexto, Alcance, Deadline).
2. Edita el **mensaje inicial** de este hilo (el que está arriba del todo) y pega la información ahí.
3. Esto asegurará que el equipo de diseño tenga toda la información a la mano.

¡Gracias por tu paciencia!"""
            
            # Send as an embed or simple message? Let's use embed to look official.
            embed = discord.Embed(
                title="Design Intake Quality Gate",
                description=msg,
                color=discord.Color.green()
            )
            embed.set_footer(text="✅ PROCESO RECUPERADO")
            
            await thread.send(embed=embed)
            print("✅ Handoff message sent.")
        else:
            print("❌ Failed to create Notion task.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    await client.close()

client.run(TOKEN)
