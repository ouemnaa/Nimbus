from typing import Dict, Any, Optional
from pydantic import BaseModel
from .architecture import ArchitectureSpecification

class AnalyzeRequest(BaseModel):
    requirement: str
    context: Optional[Dict[str, Any]] = None

class GenerationMetadata(BaseModel):
    provider: str
    model: str
    generation_duration_ms: int

class AnalyzeResponse(BaseModel):
    architecture: ArchitectureSpecification
    report_markdown: str
    metadata: GenerationMetadata
