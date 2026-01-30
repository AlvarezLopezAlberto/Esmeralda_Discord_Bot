import re
import sys
import discord

async def process_notion_links(message: discord.Message, notion_service):
    """
    Scans for Notion URLs and replaces them with Markdown links.
    Returns True if processed (enriched/replaced), False otherwise.
    """
    content = message.content
    
    # Check for Notion domains
    if "notion.so" not in content and "notion.site" not in content:
        return False

    # Find all Notion URLs
    urls = re.findall(r'(https?://(?:\S+\.)?notion\.(?:so|site)/[^\s]+)', content)
    
    if not urls:
        return False
        
    replaced_content = content
    replacements_made = False
    
    for url in urls:
        page_id = notion_service.extract_page_id(url)
        
        if page_id:
            info = notion_service.get_page_info(page_id)
            if info:
                title = info.get("title", "Notion Page")
                replaced_content = replaced_content.replace(url, f"[{title}]({url})")
                replacements_made = True
    
    if replacements_made:
        try:
            # 1. Prepare Webhook
            webhook_channel = message.channel
            if isinstance(message.channel, discord.Thread):
                webhook_channel = message.channel.parent
            
            webhooks = await webhook_channel.webhooks()
            webhook = None
            for w in webhooks:
                if w.name == "NotionFormatter":
                    webhook = w
                    break
            
            if not webhook:
                webhook = await webhook_channel.create_webhook(name="NotionFormatter")
            
            # 2. Send as User
            send_kwargs = {
                "content": replaced_content,
                "username": message.author.display_name,
                "avatar_url": message.author.display_avatar.url,
                "files": [await a.to_file() for a in message.attachments]
            }
            
            if isinstance(message.channel, discord.Thread):
                send_kwargs["thread"] = message.channel
            
            await webhook.send(**send_kwargs)
            
            # 3. Delete Original
            await message.delete()
            return True
            
        except Exception as e:
            sys.stderr.write(f"Error auto-formatting: {e}\n")
            return False

    return False
