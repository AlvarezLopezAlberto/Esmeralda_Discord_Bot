
import os
import sys
from dotenv import load_dotenv
import time
import pprint

# Add src to path so we can import services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from services.notion import NotionHandler

def test_crud():
    load_dotenv()
    
    # 1. Initialize
    print("--- Initializing Notion Handler ---")
    handler = NotionHandler()
    if not handler.is_enabled():
        print("❌ Error: Notion is not enabled. Check NOTION_TOKEN.")
        return

    # Use the clean ID from user URL
    DATABASE_ID = "9b1d386dbae1401b8a58af5a792e8f1f"
    
    # 2. Inspect Schema
    print(f"\n--- Inspecting Database {DATABASE_ID} ---")
    try:
        # We access the underlying client directly for inspection
        db_info = handler.client.databases.retrieve(user_id=None, database_id=DATABASE_ID)
        properties = db_info.get("properties", {})
        print(f"Found {len(properties)} properties:")
        for name, prop in properties.items():
            print(f" - {name} ({prop['type']})")
            
    except Exception as e:
        print(f"❌ Error retrieving database: {e}")
        return

    # 3. Construct Payload based on valid properties
    print(f"\n--- Inserting Test Page ---")
    title = "Prueba Antigravity"
    
    # Base properties (Name is usually required/standard)
    # Finding the Title property name
    title_prop_name = "Name"
    for name, prop in properties.items():
        if prop['type'] == 'title':
            title_prop_name = name
            break
            
    payload_props = {
        title_prop_name: {
            "title": [
                {
                    "text": {
                        "content": title
                    }
                }
            ]
        }
    }
    
    # Add other check items if they exist as checkboxes or select
    # This is a minimal insert to verify connection.
    # We purposefully exclude "Project" and "Sprint" unless we are sure they exist and are simple.
    # If the user wants specific fields, we might need to look for them.
    
    # Testing for "Status" or similar if available, otherwise just Title
    
    try:
        new_page = handler.client.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=payload_props,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "Test page created by Antigravity automation."
                                }
                            }
                        ]
                    }
                }
            ]
        )
        page_url = new_page.get("url")
        page_id = new_page.get("id")
        print(f"✅ Success! Created Page: {page_url}")
        print(f"   Page ID: {page_id}")
        
    except Exception as e:
        print(f"❌ Failed to create page: {e}")
        return

    # Wait a bit
    time.sleep(2)

    # 4. Delete
    print(f"\n--- Deleting Page {page_id} ---")
    success = handler.delete_page(page_id)
    
    if success:
        print("✅ Success! Page deleted (archived).")
    else:
        print("❌ Failed to delete page.")

if __name__ == "__main__":
    test_crud()
