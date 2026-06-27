from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.project_service import (
    create_project, get_projects, update_project,
    delete_project, assign_session_to_project, get_project_sessions
)

router = APIRouter()


class CreateProjectRequest(BaseModel):
    user_id: int
    name: str
    description: Optional[str] = ""

class UpdateProjectRequest(BaseModel):
    user_id: int
    name: Optional[str] = None
    description: Optional[str] = None

class AssignSessionRequest(BaseModel):
    user_id: int
    session_id: int
    project_id: int


@router.get("/")
def list_projects(user_id: int):
    return get_projects(user_id)


@router.post("/")
def new_project(req: CreateProjectRequest):
    project_id = create_project(req.user_id, req.name, req.description)
    return {"message": "Project created", "id": project_id}


@router.put("/{project_id}")
def edit_project(project_id: int, req: UpdateProjectRequest):
    success = update_project(req.user_id, project_id, req.name, req.description)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project updated"}


@router.delete("/{project_id}")
def remove_project(project_id: int, user_id: int):
    success = delete_project(user_id, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted"}


@router.post("/assign")
def assign_session(req: AssignSessionRequest):
    success = assign_session_to_project(req.user_id, req.session_id, req.project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session assigned to project"}


@router.get("/{project_id}/sessions")
def project_sessions(project_id: int, user_id: int):
    return get_project_sessions(user_id, project_id)
