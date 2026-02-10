import os
import sys
import unittest
import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from agents.design.agent import DesignAgent


class _DummyBot:
    pass


class DesignAgentHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        agent_dir = os.path.join(ROOT, "agents", "design")
        cls.agent = DesignAgent(_DummyBot(), "design", agent_dir)

    def test_normalize_deadline_same_year_future(self):
        reference = datetime.datetime(2026, 2, 2, tzinfo=datetime.timezone.utc)
        result = self.agent._normalize_deadline("2024-02-14", reference)
        self.assertEqual(result, "2026-02-14")

    def test_normalize_deadline_rolls_to_next_year_if_past(self):
        reference = datetime.datetime(2026, 2, 20, tzinfo=datetime.timezone.utc)
        result = self.agent._normalize_deadline("2026-02-14", reference)
        self.assertEqual(result, "2027-02-14")

    def test_normalize_deadline_same_day(self):
        reference = datetime.datetime(2026, 2, 2, tzinfo=datetime.timezone.utc)
        result = self.agent._normalize_deadline("2026-02-02", reference)
        self.assertEqual(result, "2026-02-02")

    def test_match_project_option_case_and_space(self):
        options = ["Proyecto Alfa", "Beta Project"]
        self.assertEqual(
            self.agent._match_project_option("  proyecto  alfa ", options),
            "Proyecto Alfa",
        )

    def test_match_project_option_unknown(self):
        options = ["Proyecto Alfa", "Beta Project"]
        self.assertIsNone(self.agent._match_project_option("Gamma", options))


if __name__ == "__main__":
    unittest.main()
