from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.sessions import current_user_id
from services.project_service import (
    assign_session_to_project,
    create_project,
    delete_project,
    get_project_sessions,
    get_projects,
    update_project,
)

router = APIRouter()


class CreateProjectRequest(BaseModel):
    user_id: int | None = None
    name: str
    description: Optional[str] = ""


class UpdateProjectRequest(BaseModel):
    user_id: int | None = None
    name: Optional[str] = None
    description: Optional[str] = None


class AssignSessionRequest(BaseModel):
    user_id: int | None = None
    session_id: int
    project_id: int


@router.get("/")
def list_projects(user_id: int = Depends(current_user_id)):
    return get_projects(user_id)


@router.post("/")
def new_project(req: CreateProjectRequest, authenticated_user: int = Depends(current_user_id)):
    req.user_id = authenticated_user
    project_id = create_project(req.user_id, req.name, req.description)
    return {"message": "Project created", "id": project_id}


@router.put("/{project_id}")
def edit_project(
    project_id: int, req: UpdateProjectRequest, authenticated_user: int = Depends(current_user_id)
):
    req.user_id = authenticated_user
    success = update_project(req.user_id, project_id, req.name, req.description)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project updated"}


@router.delete("/{project_id}")
def remove_project(project_id: int, user_id: int = Depends(current_user_id)):
    success = delete_project(user_id, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted"}


@router.post("/assign")
def assign_session(req: AssignSessionRequest, authenticated_user: int = Depends(current_user_id)):
    req.user_id = authenticated_user
    success = assign_session_to_project(req.user_id, req.session_id, req.project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session assigned to project"}


@router.get("/{project_id}/sessions")
def project_sessions(project_id: int, user_id: int = Depends(current_user_id)):
    return get_project_sessions(user_id, project_id)
