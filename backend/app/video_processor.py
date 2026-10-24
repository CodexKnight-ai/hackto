"""
RecallVision – Video Processing Utilities
Handles frame extraction using OpenCV and FFmpeg.
"""

import cv2
import subprocess
import shutil
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


def extract_frames_opencv(
    video_path: Path,
    output_dir: Path,
    fps: int = 1,
) -> List[Path]:
    """
    Extract frames from a video at the given FPS using OpenCV.
    Returns a sorted list of extracted frame paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    video_fps: float = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = max(1, int(round(video_fps / fps)))

    frames: List[Path] = []
    frame_idx = 0
    saved_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            timestamp_s = timestamp_ms / 1000.0
            frame_path = output_dir / f"frame_{saved_idx:06d}_{timestamp_s:.3f}s.jpg"
            cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frames.append(frame_path)
            saved_idx += 1

        frame_idx += 1

    cap.release()
    logger.info("Extracted %d frames from %s", len(frames), video_path.name)
    return sorted(frames)


def extract_frames_ffmpeg(
    video_path: Path,
    output_dir: Path,
    fps: int = 1,
) -> List[Path]:
    """
    Extract frames using FFmpeg (fallback / alternative to OpenCV).
    Returns a sorted list of extracted frame paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg not found in PATH")

    output_pattern = str(output_dir / "frame_%06d.jpg")
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-q:v", "2",
        "-y",
        output_pattern,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error:\n{result.stderr}")

    frames = sorted(output_dir.glob("frame_*.jpg"))
    logger.info("FFmpeg extracted %d frames from %s", len(frames), video_path.name)
    return frames


def get_video_metadata(video_path: Path) -> dict:
    """Return basic metadata about a video file."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {}

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_s = frame_count / fps if fps > 0 else 0
    cap.release()

    return {
        "fps": round(fps, 2),
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration_seconds": round(duration_s, 2),
    }
