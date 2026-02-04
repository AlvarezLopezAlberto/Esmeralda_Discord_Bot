import os
from notion_client import Client
from dotenv import load_dotenv
import pprint

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
# Remove dashes if they cause issues, though the API usually handles both.
# The user provided URL has NO dashes: 9b1d386dbae1401b8a58af5a792e8f1f
# BUT that seems to be a Linked View. The source is: 30dfa1b3-8ea3-44ba-88cd-51f753863606
DATABASE_ID = "30dfa1b3-8ea3-44ba-88cd-51f753863606"

if not NOTION_TOKEN:
    print("Error: NOTION_TOKEN not found.")
    exit(1)

client = Client(auth=NOTION_TOKEN)

try:
    print(f"Retrieving Database Schema: {DATABASE_ID}")
    db = client.databases.retrieve(database_id=DATABASE_ID)
    import pprint
    pprint.pprint(db)
    print("\n--- Database Properties Schema ---")
    for name, prop in db["properties"].items():
        print(f"Property: '{name}'")
        print(f"  Type: {prop['type']}")
        if prop['type'] == 'select':
             print(f"  Options: {[opt['name'] for opt in prop['select']['options']]}")
        elif prop['type'] == 'multi_select':
             print(f"  Options: {[opt['name'] for opt in prop['multi_select']['options']]}")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
