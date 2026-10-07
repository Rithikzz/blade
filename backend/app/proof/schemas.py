from pydantic import BaseModel
from typing import List, Optional, Any, Literal, Dict

class EvidenceItem(BaseModel):
    id: str
    type: Literal["dataset", "filter", "aggregation", "grouping", "calculation", "execution", "verification", "data_quality", "limitation"]
    title: str
    description: str
    status: Literal["passed", "failed", "warning", "info"]
    details: Dict[str, Any]

class ComputationEvidence(BaseModel):
    steps: List[Dict[str, Any]]

class VerificationEvidence(BaseModel):
    status: Literal["verified", "failed", "inconclusive"]
    methods: List[str]
    checks_passed: int
    checks_failed: int
    confidence: float
    discrepancies: List[str]
    verification_time_ms: float

class DatasetEvidence(BaseModel):
    dataset_id: str
    filename: str
    row_count: int
    column_count: int
    columns_used: List[str]

class ProvenanceEvidence(BaseModel):
    code_language: str
    libraries: List[str]
    execution_time_ms: float
    sandbox_type: str
    result_type: str
    result_truncated: bool

class HashEvidence(BaseModel):
    code_hash: str
    plan_hash: str
    execution_hash: str
    verification_hash: str
    dataset_hash: Optional[str] = None
    proof_package_hash: Optional[str] = None

class JoinEvidence(BaseModel):
    left_dataset_id: str
    right_dataset_id: str
    left_column: str
    right_column: str
    join_type: str

class ProofPackage(BaseModel):
    proof_id: str
    question: str
    answer: Any
    status: Literal["verified", "failed", "inconclusive"]
    confidence: float
    evidence: List[EvidenceItem]
    computation: ComputationEvidence
    verification: VerificationEvidence
    dataset_evidence: Optional[DatasetEvidence] = None
    datasets_evidence: Optional[List[DatasetEvidence]] = None
    join_evidence: Optional[List[JoinEvidence]] = None
    provenance: ProvenanceEvidence
    hashes: HashEvidence
    limitations: List[str]
    created_at: str

class ProofRequest(BaseModel):
    dataset_id: Optional[str] = None
    dataset_ids: Optional[List[str]] = None
    question: str
    analysis_plan: dict
    generated_code: str
    execution_result: dict
    execution_metadata: Optional[dict] = None
    verification_report: dict

class IntegrityResponse(BaseModel):
    proof_id: str
    integrity_valid: bool
    stored_hash: str
    calculated_hash: str
