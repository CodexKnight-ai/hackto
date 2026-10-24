"""
RecallVision – API Routes
POST /api/upload  – Upload a video file and extract frames
POST /api/search  – Search a processed video with a natural language query
GET  /api/videos  – List uploaded videos
GET  /api/health  – Health check
"""

import uuid
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
import aiofiles

from ..config import settings
from ..video_processor import extract_frames_opencv, get_video_metadata
from ..gemini_service import search_frames

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory registry: video_id → metadata dict
# In a production system this would be a database.
VIDEO_REGISTRY: dict[str, dict[str, Any]] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _registry_path() -> Path:
    """Persist the registry as JSON next to the uploads directory."""
    return settings.upload_dir / "_registry.json"


def _load_registry() -> None:
    p = _registry_path()
    if p.exists():
        with open(p) as f:
            VIDEO_REGISTRY.update(json.load(f))


def _save_registry() -> None:
    with open(_registry_path(), "w") as f:
        json.dump(VIDEO_REGISTRY, f, indent=2)


# Load existing registry on import
try:
    _load_registry()
except Exception:
    pass


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "RecallVision",
        "gemini_key_configured": bool(settings.gemini_api_key),
    }


@router.get("/videos")
async def list_videos() -> dict:
    return {"videos": list(VIDEO_REGISTRY.values())}


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)) -> dict:
    """
    Accept a video upload, save it to disk, extract frames, return video_id.
    """
    allowed_types = {
        "video/mp4", "video/mpeg", "video/quicktime",
        "video/x-msvideo", "video/webm", "video/x-matroska",
    }
    content_type = file.content_type or ""
    if content_type not in allowed_types and not file.filename.lower().endswith(
        (".mp4", ".mov", ".avi", ".mkv", ".webm", ".mpeg")
    ):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {content_type}. Please upload a video file.",
        )

    video_id = str(uuid.uuid4())
    suffix = Path(file.filename).suffix or ".mp4"
    video_path = settings.upload_dir / f"{video_id}{suffix}"
    frames_path = settings.frames_dir / video_id

    # Stream-write to disk
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    bytes_written = 0
    async with aiofiles.open(video_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            bytes_written += len(chunk)
            if bytes_written > max_bytes:
                await out.close()
                video_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds {settings.max_upload_size_mb} MB limit.",
                )
            await out.write(chunk)

    logger.info("Saved video %s (%d bytes)", video_id, bytes_written)

    # Extract frames
    try:
        frame_paths = extract_frames_opencv(
            video_path, frames_path, fps=settings.frames_per_second
        )
    except Exception as exc:
        video_path.unlink(missing_ok=True)
        shutil.rmtree(frames_path, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Frame extraction failed: {exc}")

    # Gather metadata
    meta = get_video_metadata(video_path)

    entry = {
        "video_id": video_id,
        "filename": file.filename,
        "size_bytes": bytes_written,
        "frame_count": len(frame_paths),
        "frames_dir": str(frames_path),
        "video_path": str(video_path),
        **meta,
    }
    VIDEO_REGISTRY[video_id] = entry
    _save_registry()

    return {
        "success": True,
        "video_id": video_id,
        "filename": file.filename,
        "frame_count": len(frame_paths),
        "metadata": meta,
    }


@router.post("/search")
async def search_video(
    video_id: str = Form(...),
    query: str = Form(...),
) -> dict:
    """
    Search a previously uploaded video using a natural language query.
    """
    if video_id not in VIDEO_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found.")

    entry = VIDEO_REGISTRY[video_id]
    frames_path = Path(entry["frames_dir"])

    if not frames_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Frames directory missing. Please re-upload the video.",
        )

    frame_paths = sorted(frames_path.glob("frame_*.jpg"))
    if not frame_paths:
        raise HTTPException(
            status_code=404,
            detail="No frames found for this video. Please re-upload.",
        )

    if not query.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty.")

    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not configured. Add it to your .env file.",
        )

    try:
        result = search_frames(query=query, frame_paths=frame_paths)
    except Exception as exc:
        logger.exception("Search failed for video %s", video_id)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "success": True,
        "video_id": video_id,
        "query": query,
        **result,
    }
