import argparse
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.architecture_service import ArchitectureService
from app.llm.factory import GeminiProvider, GroqProvider
from app.core.config import settings

async def run_smoke_test(provider_name: str):
    print(f"Running smoke test for provider: {provider_name}")
    
    load_dotenv()
    
    if provider_name == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Error: GEMINI_API_KEY not found in environment")
            return
        provider = GeminiProvider(api_key, settings.GEMINI_MODEL)
    elif provider_name == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("Error: GROQ_API_KEY not found in environment")
            return
        provider = GroqProvider(api_key, settings.GROQ_MODEL)
    else:
        print(f"Error: Unsupported provider {provider_name}")
        return

    service = ArchitectureService(provider)
    requirement = "Deploy a small containerized web application with PostgreSQL on AWS. Low cost is a priority."
    
    try:
        print("Sending request to LLM...")
        response = await service.analyze_requirement(requirement)
        print("\n--- Architecture Result ---")
        print(f"Title: {response.architecture.title}")
        print(f"Status: {response.architecture.status}")
        print(f"Duration: {response.metadata.generation_duration_ms}ms")
        print("\n--- Markdown Report Snippet ---")
        print(response.report_markdown[:500] + "...")
        print("\nSmoke test completed successfully!")
    except Exception as e:
        print(f"Smoke test failed: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["gemini", "groq"], required=True)
    args = parser.parse_args()
    
    asyncio.run(run_smoke_test(args.provider))
