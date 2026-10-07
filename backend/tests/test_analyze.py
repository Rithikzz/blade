import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ai.router import AIRouter
from app.models.analysis_plan import AnalysisPlan

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200

# Mock router for plan generation
class MockAIRouter:
    async def generate_plan(self, question, dataset_profile):
        if "timeout" in question.lower():
            raise Exception("Timeout simulated")
        
        return AnalysisPlan(
            question=question,
            intent="ranking",
            target_metric="sales",
            aggregation="sum",
            group_by=["product"],
            filters=[],
            required_columns=["product", "sales"],
            reasoning="Mock reasoning",
            confidence=0.9
        ), {"provider": "gemini", "fallback_used": False, "fallback_reason": None}

def test_analyze_plan(monkeypatch):
    monkeypatch.setattr("app.api.analyze.AIRouter", lambda: MockAIRouter())
    
    # We need to mock profiling_service.get_profile
    monkeypatch.setattr("app.api.analyze.profiling_service.get_profile", lambda x: {"filename": "test.csv", "row_count": 100, "column_count": 2})

    response = client.post("/api/analyze/plan", json={
        "dataset_id": "test_id",
        "question": "Which product had highest sales?"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["provider"] == "gemini"
    assert data["plan"]["intent"] == "ranking"
