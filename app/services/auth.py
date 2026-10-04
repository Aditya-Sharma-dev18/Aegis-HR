from datetime import datetime, timedelta
from jose import JWTError,  jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    role: str           # e.g., employee, hr_admin, executive
    department: str     # e.g., engineering, hr, sales
    clearance: int      # 1 (Standard) to 5 (Top Secret)

# --- Mock Enterprise Directory (Simulating Okta / Active Directory) ---
FAKE_USERS_DB = {
    "aditya": {
        "username": "aditya",
        "password": "password123",
        "role": "executive",
        "department": "board",
        "clearance": 5
    },
    "intern_bob": {
        "username": "intern_bob",
        "password": "password123",
        "role": "employee",
        "department": "engineering",
        "clearance": 1
    },
    "hr_alice": {
        "username": "hr_alice",
        "password": "password123",
        "role": "hr_admin",
        "department": "hr",
        "clearance": 4
    }
}

# --- Core Security Functions ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Sign the JWT using the secret key from your .env
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        user_dict = FAKE_USERS_DB.get(username)
        if user_dict is None:
            raise credentials_exception
            
        return User(**user_dict)
    except JWTError:
        raise credentials_exception