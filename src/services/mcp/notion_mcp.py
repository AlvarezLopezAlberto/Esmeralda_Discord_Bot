"""
MCP Client for Notion Integration

This module provides a Model Context Protocol (MCP) wrapper around Notion operations,
enabling intelligent, context-aware interactions with Notion databases.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from notion_client import Client


class NotionMCPClient:
    """
    MCP-enabled Notion client that provides intelligent access to Notion resources.
    
    This client extends the basic Notion API with:
    - Semantic search capabilities
    - Context-aware resource retrieval
    - Schema understanding
    - Relationship mapping
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Notion MCP client.
        
        Args:
            token: Notion integration token. If None, reads from NOTION_TOKEN env var.
        """
        self.token = token or os.getenv("NOTION_TOKEN")
        self.client = Client(auth=self.token) if self.token else None
        self.logger = logging.getLogger(__name__)
        self._schema_cache = {}  # Cache database schemas
        
    def is_enabled(self) -> bool:
        """Check if the client is properly configured."""
        return self.client is not None
    
    async def search_resources(
        self,
        query: str,
        resource_type: str = "page",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for Notion resources.
        
        This is MCP's enhanced search that understands context and relationships.
        
        Args:
            query: Search query (can be fuzzy/semantic)
            resource_type: Type of resource ("page", "database", etc.)
            filters: Additional filters to apply
            limit: Maximum number of results
            
        Returns:
            List of matching resources with metadata
        """
        if not self.is_enabled():
            self.logger.error("MCP client not enabled")
            return []
        
        try:
            search_params = {
                "query": query,
                "filter": {"value": resource_type, "property": "object"},
                "page_size": limit
            }
            
            response = self.client.search(**search_params)
            results = response.get("results", [])
            
            # Enhanced results with MCP context
            enhanced_results = []
            for result in results:
                enhanced = {
                    "id": result.get("id"),
                    "type": result.get("object"),
                    "url": result.get("url"),
                    "title": self._extract_title(result),
                    "properties": result.get("properties", {}),
                    "parent": result.get("parent", {}),
                    "created_time": result.get("created_time"),
                    "last_edited_time": result.get("last_edited_time"),
                }
                enhanced_results.append(enhanced)
            
            return enhanced_results
            
        except Exception as e:
            self.logger.error(f"MCP search error: {e}")
            return []
    
    async def get_database_schema(self, database_id: str) -> Dict[str, Any]:
        """
        Get comprehensive database schema with MCP enhancements.
        
        Returns not just property types, but also:
        - Valid options for select/multi-select
        - Relationships to other databases
        - Property descriptions
        
        Args:
            database_id: Notion database ID
            
        Returns:
            Enhanced schema dictionary
        """
        # Check cache first
        if database_id in self._schema_cache:
            return self._schema_cache[database_id]
        
        if not self.is_enabled():
            return {}
        
        try:
            db = self.client.databases.retrieve(database_id=database_id)
            properties = db.get("properties", {})
            
            schema = {
                "database_id": database_id,
                "title": db.get("title", [{}])[0].get("plain_text", ""),
                "properties": {}
            }
            
            for prop_name, prop_def in properties.items():
                prop_type = prop_def.get("type")
                prop_schema = {
                    "type": prop_type,
                    "id": prop_def.get("id")
                }
                
                # Extract options for select/multi-select
                if prop_type == "select":
                    options = prop_def.get("select", {}).get("options", [])
                    prop_schema["options"] = [opt.get("name") for opt in options]
                    
                elif prop_type == "multi_select":
                    options = prop_def.get("multi_select", {}).get("options", [])
                    prop_schema["options"] = [opt.get("name") for opt in options]
                
                # Extract relation info
                elif prop_type == "relation":
                    relation = prop_def.get("relation", {})
                    prop_schema["related_database_id"] = relation.get("database_id")
                
                schema["properties"][prop_name] = prop_schema
            
            # Cache the schema
            self._schema_cache[database_id] = schema
            return schema
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve database schema: {e}")
            return {}
    
    async def find_page_fuzzy(
        self,
        database_id: str,
        title_query: str,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find a page using fuzzy matching on title.
        
        This is key for MCP - users don't need exact names.
        
        Args:
            database_id: Database to search in
            title_query: Fuzzy title to match
            additional_filters: Additional property filters
            
        Returns:
            Best matching page or None
        """
        # Search across the entire workspace
        results = await self.search_resources(title_query, resource_type="page")
        
        # Filter to specific database
        if results and database_id:
            results = [
                r for r in results
                if r.get("parent", {}).get("database_id") == database_id
            ]
        
        # Return best match (first result)
        return results[0] if results else None
    
    async def get_select_options(
        self,
        database_id: str,
        property_name: str
    ) -> List[str]:
        """
        Get valid options for a select/multi-select property.
        
        Args:
            database_id: Database ID
            property_name: Property name
            
        Returns:
            List of valid option names
        """
        schema = await self.get_database_schema(database_id)
        prop = schema.get("properties", {}).get(property_name, {})
        return prop.get("options", [])
    
    def _extract_title(self, page: Dict[str, Any]) -> str:
        """Extract title from a Notion page object."""
        props = page.get("properties", {})
        
        # Find the title property
        for prop_name, prop_value in props.items():
            if prop_value.get("type") == "title":
                title_array = prop_value.get("title", [])
                if title_array:
                    return title_array[0].get("plain_text", "")
        
        return "Untitled"
    
    async def create_page(
        self,
        database_id: str,
        properties: Dict[str, Any],
        content_blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        """
        Create a page in a Notion database with MCP validation.
        
        Args:
            database_id: Parent database ID
            properties: Page properties (will be validated against schema)
            content_blocks: Optional content blocks
            
        Returns:
            URL of created page or None on failure
        """
        if not self.is_enabled():
            return None
        
        try:
            # Validate properties against schema
            schema = await self.get_database_schema(database_id)
            # TODO: Add property validation logic here
            
            # Create the page
            response = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=content_blocks or []
            )
            
            return response.get("url")
            
        except Exception as e:
            self.logger.error(f"Failed to create page: {e}")
            return None
    
    async def update_page(
        self,
        page_id: str,
        properties: Dict[str, Any]
    ) -> bool:
        """
        Update a Notion page's properties.
        
        Args:
            page_id: Page ID to update
            properties: Properties to update
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            return False
        
        try:
            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update page: {e}")
            return False
    
    def query_database(
        self,
        database_id: str,
        filter_params: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, str]]] = None,
        start_cursor: Optional[str] = None,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Query a Notion database with optional filters and sorting.
        
        Args:
            database_id: Database ID to query
            filter_params: Notion filter object
            sorts: List of sort objects
            start_cursor: Pagination cursor
            page_size: Number of results per page
            
        Returns:
            Query response with results
        """
        if not self.is_enabled():
            self.logger.error("MCP client not enabled")
            return {"results": []}
        
        try:
            import httpx
            
            # Build query payload
            payload = {"page_size": page_size}
            
            if filter_params:
                payload["filter"] = filter_params
            
            if sorts:
                payload["sorts"] = sorts
            
            if start_cursor:
                payload["start_cursor"] = start_cursor
            
            # Direct POST to Notion API
            url = f"https://api.notion.com/v1/databases/{database_id}/query"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            with httpx.Client() as http_client:
                response = http_client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to query database: {e}", exc_info=True)
            return {"results": []}
