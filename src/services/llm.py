import os
import openai
from typing import Optional, Dict

class LLMHandler:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        if self.api_key:
            openai.api_key = self.api_key
            self.client = openai.Client(api_key=self.api_key)

    def load_prompt(self, prompt_name: str) -> str:
        """
        Loads a prompt from the prompts/ directory.
        """
        prompt_path = os.path.join(os.getcwd(), "prompts", f"{prompt_name}.md")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def generate_completion(self, system_prompt: str, user_prompt: str, model: str = "gpt-4o", json_mode: bool = False) -> str:
        if not self.client:
            return "Error: No OpenAI API Key configured."

        try:
            response_format = {"type": "json_object"} if json_mode else None
            
            response = self.client.chat.completions.create(
                model=model,
                response_format=response_format,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating completion: {str(e)}"
