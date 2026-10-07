from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Any

class DatasetRelationship(BaseModel):
    left_dataset_id: str
    right_dataset_id: str
    left_column: str
    right_column: str
    relationship_type: Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many", "unknown"]
    compatibility_score: float
    confidence: Literal["high", "medium", "low", "unsafe"]
    evidence: List[str]
    warnings: List[str]

class JoinPreviewRequest(BaseModel):
    left_dataset_id: str
    right_dataset_id: str
    left_column: str
    right_column: str

class JoinPreviewResponse(BaseModel):
    left_rows: int
    right_rows: int
    matched_rows: int
    unmatched_left_rows: int
    unmatched_right_rows: int
    estimated_output_rows: int
    duplicate_key_counts: dict
    null_key_counts: dict
    join_type: str
    warnings: List[str]

class DatasetReference(BaseModel):
    dataset_id: str
    role: str

class JoinSpecification(BaseModel):
    left_dataset_id: str
    right_dataset_id: str
    left_column: str
    right_column: str
    join_type: Literal["inner", "left", "right", "outer"]

# MultiDatasetAnalysisPlan can incorporate from AnalysisPlan
class MultiDatasetAnalysisPlan(BaseModel):
    question: str
    datasets: List[DatasetReference]
    joins: List[JoinSpecification]
    target_metric: Optional[str] = None
    aggregation: Optional[str] = None
    group_by: List[str] = Field(default_factory=list)
    filters: List[Any] = Field(default_factory=list)
    calculations: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
    confidence: float
