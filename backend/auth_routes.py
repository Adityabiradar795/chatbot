import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from database import (
    get_db,
    User,
    hash_password,
    verify_password
)


# =========================
# JWT CONFIG
# =========================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key"
)

ALGORITHM = "HS256"

# Token now actually expires (was missing entirely before — tokens never
# expired, which is a security bug). Configurable via .env, default 24h.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))


# =========================
# ROUTER
# =========================

router = APIRouter(
    tags=["Authentication"]
)

bearer_scheme = HTTPBearer()


# =========================
# REQUEST MODELS
# =========================

class UserRegister(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


# =========================
# CREATE JWT
# =========================

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# =========================
# GET CURRENT USER
# (this dependency was used in server.py's /chat/stream but never
# actually existed anywhere — that would have crashed the app at import
# time. Added here so it can be imported into server.py.)
# =========================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credentials_exception

    return user


# =========================
# REGISTER
# =========================

@router.post("/register")
def register(
    data: UserRegister,
    db: Session = Depends(get_db)
):

    # Check username/email
    existing_user = (
        db.query(User)
        .filter(
            (User.username == data.username)
            |
            (User.email == data.email)
        )
        .first()
    )

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Username or Email already exists"
        )

    # Hash password
    hashed_password = hash_password(
        data.password
    )

    # Create user
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hashed_password
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create token
    token = create_access_token(
        {
            "user_id": user.id,
            "username": user.username
        }
    )

    return {
        "message": "Registration successful",
        "token": token,
        "username": user.username
    }


# =========================
# LOGIN
# =========================

@router.post("/login")
def login(
    data: UserLogin,
    db: Session = Depends(get_db)
):

    # Find user
    user = (
        db.query(User)
        .filter(
            User.username == data.username
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Verify password
    if not verify_password(
        data.password,
        user.hashed_password
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Create JWT
    token = create_access_token(
        {
            "user_id": user.id,
            "username": user.username
        }
    )

    return {
        "message": "Login successful",
        "token": token,
        "username": user.username
    }
