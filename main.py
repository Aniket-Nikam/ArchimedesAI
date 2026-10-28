import asyncio
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import config
import db.database as database
from auth.sessions import require_session
from routers.auth_router import router as auth_router
from routers.bookmark_router import router as bookmark_router
from routers.draft_router import router as draft_router
from routers.export_router import router as export_router
from routers.extract_router import router as extract_router
from routers.history_router import router as history_router
from routers.litreview_router import router as litreview_router
from routers.project_router import router as project_router
from routers.research_router import router as research_router
from routers.upload_router import router as upload_router
from services.body_limits import BodyLimits
from services.job_service import dispatch

# Configure global logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize DB
database.init_db()


@asynccontextmanager
async def lifespan(app):
    async def recover_jobs():
        while True:
            await asyncio.to_thread(dispatch)
            await asyncio.sleep(1)

    task = asyncio.create_task(recover_jobs())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Archimedes Backend", lifespan=lifespan)

# Setup CORS with allowed origins from environment
allowed_origins_str = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]


@app.middleware("http")
async def check_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    # Includes login/register to prevent cross-site login CSRF.
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
        same_origin = str(request.base_url).rstrip("/")
        if origin not in origins and origin != same_origin:
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    try:
        response = await call_next(request)
    except sqlite3.Error:
        return JSONResponse(
            {"detail": "Storage is temporarily unavailable. Please retry later."}, status_code=503
        )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'"
    )
    return response


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "ai_configured": bool(config.GROQ_API_KEY),
        "google_scholar_enabled": config.ENABLE_GOOGLE_SCHOLAR,
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BodyLimits)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(
    history_router, dependencies=[Depends(require_session)], prefix="/api/history", tags=["history"]
)
app.include_router(
    research_router,
    dependencies=[Depends(require_session)],
    prefix="/api/research",
    tags=["research"],
)
app.include_router(
    export_router, dependencies=[Depends(require_session)], prefix="/api/export", tags=["export"]
)
app.include_router(
    bookmark_router,
    dependencies=[Depends(require_session)],
    prefix="/api/bookmarks",
    tags=["bookmarks"],
)
app.include_router(
    project_router,
    dependencies=[Depends(require_session)],
    prefix="/api/projects",
    tags=["projects"],
)
app.include_router(
    upload_router, dependencies=[Depends(require_session)], prefix="/api/upload", tags=["upload"]
)
app.include_router(
    litreview_router,
    dependencies=[Depends(require_session)],
    prefix="/api/litreview",
    tags=["litreview"],
)
app.include_router(
    extract_router, dependencies=[Depends(require_session)], prefix="/api/extract", tags=["extract"]
)
app.include_router(
    draft_router, dependencies=[Depends(require_session)], prefix="/api/draft", tags=["draft"]
)

dist = Path(__file__).parent / "frontend" / "dist"
if dist.is_dir():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def frontend():
        return FileResponse(dist / "index.html")

    @app.get("/favicon.svg", include_in_schema=False)
    def favicon():
        return FileResponse(dist / "favicon.svg")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
