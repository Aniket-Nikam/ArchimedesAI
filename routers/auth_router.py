from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from auth.auth_service import register_user, login_user, AuthError

router = APIRouter()

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/register")
def register(req: RegisterRequest):
    try:
        user = register_user(req.username, req.email, req.password)
        return {"message": "User created successfully", "user": {"id": user["id"], "username": user["username"], "email": user["email"]}}
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login(req: LoginRequest):
    try:
        user = login_user(req.username, req.password)
        return {"message": "Login successful", "user": {"id": user["id"], "username": user["username"], "email": user["email"]}}
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
