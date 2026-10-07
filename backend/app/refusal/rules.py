from typing import Dict, Any, List, Optional
from app.services import profiling_service

# Reason Codes
MISSING_COLUMN = "MISSING_COLUMN"
EMPTY_DATASET = "EMPTY_DATASET"
NO_MATCHING_ROWS = "NO_MATCHING_ROWS"
VERIFICATION_FAILED = "VERIFICATION_FAILED"
VERIFICATION_INCONCLUSIVE = "VERIFICATION_INCONCLUSIVE"
EXECUTION_FAILED = "EXECUTION_FAILED"
SECURITY_REJECTED = "SECURITY_REJECTED"
DATA_QUALITY_FAILURE = "DATA_QUALITY_FAILURE"
EXTERNAL_INFORMATION_REQUIRED = "EXTERNAL_INFORMATION_REQUIRED"
CAUSALITY_NOT_SUPPORTED = "CAUSALITY_NOT_SUPPORTED"
PREDICTION_NOT_SUPPORTED = "PREDICTION_NOT_SUPPORTED"
MULTI_DATASET_REQUIRED = "MULTI_DATASET_REQUIRED"

# Configurable constraints
MAX_MISSING_PERCENT_FOR_CRITICAL_ANALYSIS = 0.50
MIN_ROWS_FOR_ANALYSIS = 1

def check_empty_dataset(dataset_ids: List[str]) -> Optional[Dict[str, Any]]:
    for ds_id in dataset_ids:
        profile = profiling_service.get_profile(ds_id)
        if not profile or profile.get('row_count', 0) < MIN_ROWS_FOR_ANALYSIS:
            return {
                "reason_code": EMPTY_DATASET,
                "reasons": [f"Dataset {ds_id} is empty or does not meet the minimum row count."],
                "missing_information": [],
                "affected_columns": [],
                "recommended_action": "Upload a valid dataset with data rows.",
                "evidence": {
                    "check": "empty_dataset",
                    "passed": False,
                    "severity": "error",
                    "message": f"Dataset {ds_id} has insufficient rows.",
                    "details": {"rows": profile.get('row_count', 0) if profile else 0}
                }
            }
    return None

