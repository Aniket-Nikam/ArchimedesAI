from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.auth_router import router as auth_router
from routers.history_router import router as history_router
from routers.research_router import router as research_router
from routers.export_router import router as export_router
from routers.bookmark_router import router as bookmark_router
from routers.project_router import router as project_router
from routers.upload_router import router as upload_router
from routers.litreview_router import router as litreview_router
from routers.extract_router import router as extract_router
from routers.draft_router import router as draft_router
import db.database as database
import logging
import os

# Configure global logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize DB
database.init_db()

app = FastAPI(title="Archimedes Backend")

# Setup CORS with allowed origins from environment
allowed_origins_str = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(history_router, prefix="/api/history", tags=["history"])
app.include_router(research_router, prefix="/api/research", tags=["research"])
app.include_router(export_router, prefix="/api/export", tags=["export"])
app.include_router(bookmark_router, prefix="/api/bookmarks", tags=["bookmarks"])
app.include_router(project_router, prefix="/api/projects", tags=["projects"])
app.include_router(upload_router, prefix="/api/upload", tags=["upload"])
app.include_router(litreview_router, prefix="/api/litreview", tags=["litreview"])
app.include_router(extract_router, prefix="/api/extract", tags=["extract"])
app.include_router(draft_router, prefix="/api/draft", tags=["draft"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
