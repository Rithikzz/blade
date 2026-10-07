import pytest
from app.refusal.schemas import DecisionRequest
from app.refusal.evaluator import evaluate_decision
import app.refusal.rules as rules

@pytest.fixture
def mock_profile(monkeypatch):
    profile_data = {
        "filename": "test.csv",
        "row_count": 100,
        "column_count": 3,
        "columns": [
            {"column_name": "id", "null_percentage": 0.0},
            {"column_name": "sales", "null_percentage": 0.1},
            {"column_name": "region", "null_percentage": 0.0}
        ]
    }
    monkeypatch.setattr("app.services.profiling_service.get_profile", lambda x: profile_data)
    return profile_data

def test_missing_column(mock_profile):
    req = DecisionRequest(
        dataset_id="test",
        question="What is the average age?",
        analysis_plan={
            "required_columns": ["age"],
            "target_metric": "age"
        },
        execution_result=None,
        verification_report=None
    )
    decision = evaluate_decision(req)
    assert decision.can_answer is False
    assert decision.status == "cannot_determine"
    assert decision.reason_code == rules.MISSING_COLUMN
    assert "age" in decision.missing_information

def test_answerable(mock_profile):
    req = DecisionRequest(
        dataset_id="test",
        question="What is the total sales?",
        analysis_plan={
            "required_columns": ["sales"],
            "target_metric": "sales"
        },
        execution_result={"success": True, "result": {"type": "scalar", "value": 100}},
        verification_report={"verification_status": "verified"}
    )
    decision = evaluate_decision(req)
    assert decision.can_answer is True
    assert decision.status == "answerable"
    assert decision.reason_code is None

def test_causality_unsupported(mock_profile):
    req = DecisionRequest(
        dataset_id="test",
        question="Did advertising cause sales to increase?",
        analysis_plan={"required_columns": ["sales"]},
        execution_result=None,
        verification_report=None
    )
    decision = evaluate_decision(req)
    assert decision.can_answer is False
    assert decision.status == "cannot_determine"
    assert decision.reason_code == rules.CAUSALITY_NOT_SUPPORTED

def test_verification_failed(mock_profile):
    req = DecisionRequest(
        dataset_id="test",
        question="What is total sales?",
        analysis_plan={"required_columns": ["sales"]},
        execution_result={"success": True},
        verification_report={"verification_status": "failed"}
    )
    decision = evaluate_decision(req)
    assert decision.can_answer is False
    assert decision.status == "cannot_determine"
    assert decision.reason_code == rules.VERIFICATION_FAILED

def test_data_quality_failure(monkeypatch):
    profile_data = {
        "filename": "test.csv",
        "row_count": 100,
        "columns": [
            {"column_name": "age", "null_percentage": 0.85},
        ]
    }
    monkeypatch.setattr("app.services.profiling_service.get_profile", lambda x: profile_data)
    
    req = DecisionRequest(
        dataset_id="test",
        question="What is average age?",
        analysis_plan={"required_columns": ["age"]},
        execution_result=None,
        verification_report=None
    )
    decision = evaluate_decision(req)
    assert decision.can_answer is False
    assert decision.status == "cannot_determine"
    assert decision.reason_code == rules.DATA_QUALITY_FAILURE

def test_execution_failed(mock_profile):
    req = DecisionRequest(
        dataset_id="test",
        question="What is total sales?",
        analysis_plan={"required_columns": ["sales"]},
        execution_result={"success": False, "error": "Crash"},
        verification_report=None
    )
    decision = evaluate_decision(req)
    assert decision.can_answer is False
    assert decision.status == "cannot_determine"
    assert decision.reason_code == rules.EXECUTION_FAILED

def test_no_matching_rows(mock_profile):
    req = DecisionRequest(
        dataset_id="test",
        question="Sales in Germany?",
        analysis_plan={
            "required_columns": ["sales", "region"],
            "filters": [{"column": "region", "operator": "equals", "value": "Germany"}]
        },
        execution_result={"success": True, "result": {"type": "dataframe", "returned_rows": 0}},
        verification_report=None
    )
    decision = evaluate_decision(req)
    assert decision.can_answer is False
    assert decision.status == "cannot_determine"
    assert decision.reason_code == rules.NO_MATCHING_ROWS

