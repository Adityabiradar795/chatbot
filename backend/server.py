import os
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import desc
from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage
)
import json

from pydantic import BaseModel

from auth_routes import router as auth_router, get_current_user
from database import get_db, User, ChatSession, ChatMessage


# =========================
# LOAD ENV
# =========================

load_dotenv(override=True)


# =========================
# FASTAPI
# =========================

app = FastAPI(
    title="GenAI API",
    description="FastAPI + PostgreSQL + JWT + LangChain",
    version="1.0"
)


# =========================
# CORS
# =========================
# In production, set ALLOWED_ORIGINS in the environment to your deployed
# frontend URL(s), comma-separated, e.g.:
#   ALLOWED_ORIGINS=https://your-frontend.vercel.app
# Falls back to "*" for local development.

_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = (
    ["*"] if _allowed_origins_env == "*"
    else [origin.strip() for origin in _allowed_origins_env.split(",")]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# =========================
# AUTH ROUTER
# =========================

app.include_router(auth_router)


# =========================
# LANGCHAIN MODEL
# =========================
# Groq provider for ultra-low latency

model = init_chat_model("openai/gpt-oss-120b", model_provider="groq")


# =========================
# SCHEMAS
# =========================

class ChatRequest(BaseModel):
    user_input: str
    system_prompt: str = "You are a funny helpful assistant."
    # This field was missing before — server.py read req.session_id but
    # the model never declared it, so FastAPI would have silently dropped
    # it (or thrown a validation error depending on client payload).
    session_id: Optional[int] = None


class SessionOut(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    sender: str
    content: str

    class Config:
        from_attributes = True


# =========================
# HOME
# =========================

@app.get("/")
def home():
    return {"message": "GenAI API is running"}


# =========================
# LIST MY CHAT SESSIONS
# (frontend needs this to build the history sidebar; endpoint didn't exist)
# =========================

@app.get("/sessions", response_model=List[SessionOut])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.created_at))
        .all()
    )
    return sessions


# =========================
# GET MESSAGES FOR A SESSION
# =========================

@app.get("/sessions/{session_id}/messages", response_model=List[MessageOut])
def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session.messages


# =========================
# CHAT (streamed)
# =========================

@app.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # cascade="all, delete-orphan" on the relationship takes care of
    # deleting the session's messages too
    db.delete(session)
    db.commit()

    return {"message": "Session deleted"}


@app.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create or retrieve session, scoped to the logged-in user
    if not req.session_id:
        title = req.user_input[:30] + "..." if len(req.user_input) > 30 else req.user_input
        session = ChatSession(title=title, user_id=current_user.id)
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id
    else:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == req.session_id,
                ChatSession.user_id == current_user.id
            )
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session_id = session.id

    # Build memory context — last 10 messages for speed
    db_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(10)
        .all()
    )[::-1]  # back to chronological order

    lc_messages = [SystemMessage(content=req.system_prompt)]
    for msg in db_messages:
        if msg.sender == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        else:
            lc_messages.append(AIMessage(content=msg.content))

    lc_messages.append(HumanMessage(content=req.user_input))

    async def event_generator():
        full_ai_response = ""
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        async for chunk in model.astream(lc_messages):
            content = chunk.content
            if content:
                full_ai_response += content
                yield f"data: {json.dumps({'type': 'token', 'token': content})}\n\n"

        user_msg = ChatMessage(session_id=session_id, sender="user", content=req.user_input)
        ai_msg = ChatMessage(session_id=session_id, sender="ai", content=full_ai_response)
        db.add_all([user_msg, ai_msg])
        db.commit()
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
