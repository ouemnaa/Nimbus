from typing import Dict, Any, List, Literal, Optional
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


class FollowUpMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class FollowUpRequest(BaseModel):
    session_id: str
    current_architecture: Dict[str, Any]
    current_report_markdown: Optional[str] = None
    conversation_summary: Optional[str] = None
    messages: List[FollowUpMessage] = []
    user_message: str


class FollowUpResponse(BaseModel):
    intent: Literal["EXPLAIN", "MODIFY", "CLARIFY", "UNSUPPORTED"]
    architecture_changed: bool
    answer: str
    change_summary: List[str] = []
    previous_version: Optional[str] = None
    new_version: Optional[str] = None
    architecture: Optional[ArchitectureSpecification] = None
    report_markdown: Optional[str] = None
    metadata: Dict[str, Any] = {}
