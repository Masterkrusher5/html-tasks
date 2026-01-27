from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class GraphData(BaseModel):
    nodes: List[str]
    edges: List[Dict[str, str]]
    entry_point: str

class SemanticChunk(BaseModel):
    chunk_id: str
    logic_type: str  # e.g., "Calculation", "Data Access", "UI"
    description: str
    dependencies: List[str]
    original_code: str
    context_score: float

class ModernizationPlan(BaseModel):
    source_chunk_id: str
    target_architecture: str
    suggested_refactoring: str
    risk_level: str
