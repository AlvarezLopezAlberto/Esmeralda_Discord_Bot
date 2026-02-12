"""
Test suite for PM Agent Skills

Tests all PM agent skills with realistic scenarios.
"""

import os
import sys
import unittest
from unittest.mock import Mock, AsyncMock, patch
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.pm.skills.parse_daily_sync import ParseDailySyncSkill
from agents.pm.skills.track_capacity import TrackCapacitySkill
from agents.pm.skills.manage_backlog import ManageBacklogSkill
from agents.pm.skills.document_decision import DocumentDecisionSkill
from agents.pm.skills.translate_feedback import TranslateFeedbackSkill
from src.skills.base import SkillContext


class TestParseDailySyncSkill(unittest.IsolatedAsyncioTestCase):
    """Test daily sync parsing."""
    
    def setUp(self):
        self.bot = Mock()
        self.skill = ParseDailySyncSkill(self.bot)
        self.context = SkillContext()
    
    async def test_parse_valid_daily_sync(self):
        """Test parsing a valid daily sync message."""
        message = """
        ¿Qué hice? Terminé el diseño de la pantalla de login
        ¿Qué haré? Voy a trabajar en los componentes del dashboard
        ¿Qué me bloquea? Necesito feedback del cliente sobre los colores
        """
        
        author = Mock()
        author.name = "TestDesigner"
        author.id = 123456
        
        result = await self.skill.execute(
            self.context,
            message_content=message,
            author=author
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["author"], "TestDesigner")
        self.assertIn("pantalla de login", result["data"]["what_did"])
        self.assertIn("dashboard", result["data"]["what_will"])
        self.assertIn("feedback", result["data"]["blockers"])
    
    async def test_parse_critical_blocker(self):
        """Test detection of critical blockers."""
        message = """
        ¿Qué hice? Nada
        ¿Qué haré? Intentar debuggear
        ¿Qué me bloquea? Estoy completamente bloqueado, necesito ayuda urgente
        """
        
        author = Mock()
        author.name = "TestDesigner"
        author.id = 123456
        
        result = await self.skill.execute(
            self.context,
            message_content=message,
            author=author
        )
        
        self.assertTrue(result["success"])
        self.assertTrue(result["has_critical_blocker"])
        self.assertTrue(result["needs_attention"])
    
    async def test_parse_invalid_format(self):
        """Test handling of invalid format."""
        message = "Este es un mensaje sin el formato correcto"
        
        author = Mock()
        author.name = "TestDesigner"
        author.id = 123456
        
        result = await self.skill.execute(
            self.context,
            message_content=message,
            author=author
        )
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)


class TestTrackCapacitySkill(unittest.IsolatedAsyncioTestCase):
    """Test capacity tracking."""
    
    def setUp(self):
        self.bot = Mock()
        self.bot.notion_mcp = Mock()
        self.skill = TrackCapacitySkill(self.bot)
        self.context = SkillContext()
    
    async def test_calculate_workload(self):
        """Test workload calculation."""
        # Mock Notion tasks
        tasks = [
            {
                "properties": {
                    "Asignado a": {
                        "people": [{"id": "user1", "name": "Designer A"}]
                    },
                    "Project": {
                        "select": {"name": "Vexia"}
                    }
                }
            },
            {
                "properties": {
                    "Asignado a": {
                        "people": [{"id": "user1", "name": "Designer A"}]
                    },
                    "Project": {
                        "select": {"name": "Internal"}
                    }
                }
            },
            {
                "properties": {
                    "Asignado a": {
                        "people": [{"id": "user2", "name": "Designer B"}]
                    },
                    "Project": {
                        "select": {"name": "Vexia"}
                    }
                }
            }
        ]
        
        workload = self.skill._calculate_workload(tasks, [])
        
        self.assertEqual(len(workload), 2)
        self.assertEqual(workload["user1"]["total_tasks"], 2)
        self.assertEqual(workload["user1"]["critical_tasks"], 1)
        self.assertEqual(workload["user2"]["total_tasks"], 1)
    
    async def test_analyze_capacity_overloaded(self):
        """Test detection of overloaded team members."""
        workload = {
            "user1": {
                "name": "Designer A",
                "total_tasks": 6,
                "critical_tasks": 2,
                "projects": ["Vexia", "Internal"]
            },
            "user2": {
                "name": "Designer B",
                "total_tasks": 0,
                "critical_tasks": 0,
                "projects": []
            }
        }
        
        analysis = self.skill._analyze_capacity(workload)
        
        self.assertEqual(len(analysis["overloaded"]), 1)
        self.assertEqual(analysis["overloaded"][0]["name"], "Designer A")
        self.assertIn("Designer B", analysis["idle"])


