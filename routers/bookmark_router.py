from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.bookmark_service import (
    add_bookmark, remove_bookmark, get_bookmarks,
    is_bookmarked, update_bookmark_notes
)

router = APIRouter()


class BookmarkRequest(BaseModel):
    user_id: int
    paper: dict
    notes: Optional[str] = ""

class RemoveBookmarkRequest(BaseModel):
    user_id: int
    paper_title: str

class UpdateNotesRequest(BaseModel):
    user_id: int
    paper_title: str
    notes: str


@router.get("/")
def list_bookmarks(user_id: int):
    return get_bookmarks(user_id)


@router.post("/")
def create_bookmark(req: BookmarkRequest):
    success = add_bookmark(req.user_id, req.paper, req.notes)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save bookmark")
    return {"message": "Bookmark saved"}


@router.delete("/")
def delete_bookmark(req: RemoveBookmarkRequest):
    success = remove_bookmark(req.user_id, req.paper_title)
    if not success:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Bookmark removed"}


@router.get("/check")
def check_bookmark(user_id: int, paper_title: str):
    return {"is_bookmarked": is_bookmarked(user_id, paper_title)}


@router.put("/notes")
def update_notes(req: UpdateNotesRequest):
    success = update_bookmark_notes(req.user_id, req.paper_title, req.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Notes updated"}
