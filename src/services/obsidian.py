import os
from typing import List, Optional

class ObsidianVaultHandler:
    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.proyectos_path = os.path.join(vault_path, "Proyectos")

    def get_existing_projects(self) -> List[str]:
        """
        Scans the 'Proyectos' directory and returns a list of project names
        based on the filenames (without .md extension).
        """
        if not os.path.exists(self.proyectos_path):
            print(f"Warning: Directory {self.proyectos_path} does not exist.")
            return []

        projects = []
        for filename in os.listdir(self.proyectos_path):
            if filename.endswith(".md"):
                # Remove extension to get the project name (e.g. "Coolector.md" -> "Coolector")
                project_name = filename[:-3]
                projects.append(project_name)
        
        return sorted(projects)

    def create_note(self, title: str, content: str, folder: str = "Inbox") -> Optional[str]:
        """
        Creates a new markdown note in the specified folder within the vault.
        Returns the absolute path of the created file, or None if failed.
        """
        target_dir = os.path.join(self.vault_path, folder)
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir)
            except OSError as e:
                print(f"Error creating directory {target_dir}: {e}")
                return None

        # Sanitize title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        file_path = os.path.join(target_dir, f"{safe_title}.md")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return file_path
        except IOError as e:
            print(f"Error writing file {file_path}: {e}")
            return None

    def ensure_topic_node(self, topic_name: str, parent_project: str, summary: str = "") -> str:
        """
        Ensures a Topic Node exists (e.g. [[Agente REPARE]]).
        - Creates it if missing.
        - Links it UP to the Project (e.g. [[Solkos Intelligence]]).
        - Appends the daily activity summary.
        """
        # Directory for Topics
        topic_dir = os.path.join(self.vault_path, "Proyectos", "Topics")
        if not os.path.exists(topic_dir):
            os.makedirs(topic_dir, exist_ok=True)
            
        safe_name = "".join(c for c in topic_name if c.isalnum() or c in (' ', '-', '_')).strip()
        file_path = os.path.join(topic_dir, f"{safe_name}.md")
        
        from datetime import datetime
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Create content if new
        if not os.path.exists(file_path):
            content = f"""---
tags: [topic]
created: {today_str}
project: [[{parent_project}]]
---
# {topic_name}

**Proyecto Padre**: [[{parent_project}]]

## Contexto
Nodo generado automáticamente por actividad en Discord.

## 📜 Bitácora de Actividad
### {today_str}
{summary}

"""
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            # 2. Append if existing
            try:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(f"\n### {today_str}\n{summary}\n")
            except Exception as e:
                print(f"Error appending to {file_path}: {e}")
                
        return safe_name

# Simple test execution
if __name__ == "__main__":
    # Assuming the script is run from the project root and the vault is in "Emerald Digital Operation"
    VAULT_DIR = "Emerald Digital Operation"
    handler = ObsidianVaultHandler(VAULT_DIR)
    
    print("Scanning projects...")
    projects = handler.get_existing_projects()
    print(f"Found {len(projects)} projects:")
    for p in projects:
        print(f"- {p}")
