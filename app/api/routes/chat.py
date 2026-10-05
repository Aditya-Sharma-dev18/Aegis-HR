from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.auth import get_current_user, User
from app.rag.workflow import rag_app

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

@router.post("/ask")
async def ask_question(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """
    Secure Chat Endpoint with Memory and Routing.
    """
    print(f"\n🕵️ User {current_user.username} (Clearance {current_user.clearance}) is asking: {request.question}")
    
    inputs = {
        "question": request.question,
        "user_clearance": current_user.clearance,
        "user_department": current_user.department
    }
    
    try:
        # 1. CREATE THE THREAD CONFIG (This was missing!)
        # Using the username as the unique thread_id for Postgres Memory
        thread_config = {"configurable": {"thread_id": current_user.username}}
        
        # 2. Run the graph asynchronously with the config
        result =  rag_app.invoke(inputs, config=thread_config)
        
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