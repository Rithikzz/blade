from pydantic import BaseModel
from typing import Any, Dict, Optional, List

class ExecuteRequest(BaseModel):
    dataset_id: Optional[str] = None
    dataset_ids: Optional[List[str]] = None
    code: str

class ExecutionResult(BaseModel):
    success: bool
    execution_time_ms: int
    result: Optional[Dict[str, Any]] = None
    dataset_id: Optional[str] = None
    dataset_ids: Optional[List[str]] = None
    code_hash: str
    truncated: bool
    sandbox_type: str
    error: Optional[str] = None
