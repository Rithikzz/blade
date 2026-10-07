from app.models.generated_code import GeneratedAnalysisCode
from abc import ABC, abstractmethod
from app.models.analysis_plan import AnalysisPlan
from typing import Dict, Any

class AIProvider(ABC):
    @abstractmethod
    async def generate_analysis_plan(
        self,
        question: str,
        dataset_profile: str
    ) -> AnalysisPlan:
        pass

    @abstractmethod
    async def generate_code(
        self,
        analysis_plan: str,
        dataset_profile: str
    ) -> GeneratedAnalysisCode:
        pass
