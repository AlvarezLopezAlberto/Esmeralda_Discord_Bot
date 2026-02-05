import os
from notion_client import Client
from dotenv import load_dotenv
import pprint

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
# Remove dashes if they cause issues, though the API usually handles both.
# The user provided URL has NO dashes: 9b1d386dbae1401b8a58af5a792e8f1f
# The user provided ID: 9b1d386dbae1401b8a58af5a792e8f1f
DATABASE_ID = "9b1d386dbae1401b8a58af5a792e8f1f"

if not NOTION_TOKEN:
    print("Error: NOTION_TOKEN not found.")
    exit(1)

client = Client(auth=NOTION_TOKEN)

PAGE_ID = "2fed14a8-642b-81d8-a9e8-dfcf1f46106b"

try:
    print(f"Inspecting Page: {PAGE_ID}")
    page = client.pages.retrieve(page_id=PAGE_ID)
    
    print("\n--- Page Properties (Schema Inference) ---")
    props = page.get("properties", {})
    for name, prop_val in props.items():
        prop_type = prop_val['type']
        print(f"Property: '{name}'")
        print(f"  Type: {prop_type}")
        
        # Print select options if available in the property definition usage (sometimes attached)
        # Note: 'properties' in a page object are Value objects, but sometimes contain context.
        # Actually, for Select/MultiSelect, the page value just shows the *selected* option.
        # But we need to know the *Type* mainly.
        
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error inspecting page: {e}")
