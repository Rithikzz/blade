from typing import Dict, Any, Optional
from .schemas import RefusalDecision, RefusalEvidence, DecisionRequest
from .rules import (
    check_empty_dataset,
    check_missing_columns,
    check_unsupported_semantics,
    check_data_quality,
    check_execution,
    check_no_matching_rows,
    check_verification
)

def evaluate_decision(req: DecisionRequest) -> RefusalDecision:
    datasets_to_use = req.dataset_ids if req.dataset_ids else ([req.dataset_id] if req.dataset_id else [])
    plan = req.analysis_plan
    question = req.question
    exec_res = req.execution_result
    ver_report = req.verification_report
    
    # Check execution and verification if they exist.
    # Note: Execution and Verification might not exist if we run this earlier,
    # but the pipeline says execute -> verify -> decision. So they should exist.
    
    checks_to_run = [
        lambda: check_empty_dataset(datasets_to_use),
        lambda: check_unsupported_semantics(question),
        lambda: check_missing_columns(datasets_to_use, plan),
        lambda: check_data_quality(datasets_to_use, plan),
    ]
    
    if exec_res:
        checks_to_run.append(lambda: check_execution(exec_res))
        checks_to_run.append(lambda: check_no_matching_rows(exec_res, plan))
        
    if ver_report:
        checks_to_run.append(lambda: check_verification(ver_report))
        
    for check_func in checks_to_run:
        res = check_func()
        if res:
            # We found a refusal reason
            evidence = RefusalEvidence(**res['evidence'])
            return RefusalDecision(
                can_answer=False,
                status="cannot_determine",
                reason_code=res['reason_code'],
                reasons=res['reasons'],
                evidence=[evidence],
                missing_information=res.get('missing_information', []),
                affected_columns=res.get('affected_columns', []),
                recommended_action=res.get('recommended_action', "Modify request."),
                confidence=0.99
            )
            
    # If all checks pass
    return RefusalDecision(
        can_answer=True,
        status="answerable",
        reason_code=None,
        reasons=[],
        evidence=[],
        missing_information=[],
        affected_columns=[],
        recommended_action="Proceed to proof generation.",
        confidence=0.99
    )
