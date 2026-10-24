"""
RecallVision – FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routes.api import router as api_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure storage directories exist on startup
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.frames_dir.mkdir(parents=True, exist_ok=True)
    logger.info("RecallVision backend starting on %s:%s", settings.backend_host, settings.backend_port)
    logger.info("Upload dir : %s", settings.upload_dir)
    logger.info("Frames dir : %s", settings.frames_dir)
    logger.info("Gemini key : %s", "configured" if settings.gemini_api_key else "NOT SET")
    yield
    logger.info("RecallVision backend shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="RecallVision API",
    description="AI-powered video search using natural language",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the Next.js dev server and any localhost origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes under /api
app.include_router(api_router, prefix="/api")

# Serve extracted frames as static files so the frontend can display them
frames_dir = settings.frames_dir
frames_dir.mkdir(parents=True, exist_ok=True)
app.mount("/frames", StaticFiles(directory=str(frames_dir)), name="frames")


# ── Dev entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
