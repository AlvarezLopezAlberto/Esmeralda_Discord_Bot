import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = "9b1d386d-bae1-401b-8a58-af5a792e8f1f"

if not NOTION_TOKEN:
    print("Error: NOTION_TOKEN not found.")
    exit(1)

client = Client(auth=NOTION_TOKEN)

try:
    # Manual request since .query() is missing
    response = client.request(
        path=f"databases/{DATABASE_ID}/query", 
        method="POST", 
        body={"page_size": 1}
    )
    
    if response["results"]:
        page = response["results"][0]
        print("Page Properties found:")
        for name, prop in page["properties"].items():
            print(f"- {name}: {prop['type']}")
            if prop['type'] == 'select':
                if prop['select']:
                    print(f"  Current Value: {prop['select']['name']}")
                else:
                    print(f"  Current Value: None")
            elif prop['type'] == 'relation':
                 print(f"  Relation ID: {prop['id']}")
            elif prop['type'] == 'title':
                 print(f"  (Title Field)")
            elif prop['type'] == 'rich_text':
                 print(f"  (Rich Text)")
            elif prop['type'] == 'multi_select':
                 print(f"  (Multi-Select)")
    else:
        print("No pages found in database to inspect.")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
