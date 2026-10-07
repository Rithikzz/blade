import asyncio
from app.ai.ollama_provider import OllamaProvider
from app.core import config

async def main():
    provider = OllamaProvider()
    profile = '{"filename": "test.csv"}'
    question = "What is the revenue?"
    plan = await provider.generate_analysis_plan(question, profile)
    print(plan)

asyncio.run(main())
