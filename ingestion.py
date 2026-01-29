import os
import re

class FileIngestor:
    """
    Phase 1: Legacy Code Ingestion & Normalization.
    Handles file parsing, encoding resilience, and structural normalization
    to prepare voluminous code for technical analysis.
    """

    @staticmethod
    def normalize(code: str) -> str:
        """
        Standardizes legacy source code to reduce token usage and improve clarity.
        1. Collapses redundant multiple spaces (common in COBOL).
        2. Strips leading/trailing whitespace.
        3. Removes empty lines to condense logic.
        """
        if not code:
            return ""

        # 1. Replace multiple spaces with a single space 
        # (This collapses COBOL's fixed-field whitespace while preserving logic)
        code = re.sub(r' +', ' ', code)

        # 2. Process line by line for standardization
        lines = code.splitlines()
        normalized_lines = []
        
        for line in lines:
            clean_line = line.strip()
            # Only keep lines that have actual content to save processing time
            if clean_line:
                normalized_lines.append(clean_line)

        return "\n".join(normalized_lines)

    @staticmethod
    def read_uploaded_file(uploaded_file) -> str:
        """
        Safely reads file content from a Streamlit UploadedFile object.
        Implements fallback decoding for legacy encodings (Latin-1).
        """
        try:
            # Try standard modern encoding
            return uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            # Fallback for legacy files (Common in Mainframe/VB6 exports)
            uploaded_file.seek(0)
            return uploaded_file.read().decode("latin-1", errors="ignore")

    @staticmethod
    def analyze_file_role(code: str, file_name: str) -> str:
        """
        Performs a heuristic scan to determine the file's architectural role.
        Identifies 'Entry Points' vs 'Shared Libraries'.
        """
        code_upper = code.upper()
        ext = os.path.splitext(file_name)[1].lower()

        # 1. COBOL Role Detection
        if ext in ['.cbl', '.cob']:
            if "PROCEDURE DIVISION" in code_upper and "STOP RUN" in code_upper:
                return "Entry Program (Main)"
            return "Shared Library (Copybook/Subroutine)"

        # 2. VB6 Role Detection
        if ext in ['.bas', '.frm', '.cls']:
            if "SUB MAIN()" in code_upper or "PRIVATE SUB FORM_LOAD" in code_upper:
                return "Entry Program (UI/Startup)"
            return "Shared Library (Module/Class)"

        # 3. Java Role Detection
        if ext == '.java':
            if "PUBLIC STATIC VOID MAIN" in code_upper:
                return "Entry Program (Main)"
            return "Shared Library (Utility/Bean)"

        return "Source Component"

    @staticmethod
    def extract_metadata(uploaded_file, code: str) -> dict:
        """
        Extracts metadata used for the Ingestion Dashboard.
        """
        file_name = uploaded_file.name
        role = FileIngestor.analyze_file_role(code, file_name)
        
        return {
            "file_name": file_name,
            "size_kb": round(uploaded_file.size / 1024, 2),
            "role": role,
            "line_count": len(code.splitlines())
        }

    @staticmethod
    def scan_for_dependencies(code: str) -> list:
        """
        Scans normalized code for external references to build 
        initial call graph hints.
        """
        dependencies = []
        
        # Patterns for COBOL CALL, COPY, VB Declare, and Java Import
        patterns = [
            r'(?i)CALL\s+[\'\"](\w+)[\'\"]',  # COBOL Call
            r'(?i)COPY\s+(\w+)',              # COBOL Copybook
            r'(?i)Declare\s+Sub\s+(\w+)',     # VB API
            r'(?i)import\s+([\w\.]+)'         # Java Import
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, code)
            dependencies.extend(matches)
            
        return list(set(dependencies))
