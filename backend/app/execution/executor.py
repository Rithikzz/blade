import hashlib
from app.codegen.validator import validate_code
from app.execution.sandbox import execute_in_sandbox
from app.services.dataset_service import get_dataset_path
from typing import Dict, Any

from app.execution.schemas import ExecuteRequest
from app.services.profiling_service import get_profile

def execute_analysis(request: ExecuteRequest) -> Dict[str, Any]:
    # 1. Static Validation
    try:
        validate_code(request.code)
    except ValueError as e:
        return {"success": False, "error": f"Security validation failed: {str(e)}"}
        
    # 2. Collect Datasets
    datasets_to_use = request.dataset_ids if request.dataset_ids else ([request.dataset_id] if request.dataset_id else [])
    if not datasets_to_use:
         return {"success": False, "error": "No dataset specified."}
         
    dataset_paths = {}
    for ds_id in datasets_to_use:
        dataset_path = get_dataset_path(ds_id)
        if not dataset_path:
            return {"success": False, "error": f"Dataset {ds_id} not found on disk."}
        profile = get_profile(ds_id)
        original_filename = Path(dataset_path).name # fallback
        var_name = "df" # fallback for single dataset
        if profile and "filename" in profile:
             original_filename = profile["filename"]
             var_name = original_filename.rsplit(".", 1)[0]
             # safe var name
             import re
             var_name = re.sub(r'[^a-zA-Z0-9_]', '_', var_name)
        dataset_paths[ds_id] = {"path": dataset_path, "var_name": var_name, "original_filename": original_filename}
        
    # 3. Code Hash
    code_hash = hashlib.sha256(request.code.encode('utf-8')).hexdigest()
    
    # 4. Sandbox Execution
    sandbox_result = execute_in_sandbox(dataset_paths, request.code)
    
    # 5. Format Result
    sandbox_result["dataset_id"] = request.dataset_id
    sandbox_result["dataset_ids"] = request.dataset_ids
    sandbox_result["code_hash"] = code_hash
    
    if "execution_time_ms" not in sandbox_result:
        sandbox_result["execution_time_ms"] = 0
    if "truncated" not in sandbox_result:
        sandbox_result["truncated"] = False
        
    return sandbox_result
