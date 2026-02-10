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

    def _get_database_properties(self, database_id: str) -> Dict:
        if not self.is_enabled():
            return {}

        import time
        cache_key = f"db_props:{database_id}"
        now = time.time()
        if cache_key in self._cache:
            timestamp, cached_results = self._cache[cache_key]
            if now - timestamp < self._cache_ttl:
                return cached_results or {}

        try:
            db = self.client.databases.retrieve(database_id=database_id)
            props = db.get("properties", {}) or {}
            self._cache[cache_key] = (now, props)
            return props
        except Exception as e:
            print(f"Error retrieving Notion database properties: {e}")
            return {}

    def ensure_database_property(self, database_id: str, property_name: str, property_type: str = "url") -> bool:
        if not self.is_enabled():
            return False

        props = self._get_database_properties(database_id)
        if property_name in props:
            return True

        try:
            self.client.databases.update(
                database_id=database_id,
                properties={property_name: {property_type: {}}}
            )
            # Bust cache
            self._cache.pop(f"db_props:{database_id}", None)
            return True
        except Exception as e:
            print(f"Error updating Notion database with property '{property_name}': {e}")
            return False

    def set_page_property(self, page_id: str, property_name: str, property_type: str, value: str) -> bool:
        if not self.is_enabled():
            return False

        try:
            if property_type == "url":
                properties = {property_name: {"url": value}}
            elif property_type == "rich_text":
                properties = {property_name: {"rich_text": [{"text": {"content": value}}]}}
            else:
                return False

            self.client.pages.update(page_id=page_id, properties=properties)
            return True
        except Exception as e:
            print(f"Error updating Notion page property '{property_name}': {e}")
            return False

    def update_task_with_thread_link(
        self,
        database_id: str,
        page_id: str,
        thread_url: str,
        property_name: str = "Discord Thread"
    ) -> bool:
        if not self.is_enabled():
            return False

        if not thread_url:
            return False

        props = self._get_database_properties(database_id)
        prop_info = props.get(property_name)

        if not prop_info:
            if not self.ensure_database_property(database_id, property_name, "url"):
                return False
            prop_type = "url"
        else:
            prop_type = prop_info.get("type")

        if prop_type not in {"url", "rich_text"}:
            print(f"Unsupported property type for '{property_name}': {prop_type}")
            return False

        return self.set_page_property(page_id, property_name, prop_type, thread_url)

    def find_task_by_discord_thread(
        self,
        database_id: str,
        guild_id: int,
        thread_id: int,
        property_name: str = "Discord Thread",
        require_property: bool = True
    ) -> Optional[str]:
        """
        Searches Notion for a page containing the Discord thread link and belonging to the given database.
        Returns the page URL if found.
        """
        if not self.is_enabled():
            return None

        if not guild_id or not thread_id:
            return None

        import time
        exact_thread_url = f"https://discord.com/channels/{guild_id}/{thread_id}/{thread_id}"
        search_query = f"discord.com/channels/{guild_id}/{thread_id}"
        cache_key = f"thread:{database_id}:{exact_thread_url}"
        now = time.time()
        if cache_key in self._cache:
            timestamp, cached_results = self._cache[cache_key]
            if now - timestamp < self._cache_ttl:
                return cached_results

        try:
            props = self._get_database_properties(database_id)
            prop_info = props.get(property_name)
            if prop_info:
                prop_type = prop_info.get("type")
                if prop_type == "url":
                    filter_payload = {"property": property_name, "url": {"equals": exact_thread_url}}
                elif prop_type == "rich_text":
                    filter_payload = {"property": property_name, "rich_text": {"equals": exact_thread_url}}
                else:
                    filter_payload = None

                if filter_payload:
                    response = self.client.databases.query(
                        database_id=database_id,
                        filter=filter_payload,
                        page_size=1
                    )
                    results = response.get("results", [])
                    if results:
                        notion_url = results[0].get("url")
                        self._cache[cache_key] = (now, notion_url)
                        return notion_url
            elif require_property:
                self._cache[cache_key] = (now, None)
                return None

            if require_property:
                self._cache[cache_key] = (now, None)
                return None

            response = self.client.search(
                query=search_query,
                filter={"value": "page", "property": "object"},
                page_size=10
            )

            notion_url = None
            for page in response.get("results", []):
                parent = page.get("parent", {})
                if parent.get("type") == "database_id" and parent.get("database_id") == database_id:
                    notion_url = page.get("url")
                    break

            self._cache[cache_key] = (now, notion_url)
            return notion_url
        except Exception as e:
            print(f"Error searching Notion for thread URL: {e}")
            return None

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
            }
        except Exception as e:
            import sys
            sys.stderr.write(f"Error fetching page {page_id}: {e}\n")
            return None

    def create_task(
        self,
        database_id: str,
        title: str,
        project: str,
        deadline: Optional[str] = None,
        content: Optional[str] = None,
        thread_url: Optional[str] = None,
        thread_property_name: str = "Discord Thread"
    ) -> Optional[str]:
        """
        Creates a new task in the specified Notion database.
        Returns the URL of the created page or None.
        Matches schema:
        - Name (title)
        - Proyecto (multi_select)
        - Fecha de entrega (date)
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
                }
            }

            if project and project != "Sin Proyecto":
                properties["Proyecto"] = {
                    "multi_select": [
                        {"name": project}
                    ]
                }
            
            if deadline:
                # Assuming deadline string is ISO 8601 or YYYY-MM-DD
                # If LLM extracts "next friday", we might need to parse it. 
                # For now, we assume the agent passes a valid date string or we skip it if invalid format logic is needed.
                # But simple string is robust if standardized.
                properties["Fecha de entrega"] = {
                    "date": {
                        "start": deadline
                    }
                }

            if thread_url:
                if self.ensure_database_property(database_id, thread_property_name, "url"):
                    properties[thread_property_name] = {
                        "url": thread_url
                    }

            children = []
            if content:
                # Add content as children blocks (Paragraph)
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content[:2000] # Truncate to avoid Notion limit
                                }
                            }
                        ]
                    }
                })
            
            new_page = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=children
            )
            return new_page.get("url")
        except Exception as e:
            import sys
            sys.stderr.write(f"Error creating task in Notion: {e}\n")
            return None

    def delete_page(self, page_id: str) -> bool:
        """
        Archives (deletes) a page in Notion by ID.
        Returns True if successful, False otherwise.
        """
        if not self.is_enabled():
            return False

        try:
            self.client.pages.update(page_id=page_id, archived=True)
            return True
        except Exception as e:
            import sys
            sys.stderr.write(f"Error deleting page {page_id}: {e}\n")
            return False
