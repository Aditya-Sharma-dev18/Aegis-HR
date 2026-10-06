from fastapi import FastAPI
from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter

from app.core.config import settings
from app.api.routes import auth, chat

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to Docker Redis
    redis_connection = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_connection)
    print("🟢 Redis Rate Limiter Initialized via Docker!")
    
    yield
    
    await FastAPILimiter.close()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Tere existing routers...
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/rag", tags=["Chat"])