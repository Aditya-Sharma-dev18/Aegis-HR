from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db, UserModel
from app.services.auth import authenticate_user, create_access_token, get_password_hash

router = APIRouter()

class RegisterRequest(BaseModel):
    username: str
    password: str
    clearance: int = 1
    department: str = "General"

@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={
            "sub": user.username,
            "clearance": user.clearance,
            "department": user.department
        }
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(UserModel).where(UserModel.username == request.username))
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = UserModel(
        username=request.username,
        hashed_password=get_password_hash(request.password),
        clearance=request.clearance,
        department=request.department
    )
    db.add(new_user)
    db.commit()
    return {"message": f"User '{request.username}' created successfully with clearance {request.clearance}"}