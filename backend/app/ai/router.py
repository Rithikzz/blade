import asyncio
import logging
from typing import Dict, Any, Tuple
from app.ai.gemini_provider import GeminiProvider
from app.ai.grok_provider import GrokProvider
from app.ai.ollama_provider import OllamaProvider
from app.models.analysis_plan import AnalysisPlan
from app.models.generated_code import GeneratedAnalysisCode
from app.core import config

logger = logging.getLogger(__name__)

class AIRouter:
    def __init__(self):
        self.primary_provider_name = config.AI_PRIMARY_PROVIDER
        self.fallback_provider_name = config.AI_FALLBACK_PROVIDER
        self.timeout = config.AI_TIMEOUT_SECONDS

        self.providers = {
            "gemini": GeminiProvider(),
            "grok": GrokProvider(),
            "ollama": OllamaProvider()
        }

    async def generate_plan(self, question: str, dataset_profile: str) -> Tuple[AnalysisPlan, Dict[str, Any]]:
        primary = self.providers.get(self.primary_provider_name)
        fallback = self.providers.get(self.fallback_provider_name)

        if not primary:
            raise ValueError(f"Primary provider {self.primary_provider_name} not found.")

        # Attempt Primary
        try:
            logger.info(f"Attempting primary provider: {self.primary_provider_name}")
            plan = await asyncio.wait_for(
                primary.generate_analysis_plan(question, dataset_profile),
                timeout=self.timeout
            )
            return plan, {
                "provider": self.primary_provider_name,
                "fallback_used": False
            }
        except Exception as e:
            logger.warning(f"Primary provider ({self.primary_provider_name}) failed: {str(e)}")
            if isinstance(e, asyncio.TimeoutError):
                fallback_reason = "Timeout exceeded"
            else:
                fallback_reason = str(e)
            
            if not fallback:
                raise Exception(f"Primary provider failed and no fallback available. Error: {fallback_reason}")

            # Attempt Fallback
            try:
                logger.info(f"Attempting fallback provider: {self.fallback_provider_name}")
                plan = await asyncio.wait_for(
                    fallback.generate_analysis_plan(question, dataset_profile),
                    timeout=self.timeout
                )
                return plan, {
                    "provider": self.fallback_provider_name,
                    "fallback_used": True,
                    "fallback_reason": fallback_reason
                }
            except Exception as fallback_err:
                logger.error(f"Fallback provider ({self.fallback_provider_name}) also failed: {str(fallback_err)}")
                raise Exception(f"Both AI providers failed. Primary error: {fallback_reason}. Fallback error: {str(fallback_err)}")

    async def generate_code(self, analysis_plan: str, dataset_profile: str) -> Tuple[GeneratedAnalysisCode, Dict[str, Any]]:
        primary = self.providers.get(self.primary_provider_name)
        fallback = self.providers.get(self.fallback_provider_name)
        
        if not primary:
            raise ValueError(f"Primary provider {self.primary_provider_name} not found.")
            
        try:
            logger.info(f"Attempting primary provider for code gen: {self.primary_provider_name}")
            code_res = await asyncio.wait_for(
                primary.generate_code(analysis_plan, dataset_profile),
                timeout=self.timeout
            )
            return code_res, {"provider": self.primary_provider_name, "fallback_used": False}
        except Exception as e:
            logger.warning(f"Primary provider code gen failed: {str(e)}")
            if isinstance(e, asyncio.TimeoutError):
                fallback_reason = "Timeout exceeded"
            else:
                fallback_reason = str(e)
            if not fallback:
                raise Exception(f"Primary provider failed and no fallback available. Error: {fallback_reason}")
                
            try:
                logger.info(f"Attempting fallback provider for code gen: {self.fallback_provider_name}")
                code_res = await asyncio.wait_for(
                    fallback.generate_code(analysis_plan, dataset_profile),
                    timeout=self.timeout
                )
                return code_res, {"provider": self.fallback_provider_name, "fallback_used": True, "fallback_reason": fallback_reason}
            except Exception as fallback_err:
                logger.error(f"Fallback provider code gen failed: {str(fallback_err)}")
                raise Exception(f"Both AI providers failed. Primary: {fallback_reason}. Fallback: {str(fallback_err)}")