class TestManageBacklogSkill(unittest.IsolatedAsyncioTestCase):
    """Test backlog management."""
    
    def setUp(self):
        self.bot = Mock()
        self.bot.notion_mcp = Mock()
        self.skill = ManageBacklogSkill(self.bot)
        self.context = SkillContext()
    
    def test_priority_scoring(self):
        """Test priority score calculation."""
        # High priority: Vexia project with deadline in 3 days
        score1 = self.skill._calculate_priority_score(
            "Vexia",
            "2026-02-15",  # Assuming test runs around 2026-02-12
            ["Vexia"]
        )
        
        # Low priority: Non-priority project, no deadline
        score2 = self.skill._calculate_priority_score(
            "Internal",
            None,
            ["Vexia"]
        )
        
        # Overdue task
        score3 = self.skill._calculate_priority_score(
            "Other",
            "2026-01-01",
            ["Vexia"]
        )
        
        self.assertGreater(score1, score2)
        self.assertGreater(score3, score1)  # Overdue is highest priority


class TestDocumentDecisionSkill(unittest.IsolatedAsyncioTestCase):
    """Test decision documentation."""
    
    def setUp(self):
        self.bot = Mock()
        self.bot.llm = Mock()
        self.bot.notion_mcp = Mock()
        self.skill = DocumentDecisionSkill(self.bot)
        self.context = SkillContext()
    
    def test_contains_decision(self):
        """Test decision keyword detection."""
        # Positive cases
        self.assertTrue(self.skill._contains_decision("Decidimos usar el color azul"))
        self.assertTrue(self.skill._contains_decision("Se aprobó el nuevo diseño"))
        self.assertTrue(self.skill._contains_decision("Vamos con la opción A"))
        
        # Negative cases
        self.assertFalse(self.skill._contains_decision("Estoy revisando las opciones"))
        self.assertFalse(self.skill._contains_decision("¿Qué color prefieres?"))


class TestTranslateFeedbackSkill(unittest.IsolatedAsyncioTestCase):
    """Test feedback translation."""
    
    def setUp(self):
        self.bot = Mock()
        self.bot.llm = Mock()
        self.bot.notion_mcp = Mock()
        self.skill = TranslateFeedbackSkill(self.bot)
        self.context = SkillContext()
    
    async def test_clarity_check_clear_feedback(self):
        """Test clarity check with clear feedback."""
        self.bot.llm.generate_completion = Mock(return_value=json.dumps({
            "is_clear": True,
            "questions": []
        }))
        
        result = await self.skill._check_feedback_clarity(
            "El botón de login debe ser azul #0066CC y tener 16px de padding"
        )
        
        self.assertTrue(result["is_clear"])
        self.assertEqual(len(result["questions"]), 0)
    
    async def test_clarity_check_vague_feedback(self):
        """Test clarity check with vague feedback."""
        self.bot.llm.generate_completion = Mock(return_value=json.dumps({
            "is_clear": False,
            "questions": ["¿Qué botón específicamente?", "¿Qué significa 'se ve raro'?"]
        }))
        
        result = await self.skill._check_feedback_clarity(
            "El botón se ve raro, arréglalo"
        )
        
        self.assertFalse(result["is_clear"])
        self.assertGreater(len(result["questions"]), 0)


if __name__ == "__main__":
    unittest.main()
