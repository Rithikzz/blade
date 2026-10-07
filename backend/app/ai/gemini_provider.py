import json
from google import genai
from google.genai import types
from app.ai.base import AIProvider
from app.models.analysis_plan import AnalysisPlan
from app.models.generated_code import GeneratedAnalysisCode
from app.codegen.prompts import CODE_GENERATION_PROMPT
from app.core import config

class GeminiProvider(AIProvider):
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.model = config.GEMINI_MODEL
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    async def generate_analysis_plan(
        self,
        question: str,
        dataset_profile: str
    ) -> AnalysisPlan:
        if not self.client:
            raise ValueError("Gemini API key not configured")
        
        prompt = f"""
        You are VERITAS, an AI Question Planner. 
        Analyze the user's question and the dataset profile to generate a structured analysis plan.
        Detect any missing columns or ambiguities and list them. Do not fabricate columns.
        
        Dataset Profile:
        {dataset_profile}
        
        Question:
        {question}
        """

        try:
            # We'll use the async version of the client
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AnalysisPlan,
                    temperature=0.1
                )
            )
            plan_data = json.loads(response.text)
            return AnalysisPlan(**plan_data)
        except Exception as e:
            raise Exception(f"Gemini API Error: {str(e)}")

    async def generate_code(
        self,
        analysis_plan: str,
        dataset_profile: str
    ) -> GeneratedAnalysisCode:
        if not self.client:
            raise ValueError("Gemini API key not configured")
        
        prompt = CODE_GENERATION_PROMPT.format(
            dataset_profile=dataset_profile,
            analysis_plan=analysis_plan
        )
        try:
            import json
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeneratedAnalysisCode,
                    temperature=0.1
                )
            )
            data = json.loads(response.text)
            return GeneratedAnalysisCode(**data)
        except Exception as e:
            raise Exception(f"Gemini API Error: {str(e)}")
