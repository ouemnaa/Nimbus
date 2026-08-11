from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.routes import router as terraform_router
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="Nimbus Terraform Generator Agent",
    version="0.1.0",
    description="Deterministic Terraform generation and safe Terraform CLI validation for Nimbus architectures.",
)
app.include_router(health_router)
app.include_router(terraform_router)
