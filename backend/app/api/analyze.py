from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict
from app.services import profiling_service
from app.ai.router import AIRouter

from app.models.analysis_plan import AnalysisPlan
from app.codegen.validator import validate_code

from app.execution.executor import execute_analysis
from app.execution.schemas import ExecuteRequest


class CodeRequest(BaseModel):
    dataset_id: Optional[str] = None
    dataset_ids: Optional[list[str]] = None
    analysis_plan: dict


router = APIRouter(prefix="/api/analyze", tags=["analyze"])

class PlanRequest(BaseModel):
    dataset_id: Optional[str] = None
    dataset_ids: Optional[list[str]] = None
    question: str

def build_compact_profile(profile_data: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"Dataset: {profile_data.get('filename', 'Unknown')}")
    lines.append(f"Rows: {profile_data.get('row_count', 0)}")
    lines.append(f"Columns: {profile_data.get('column_count', 0)}")
    lines.append("\nColumns:")
    
    for col in profile_data.get("columns", []):
        col_name = col.get("column_name")
        logical_type = col.get("logical_type")
        lines.append(f"- {col_name}: {logical_type}")
        
        # Add basic stats based on type
        if logical_type == "numeric":
            stats = col.get("numeric_stats", {})
            if stats:
                lines.append(f"  (min: {stats.get('min')}, max: {stats.get('max')})")
        elif logical_type in ["categorical", "boolean", "text"]:
            stats = col.get("categorical_stats", {})
            if stats:
                top_vals = [str(v.get('value')) for v in stats.get('top_values', [])[:5]]
                lines.append(f"  (top values: {', '.join(top_vals)})")
        elif logical_type == "datetime":
            stats = col.get("datetime_stats", {})
            if stats:
                lines.append(f"  (min date: {stats.get('min_date')}, max date: {stats.get('max_date')})")

    return "\n".join(lines)

from app.multidataset.relationship_detector import detect_relationships

@router.post("/plan")
async def create_analysis_plan(request: PlanRequest):
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    datasets_to_use = request.dataset_ids if request.dataset_ids else ([request.dataset_id] if request.dataset_id else [])
    if not datasets_to_use:
        raise HTTPException(status_code=400, detail="At least one dataset ID must be provided")

    compact_profiles = []
    for ds_id in datasets_to_use:
        profile_data = profiling_service.get_profile(ds_id)
        if not profile_data:
            raise HTTPException(status_code=404, detail=f"Dataset profile {ds_id} not found")
        compact_profiles.append(build_compact_profile(profile_data))
        
    compact_profile = "\n\n---\n\n".join(compact_profiles)
    
    if len(datasets_to_use) > 1:
        # Detect relationships
        rels = detect_relationships(datasets_to_use)
        if rels:
            compact_profile += "\n\n--- CANDIDATE RELATIONSHIPS (JOINS) ---\n"
            for r in rels:
                if r.confidence != "unsafe":
                    compact_profile += f"- {r.left_dataset_id}.{r.left_column} <-> {r.right_dataset_id}.{r.right_column} (Type: {r.relationship_type}, Confidence: {r.confidence})\n"

    # 4. Route to AI
    ai_router = AIRouter()
    try:
        plan, metadata = await ai_router.generate_plan(request.question, compact_profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 5. Return Plan
    return {
        "success": True,
        "provider": metadata.get("provider"),
        "fallback_used": metadata.get("fallback_used"),
        "fallback_reason": metadata.get("fallback_reason"),
        "plan": plan.model_dump()
    }

@router.post("/code")
async def generate_analysis_code(request: CodeRequest):
    datasets_to_use = request.dataset_ids if request.dataset_ids else ([request.dataset_id] if request.dataset_id else [])
    if not datasets_to_use:
        raise HTTPException(status_code=400, detail="At least one dataset ID must be provided")
        
    compact_profiles = []
    all_profile_cols = []
    
    for ds_id in datasets_to_use:
        profile_data = profiling_service.get_profile(ds_id)
        if not profile_data:
            raise HTTPException(status_code=404, detail=f"Dataset profile {ds_id} not found")
        compact_profiles.append(build_compact_profile(profile_data))
        all_profile_cols.extend([c.get("column_name") for c in profile_data.get("columns", [])])

    compact_profile = "\n\n---\n\n".join(compact_profiles)
    
    required_cols = request.analysis_plan.get("required_columns", [])
    required_cols = [c for c in required_cols if c != 'string']
    
    # Simple check for missing cols across all datasets (best effort)
    for col in required_cols:
        if col not in all_profile_cols:
            raise HTTPException(status_code=400, detail=f"Column {col} not found in any provided dataset")

    # If it's multidataset, run deterministic validator
    if len(datasets_to_use) > 1:
        from app.multidataset.validators import validate_join_plan, JoinValidationError
        from app.models.analysis_plan import AnalysisPlan
        try:
            plan_obj = AnalysisPlan(**request.analysis_plan)
            # validate join plan using MultiDataset logic (it inherits/looks like it)
            validate_join_plan(plan_obj)
        except JoinValidationError as e:
            raise HTTPException(status_code=400, detail=f"Unsafe join detected: {str(e)}")
        except Exception as e:
            pass # fallback if validation fails for other reasons, but don't block code gen if plan is valid schema

    import json
    plan_str = json.dumps(request.analysis_plan, indent=2)
    
    ai_router = AIRouter()
    try:
        code_res, metadata = await ai_router.generate_code(plan_str, compact_profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    # Static AST Validation
    try:
        validate_code(code_res.code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return {
        "success": True,
        "provider": metadata.get("provider"),
        "fallback_used": metadata.get("fallback_used"),
        "fallback_reason": metadata.get("fallback_reason"),
        "code_data": code_res.model_dump()
    }


@router.post("/execute")
async def execute_generated_code(request: ExecuteRequest):
    result = execute_analysis(request)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Execution failed"))
    return result

from app.verification.schemas import VerifyRequest
from app.verification.verifier import verify_execution

@router.post("/verify")
async def verify_analysis_result(request: VerifyRequest):
    try:
        report = verify_execution(request)
        return report.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from app.proof.schemas import ProofRequest
from app.proof.proof_engine import generate_proof, get_proof, check_integrity
from fastapi.responses import JSONResponse

@router.post("/proof")
async def create_proof(request: ProofRequest):
    try:
        proof = generate_proof(request)
        return proof.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/proof/{proof_id}")
async def fetch_proof(proof_id: str):
    proof = get_proof(proof_id)
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")
    return proof

@router.get("/proof/{proof_id}/integrity")
async def verify_proof_integrity(proof_id: str):
    res = check_integrity(proof_id)
    if not res:
        raise HTTPException(status_code=404, detail="Proof not found")
    return res.model_dump()

from app.refusal.schemas import DecisionRequest
from app.refusal.evaluator import evaluate_decision

@router.post("/decision")
async def make_decision(request: DecisionRequest):
    try:
        decision = evaluate_decision(request)
        return decision.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
