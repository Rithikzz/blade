import asyncio
from app.ai.ollama_provider import OllamaProvider

async def main():
    provider = OllamaProvider()
    profile = '{"filename": "test.csv"}'
    plan = '{"intent": "ranking", "target_metric": "sales"}'
    try:
        code = await provider.generate_code(plan, profile)
        print("SUCCESS:", code)
    except Exception as e:
        print("ERROR:", repr(e))
        import traceback
        traceback.print_exc()

asyncio.run(main())
