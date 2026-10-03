from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.services.auth import FAKE_USERS_DB, create_access_token, Token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = FAKE_USERS_DB.get(form_data.username)
    
    # In production, use passlib bcrypt to verify hashes. Plaintext for demo.
    if not user_dict or form_data.password != user_dict["password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(
        data={
            "sub": user_dict["username"],
            "role": user_dict["role"],
            "department": user_dict["department"],
            "clearance": user_dict["clearance"]
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}