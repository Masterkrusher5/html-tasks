import os
import re
import json
import requests
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

class LegacyIngestor:
    """
    Phase 1, Step 1: Legacy Code Ingestion.
    Responsible for repository scanning, code normalization, and 
    AI-assisted role detection (Entry vs. Library).
    """
    def __init__(self):
        self.endpoint = os.getenv("LLM_ENDPOINT")
        self.api_key = os.getenv("LLM_KEY")
        
        # Session setup for intelligent categorization calls
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "api-key": self.api_key
        })

    def normalize(self, code: str) -> str:
        """
        Cleans voluminous code by removing redundant spaces, 
        standardizing indentation, and stripping noise.
        """
        if not code:
            return ""
            
        # 1. Remove multiple spaces and replace with a single space
        code = re.sub(r' +', ' ', code)
        
        # 2. Standardize indentation: Split lines, strip, and rejoin
        # This makes it easier for the AST parser to find logic blocks
        lines = code.splitlines()
        normalized_lines = []
        for line in lines:
            trimmed = line.strip()
            if trimmed:  # Only add non-empty lines
                normalized_lines.append(trimmed)
        
        return "\n".join(normalized_lines)

    def scan_repository(self, root_dir: str):
        """
        Recursively scans the directory to map the file system.
        """
        inventory = {
            "source_files": [],
            "config_files": [],
            "total_files": 0
        }
        
        extensions = ('.cbl', '.cob', '.vb', '.bas', '.frm', '.java', '.xml', '.config', '.properties')
        
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith(extensions):
                    path = os.path.join(root, file)
                    inventory["total_files"] += 1
                    if file.lower().endswith(('.xml', '.config', '.properties')):
                        inventory["config_files"].append(path)
                    else:
                        inventory["source_files"].append(path)
                        
        return inventory

    def detect_file_role(self, file_name: str, code_snippet: str):
        """
        Uses the LLM to intelligently decide if a file is an 
        'Entry Point' (Main), 'Shared Library' (Utility), or 'Config'.
        """
        prompt = f"""
        Act as a Legacy Systems Architect. Categorize this file based on its name and code snippet.
        
        FILE NAME: {file_name}
        SNIPPET:
        \"\"\"
        {code_snippet[:1000]}
        \"\"\"

        Return a JSON object:
        {{
            "role": "Entry Program" | "Shared Library" | "Configuration",
            "reason": "Brief explanation",
            "main_logic_found": true/false
        }}
        """

        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0
        }

        try:
            response = self.session.post(self.endpoint, json=payload, timeout=20)
            response.raise_for_status()
            
            raw_res = response.json()['choices'][0]['message']['content']
            
            # Helper to extract JSON from string
            start = raw_res.find("{")
            end = raw_res.rfind("}")
            if start != -1 and end != -1:
                return json.loads(raw_res[start : end + 1])
            return {"role": "Unknown", "reason": "Failed to parse AI response"}
            
        except Exception as e:
            return {"role": "Unknown", "reason": str(e)}

    def build_dependency_registry(self, inventory: dict):
        """
        Initial mapping to determine call graphs between files.
        Analyzes imports, copybooks, and references.
        """
        # In Phase 1, we identify keywords like "CALL", "COPY", "Import", "Include"
        registry = {}
        for file_path in inventory["source_files"]:
            file_name = os.path.basename(file_path)
            try:
                with open(file_path, 'r', errors='ignore') as f:
                    content = f.read()
                    # Detect potential dependencies
                    deps = re.findall(r'(?i)CALL ["\'](\w+)["\']|COPY (\w+)|import (\w+)', content)
                    # Flatten list of tuples
                    flat_deps = [d for sub in deps for d in sub if d]
                    registry[file_name] = flat_deps
            except:
                continue
        return registry
