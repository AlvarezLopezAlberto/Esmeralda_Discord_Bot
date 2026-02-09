import os
from notion_client import Client
from dotenv import load_dotenv
import pprint

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = "9b1d386dbae1401b8a58af5a792e8f1f"

if not NOTION_TOKEN:
    print("Error: NOTION_TOKEN not found.")
    exit(1)

client = Client(auth=NOTION_TOKEN)

try:
    print(f"Searching for tasks in DB: {DATABASE_ID}")
    # Search for pages with the title
    results = client.search(query="Optimizar la UI de la versión mobile", filter={"value": "page", "property": "object"})
    
    pages = results.get("results", [])
    if pages:
        print(f"Found {len(pages)} pages:")
        for p in pages:
            print(f" - Title: {p['url']}")
    else:
        print("No pages found.")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
