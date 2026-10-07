import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone
from app.services import profiling_service

from .schemas import (
    ProofPackage,
    EvidenceItem,
    ComputationEvidence,
    VerificationEvidence,
    DatasetEvidence,
    ProvenanceEvidence,
    HashEvidence,
    ProofRequest
)
from .hashing import sha256_json, generate_code_hash

def build_proof_package(request: ProofRequest) -> ProofPackage:
    proof_id = f"proof_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
    
    plan = request.analysis_plan
    ver = request.verification_report
    exec_res = request.execution_result
    
    datasets_to_use = request.dataset_ids if request.dataset_ids else ([request.dataset_id] if request.dataset_id else [])
    
    datasets_evidence = []
    evidence_items = []
    
    for ds_id in datasets_to_use:
        profile = profiling_service.get_profile(ds_id) or {}
        
        # Extract columns used (simplified for multi-dataset, just all plan columns for now)
        cols_used = set()
        if plan.get('target_metric') and plan['target_metric'] != 'string':
            cols_used.add(plan['target_metric'])
        for gb in plan.get('group_by', []):
            if gb != 'string': cols_used.add(gb)
        for f in plan.get('filters', []):
            if f.get('column') != 'string': cols_used.add(f.get('column'))
        time_col = plan.get('time_range', {}).get('column') if plan.get('time_range') else None
        if time_col and time_col != 'string': cols_used.add(time_col)
        
        # also add join columns
        for j in plan.get('joins', []):
             if j['left_dataset_id'] == ds_id: cols_used.add(j['left_column'])
             if j['right_dataset_id'] == ds_id: cols_used.add(j['right_column'])
             
        ds_ev = DatasetEvidence(
            dataset_id=ds_id,
            filename=profile.get('filename', 'unknown'),
            row_count=profile.get('row_count', 0),
            column_count=profile.get('column_count', 0),
            columns_used=list(cols_used)
        )
        datasets_evidence.append(ds_ev)
        
        evidence_items.append(EvidenceItem(
            id=uuid.uuid4().hex[:8],
            type="dataset",
            title=f"Source dataset: {ds_ev.filename}",
            description="Analysis was performed against this dataset.",
            status="passed",
            details={
                "dataset_id": ds_ev.dataset_id,
                "filename": ds_ev.filename,
                "rows": ds_ev.row_count,
                "columns": ds_ev.column_count
            }
        ))
        
    dataset_ev = datasets_evidence[0] if datasets_evidence else None
    
    join_evidence = []
    for j in plan.get('joins', []):
        from .schemas import JoinEvidence
        join_evidence.append(JoinEvidence(
            left_dataset_id=j['left_dataset_id'],
            right_dataset_id=j['right_dataset_id'],
            left_column=j['left_column'],
            right_column=j['right_column'],
            join_type=j['join_type']
        ))
        
        evidence_items.append(EvidenceItem(
            id=uuid.uuid4().hex[:8],
            type="calculation", # Using existing valid literal
            title="Dataset Join",
            description=f"Joined {j['left_dataset_id']} with {j['right_dataset_id']} on {j['left_column']}={j['right_column']}",
            status="passed",
            details=j
        ))
    
    # 2. Filter & Date Evidence
    step_num = 1
    comp_steps = []
    for idx, f in enumerate(plan.get('filters', [])):
        if f.get('column') == 'string': continue
        evidence_items.append(EvidenceItem(
            id=uuid.uuid4().hex[:8],
            type="filter",
            title=f"Filter: {f['column']}",
            description=f"Applied condition: {f['operator']} {f['value']}",
            status="passed",
            details=f
        ))
        comp_steps.append({
            "step": step_num,
            "operation": "filter",
            "description": f"Keep rows where {f['column']} {f['operator']} {f['value']}"
        })
        step_num += 1
        
    tr = plan.get('time_range')
    if tr and tr.get('column') and tr.get('column') != 'string':
        evidence_items.append(EvidenceItem(
            id=uuid.uuid4().hex[:8],
            type="filter",
            title="Time Range Filter",
            description=f"Applied date range on {tr['column']}",
            status="passed",
            details=tr
        ))
        comp_steps.append({
            "step": step_num,
            "operation": "date_filter",
            "description": f"Keep rows between {tr.get('start', 'any')} and {tr.get('end', 'any')}"
        })
        step_num += 1
        
    # 3. Aggregation Evidence
    agg = plan.get('aggregation')
    tm = plan.get('target_metric')
    if agg and tm and tm != 'string':
        desc = f"{agg.upper()}({tm})"
        evidence_items.append(EvidenceItem(
            id=uuid.uuid4().hex[:8],
            type="aggregation",
            title="Aggregation",
            description=desc,
            status="passed",
            details={"aggregation": agg, "target_metric": tm}
        ))
        comp_steps.append({
            "step": step_num,
            "operation": "aggregation",
            "description": desc
        })
        step_num += 1
        
    gb = [g for g in plan.get('group_by', []) if g != 'string']
    if gb:
        evidence_items.append(EvidenceItem(
            id=uuid.uuid4().hex[:8],
            type="grouping",
            title="Group By",
            description=f"Grouped by {', '.join(gb)}",
            status="passed",
            details={"group_by": gb}
        ))
        
    # Verification Evidence Item
    evidence_items.append(EvidenceItem(
        id=uuid.uuid4().hex[:8],
        type="verification",
        title="Independent Verification",
        description=f"Result independently computed and compared. Expected: {ver.get('expected_result')}, Actual: {ver.get('actual_result')}",
        status="passed" if ver.get('verified') else ("warning" if ver.get('verification_status') == 'inconclusive' else "failed"),
        details={"checks": ver.get("checks", [])}
    ))
    
    # Limitations
    limitations = [
        "Analysis is based only on the uploaded dataset.",
        "Missing values may affect the calculation.",
        "The result does not establish causation."
    ]
    if ver.get('verification_status') == 'inconclusive':
        limitations.append("Unsupported analysis types cannot receive full verification.")
        
    checks_passed = sum(1 for c in ver.get('checks', []) if c.get('passed') and c.get('severity') == 'error')
    checks_failed = sum(1 for c in ver.get('checks', []) if not c.get('passed') and c.get('severity') == 'error')
    
    verification_ev = VerificationEvidence(
        status=ver.get('verification_status', 'inconclusive'),
        methods=ver.get('verification_method', []),
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        confidence=ver.get('confidence', 0.0),
        discrepancies=ver.get('discrepancies', []),
        verification_time_ms=ver.get('verification_time_ms', 0.0)
    )
    
    provenance_ev = ProvenanceEvidence(
        code_language="python",
        libraries=["pandas", "numpy", "duckdb"], # Hardcoded for now based on runner template
        execution_time_ms=exec_res.get('execution_time_ms', 0.0),
        sandbox_type=exec_res.get('sandbox_type', 'unknown'),
        result_type=exec_res.get('result', {}).get('type', 'unknown'),
        result_truncated=exec_res.get('truncated', False)
    )
    
    plan_hash = sha256_json(plan)
    exec_hash = sha256_json(exec_res)
    ver_hash = sha256_json(ver)
    code_hash = generate_code_hash(request.generated_code)
    
    hash_ev = HashEvidence(
        code_hash=code_hash,
        plan_hash=plan_hash,
        execution_hash=exec_hash,
        verification_hash=ver_hash
    )
    
    ans = exec_res.get('result', {}).get('value')
    if ans is None:
        ans = exec_res.get('result', {})
        
    proof = ProofPackage(
        proof_id=proof_id,
        question=request.question,
        answer=ans,
        status=ver.get('verification_status', 'inconclusive'),
        confidence=ver.get('confidence', 0.0),
        evidence=evidence_items,
        computation=ComputationEvidence(steps=comp_steps),
        verification=verification_ev,
        dataset_evidence=dataset_ev,
        datasets_evidence=datasets_evidence,
        join_evidence=join_evidence,
        provenance=provenance_ev,
        hashes=hash_ev,
        limitations=limitations,
        created_at=datetime.now(timezone.utc).isoformat()
    )
    
    # Calculate self hash
    proof_dict = proof.model_dump()
    proof_dict['hashes']['proof_package_hash'] = None
    proof.hashes.proof_package_hash = sha256_json(proof_dict)
    
    return proof
