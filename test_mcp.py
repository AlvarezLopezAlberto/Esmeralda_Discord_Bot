#!/usr/bin/env python3
"""
Test script to verify Notion MCP connection and database queries
"""

import sys
import os
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.mcp.notion_mcp import NotionMCPClient

# Load environment
load_dotenv()

def test_mcp_connection():
    """Test MCP client in connection."""
    print("🧪 Testing Notion MCP Client...")
    
    client = NotionMCPClient()
    
    if not client.is_enabled():
        print("❌ MCP Client not enabled - check NOTION_TOKEN")
        return False
    
    print("✅ MCP Client initialized")
    return True

def test_database_query():
    """Test database query with filters."""
    print("\n🔍 Testing database query...")
    
    client = NotionMCPClient()
    database_id = "9b1d386dbae1401b8a58af5a792e8f1f"  # Growth & Strategy
    
    # Test 1: Query all tasks
    print(f"\n📋 Querying database {database_id}...")
    result = client.query_database(database_id)
    
    total_tasks = len(result.get("results", []))
    print(f"   Total tasks found: {total_tasks}")
    
    if total_tasks > 0:
        print(f"   ✅ Successfully retrieved {total_tasks} tasks")
        # Show first task
        first_task = result["results"][0]
        props = first_task.get("properties", {})
        title = props.get("Nombre", {}).get("title", [{}])[0].get("plain_text", "No title")
        status = props.get("Status", {}).get("status", {}).get("name", "No status")
        print(f"   First task: '{title}' - Status: {status}")
    else:
        print(f"   ⚠️  No tasks found in database")
    
    # Test 2: Query backlog (Pendiente or unassigned)
    print(f"\n📋 Querying backlog (Status=Pendiente OR Asignado a=empty)...")
    backlog_filter = {
        "or": [
            {
                "property": "Status",
                "status": {
                    "equals": "Pendiente"
                }
            },
            {
                "property": "Asignado a",
                "people": {
                    "is_empty": True
                }
            }
        ]
    }
    
    backlog_result = client.query_database(database_id, filter_params=backlog_filter)
    backlog_count = len(backlog_result.get("results", []))
    print(f"   Backlog tasks: {backlog_count}")
    
    # Test 3: Query active tasks (for capacity)
    print(f"\n📋 Querying active tasks...")
    active_filter = {
        "property": "Status",
        "status": {
            "does_not_equal": "Completada"
        }
    }
    
    active_result = client.query_database(database_id, filter_params=active_filter)
    active_count = len(active_result.get("results", []))
    print(f"   Active tasks: {active_count}")
    
    # Show workload distribution
    if active_count > 0:
        print("\n👥 Workload distribution:")
        workload = {}
        for task in active_result["results"]:
            assigned = task.get("properties", {}).get("Asignado a", {}).get("people", [])
            if assigned:
                for person in assigned:
                    name = person.get("name", "Unknown")
                    workload[name] = workload.get(name, 0) + 1
            else:
                workload["Unassigned"] = workload.get("Unassigned", 0) + 1
        
        for person, count in sorted(workload.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {person}: {count} tasks")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("NOTION MCP VERIFICATION TEST")
    print("=" * 60)
    
    if not test_mcp_connection():
        sys.exit(1)
    
    if not test_database_query():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
