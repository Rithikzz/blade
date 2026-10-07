from pydantic import BaseModel, Field
from typing import List

class GeneratedAnalysisCode(BaseModel):
    code: str
    language: str = "python"
    libraries: List[str] = Field(default_factory=list)
    result_type: str
    result_description: str
    columns_used: List[str] = Field(default_factory=list)
    operations: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
