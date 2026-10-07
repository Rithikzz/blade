from pydantic import BaseModel
from typing import List, Optional, Any, Literal, Dict

class VerifyRequest(BaseModel):
    dataset_id: Optional[str] = None
    dataset_ids: Optional[List[str]] = None
    question: str
    analysis_plan: dict
    generated_code: dict | str
    execution_result: dict
    execution_metadata: Optional[dict] = None

class VerificationCheck(BaseModel):
    name: str
    passed: bool
    severity: Literal["info", "warning", "error"]
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    message: str

class VerificationReport(BaseModel):
    verified: bool
    verification_status: Literal["verified", "failed", "inconclusive"]
    verification_method: List[str]
    checks: List[VerificationCheck]
    expected_result: Optional[Any] = None
    actual_result: Optional[Any] = None
    discrepancies: List[str]
    warnings: List[str]
    confidence: float
    explanation: str
    code_hash: str
    verification_time_ms: float
