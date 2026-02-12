"""
Test Conversation Memory Skill

Tests for the ConversationMemorySkill using unittest instead of pytest.
"""

import unittest
from unittest.mock import Mock, AsyncMock
import os
import sys
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.design.skills.conversation_memory import ConversationMemorySkill
from src.skills.base import SkillContext


class MockLLMHandler:
    """Mock LLM handler for testing."""
    
    def generate_completion(self, system_prompt, user_prompt, json_mode=False):
        """Mock LLM completion."""
        return """## Summary 1 (Messages 1-20)
**Period**: 2026-02-12T10:00:00 - 2026-02-12T10:30:00
**Generated**: 2026-02-12T10:30:00

### Agreements & Decisions
- **[2026-02-12T10:05:00] @user1**: Agreed to complete the design by Friday
- **[2026-02-12T10:10:00] BOT**: Confirmed project scope

### Deadlines & Time Commitments
- **Deadline: 2026-02-14** - Design mockups (Mentioned by @user1 at 2026-02-12T10:05:00)

### Commitments & Action Items
- **@user1 (2026-02-12T10:15:00)**: Will provide assets by tomorrow

### Key Discussion Points
- **Project Setup**: Discussed between 10:00:00 - 10:20:00
  - @user1: Needs help with intake form
  - BOT: Explained required fields
"""


class TestConversationMemorySkill(unittest.IsolatedAsyncioTestCase):
    """Test suite for ConversationMemorySkill."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.memory_dir = os.path.join(self.temp_dir, "memory", "threads")
        os.makedirs(self.memory_dir, exist_ok=True)
        
        self.mock_llm = MockLLMHandler()
        self.skill = ConversationMemorySkill(self.mock_llm, memory_base_path=self.memory_dir)
        
        # Sample messages for testing
        self.sample_messages = []
        for i in range(20):
            self.sample_messages.append({
                "author": f"@user{i % 3}",
                "content": f"Test message {i + 1}",
                "timestamp": f"2026-02-12T10:{i:02d}:00"
            })
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    async def test_should_create_summary_threshold(self):
        """Test summary threshold detection."""
        context = SkillContext()
        
        # Should not create at 19 messages
        result = await self.skill.should_create_summary(context, 19, 0)
        self.assertFalse(result)
        
        # Should create at 20 messages
        result = await self.skill.should_create_summary(context, 20, 0)
        self.assertTrue(result)
        
        # Should not create at 25 messages if last was at 20
        result = await self.skill.should_create_summary(context, 25, 20)
        self.assertFalse(result)
        
        # Should create at 40 messages if last was at 20
        result = await self.skill.should_create_summary(context, 40, 20)
        self.assertTrue(result)
    
    async def test_memory_file_creation(self):
        """Test that memory file is created with correct structure."""
        context = SkillContext()
        thread_id = 123456789
        
        # Execute skill to create summary
        result = await self.skill.execute(
            context,
            thread_id=thread_id,
            messages=self.sample_messages,
            thread_title="Test Thread",
            current_count=20,
            last_summary_count=0
        )
        
        # Verify file was created
        self.assertIsNotNone(result)
        memory_file = Path(result)
        self.assertTrue(memory_file.exists())
        
        # Verify file structure
        content = memory_file.read_text()
        self.assertIn("# Thread Memory: Test Thread", content)
        self.assertIn(f"Thread ID: {thread_id}", content)
        self.assertIn("Summary 1", content)
    
    async def test_no_summary_below_threshold(self):
        """Test that no summary is created below threshold."""
        context = SkillContext()
        thread_id = 123456789
        
        # Only 10 messages - below threshold
        messages = [
            {"author": "@user1", "content": f"Message {i}", "timestamp": f"2026-02-12T10:{i:02d}:00"}
            for i in range(10)
        ]
        
        result = await self.skill.execute(
            context,
            thread_id=thread_id,
            messages=messages,
            current_count=10,
            last_summary_count=0
        )
        
        # No summary should be created
        self.assertIsNone(result)
    
    async def test_load_memory(self):
        """Test loading existing memory."""
        context = SkillContext()
        thread_id = 987654321
        
        # Create a summary first
        await self.skill.execute(
            context,
            thread_id=thread_id,
            messages=self.sample_messages,
            thread_title="Test Thread",
            current_count=20,
            last_summary_count=0
        )
        
        # Load the memory
        loaded = await self.skill.load_memory(thread_id)
        
        self.assertIsNotNone(loaded)
        self.assertIn("Test Thread", loaded)
        self.assertIn(f"Thread ID: {thread_id}", loaded)
        self.assertIn("Summary 1", loaded)
    
    async def test_load_nonexistent_memory(self):
        """Test loading memory for thread without memory file."""
        loaded = await self.skill.load_memory(999999999)
        self.assertIsNone(loaded)
    
    async def test_incremental_summaries(self):
        """Test that multiple summaries are appended correctly."""
        context = SkillContext()
        thread_id = 111222333
        
        # Create first batch of messages (1-20)
        messages_1 = [
            {"author": "@user1", "content": f"Message {i}", "timestamp": f"2026-02-12T10:{i:02d}:00"}
            for i in range(1, 21)
        ]
        
        # Create first summary
        await self.skill.execute(
            context,
            thread_id=thread_id,
            messages=messages_1,
            thread_title="Incremental Test",
            current_count=20,
            last_summary_count=0
        )
        
        # Create second batch of messages (21-40)
        messages_2 = [
            {"author": "@user2", "content": f"Message {i}", "timestamp": f"2026-02-12T11:{i-20:02d}:00"}
            for i in range(21, 41)
        ]
        
        # Create second summary
        await self.skill.execute(
            context,
            thread_id=thread_id,
            messages=messages_2,
            thread_title="Incremental Test",
            current_count=40,
            last_summary_count=20
        )
        
        # Load and verify both summaries exist
        loaded = await self.skill.load_memory(thread_id)
        self.assertIsNotNone(loaded)
        # At least 2 summary sections should exist
        self.assertGreaterEqual(loaded.count("Summary"), 2)
    
    async def test_validate_input(self):
        """Test input validation."""
        context = SkillContext()
        
        # Valid input
        valid = await self.skill.validate_input(
            context,
            thread_id=123,
            messages=[{"author": "@user", "content": "test", "timestamp": "2026-02-12T10:00:00"}]
        )
        self.assertTrue(valid)
        
        # Missing thread_id
        invalid1 = await self.skill.validate_input(context, messages=[])
        self.assertFalse(invalid1)
        
        # Missing messages
        invalid2 = await self.skill.validate_input(context, thread_id=123)
        self.assertFalse(invalid2)
        
        # Invalid messages format
        invalid3 = await self.skill.validate_input(context, thread_id=123, messages="not a list")
        self.assertFalse(invalid3)


if __name__ == "__main__":
    unittest.main()
