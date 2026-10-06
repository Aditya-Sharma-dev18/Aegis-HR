from fastapi import FastAPI
from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings
from app.api.routes import auth, chat
from app.rag.workflow import build_rag_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---

    # 1. Initialize Redis Rate Limiter
    redis_connection = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_connection)
    print("🟢 Redis Rate Limiter Initialized via Docker!")

    # 2. Initialize Async Postgres Connection Pool for LangGraph Memory
    pool = AsyncConnectionPool(
        conninfo=settings.DATABASE_URL,
        max_size=20,
        kwargs={"autocommit": True},
    )
    await pool.open()
    print("🟢 Async Postgres Connection Pool Opened!")

    # 3. Setup AsyncPostgresSaver (creates checkpoint tables if needed)
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    print("🟢 LangGraph Async Checkpointer Ready!")

    # 4. Build & compile the RAG app with the async checkpointer
    app.state.rag_app = build_rag_app(checkpointer=checkpointer)
    app.state.pool = pool
    print("🟢 Agentic RAG Graph Compiled Successfully!")

    yield

    # --- Shutdown ---
    await pool.close()
    await FastAPILimiter.close()
    print("🔴 Connections Closed. Shutting Down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agentic RAG Engine with RBAC, Hybrid Search, and Async Architecture",
    lifespan=lifespan
)

# Register Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/rag", tags=["RAG Core"])


@app.get("/health")
async def health_check():
    return {"status": "online", "project": settings.PROJECT_NAME}