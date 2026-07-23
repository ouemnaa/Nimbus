from fastapi import APIRouter, Depends, HTTPException
from ..schemas.requests import AnalyzeRequest, AnalyzeResponse
from ..services.architecture_service import ArchitectureService
from ..llm.factory import get_llm_provider
from ..core.exceptions import LLMProviderError, ValidationError

router = APIRouter(prefix="/architectures", tags=["architectures"])

def get_architecture_service():
    provider = get_llm_provider()
    return ArchitectureService(provider)

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_architecture(
    request: AnalyzeRequest,
    service: ArchitectureService = Depends(get_architecture_service)
):
    try:
        return await service.analyze_requirement(request.requirement, request.context)
    except (LLMProviderError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An internal error occurred")
