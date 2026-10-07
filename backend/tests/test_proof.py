import pytest
import pandas as pd
import tempfile
import os
import json
from app.proof.schemas import ProofRequest
from app.proof.proof_engine import generate_proof, get_proof, check_integrity

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
    
@pytest.fixture
def base_request():
    plan = {
        "question": "What was the total revenue in the South region during 2025?",
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
    exec_result = {
        "success": True,
        "result": {"type": "scalar", "value": 700.0},
        "execution_time_ms": 150,
        "sandbox_type": "docker",
        "code_hash": "dummyhash"
    }
    ver_report = {
        "verified": True,
        "verification_status": "verified",
        "verification_method": ["independent aggregation"],
        "checks": [{"name": "test", "passed": True, "severity": "error"}],
        "expected_result": 700.0,
        "actual_result": 700.0,
        "discrepancies": [],
        "warnings": [],
        "confidence": 0.99,
        "verification_time_ms": 10.0
    }
    
    return ProofRequest(
        dataset_id="test_id",
        question=plan["question"],
        analysis_plan=plan,
        generated_code="import pandas as pd",
        execution_result=exec_result,
        verification_report=ver_report
    )

def test_proof_generation_success(temp_dataset, monkeypatch, base_request):
    monkeypatch.setattr("app.services.profiling_service.get_profile", lambda x: {"filename": "test.csv", "row_count": 5, "column_count": 5})
    
    proof = generate_proof(base_request)
    assert proof.status == "verified"
    assert proof.answer == 700.0
    assert len(proof.evidence) > 0
    assert proof.hashes.proof_package_hash is not None
    assert "region" in proof.dataset_evidence.columns_used
    assert "date" in proof.dataset_evidence.columns_used

def test_proof_generation_failed(temp_dataset, monkeypatch, base_request):
    monkeypatch.setattr("app.services.profiling_service.get_profile", lambda x: {"filename": "test.csv", "row_count": 5, "column_count": 5})
    
    # Modify request to simulate failure
    base_request.execution_result["result"]["value"] = 1000.0
    base_request.verification_report["verified"] = False
    base_request.verification_report["verification_status"] = "failed"
    
    proof = generate_proof(base_request)
    assert proof.status == "failed"
    assert proof.answer == 1000.0

def test_proof_integrity(temp_dataset, monkeypatch, base_request):
    monkeypatch.setattr("app.services.profiling_service.get_profile", lambda x: {"filename": "test.csv", "row_count": 5, "column_count": 5})
    
    proof = generate_proof(base_request)
    proof_id = proof.proof_id
    
    # Check integrity
    res = check_integrity(proof_id)
    assert res.integrity_valid is True
    
    # Tamper with file
    from app.proof.proof_engine import PROOFS_DIR
    path = os.path.join(PROOFS_DIR, f"{proof_id}.json")
    with open(path, 'r') as f:
        data = json.load(f)
        
    data["answer"] = 9999.0 # Tamper!
    
    with open(path, 'w') as f:
        json.dump(data, f)
        
    res2 = check_integrity(proof_id)
    assert res2.integrity_valid is False
