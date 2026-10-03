from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agentic RAG Engine with RBAC and Hybrid Search"
)

@app.get("/health")
async def health_check():
    """
    Production health check endpoint for load balancers (e.g., AWS ALB or Kubernetes).
    """
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

# We will include our API routers here in the next steps