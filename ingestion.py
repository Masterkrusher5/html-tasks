import re
import os

class LegacyIngestor:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.file_registry = {}

    def scan(self):
        """Detects entry programs and libraries."""
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                ext = file.split('.')[-1].lower()
                path = os.path.join(root, file)
                self.file_registry[file] = {"path": path, "type": ext}
        return self.file_registry

    def normalize(self, code: str) -> str:
        """Standardizes indentation and removes redundant whitespace."""
        # Remove multiple spaces
        code = re.sub(r' +', ' ', code)
        # Standardize line breaks
        lines = [line.strip() for line in code.splitlines() if line.strip()]
        return "\n".join(lines)
