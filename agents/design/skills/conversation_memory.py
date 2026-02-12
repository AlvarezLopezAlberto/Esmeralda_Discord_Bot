"""
ConversationMemory Skill

Manages persistent conversation memory by creating summaries every 20 messages.
Each thread gets its own markdown file tracking agreements, deadlines, and key discussions.
"""

import json
import logging
import sys
import os
import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.skills.base import BaseSkill, SkillContext


class ConversationMemorySkill(BaseSkill):
    """
    Creates and maintains persistent conversation memory for Discord threads.
    
    Features:
    - Generates summaries every 20 messages (20, 40, 60...)
    - Stores summaries in markdown files per thread
    - Emphasizes agreements, deadlines, and commitments
    - Tracks who said what and when
    """
    
    SUMMARY_INTERVAL = 20  # Generate summary every N messages
    
    def __init__(self, llm_handler, memory_base_path: str = None):
        """
        Initialize the skill.
        
        Args:
            llm_handler: LLMHandler instance for generating summaries
            memory_base_path: Base directory for memory files (default: ./memory/threads)
        """
        super().__init__(
            name="conversation_memory",
            description="Manages persistent conversation memory with automatic summaries"
        )
        self.llm = llm_handler
        self.memory_base_path = memory_base_path or os.path.join(os.getcwd(), "memory", "threads")
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the conversation memory prompt template."""
        prompt_path = os.path.join(os.getcwd(), "prompts", "conversation_memory.txt")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to load prompt template: {e}")
            return ""
    
    def _get_memory_dir(self, thread_id: int) -> Path:
        """Get the memory directory for a specific thread."""
        return Path(self.memory_base_path) / str(thread_id)
    
    def _get_memory_file_path(self, thread_id: int) -> Path:
        """Get the memory file path for a specific thread."""
        return self._get_memory_dir(thread_id) / "conversation_memory.md"
    
    def _ensure_memory_dir(self, thread_id: int) -> None:
        """Ensure the memory directory exists for a thread."""
        memory_dir = self._get_memory_dir(thread_id)
        memory_dir.mkdir(parents=True, exist_ok=True)
    
    async def should_create_summary(
        self,
        context: SkillContext,
        current_message_count: int,
        last_summary_count: int = 0
    ) -> bool:
        """
        Check if a summary should be created based on message count.
        
        Args:
            context: Skill context
            current_message_count: Current total message count in thread
            last_summary_count: Message count when last summary was created
            
        Returns:
            True if summary should be created, False otherwise
        """
        # Calculate the next summary threshold
        next_threshold = ((last_summary_count // self.SUMMARY_INTERVAL) + 1) * self.SUMMARY_INTERVAL
        
        should_create = current_message_count >= next_threshold
        
        if should_create:
            self.logger.info(
                f"Summary needed: current={current_message_count}, "
                f"last={last_summary_count}, threshold={next_threshold}"
            )
        
        return should_create
    
    async def execute(
        self,
        context: SkillContext,
        thread_id: int,
        messages: List[Dict[str, Any]],
        thread_title: str = "",
        current_count: int = 0,
        last_summary_count: int = 0
    ) -> Optional[str]:
        """
        Execute memory summary creation.
        
        Args:
            context: Skill context
            thread_id: Discord thread ID
            messages: List of messages to summarize, each with:
                - author: str (username or "BOT")
                - content: str (message content)
                - timestamp: str (ISO format or Discord timestamp)
            thread_title: Title of the thread (optional)
            current_count: Current total message count
            last_summary_count: Count when last summary was created
            
        Returns:
            Path to updated memory file, or None if no summary created
        """
        self.logger.info(
            f"Processing memory for thread {thread_id}: "
            f"messages={len(messages)}, current_count={current_count}, "
            f"last_summary_count={last_summary_count}"
        )
        
        # Check if we should create a summary
        if not await self.should_create_summary(context, current_count, last_summary_count):
            self.logger.debug("Summary threshold not reached, skipping")
            return None
        
        # Ensure memory directory exists
        self._ensure_memory_dir(thread_id)
        memory_file = self._get_memory_file_path(thread_id)
        
        # Calculate summary number and range
        summary_number = current_count // self.SUMMARY_INTERVAL
        start_msg = last_summary_count + 1
        end_msg = summary_number * self.SUMMARY_INTERVAL
        
        # Initialize memory file if it doesn't exist
        if not memory_file.exists():
            await self._initialize_memory_file(memory_file, thread_id, thread_title)
        
        # Format messages for LLM
        formatted_messages = self._format_messages_for_llm(messages)
        
        # Generate summary using LLM
        summary = await self._generate_summary(
            formatted_messages,
            summary_number,
            start_msg,
            end_msg
        )
        
        if not summary:
            self.logger.error("Failed to generate summary")
            return None
        
        # Append summary to memory file
        await self._append_summary_to_file(memory_file, summary)
        
        # Store metadata in context
        context.set("last_summary_created", {
            "thread_id": thread_id,
            "summary_number": summary_number,
            "message_range": f"{start_msg}-{end_msg}",
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        
        self.logger.info(
            f"Created summary #{summary_number} for thread {thread_id} "
            f"(messages {start_msg}-{end_msg})"
        )
        
        return str(memory_file)
    
    async def _initialize_memory_file(
        self,
        file_path: Path,
        thread_id: int,
        thread_title: str
    ) -> None:
        """Initialize a new memory file with header."""
        header = f"""# Thread Memory: {thread_title or 'Untitled Thread'}
