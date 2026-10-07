from pydantic import BaseModel, Field
from typing import List, Optional, Union

class SortConfig(BaseModel):
    column: str
    direction: str = Field(pattern="^(asc|desc)$")

class FilterConfig(BaseModel):
    column: str
    operator: str
    value: str  # Kept as str to avoid 'Any' schema issues

class TimeRangeConfig(BaseModel):
    column: str
    start: Optional[str] = None
    end: Optional[str] = None

class DatasetReference(BaseModel):
    dataset_id: str
    role: str

class JoinSpecification(BaseModel):
    left_dataset_id: str
    right_dataset_id: str
    left_column: str
    right_column: str
    join_type: str = Field(pattern="^(inner|left|right|outer)$")

class AnalysisPlan(BaseModel):
    question: str
    intent: str
    datasets: Optional[List[DatasetReference]] = Field(default_factory=list)
    joins: Optional[List[JoinSpecification]] = Field(default_factory=list)
    target_metric: Optional[str] = None
    aggregation: Optional[str] = None
    group_by: List[str] = Field(default_factory=list)
    filters: List[FilterConfig] = Field(default_factory=list)
    sort: Optional[SortConfig] = None
    limit: Optional[int] = None
    required_columns: List[str] = Field(default_factory=list)
    time_range: Optional[TimeRangeConfig] = None
    calculations: List[str] = Field(default_factory=list)
    reasoning: str
    ambiguities: List[str] = Field(default_factory=list)
    confidence: float
    assumptions: List[str] = Field(default_factory=list)
