import os
import re

class FileIngestor:
    """
    Phase 1: Intelligent Parsing & Chunking.
    Handles extraction of Global Context and Logic Chunks.
    Includes fallback logic to ensure LLM never receives empty context.
    """

    @staticmethod
    def read_uploaded_file(uploaded_file) -> str:
        """Reads file content with encoding resilience."""
        try:
            return uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return uploaded_file.read().decode("latin-1", errors="ignore")

    @staticmethod
    def normalize(code: str) -> str:
        """Collapses multiple spaces but preserves newlines."""
        return re.sub(r'[ \t]+', ' ', code)

    @staticmethod
    def chunk_code(code: str, file_name: str) -> dict:
        """
        Parses code into 'Global Context' (State) and 'Chunks' (Logic).
        """
        ext = os.path.splitext(file_name)[1].lower()
        
        # 1. Select Parsing Strategy
        if ext in ['.cbl', '.cob']:
            data = FileIngestor._chunk_cobol(code)
        elif ext in ['.vb', '.bas', '.frm']:
            data = FileIngestor._chunk_vb(code)
        elif ext in ['.java', '.cs', '.py', '.js', '.ts']:
            data = FileIngestor._chunk_c_style(code)
        else:
            # Default for unknown text files
            data = {"global_context": "", "chunks": []}

        # 2. SAFETY FALLBACK: Global Context
        # If the parser failed to extract a specific header/state section, 
        # force-feed the top 3000 characters so the LLM has context.
        if not data.get("global_context") or len(data["global_context"].strip()) < 50:
            data["global_context"] = f"// AUTOMATIC CONTEXT EXTRACTION (Top of File):\n{code[:3000]}"

        # 3. SAFETY FALLBACK: Logic Chunks
        # If no specific functions/paragraphs were found, treat the whole file as one chunk.
        if not data.get("chunks"):
            data["chunks"] = [{"name": "Main_Body", "code": code, "dependencies": []}]

        return data

    # --- LANGUAGE SPECIFIC PARSERS ---

    @staticmethod
    def _chunk_cobol(code: str) -> dict:
        # Attempt to split at Procedure Division
        parts = re.split(r'(?i)PROCEDURE\s+DIVISION\.?', code)
        
        global_ctx = parts[0] if len(parts) > 0 else ""
        proc_body = parts[1] if len(parts) > 1 else code

        # Regex to find Paragraphs (Start of line, alphanumeric, followed by dot)
        chunks = []
        raw_splits = re.split(r'\n\s*([A-Z0-9\-]+)\.\s', "\n" + proc_body)
        
        # raw_splits[0] is pre-paragraph code, subsequent are [name, body, name, body...]
        if len(raw_splits) > 1:
            for i in range(1, len(raw_splits), 2):
                name = raw_splits[i]
                body = raw_splits[i+1]
                chunks.append({"name": name, "code": body, "dependencies": []})
        
        return {"global_context": global_ctx, "chunks": chunks}

    @staticmethod
    def _chunk_vb(code: str) -> dict:
        lines = code.splitlines()
        globals_lines = []
        chunks = []
        current_chunk = []
        chunk_name = None
        in_func = False

        for line in lines:
            # Detect Start of Sub/Function
            if re.search(r'(?i)^(Public|Private|Friend)?\s*(Sub|Function)', line):
                in_func = True
                match = re.search(r'(?i)(Sub|Function)\s+(\w+)', line)
                chunk_name = match.group(2) if match else "UnknownSub"
                current_chunk.append(line)
            
            # Detect End of Sub/Function
            elif re.search(r'(?i)End\s*(Sub|Function)', line):
                current_chunk.append(line)
                chunks.append({
                    "name": chunk_name, 
                    "code": "\n".join(current_chunk), 
                    "dependencies": []
                })
                current_chunk = []
                in_func = False
                chunk_name = None
            
            # Inside Function
            elif in_func:
                current_chunk.append(line)
            
            # Global/Header space
            else:
                if line.strip(): 
                    globals_lines.append(line)

        return {"global_context": "\n".join(globals_lines), "chunks": chunks}

    @staticmethod
    def _chunk_c_style(code: str) -> dict:
        """
        Generic chunker for Java/C#/Python.
        Uses spacing/indentation heuristics as regex is brittle for nested brackets.
        """
        lines = code.splitlines()
        
        # Heuristic: The first 50 lines usually contain Imports, Class Def, and Class Variables
        limit = min(len(lines), 50)
        global_ctx = "\n".join(lines[:limit])
        
        # For simplicity in this architecture, we treat the rest as one main chunk 
        # (The Segmented Streaming in analyzer.py handles the token limits)
        return {
            "global_context": global_ctx, 
            "chunks": [{"name": "Class_Logic", "code": code, "dependencies": []}]
        }

    @staticmethod
    def extract_metadata(uploaded_file, code) -> dict:
        return {
            "file_name": uploaded_file.name,
            "size_kb": round(uploaded_file.size / 1024, 2),
            "role": "Source Code",
            "line_count": len(code.splitlines())
        }
