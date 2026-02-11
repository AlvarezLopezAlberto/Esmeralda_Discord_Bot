# Thread-Notion Mapping System

## Overview

This system uses a manual CSV file (`thread_notion_mapping.csv`) as the **single source of truth** for mapping Discord threads to Notion tasks. This provides reliable, editable tracking of which threads have associated Notion tasks.

## Files

### `thread_notion_mapping.csv`
**The master index.** Edit this file to manually add or update thread mappings.

**Columns:**
- `thread_id`: Discord thread ID (numeric)
- `thread_title`: Human-readable thread title
- `notion_url`: Full URL to the Notion task
- `status`: One of:
  - `approved`: Thread has a Notion task (task exists)
  - `pending`: No Notion task yet (needs manual action)
  - `ignored`: Skip processing for this thread
- `notes`: Any additional notes (optional)

**Example:**
```csv
thread_id,thread_title,notion_url,status,notes
1463668685993541696,[HDI] - Mejoras UI,https://www.notion.so/emerald-dev/...,approved,
1470846699198222489,Optimizar credenciales,,pending,Waiting for design team
```

### `populate_thread_mapping.py`
**Auto-population script.** Run this to fetch all threads from the intake forum and populate the CSV with what it can find.

**Usage:**
```bash
python3 populate_thread_mapping.py
```

This will:
1. Fetch all threads from #design-intake forum
2. Extract Notion links from starter messages where available
3. Write to `thread_notion_mapping.csv`
4. Show summary of approved vs pending threads

## How the Agent Uses This

### Priority Order

The agent checks for existing tasks in this order:

1. **CSV Mapping** (PRIMARY) - Checks `thread_notion_mapping.csv` first
2. **Notion API** (FALLBACK) - Searches Notion by Discord Thread property
3. **Starter Message** (FALLBACK) - Extracts Notion link from thread starter

If the CSV has an entry for a thread, that takes priority over everything else.

### Status Behavior

- **`approved`** with URL: Thread is marked as processed, agent exits immediately
- **`pending`** without URL: Agent proceeds with normal intake flow
- **`ignored`** without URL: Thread is skipped entirely (useful for test threads)

## Maintenance Workflow

### Adding a New Thread Mapping

When you create a Notion task manually or want to link an existing task:

1. Open `thread_notion_mapping.csv`
2. Add a new row or update existing row:
   ```csv
   1234567890123456789,My Thread Title,https://www.notion.so/emerald-dev/My-Task-xxx,approved,
   ```
3. Save the file
4. The agent will use this mapping immediately (no restart needed)

### Bulk Update

If you want to refresh all mappings:

```bash
python3 populate_thread_mapping.py
```

This will regenerate the entire CSV from scratch. **Warning:** Manual edits will be overwritten.

### Finding Missing Mappings

Look for rows with:
- `status=pending` 
- Empty `notion_url`

These need manual intervention.

## Advantages

✅ **Manual Control**: You can edit the file directly instead of relying on API searches  
✅ **Single Source of Truth**: No confusion about which threads have tasks  
✅ **Fast**: CSV lookup is instant, no API calls needed for known threads  
✅ **Reliable**: Doesn't depend on Notion search working correctly  
✅ **Auditable**: You can see all mappings at a glance  

## Migration from Old System

The old system relied on:
1. Notion API search for "Discord Thread" property
2. Extracting links from starter messages

Now:
1. CSV mapping is checked **first**
2. Old methods are fallbacks for new threads not yet in CSV

All existing threads have been auto-populated into the CSV.

## Monitoring

Check the bot logs for:
```
Thread {id} found in CSV mapping with status 'approved': {url}
```

This confirms the CSV lookup is working.

## Troubleshooting

**Agent still re-processing a thread:**
1. Check if thread is in CSV with `status=approved`
2. Verify the `notion_url` is populated
3. Check bot logs for debug messages about the thread state

**Thread not in CSV:**
1. Re-run `populate_thread_mapping.py`
2. Or manually add the thread to the CSV

**Want to force re-process a thread:**
1. Remove it from the CSV
2. OR change status to `pending`
3. OR clear its entry from `memory/design_intake_state.json`
