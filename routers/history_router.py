from fastapi import APIRouter, Depends, HTTPException

from auth.sessions import current_user_id
from services.history_service import delete_session, get_session_by_id, get_user_history

router = APIRouter()


@router.get("/")
def get_history(user_id: int = Depends(current_user_id)):
    history = get_user_history(user_id)
    return history


@router.get("/{session_id}")
def get_session(session_id: int, user_id: int = Depends(current_user_id)):
    session = get_session_by_id(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
def delete_history_session(session_id: int, user_id: int = Depends(current_user_id)):
    success = delete_session(session_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}
