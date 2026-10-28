from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from auth.sessions import current_user_id
from services.bookmark_service import (
    add_bookmark,
    get_bookmarks,
    is_bookmarked,
    remove_bookmark,
    update_bookmark_notes,
)

router = APIRouter()


class BookmarkRequest(BaseModel):
    user_id: int | None = None
    paper: dict
    notes: str = Field(default="", max_length=20000)

    @field_validator("paper")
    @classmethod
    def validate_paper(cls, paper):
        if not isinstance(paper.get("title"), str) or not paper["title"].strip():
            raise ValueError("Paper title is required")
        return paper


class RemoveBookmarkRequest(BaseModel):
    user_id: int | None = None
    paper_title: str


class UpdateNotesRequest(BaseModel):
    user_id: int | None = None
    paper_title: str
    notes: str = Field(max_length=20000)


@router.get("/")
def list_bookmarks(user_id: int = Depends(current_user_id)):
    return get_bookmarks(user_id)


@router.post("/")
def create_bookmark(req: BookmarkRequest, authenticated_user: int = Depends(current_user_id)):
    req.user_id = authenticated_user
    success = add_bookmark(req.user_id, req.paper, req.notes)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save bookmark")
    return {"message": "Bookmark saved"}


@router.delete("/")
def delete_bookmark(req: RemoveBookmarkRequest, authenticated_user: int = Depends(current_user_id)):
    req.user_id = authenticated_user
    success = remove_bookmark(req.user_id, req.paper_title)
    if not success:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Bookmark removed"}


@router.get("/check")
def check_bookmark(paper_title: str, user_id: int = Depends(current_user_id)):
    return {"is_bookmarked": is_bookmarked(user_id, paper_title)}


@router.put("/notes")
def update_notes(req: UpdateNotesRequest, authenticated_user: int = Depends(current_user_id)):
    req.user_id = authenticated_user
    success = update_bookmark_notes(req.user_id, req.paper_title, req.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"message": "Notes updated"}
