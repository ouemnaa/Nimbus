from fastapi import FastAPI
from .api import architecture_routes
from .core.config import settings
from .core.logging import setup_logging

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

app.include_router(architecture_routes.router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
