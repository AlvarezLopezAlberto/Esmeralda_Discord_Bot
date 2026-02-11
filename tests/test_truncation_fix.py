import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))
from services.notion import NotionHandler

class TestTruncationFix(unittest.TestCase):
    @patch('services.notion.Client')
    def test_content_truncation(self, mock_client_class):
        # Setup mock
        mock_client = mock_client_class.return_value
        handler = NotionHandler("fake_token")
        handler.client = mock_client
        
        # Mock successful creation
        mock_client.pages.create.return_value = {"url": "https://notion.so/test"}
        
        long_content = "a" * 3000
        handler.create_task("db_id", "Title", "Project", content=long_content)
        
        # Check that pages.create was called with truncated content
        args, kwargs = mock_client.pages.create.call_args
        called_content = kwargs['children'][0]['paragraph']['rich_text'][0]['text']['content']
        self.assertEqual(len(called_content), 1900)
        self.assertTrue(called_content.startswith("a"))

if __name__ == '__main__':
    unittest.main()