Thread ID: {thread_id}
Created: {datetime.datetime.utcnow().isoformat()}

---

"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(header)
        
        self.logger.info(f"Initialized memory file: {file_path}")
    
    def _format_messages_for_llm(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into a readable format for the LLM."""
        formatted = []
        
        for msg in messages:
            author = msg.get("author", "Unknown")
            content = msg.get("content", "").strip()
            timestamp = msg.get("timestamp", "")
            
            if not content:
                continue
            
            # Format: [TIMESTAMP] AUTHOR: content
            formatted.append(f"[{timestamp}] {author}: {content}")
        
        return "\n".join(formatted)
    
    async def _generate_summary(
        self,
        formatted_messages: str,
        summary_number: int,
        start_msg: int,
        end_msg: int
    ) -> Optional[str]:
        """Generate summary using LLM."""
        if not self.prompt_template:
            self.logger.error("Prompt template not loaded")
            return None
        
        # Get current timestamp range from messages
        lines = formatted_messages.split("\n")
        start_date = lines[0].split("]")[0][1:] if lines else "Unknown"
        end_date = lines[-1].split("]")[0][1:] if lines else "Unknown"
        
        user_prompt = f"""Generate a summary for the following conversation messages:

Summary Number: {summary_number}
Message Range: {start_msg}-{end_msg}
Period: {start_date} to {end_date}

MESSAGES:
{formatted_messages}

Remember to:
- Only include information that is actually present in the messages
- Prioritize agreements, deadlines, and commitments
- Always attribute statements to their authors with timestamps
- Omit sections that have no relevant information
- Be concise and focus on what matters for future context
"""
        
        try:
            # Call LLM (not in JSON mode - we want markdown)
            summary = self.llm.generate_completion(
                self.prompt_template,
                user_prompt,
                json_mode=False
            )
            
            return summary.strip()
            
        except Exception as e:
            self.logger.error(f"LLM summary generation failed: {e}", exc_info=True)
            return None
    
    async def _append_summary_to_file(self, file_path: Path, summary: str) -> None:
        """Append a new summary to the memory file."""
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(summary)
            f.write("\n\n---\n\n")
        
        self.logger.debug(f"Appended summary to {file_path}")
    
    async def load_memory(self, thread_id: int) -> Optional[str]:
        """
        Load existing memory summary for a thread.
        
        Args:
            thread_id: Discord thread ID
            
        Returns:
            Memory content as string, or None if no memory exists
        """
        memory_file = self._get_memory_file_path(thread_id)
        
        if not memory_file.exists():
            self.logger.debug(f"No memory file found for thread {thread_id}")
            return None
        
        try:
            with open(memory_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            self.logger.info(f"Loaded memory for thread {thread_id} ({len(content)} chars)")
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to load memory file: {e}")
            return None
    
    async def validate_input(self, context: SkillContext, **kwargs) -> bool:
        """Validate that required parameters are provided."""
        required = ["thread_id", "messages"]
        
        for param in required:
            if param not in kwargs:
                self.logger.error(f"Missing required parameter: {param}")
                return False
        
        # Validate messages format
        messages = kwargs.get("messages", [])
        if not isinstance(messages, list):
            self.logger.error("Messages must be a list")
            return False
        
        return True
