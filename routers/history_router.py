from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from services.history_service import get_user_history, get_session_by_id, delete_session

router = APIRouter()

# Note: In a real app we would use JWT for getting the user_id.
# For simplicity in this demo, we'll accept it via query params.
@router.get("/")
def get_history(user_id: int):
    history = get_user_history(user_id)
    return history

@router.get("/{session_id}")
def get_session(session_id: int, user_id: int):
    session = get_session_by_id(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/{session_id}")
def delete_history_session(session_id: int, user_id: int):
    success = delete_session(session_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}
