"""
Test basic imports and module structure for MCP + Skills system.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_imports():
    """Test that all new modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test MCP imports
        from src.services.mcp import NotionMCPClient
        print("✅ NotionMCPClient imported successfully")
        
        # Test Skills base imports
        from src.skills.base import BaseSkill, SkillContext, SkillRegistry, SkillExecutor
        print("✅ Skills base classes imported successfully")
        
        # Test Design skills imports
        from agents.design.skills import (
            ValidateIntakeSkill,
            ExtractNotionURLSkill,
            MatchProjectSkill,
            CreateNotionTaskSkill,
            UpdateTaskStatusSkill,
            create_design_skills_registry
        )
        print("✅ Design skills imported successfully")
        
        print("\n✅ ALL IMPORTS SUCCESSFUL!")
        return True
        
    except ImportError as e:
        print(f"\n❌ IMPORT ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_skill_registry():
    """Test skill registry creation."""
    print("\nTesting skill registry...")
    
    try:
        from src.skills.base import SkillRegistry, BaseSkill
        
        # Create registry
        registry = SkillRegistry()
        
        # Create a simple test skill
        class TestSkill(BaseSkill):
            def __init__(self):
                super().__init__("test_skill", "A test skill")
            
            async def execute(self, context, **kwargs):
                return "success"
        
        # Register skill
        skill = TestSkill()
        registry.register(skill)
        
        # Verify registration
        assert registry.get("test_skill") == skill
        assert "test_skill" in registry.list_names()
        
        print("✅ Skill registry works correctly")
        return True
        
    except Exception as e:
        print(f"❌ REGISTRY ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_client():
    """Test MCP client initialization."""
    print("\nTesting MCP client...")
    
    try:
        from src.services.mcp import NotionMCPClient
        
        # Initialize (may not work without token, but should not crash)
        client = NotionMCPClient()
        
        # Check basic methods exist
        assert hasattr(client, 'search_resources')
        assert hasattr(client, 'get_database_schema')
        assert hasattr(client, 'find_page_fuzzy')
        
        print("✅ MCP client initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ MCP CLIENT ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("MCP + Skills Integration Tests")
    print("=" * 50)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Skill Registry", test_skill_registry()))
    results.append(("MCP Client", test_mcp_client()))
    
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)
