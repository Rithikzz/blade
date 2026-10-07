import json
from openai import AsyncOpenAI
from app.ai.base import AIProvider
from app.models.analysis_plan import AnalysisPlan
from app.models.generated_code import GeneratedAnalysisCode
from app.codegen.prompts import CODE_GENERATION_PROMPT
from app.core import config
import logging

logger = logging.getLogger(__name__)

class OllamaProvider(AIProvider):
    def __init__(self):
        self.model = config.OLLAMA_MODEL
        self.base_url = config.OLLAMA_BASE_URL
        self.client = AsyncOpenAI(
            api_key="ollama", # API key is required by the SDK but ignored by Ollama
            base_url=self.base_url
        )

    async def generate_analysis_plan(
        self,
        question: str,
        dataset_profile: str
    ) -> AnalysisPlan:
        prompt = f"""
        You are VERITAS, an AI Question Planner. 
        Analyze the user's question and the dataset profile to generate a structured analysis plan.
        Detect any missing columns or ambiguities and list them. Do not fabricate columns.
        
        Dataset Profile:
        {dataset_profile}
        
        Question:
        {question}
        
        Return ONLY valid JSON matching this schema:
        {{
            "question": "string",
            "intent": "string",
            "datasets": [
                {{"dataset_id": "string", "role": "string"}}
            ],
            "joins": [
                {{"left_dataset_id": "string", "right_dataset_id": "string", "left_column": "string", "right_column": "string", "join_type": "inner|left|right|outer"}}
            ],
            "target_metric": "string or null",
            "aggregation": "string or null",
            "group_by": ["string"],
            "filters": [
                {{"column": "string", "operator": "string", "value": "string"}}
            ],
            "sort": {{"column": "string", "direction": "asc or desc"}} or null,
            "limit": integer or null,
            "required_columns": ["string"],
            "time_range": {{"column": "string", "start": "string", "end": "string"}} or null,
            "calculations": ["string"],
            "reasoning": "string",
            "ambiguities": ["string"],
            "confidence": float between 0 and 1,
            "assumptions": ["string"]
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analysis planning assistant. Always output JSON without markdown blocks."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            plan_data = json.loads(content.strip())
            for field in ['group_by', 'filters', 'required_columns', 'calculations', 'ambiguities', 'assumptions']:
                if plan_data.get(field) is None:
                    plan_data[field] = []
            if plan_data.get('reasoning') is None:
                plan_data['reasoning'] = "Model provided no reasoning."
            if plan_data.get('confidence') is None:
                plan_data['confidence'] = 0.5
            
            if plan_data.get('sort'):
                if plan_data['sort'].get('direction') not in ['asc', 'desc']:
                    plan_data['sort']['direction'] = 'desc'
                    
            if 'string' in plan_data.get('required_columns', []):
                plan_data['required_columns'].remove('string')
            if 'string' in plan_data.get('group_by', []):
                plan_data['group_by'].remove('string')
                
            # Clean up dummy dicts that Ollama might spit out verbatim
            for ds in list(plan_data.get('datasets', [])):
                if isinstance(ds, str) or ds.get('dataset_id') == 'string':
                    plan_data['datasets'].remove(ds)
            for jn in list(plan_data.get('joins', [])):
                if isinstance(jn, str) or jn.get('left_dataset_id') == 'string':
                    plan_data['joins'].remove(jn)
            for flt in list(plan_data.get('filters', [])):
                if isinstance(flt, str) or flt.get('column') == 'string':
                    plan_data['filters'].remove(flt)
                
            return AnalysisPlan(**plan_data)
        except Exception as e:
            logger.error(f"Ollama API Error: {str(e)}")
            raise Exception(f"Ollama API Error: {str(e)}")

    async def generate_code(
        self,
        analysis_plan: str,
        dataset_profile: str
    ) -> GeneratedAnalysisCode:
        prompt = CODE_GENERATION_PROMPT.format(
            dataset_profile=dataset_profile,
            analysis_plan=analysis_plan
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a safe code generator. Always output JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            content = response.choices[0].message.content
            if content.startswith("```json"): content = content[7:]
            if content.endswith("```"): content = content[:-3]
            data = json.loads(content.strip())
            
            for list_field in ['libraries', 'columns_used', 'operations', 'assumptions']:
                if data.get(list_field) is None:
                    data[list_field] = []
            if data.get('result_type') is None:
                data['result_type'] = "dataframe"
            if data.get('result_description') is None:
                data['result_description'] = "Generated code."
            if data.get('language') is None:
                data['language'] = "python"
            if data.get('code') is None:
                data['code'] = "result = df.copy()"
                
            return GeneratedAnalysisCode(**data)
        except Exception as e:
            logger.error(f"Ollama CodeGen Error: {str(e)}")
            raise Exception(f"Ollama CodeGen Error: {str(e)}")
