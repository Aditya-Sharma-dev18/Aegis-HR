from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from fastapi_limiter.depends import RateLimiter

from app.services.auth import get_current_user, User

router = APIRouter()


class ChatRequest(BaseModel):
    question: str


@router.post("/ask", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def ask_question(
    request: ChatRequest,
    req: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Secure Chat Endpoint with Async Memory, Routing, and Rate Limiting.
    The RAG app is fully async — no event loop blocking.
    """
    print(f"\n🕵️ User {current_user.username} (Clearance {current_user.clearance}) is asking: {request.question}")

    inputs = {
        "question": request.question,
        "user_clearance": current_user.clearance,
        "user_department": current_user.department
    }

    try:
        # 1. Get the async RAG app from FastAPI app state (injected via lifespan)
        rag_app = req.app.state.rag_app

        # 2. Create thread config for per-user persistent memory
        thread_config = {"configurable": {"thread_id": current_user.username}}

        # 3. Run the graph ASYNCHRONOUSLY — yields control back to the event loop
        result = await rag_app.ainvoke(inputs, config=thread_config)

        print(f"🧠 LangGraph Final Output: {result}")

        answer = result.get("generation", "Error: No answer was generated. Check terminal logs.")

        return {
            "query": request.question,
            "answer": answer,
            "security_context": {
                "user": current_user.username,
                "clearance_applied": current_user.clearance,
                "thread_id": current_user.username
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)} - type: {type(e).__name__}")