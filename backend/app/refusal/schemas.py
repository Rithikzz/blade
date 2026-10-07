from pydantic import BaseModel
from typing import List, Optional, Any, Literal, Dict

class RefusalEvidence(BaseModel):
    check: str
    passed: bool
    severity: Literal["info", "warning", "error"]
    message: str
    details: dict

class RefusalDecision(BaseModel):
    can_answer: bool
    status: Literal["answerable", "cannot_determine"]
    reason_code: Optional[str] = None
    reasons: List[str] = []
    evidence: List[RefusalEvidence] = []
    missing_information: List[str] = []
    affected_columns: List[str] = []
    recommended_action: Optional[str] = None
    confidence: float

class DecisionRequest(BaseModel):
    dataset_id: Optional[str] = None
    dataset_ids: Optional[List[str]] = None
    question: str
    analysis_plan: dict
    execution_result: Optional[dict] = None
    execution_metadata: Optional[dict] = None
    verification_report: Optional[dict] = None
