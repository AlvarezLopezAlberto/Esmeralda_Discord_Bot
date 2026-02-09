import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = "9b1d386dbae1401b8a58af5a792e8f1f"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Search for the page
url = "https://api.notion.com/v1/search"
params = {
    "query": "Optimizar la UI de la versión mobile",
    "filter": {
        "value": "page",
        "property": "object"
    }
}

response = requests.post(url, headers=headers, json=params)
if response.status_code == 200:
    data = response.json()
    results = data.get("results", [])
    if results:
        print(f"Found {len(results)} pages:")
        for r in results:
            print(f" - {r.get('url')}")
    else:
        print("No pages found.")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
