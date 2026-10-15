from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Pydantic Schema for Current User (Used across routes like chat.py)
class User(BaseModel):
    username: str
    clearance: int
    department: str

    model_config = {"from_attributes": True}


# ==========================================
# 1. BCRYPT PASSWORD UTILITIES
# ==========================================
def get_password_hash(password: str) -> str:
    """Hashes plain password using bcrypt with automatic salt generation."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ==========================================
# 2. JWT & DATABASE AUTHENTICATION
# ==========================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM
    )


def authenticate_user(db: Session, username: str, password: str) -> Optional[UserModel]:
    """Queries PostgreSQL using SQLAlchemy 2.0 select() and checks bcrypt hash."""
    stmt = select(UserModel).where(UserModel.username == username)
    user = db.scalar(stmt)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Decodes JWT and verifies user still exists in PostgreSQL."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    stmt = select(UserModel).where(UserModel.username == username)
    user_record = db.scalar(stmt)
    if user_record is None:
        raise credentials_exception

    return User.model_validate(user_record)