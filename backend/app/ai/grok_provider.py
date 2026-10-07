import json
from openai import AsyncOpenAI
from app.ai.base import AIProvider
from app.models.analysis_plan import AnalysisPlan
from app.models.generated_code import GeneratedAnalysisCode
from app.codegen.prompts import CODE_GENERATION_PROMPT
from app.core import config

class GrokProvider(AIProvider):
    def __init__(self):
        self.api_key = config.GROK_API_KEY
        self.model = config.GROK_MODEL
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.x.ai/v1"
            )
        else:
            self.client = None

    async def generate_analysis_plan(
        self,
        question: str,
        dataset_profile: str
    ) -> AnalysisPlan:
        if not self.client:
            raise ValueError("Grok API key not configured")
        
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
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analysis planning assistant."},
                    {"role": "user", "content": prompt}
                ],
                response_format=AnalysisPlan,
                temperature=0.1
            )
            
            plan_obj = response.choices[0].message.parsed
            if plan_obj is None:
                plan_data = json.loads(response.choices[0].message.content)
                return AnalysisPlan(**plan_data)
            return plan_obj
        except Exception as e:
            raise Exception(f"Grok API Error: {str(e)}")

    async def generate_code(
        self,
        analysis_plan: str,
        dataset_profile: str
    ) -> GeneratedAnalysisCode:
        if not self.client:
            raise ValueError("Grok API key not configured")
        
        prompt = CODE_GENERATION_PROMPT.format(
            dataset_profile=dataset_profile,
            analysis_plan=analysis_plan
        )

        try:
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a code generation assistant."},
                    {"role": "user", "content": prompt}
                ],
                response_format=GeneratedAnalysisCode,
                temperature=0.1
            )
            
            code_obj = response.choices[0].message.parsed
            if code_obj is None:
                import json
                code_data = json.loads(response.choices[0].message.content)
                return GeneratedAnalysisCode(**code_data)
            return code_obj
        except Exception as e:
            raise Exception(f"Grok API Error: {str(e)}")
