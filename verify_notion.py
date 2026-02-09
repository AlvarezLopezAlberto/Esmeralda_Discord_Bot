import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.notion import NotionHandler
import os
from dotenv import load_dotenv

load_dotenv()
notion = NotionHandler()
db_id = "9b1d386dbae1401b8a58af5a792e8f1f"
title_to_search = "Optimizar la UI de la versión mobile para las vistas de Jugadores y DTs."

print(f"Searching for task: '{title_to_search}'")
results = notion.search_pages(title_to_search)

if results:
    print(f"Found {len(results)} matches:")
    for r in results:
        print(f" - Title: {r['title']}")
        print(f"   URL: {r['url']}")
        print(f"   ID: {r['id']}")
else:
    print("No tasks found with that title.")
