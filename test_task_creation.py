import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = "9b1d386dbae1401b8a58af5a792e8f1f"

if not NOTION_TOKEN:
    print("Error: NOTION_TOKEN not found.")
    exit(1)

client = Client(auth=NOTION_TOKEN)

try:
    print(f"Testing Task Creation in: {DATABASE_ID}")
    
    # Test with all fields
    new_page = client.pages.create(
        parent={"database_id": DATABASE_ID},
        properties={
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": "Test Task - Bot Integration Test"
                        }
                    }
                ]
            },
            "Proyecto": {
                "multi_select": [
                    {"name": "Test Project"}
                ]
            },
            "Fecha de entrega": {
                "date": {
                    "start": "2026-02-10"
                }
            }
        },
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "This is a test task created by the bot integration test. Context: Testing the new intake flow. Deliverables: Verify all fields populate correctly."
                            }
                        }
                    ]
                }
            }
        ]
    )
    print("✅ SUCCESS! Created test task:")
    print(f"URL: {new_page.get('url')}")
    print(f"ID: {new_page.get('id')}")
    print("\nPlease verify the task in Notion and delete it if needed.")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"❌ Error creating task: {e}")
