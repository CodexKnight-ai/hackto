"""
RecallVision – Gemini Vision Search Service
Sends extracted frames to the Google Gemini API for natural-language video search.
"""

import json
import logging
import math
from pathlib import Path
from typing import List, Optional

from google import genai
from google.genai import types

from .config import settings

logger = logging.getLogger(__name__)

# Lazy singleton client
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _client

    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Copy .env.example to .env and add your key."
            )

        _client = genai.Client(api_key=settings.gemini_api_key)

    return _client


def _empty_result(description: str) -> dict:
    """Return a consistent unsuccessful search result."""
    return {
        "found": False,
        "timestamp_seconds": None,
        "frame_index": None,
        "frame_filename": None,
        "description": description,
        "confidence": "low",
    }


def _parse_model_response(raw: Optional[str]) -> dict:
    """
    Parse a model response into a JSON object.

    Supports plain JSON and JSON wrapped in Markdown fences.
    Does not attempt to repair arbitrary malformed model output.
    """
    if not raw or not raw.strip():
        raise ValueError("Model returned an empty response.")

    raw = raw.strip()

    # Remove Markdown fences if present.
    if raw.startswith("```"):
        lines = raw.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        raw = "\n".join(lines).strip()

        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    # Prefer parsing the complete response.
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # If the model included explanatory text, try the outermost
        # JSON object. This does not repair invalid JSON.
        start = raw.find("{")
        end = raw.rfind("}")

        if start == -1 or end <= start:
            raise ValueError(
                f"No JSON object found in model response: {raw[:300]!r}"
            )

        result = json.loads(raw[start : end + 1])

    if not isinstance(result, dict):
        raise ValueError("Model response must be a JSON object.")

    return result


def _validate_result(result: dict, frame_count: int) -> dict:
    """Validate and normalize the fields returned by the model."""
    found = result.get("found", False)

    if not isinstance(found, bool):
        raise ValueError("'found' must be a boolean.")

    frame_index = result.get("frame_index")
    timestamp = result.get("timestamp_seconds")

    if frame_index is not None:
        # bool is a subclass of int in Python, so reject it explicitly.
        if isinstance(frame_index, bool) or not isinstance(frame_index, int):
            raise ValueError("'frame_index' must be an integer or null.")

        if not 0 <= frame_index < frame_count:
            raise ValueError(
                f"frame_index {frame_index} is outside the valid range."
            )

    if timestamp is not None:
        if isinstance(timestamp, bool) or not isinstance(
            timestamp, (int, float)
        ):
            raise ValueError(
                "'timestamp_seconds' must be a number or null."
            )

        if not math.isfinite(timestamp) or timestamp < 0:
            raise ValueError("'timestamp_seconds' must be finite and nonnegative.")

        timestamp = float(timestamp)

    description = result.get("description", "")
    if not isinstance(description, str):
        raise ValueError("'description' must be a string.")

    confidence = result.get("confidence", "low")
    if confidence not in ("high", "medium", "low"):
        confidence = "low"

    if not found:
        frame_index = None
        timestamp = None

    return {
        "found": found,
        "frame_index": frame_index,
        "timestamp_seconds": timestamp,
        "description": description,
        "confidence": confidence,
    }


def _generate(
    client: genai.Client,
    prompt: str,
    frame_info: list,
    max_output_tokens: int = 8192,
):
    """Call Gemma with text and image parts.

    Gemma 4 is a thinking model.  ThinkingConfig is not supported for this
    model via the API, so we cannot disable thinking.  Instead we set a high
    max_output_tokens ceiling so the model has room for both reasoning tokens
    and the JSON response.
    """
    parts = [types.Part.from_text(text=prompt)]

    for frame in frame_info:
        parts.append(
            types.Part.from_bytes(
                data=frame["path"].read_bytes(),
                mime_type="image/jpeg",
            )
        )

    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=parts,
        config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=max_output_tokens,
        ),
    )

    candidates = response.candidates or []
    finish_reasons = [
        str(getattr(candidate, "finish_reason", None))
        for candidate in candidates
    ]

    raw = response.text

    logger.info(
        "Gemma response: %r; finish_reasons=%s",
        raw[:1000] if raw else None,
        finish_reasons,
    )

    if not raw or not raw.strip():
        raise ValueError(
            f"Gemma returned no text. Finish reasons: {finish_reasons}"
        )

    return raw




