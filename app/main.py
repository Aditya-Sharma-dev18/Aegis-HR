from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import auth, chat

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agentic RAG Engine with RBAC and Hybrid Search"
)

# Register Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/rag", tags=["RAG Core"])

@app.get("/health")
async def health_check():
    return {"status": "online", "project": settings.PROJECT_NAME}