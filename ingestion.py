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
            data = FileIngestor._chunk_cobol(code)
        elif ext in ['.vb', '.bas', '.frm', '.cls']:
            data = FileIngestor._chunk_vb(code)
        elif ext in ['.java', '.cs', '.py', '.js', '.ts']:
            data = FileIngestor._chunk_c_style(code)
        else:
            data = {"global_context": "", "chunks": []}

        if not data.get("global_context") or len(data["global_context"].strip()) < 50:
            data["global_context"] = f"// AUTOMATIC CONTEXT EXTRACTION (Top of File):\n{code[:4000]}"

        if not data.get("chunks"):
            data["chunks"] = [{"name": "Main_Body", "code": code}]

        return data

    @staticmethod
    def _chunk_cobol(code: str) -> dict:
        parts = re.split(r'(?i)PROCEDURE\s+DIVISION\.?', code)
        global_ctx = parts[0] if len(parts) > 0 else ""
        proc_body = parts[1] if len(parts) > 1 else code
        chunks = []
        raw_splits = re.split(r'\n\s*([A-Z0-9\-]+)\.\s', "\n" + proc_body)
        
        if len(raw_splits) > 1:
            for i in range(1, len(raw_splits), 2):
                name = raw_splits[i]
                body = raw_splits[i+1]
                chunks.append({"name": name, "code": body})
        else:
            chunks.append({"name": "PROCEDURE_DIVISION", "code": proc_body})
            
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
            if re.search(r'(?i)^(Public|Private|Friend)?\s*(Sub|Function)', line):
                in_func = True
                match = re.search(r'(?i)(Sub|Function)\s+(\w+)', line)
                chunk_name = match.group(2) if match else "UnknownSub"
                current_chunk.append(line)
            elif re.search(r'(?i)End\s*(Sub|Function)', line):
                current_chunk.append(line)
                chunks.append({"name": chunk_name, "code": "\n".join(current_chunk)})
                current_chunk, in_func, chunk_name = [], False, None
            elif in_func:
                current_chunk.append(line)
            else:
                if line.strip():
                    globals_lines.append(line)

        return {"global_context": "\n".join(globals_lines), "chunks": chunks}

    @staticmethod
    def _chunk_c_style(code: str) -> dict:
        lines = code.splitlines()
        limit = min(len(lines), 60)
        global_ctx = "\n".join(lines[:limit])
        return {
            "global_context": global_ctx, 
            "chunks": [{"name": "Class_Logic", "code": code}]
        }

    @staticmethod
    def extract_metadata(uploaded_file, code) -> dict:
        return {
            "file_name": uploaded_file.name,
            "size_kb": round(uploaded_file.size / 1024, 2),
            "role": "Source Code",
            "line_count": len(code.splitlines())
        }
