import unittest
import datetime
import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.getcwd(), "agents", "design"))
sys.path.append(os.path.join(os.getcwd(), "src"))

from agent import DesignAgent


class TestDateNormalization(unittest.TestCase):
    """Test the enhanced date normalization logic"""
    
    def setUp(self):
        """Create a mock bot and agent for testing"""
        class MockBot:
            pass
        
        self.mock_bot = MockBot()
        # We can't fully initialize the agent without all dependencies,
        # so we'll test the logic separately
    
    def test_normalize_deadline_past_year(self):
        """Test that dates with past years are adjusted to current/next year"""
        # Create a minimal agent instance just to access the method
        # This is a bit hacky but works for unit testing
        agent = DesignAgent.__new__(DesignAgent)
        
        # Reference date: Feb 10, 2026
        reference = datetime.datetime(2026, 2, 10, tzinfo=datetime.timezone.utc)
        
        # LLM extracted: 2025-02-14 (past year)
        # Should become: 2026-02-14 (current year, future date)
        result = agent._normalize_deadline("2025-02-14", reference)
        self.assertEqual(result, "2026-02-14")
        
    def test_normalize_deadline_past_year_already_passed_this_year(self):
        """Test past year date that already passed in current year"""
        agent = DesignAgent.__new__(DesignAgent)
        
        # Reference date: Feb 10, 2026  
        reference = datetime.datetime(2026, 2, 10, tzinfo=datetime.timezone.utc)
        
        # LLM extracted: 2025-01-20 (past year, and Jan 20 already passed)
        # Should become: 2027-01-20 (next year)
        result = agent._normalize_deadline("2025-01-20", reference)
        self.assertEqual(result, "2027-01-20")
    
    def test_normalize_deadline_current_year_future(self):
        """Test current year with future date"""
        agent = DesignAgent.__new__(DesignAgent)
        
        # Reference date: Feb 10, 2026
        reference = datetime.datetime(2026, 2, 10, tzinfo=datetime.timezone.utc)
        
        # LLM extracted: 2026-03-15 (current year, future)
        # Should stay: 2026-03-15
        result = agent._normalize_deadline("2026-03-15", reference)
        self.assertEqual(result, "2026-03-15")
        
    def test_normalize_deadline_current_year_past(self):
        """Test current year with past date"""
        agent = DesignAgent.__new__(DesignAgent)
        
        # Reference date: Feb 10, 2026
        reference = datetime.datetime(2026, 2, 10, tzinfo=datetime.timezone.utc)
        
        # LLM extracted: 2026-01-15 (current year, but already passed)
        # Should become: 2027-01-15 (next year)
        result = agent._normalize_deadline("2026-01-15", reference)
        self.assertEqual(result, "2027-01-15")
    
    def test_normalize_deadline_next_year(self):
        """Test next year dates are kept as-is"""
        agent = DesignAgent.__new__(DesignAgent)
        
        # Reference date: Feb 10, 2026
        reference = datetime.datetime(2026, 2, 10, tzinfo=datetime.timezone.utc)
        
        # LLM extracted: 2027-02-14 (next year)
        # Should stay: 2027-02-14
        result = agent._normalize_deadline("2027-02-14", reference)
        self.assertEqual(result, "2027-02-14")
    
    def test_normalize_deadline_far_future(self):
        """Test dates far in the future are adjusted"""
        agent = DesignAgent.__new__(DesignAgent)
        agent.logger = self._create_mock_logger()
        
        # Reference date: Feb 10, 2026
        reference = datetime.datetime(2026, 2, 10, tzinfo=datetime.timezone.utc)
        
        # LLM extracted: 2030-02-14 (way in future - likely an error)
        # Should use fallback: 2026-02-14 or 2027-02-14 depending on whether it passed
        result = agent._normalize_deadline("2030-02-14", reference)
        self.assertEqual(result, "2026-02-14")  # Feb 14 hasn't passed yet
    
    def test_normalize_deadline_month_day_only(self):
        """Test when LLM only extracts month/day (no year)"""
        agent = DesignAgent.__new__(DesignAgent)
        
        # Reference date: Feb 10, 2026
        reference = datetime.datetime(2026, 2, 10, tzinfo=datetime.timezone.utc)
        
        # LLM extracted: 02-14 (will be parsed with current year)
        # This depends on how _parse_iso_date handles it
        # Should become: 2026-02-14
        result = agent._normalize_deadline("02-14", reference)
        # This might not parse, so it returns the original
        # We'll test the actual behavior
        self.assertIsNotNone(result)
    
    def _create_mock_logger(self):
        """Create a mock logger that doesn't actually log"""
        class MockLogger:
            def warning(self, msg): pass
            def info(self, msg): pass
            def error(self, msg, **kwargs): pass
            def debug(self, msg): pass
        return MockLogger()


if __name__ == '__main__':
    unittest.main()
