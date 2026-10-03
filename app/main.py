from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import auth

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agentic RAG Engine with RBAC and Hybrid Search"
)

# Register the Auth Router
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

@app.get("/health")
async def health_check():
    return {"status": "online", "project": settings.PROJECT_NAME}