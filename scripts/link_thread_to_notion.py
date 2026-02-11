import os
import sys
import argparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from services.notion import NotionHandler


def build_thread_url(guild_id: int, thread_id: int) -> str:
    return f"https://discord.com/channels/{guild_id}/{thread_id}/{thread_id}"


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Link a Discord thread ID to a Notion task by writing the thread URL into the database."
    )
    parser.add_argument("--thread-id", type=int, required=True, help="Discord thread ID")
    parser.add_argument("--notion-url", type=str, required=True, help="Notion task URL")
    parser.add_argument("--guild-id", type=int, default=None, help="Discord guild ID (optional)")
    parser.add_argument("--db-id", type=str, default=None, help="Notion database ID (optional)")
    parser.add_argument("--property-name", type=str, default="Discord Thread", help="Notion property name")
    args = parser.parse_args()

    db_id = args.db_id or os.getenv("NOTION_DB_ID") or "9b1d386dbae1401b8a58af5a792e8f1f"
    guild_id = args.guild_id or os.getenv("DISCORD_GUILD_ID")

    if not guild_id:
        print("Missing guild ID. Provide --guild-id or set DISCORD_GUILD_ID.")
        sys.exit(1)

    notion = NotionHandler()
    if not notion.is_enabled():
        print("Notion client not configured. Set NOTION_TOKEN.")
        sys.exit(1)

    page_id = notion.extract_page_id(args.notion_url)
    if not page_id:
        print("Could not parse page ID from Notion URL.")
        sys.exit(1)

    thread_url = build_thread_url(int(guild_id), args.thread_id)
    ok = notion.update_task_with_thread_link(
        database_id=db_id,
        page_id=page_id,
        thread_url=thread_url,
        property_name=args.property_name
    )

    if not ok:
        print("Failed to update Notion task with thread link.")
        sys.exit(1)

    print(f"Linked thread to Notion task: {thread_url}")


if __name__ == "__main__":
    main()