def search_frames(
    query: str,
    frame_paths: List[Path],
    max_frames: int = 20,
) -> dict:
    """
    Search sampled video frames for a natural-language query.

    Returns:
      found: bool
      timestamp_seconds: float | None
      frame_index: int | None
      frame_filename: str | None
      description: str
      confidence: str
    """
    if not query or not query.strip():
        return _empty_result("Please provide a search query.")

    if not frame_paths:
        return _empty_result("No frames available to search.")

    if max_frames < 1:
        return _empty_result("max_frames must be at least 1.")

    client = _get_client()

    # Sample across the available frames, including the final frame
    # when possible.
    if len(frame_paths) <= max_frames:
        sampled = frame_paths
    else:
        last_index = len(frame_paths) - 1
        indices = [
            round(i * last_index / (max_frames - 1))
            for i in range(max_frames)
        ] if max_frames > 1 else [0]

        sampled = [frame_paths[i] for i in indices]

    frame_info = []

    for i, path in enumerate(sampled):
        # Expected filename format: frame_000000_1.000s.jpg
        try:
            timestamp = float(path.stem.split("_")[-1].replace("s", ""))
        except (ValueError, IndexError):
            timestamp = float(i)

        frame_info.append(
            {
                "index": i,
                "timestamp": timestamp,
                "path": path,
            }
        )

    index_table = "\n".join(
        f"Frame {frame['index']}: {frame['timestamp']:.2f}s"
        for frame in frame_info
    )

    prompt = f"""
You are analyzing sampled frames from a video to find a moment.

User query: {json.dumps(query)}

Available frame indices and timestamps:
{index_table}

Inspect the supplied images and identify the frame that best matches
the user's query. Use only the listed frame indices.

Return exactly one JSON object with these fields:
{{
  "found": true,
  "frame_index": 0,
  "timestamp_seconds": 0.0,
  "description": "Brief description of the matching visual moment.",
  "confidence": "high"
}}

If no frame matches, return:
{{
  "found": false,
  "frame_index": null,
  "timestamp_seconds": null,
  "description": "No matching moment found.",
  "confidence": "low"
}}

Rules:
- Do not invent events that are not visible in the images.
- frame_index must be an available index from the list.
- confidence must be high, medium, or low.
- Return JSON only. No Markdown or explanatory text.
""".strip()

    try:
        raw = _generate(client, prompt, frame_info)
        result = _validate_result(
            _parse_model_response(raw),
            len(frame_info),
        )

    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning(
            "Full-frame search produced unusable output: %s",
            exc,
        )

        # Retry with one image to isolate failures caused by a large
        # multimodal request. This is a fallback, not a guaranteed fix.
        if len(frame_info) > 1:
            try:
                fallback_prompt = f"""
Analyze this video frame at timestamp
{frame_info[0]['timestamp']:.2f} seconds.

User query: {json.dumps(query)}

Determine whether this frame visibly matches the query.
Return one JSON object with:
found (boolean), frame_index (integer or null),
timestamp_seconds (number or null), description (string),
confidence ("high", "medium", or "low").

If it matches, frame_index must be 0 and timestamp_seconds must be
{frame_info[0]['timestamp']:.2f}.
If it does not match, set found to false and both numeric fields to null.
Return JSON only.
""".strip()

                raw = _generate(
                    client,
                    fallback_prompt,
                    frame_info[:1],
                    max_output_tokens=256,
                )

                fallback = _validate_result(
                    _parse_model_response(raw),
                    1,
                )

                if fallback["found"]:
                    result = fallback
                    frame_info = frame_info[:1]
                else:
                    return _empty_result(
                        "The full search failed, and the fallback frame "
                        "did not match. Try a different query."
                    )

            except Exception:
                logger.exception("Single-frame fallback failed")
                return _empty_result(
                    "The model returned an unusable response. "
                    "Check the backend logs and try again."
                )
        else:
            return _empty_result(
                "The model returned an unusable response. "
                "Check the backend logs and try again."
            )

    except Exception:
        logger.exception("Gemini search API request failed")
        raise

    matched_frame = None

    if result["found"] and result["frame_index"] is not None:
        matched_frame = frame_info[result["frame_index"]]

    return {
        "found": result["found"],
        "timestamp_seconds": (
            matched_frame["timestamp"]
            if matched_frame
            else result["timestamp_seconds"]
        ),
        "frame_index": result["frame_index"],
        "frame_filename": (
            matched_frame["path"].name if matched_frame else None
        ),
        "description": result["description"],
        "confidence": result["confidence"],
    }
