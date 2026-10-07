import pytest
import pandas as pd
import tempfile
import os
from app.verification.schemas import VerifyRequest
from app.verification.verifier import verify_execution

@pytest.fixture
def temp_dataset():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        # date,region,product,revenue,quantity
        df = pd.DataFrame({
            "date": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-02-01", "2026-01-01"],
            "region": ["South", "South", "North", "South", "South"],
            "product": ["A", "B", "A", "A", "C"],
            "revenue": [100, 200, 300, 400, 500],
            "quantity": [2, 4, 6, 8, 10]
        })
        df.to_csv(f.name, index=False)
        path = f.name
    yield path
    os.remove(path)

def test_verify_success_scalar(temp_dataset, monkeypatch):
    monkeypatch.setattr("app.verification.verifier.get_dataset_path", lambda x: temp_dataset)
    
    plan = {
        "question": "What is the total revenue for the South region in 2025?",
        "intent": "aggregation",
        "target_metric": "revenue",
        "aggregation": "sum",
        "filters": [
            {"column": "region", "operator": "equals", "value": "South"}
        ],
        "time_range": {
            "column": "date",
            "start": "2025-01-01",
            "end": "2025-12-31"
        }
    }
    
    # 100 + 200 + 400 = 700
    execution_result = {
        "success": True,
        "result": {"type": "scalar", "value": 700.0}
    }
    
    request = VerifyRequest(
        dataset_id="test_id",
        question="What is the total revenue for the South region in 2025?",
        analysis_plan=plan,
        generated_code="dummy code",
        execution_result=execution_result
    )
    
    report = verify_execution(request)
    assert report.verified is True
    assert report.verification_status == "verified"
    assert report.expected_result == 700.0
    assert len(report.discrepancies) == 0

def test_verify_failure_scalar(temp_dataset, monkeypatch):
    monkeypatch.setattr("app.verification.verifier.get_dataset_path", lambda x: temp_dataset)
    
    plan = {
        "question": "What is the total revenue for the South region in 2025?",
        "intent": "aggregation",
        "target_metric": "revenue",
        "aggregation": "sum",
        "filters": [
            {"column": "region", "operator": "equals", "value": "South"}
        ],
        "time_range": {
            "column": "date",
            "start": "2025-01-01",
            "end": "2025-12-31"
        }
    }
    
    # Intentionally wrong execution result (e.g. ignored filters)
    execution_result = {
        "success": True,
        "result": {"type": "scalar", "value": 1500.0}
    }
    
    request = VerifyRequest(
        dataset_id="test_id",
        question="What is the total revenue for the South region in 2025?",
        analysis_plan=plan,
        generated_code="dummy code",
        execution_result=execution_result
    )
    
    report = verify_execution(request)
    assert report.verified is False
    assert report.verification_status == "failed"
    assert len(report.discrepancies) > 0

def test_verify_success_groupby(temp_dataset, monkeypatch):
    monkeypatch.setattr("app.verification.verifier.get_dataset_path", lambda x: temp_dataset)
    
    plan = {
        "question": "What is the total revenue by region?",
        "intent": "aggregation",
        "target_metric": "revenue",
        "aggregation": "sum",
        "group_by": ["region"],
        "sort": {"column": "revenue", "direction": "desc"}
    }
    
    # South: 100+200+400+500 = 1200
    # North: 300
    # Sorted descending by revenue
    execution_result = {
        "success": True,
        "result": {
            "type": "dataframe",
            "columns": ["region", "revenue"],
            "rows": [
                ["South", 1200.0],
                ["North", 300.0]
            ],
            "returned_rows": 2,
            "total_rows": 2
        }
    }
    
    request = VerifyRequest(
        dataset_id="test_id",
        question="What is the total revenue by region?",
        analysis_plan=plan,
        generated_code="dummy code",
        execution_result=execution_result
    )
    
    report = verify_execution(request)
    assert report.verified is True
    assert report.verification_status == "verified"

def test_verify_inconclusive(temp_dataset, monkeypatch):
    monkeypatch.setattr("app.verification.verifier.get_dataset_path", lambda x: temp_dataset)
    
    # Unsupported plan structure
    plan = {
        "question": "Show the distribution of revenue",
        "intent": "distribution",
        "target_metric": "revenue",
        # Missing aggregation, etc.
    }
    
    execution_result = {
        "success": True,
        "result": {"type": "dataframe", "rows": [[1]], "columns": ["revenue"]}
    }
    
    request = VerifyRequest(
        dataset_id="test_id",
        question="Show the distribution of revenue",
        analysis_plan=plan,
        generated_code="dummy code",
        execution_result=execution_result
    )
    
    report = verify_execution(request)
    assert report.verified is False
    assert report.verification_status == "inconclusive"
