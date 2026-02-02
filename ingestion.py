import os
import re

class FileIngestor:
    @staticmethod
    def read_uploaded_file(uploaded_file) -> str:
        try:
            return uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return uploaded_file.read().decode("latin-1", errors="ignore")

    @staticmethod
    def normalize(code: str) -> str:
        return re.sub(r'[ \t]+', ' ', code)

    @staticmethod
    def chunk_code(code: str, file_name: str) -> dict:
        ext = os.path.splitext(file_name)[1].lower()
        
        if ext in ['.cbl', '.cob']:
            return FileIngestor._chunk_cobol(code)
        elif ext in ['.java', '.cs']:
            return FileIngestor._chunk_c_style(code)
        elif ext in ['.vb', '.bas', '.frm']:
            return FileIngestor._chunk_vb(code)
        else:
            return {"global_context": "Raw File", "chunks": [{"name": "Main", "code": code}]}

    @staticmethod
    def _chunk_cobol(code: str) -> dict:
        parts = re.split(r'(?i)PROCEDURE\s+DIVISION\.?', code)
        
        global_context = parts[0] if len(parts) > 0 else ""
        procedure_body = parts[1] if len(parts) > 1 else code

        chunks = []
        raw_paragraphs = re.split(r'\n\s*([A-Z0-9\-]+)\.\s', "\n" + procedure_body)
        
        call_pattern = r'(?i)PERFORM\s+([A-Z0-9\-]+)'
        
        for i in range(1, len(raw_paragraphs), 2):
            name = raw_paragraphs[i]
            body = raw_paragraphs[i+1]
            calls = re.findall(call_pattern, body)
            chunks.append({
                "name": name,
                "code": body,
                "dependencies": list(set(calls))
            })
            
        return {"global_context": global_context, "chunks": chunks}

    @staticmethod
    def _chunk_vb(code: str) -> dict:
        lines = code.splitlines()
        globals_lines = []
        chunks = []
        current_chunk = []
        chunk_name = None
        in_func = False

        for line in lines:
            if re.search(r'(?i)^(Public|Private)?\s*(Sub|Function)', line):
                in_func = True
                match = re.search(r'(?i)(Sub|Function)\s+(\w+)', line)
                chunk_name = match.group(2) if match else "Unknown"
                current_chunk.append(line)
            
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
            
            elif in_func:
                current_chunk.append(line)
            
            else:
                if line.strip(): globals_lines.append(line)

        return {"global_context": "\n".join(globals_lines), "chunks": chunks}

    @staticmethod
    def _chunk_c_style(code: str) -> dict:
        return {"global_context": "Class Imports & Definitions", "chunks": [{"name": "WholeFile", "code": code}]}

    @staticmethod
    def extract_metadata(uploaded_file, code) -> dict:
        return {
            "file_name": uploaded_file.name,
            "size_kb": round(uploaded_file.size / 1024, 2),
            "role": "Source",
            "line_count": len(code.splitlines())
        }