def check_missing_columns(dataset_ids: List[str], plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    available_cols = []
    for ds_id in dataset_ids:
        profile = profiling_service.get_profile(ds_id)
        if profile:
            available_cols.extend([c['column_name'] for c in profile.get('columns', [])])
            
    required_cols = plan.get('required_columns', [])
    
    # Also check target metric and groupby and filters
    tm = plan.get('target_metric')
    if tm and tm != 'string' and tm not in required_cols:
        required_cols.append(tm)
    for g in plan.get('group_by', []):
        if g != 'string' and g not in required_cols:
            required_cols.append(g)
    for f in plan.get('filters', []):
        col = f.get('column')
        if col != 'string' and col not in required_cols:
            required_cols.append(col)
            
    missing = [col for col in required_cols if col != 'string' and col not in available_cols]
    
    if missing:
        return {
            "reason_code": MISSING_COLUMN,
            "reasons": [f"The dataset does not contain the required column(s): {', '.join(missing)}"],
            "missing_information": missing,
            "affected_columns": missing,
            "recommended_action": "Upload a dataset containing the missing information.",
            "evidence": {
                "check": "required_column",
                "passed": False,
                "severity": "error",
                "message": f"Columns missing: {', '.join(missing)}",
                "details": {"required": missing, "available": available_cols}
            }
        }
    return None

def check_execution(exec_res: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not exec_res or not exec_res.get('success'):
        return {
            "reason_code": EXECUTION_FAILED,
            "reasons": ["The analysis code failed to execute properly."],
            "missing_information": [],
            "affected_columns": [],
            "recommended_action": "Modify the question or ensure the dataset supports the requested operation.",
            "evidence": {
                "check": "execution_status",
                "passed": False,
                "severity": "error",
                "message": "Execution failed.",
                "details": {"error": exec_res.get('error') if exec_res else "No execution result"}
            }
        }
    return None

def check_no_matching_rows(exec_res: Dict[str, Any], plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not exec_res or not exec_res.get('success'): return None
    
    # If there are filters and result is a dataframe with 0 rows or None scalar for an aggregate
    filters = plan.get('filters', [])
    if filters:
        res_data = exec_res.get('result', {})
        # Depending on how the runner works, if no rows matched, sum() might be 0 or null
        # In a real scenario we'd check if the count of rows matching is 0
        if res_data.get('type') == 'dataframe' and res_data.get('returned_rows') == 0:
            return {
                "reason_code": NO_MATCHING_ROWS,
                "reasons": ["No rows matched the requested filters."],
                "missing_information": [],
                "affected_columns": [f.get('column') for f in filters],
                "recommended_action": "Adjust the filters to match existing data.",
                "evidence": {
                    "check": "filter_matches",
                    "passed": False,
                    "severity": "error",
                    "message": "Zero rows match criteria.",
                    "details": {"filters": filters}
                }
            }
    return None

def check_verification(ver_report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not ver_report:
        return None
        
    status = ver_report.get('verification_status')
    if status == 'failed':
        return {
            "reason_code": VERIFICATION_FAILED,
            "reasons": ["The calculated result could not be independently verified."],
            "missing_information": [],
            "affected_columns": [],
            "recommended_action": "The system generated an unsafe or incorrect analysis. Rephrase your question.",
            "evidence": {
                "check": "verification_status",
                "passed": False,
                "severity": "error",
                "message": "Verification failed.",
                "details": {"discrepancies": ver_report.get('discrepancies', [])}
            }
        }
    if status == 'inconclusive':
        return {
            "reason_code": VERIFICATION_INCONCLUSIVE,
            "reasons": ["The requested analysis is too complex or ambiguous to be verified deterministically."],
            "missing_information": [],
            "affected_columns": [],
            "recommended_action": "Simplify the question to standard aggregations (SUM, COUNT, etc.).",
            "evidence": {
                "check": "verification_status",
                "passed": False,
                "severity": "error",
                "message": "Verification was inconclusive.",
                "details": {"warnings": ver_report.get('warnings', [])}
            }
        }
    return None

def check_unsupported_semantics(question: str) -> Optional[Dict[str, Any]]:
    q_lower = question.lower()
    if 'cause' in q_lower or 'because of' in q_lower:
        return {
            "reason_code": CAUSALITY_NOT_SUPPORTED,
            "reasons": ["The available dataset can show association, but it does not provide sufficient evidence to establish causation."],
            "missing_information": ["causal_model"],
            "affected_columns": [],
            "recommended_action": "Rephrase to ask for correlation or descriptive statistics.",
            "evidence": {
                "check": "semantic_causality",
                "passed": False,
                "severity": "error",
                "message": "Causation requested.",
                "details": {}
            }
        }
    
    if 'will' in q_lower or 'predict' in q_lower or 'forecast' in q_lower or 'next month' in q_lower or 'future' in q_lower:
        return {
            "reason_code": PREDICTION_NOT_SUPPORTED,
            "reasons": ["The current VERITAS analysis pipeline supports evidence-backed analysis of historical data but does not have a validated forecasting model."],
            "missing_information": ["predictive_model"],
            "affected_columns": [],
            "recommended_action": "Ask about historical data instead.",
            "evidence": {
                "check": "semantic_prediction",
                "passed": False,
                "severity": "error",
                "message": "Prediction requested.",
                "details": {}
            }
        }
    return None

def check_data_quality(dataset_ids: List[str], plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    required_cols = plan.get('required_columns', [])
    tm = plan.get('target_metric')
    if tm and tm != 'string' and tm not in required_cols:
        required_cols.append(tm)
        
    for ds_id in dataset_ids:
        profile = profiling_service.get_profile(ds_id)
        if not profile: continue
        for col_info in profile.get('columns', []):
            col_name = col_info.get('column_name')
            if col_name in required_cols:
                null_pct = col_info.get('null_percentage', 0.0)
                if null_pct > MAX_MISSING_PERCENT_FOR_CRITICAL_ANALYSIS:
                    return {
                        "reason_code": DATA_QUALITY_FAILURE,
                        "reasons": [f"The {col_name} field contains too many missing values ({null_pct*100:.1f}%) to support a reliable estimate."],
                        "missing_information": [col_name],
                        "affected_columns": [col_name],
                        "recommended_action": "Clean the dataset before analysis.",
                        "evidence": {
                            "check": "data_quality",
                            "passed": False,
                            "severity": "error",
                            "message": f"Excessive missing values in {col_name}.",
                            "details": {"missing_percentage": null_pct}
                        }
                    }
    return None
