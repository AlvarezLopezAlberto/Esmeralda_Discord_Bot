import os
from notion_client import Client
from typing import List, Dict, Optional

class NotionHandler:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("NOTION_TOKEN")
        self.client = None
        self._cache = {} # Simple in-memory cache: {query: (timestamp, results)}
        self._cache_ttl = 60 # Seconds
        if self.token:
            self.client = Client(auth=self.token)

    def is_enabled(self) -> bool:
        return self.client is not None

    def search_pages(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Searches for pages in Notion matching the query.
        Returns a list of dicts with 'id', 'title', 'url', 'icon'.
        """
        if not self.is_enabled():
            return []

        # Check Cache
        import time
        now = time.time()
        if query in self._cache:
            timestamp, cached_results = self._cache[query]
            if now - timestamp < self._cache_ttl:
                return cached_results

        try:
            response = self.client.search(
                query=query,
                filter={"value": "page", "property": "object"},
                page_size=limit
            )
            
            results = []
            for page in response.get("results", []):
                title = "Untitled"
                # Extract title safely
                props = page.get("properties", {})
                
                # Heuristic to find the title property (usually type "title")
                for _, prop_val in props.items():
                    if prop_val.get("type") == "title":
                        title_parts = prop_val.get("title", [])
                        if title_parts:
                            title = "".join([t.get("plain_text", "") for t in title_parts])
                        break
                
                # Icon
                icon = page.get("icon", {})
                icon_url = None
                if icon:
                    if icon.get("type") == "emoji":
                        icon_url = icon.get("emoji") # Not a URL, but a char
                    elif icon.get("type") == "external":
                        icon_url = icon.get("external", {}).get("url")
                    elif icon.get("type") == "file":
                        icon_url = icon.get("file", {}).get("url")

                results.append({
                    "id": page.get("id"),
                    "title": title,
                    "url": page.get("url"),
                    "icon": icon_url
                })
            
            # Update Cache
            self._cache[query] = (now, results)
            return results

        except Exception as e:
            print(f"Error searching Notion: {e}")
            return []

    @staticmethod
    def extract_page_id(url: str) -> Optional[str]:
        """
        Extracts the UUID from a Notion URL.
        Format usually: https://notion.so/Page-Title-<UUID>?...
        """
        import re
        # Match 32 hex chars or hyphenated UUID
        match = re.search(r'([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', url)
        if match:
            # Return without hyphens for consistency
            return match.group(1).replace("-", "")
        return None

    def get_page_info(self, page_id: str) -> Optional[Dict]:
        """
        Fetches a page by ID to get its title and URL.
        """
        if not self.is_enabled():
            return None

        try:
            page = self.client.pages.retrieve(page_id=page_id)
            
            # Extract title
            title = "Untitled"
            props = page.get("properties", {})
            for _, prop_val in props.items():
                if prop_val.get("type") == "title":
                    title_parts = prop_val.get("title", [])
                    if title_parts:
                        title = "".join([t.get("plain_text", "") for t in title_parts])
                    break
            
            # Extract Icon
            icon = page.get("icon", {})
            icon_url = None
            if icon:
                if icon.get("type") == "emoji":
                    icon_url = icon.get("emoji")
                elif icon.get("type") == "external":
                    icon_url = icon.get("external", {}).get("url")
                elif icon.get("type") == "file":
                    icon_url = icon.get("file", {}).get("url")

            return {
                "id": page.get("id"),
                "title": title,
                "url": page.get("url"),
                "icon": icon_url
            sys.stderr.write(f"Error fetching page {page_id}: {e}\n")
            return None

    def create_task(self, database_id: str, title: str, project: str) -> Optional[str]:
        """
        Creates a new task in the specified Notion database.
        Returns the URL of the created page or None.
        """
        if not self.is_enabled():
            return None

        try:
            properties = {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "Project": { # Assuming 'Project' is a simple text or select field. If Relation, this is harder.
                             # Based on "Project Name", it's likely a Select or Text. 
                             # We will try Text first or Rich Text.
                    "rich_text": [
                        {
                            "text": {
                                "content": project
                            }
                        }
                    ]
                }
                # Sprint and Date are handled by default/team as per instructions.
            }

            # NOTE: If 'Project' is a Relation or Select, this might fail.
            # Ideally we check the schema. But for now we try Rich Text/Title standard.
            
            new_page = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties
            )
            return new_page.get("url")
        except Exception as e:
            import sys
            sys.stderr.write(f"Error creating task: {e}\n")
            # Fallback: Try 'Project' as Select if Rich Text fails? 
            # Or maybe the key is 'Project Name'? 
            # Without schema inspection, this is a guess.
            return None
