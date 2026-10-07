import pytest
import asyncio
from app.ai.router import AIRouter
from app.models.analysis_plan import AnalysisPlan
from app.core import config

class MockGeminiProvider:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        
    async def generate_analysis_plan(self, question, dataset_profile):
        if self.should_fail:
            raise Exception("Gemini API timeout")
        return AnalysisPlan(
            question=question, intent="ranking", target_metric="sales", 
            aggregation="sum", reasoning="Mock gemini", confidence=0.9
        )

class MockGrokProvider:
    async def generate_analysis_plan(self, question, dataset_profile):
        return AnalysisPlan(
            question=question, intent="ranking", target_metric="sales", 
            aggregation="sum", reasoning="Mock grok", confidence=0.8
        )

@pytest.mark.asyncio
async def test_router_success(monkeypatch):
    router = AIRouter()
    router.primary_provider_name = 'gemini'
    router.fallback_provider_name = 'grok'
    router.providers = {
        "gemini": MockGeminiProvider(should_fail=False),
        "grok": MockGrokProvider()
    }
    
    plan, metadata = await router.generate_plan("question", "profile")
    assert metadata["provider"] == "gemini"
    assert metadata["fallback_used"] is False

@pytest.mark.asyncio
async def test_router_fallback(monkeypatch):
    router = AIRouter()
    router.primary_provider_name = 'gemini'
    router.fallback_provider_name = 'grok'
    router.providers = {
        "gemini": MockGeminiProvider(should_fail=True),
        "grok": MockGrokProvider()
    }
    
    plan, metadata = await router.generate_plan("question", "profile")
    assert metadata["provider"] == "grok"
    assert metadata["fallback_used"] is True
    assert "timeout" in metadata["fallback_reason"].lower()

@pytest.mark.asyncio
async def test_both_fail(monkeypatch):
    class FailingGrok:
        async def generate_analysis_plan(self, q, p):
            raise Exception("Grok failed too")

    router = AIRouter()
    router.primary_provider_name = 'gemini'
    router.fallback_provider_name = 'grok'
    router.providers = {
        "gemini": MockGeminiProvider(should_fail=True),
        "grok": FailingGrok()
    }
    
    with pytest.raises(Exception, match="Both AI providers failed"):
        await router.generate_plan("question", "profile")
