from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from auth.auth_service import AuthError, login_user, register_user
from auth.rate_limit import limit_auth
from auth.sessions import end_session, require_session, start_session

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(max_length=30)
    password: str = Field(max_length=128)


@router.post("/register", dependencies=[Depends(limit_auth)])
def register(req: RegisterRequest, request: Request, response: Response):
    try:
        user = register_user(req.username, req.email, req.password)
        return {"user": user, "csrf_token": start_session(user, response, request)}
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", dependencies=[Depends(limit_auth)])
def login(req: LoginRequest, request: Request, response: Response):
    try:
        user = login_user(req.username, req.password)
        return {"user": user, "csrf_token": start_session(user, response, request)}
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/session")
def session(user: dict = Depends(require_session)):
    return {
        "user": {key: user[key] for key in ("id", "username", "email")},
        "csrf_token": user["csrf_token"],
    }


@router.post("/logout")
def logout(request: Request, response: Response, user: dict = Depends(require_session)):
    end_session(request, response)
    return {"message": "Signed out"}
