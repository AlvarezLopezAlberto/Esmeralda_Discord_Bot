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

from services.notion import NotionHandler


class NotionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.token = os.getenv("NOTION_TOKEN")
        self.db_id = os.getenv("NOTION_DB_ID")
        if not self.token or not self.db_id:
            self.skipTest("Set NOTION_TOKEN and NOTION_DB_ID to run integration tests.")
        self.handler = NotionHandler(self.token)
        if not self.handler.is_enabled():
            self.skipTest("Notion client not enabled.")

    def test_create_and_archive_task(self):
        options = self.handler.get_multi_select_options(self.db_id, "Proyecto")
        project = options[0] if options else None
        title = "Integration Test Task"
        deadline = datetime.date.today().isoformat()

        url = self.handler.create_task(
            self.db_id,
            title,
            project or "Sin Proyecto",
            deadline=deadline,
            content="Integration test task created by automated tests.",
        )
        self.assertIsNotNone(url)

        page_id = self.handler.extract_page_id(url)
        if page_id:
            deleted = self.handler.delete_page(page_id)
            self.assertTrue(deleted)


if __name__ == "__main__":
    unittest.main()
