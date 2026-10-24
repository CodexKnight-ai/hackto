/**
 * RecallVision – API client
 * All API calls go through this module. NEXT_PUBLIC_API_URL is read at build time
 * from .env.local; the actual GEMINI_API_KEY is never exposed here.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface UploadResponse {
  success: boolean;
  video_id: string;
  filename: string;
  frame_count: number;
  metadata: {
    fps: number;
    frame_count: number;
    width: number;
    height: number;
    duration_seconds: number;
  };
}

export interface SearchResponse {
  success: boolean;
  video_id: string;
  query: string;
  found: boolean;
  timestamp_seconds: number | null;
  frame_index: number | null;
  frame_filename: string | null;
  description: string;
  confidence: "high" | "medium" | "low";
}

export interface HealthResponse {
  status: string;
  service: string;
  gemini_key_configured: boolean;
}

export interface VideoEntry {
  video_id: string;
  filename: string;
  size_bytes: number;
  frame_count: number;
  duration_seconds: number;
  fps: number;
  width: number;
  height: number;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`);
  return handleResponse<HealthResponse>(res);
}

export async function uploadVideo(
  file: File,
  onProgress?: (pct: number) => void
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/upload`);

    if (onProgress) {
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      });
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as UploadResponse);
      } else {
        let detail = `HTTP ${xhr.status}`;
        try {
          detail = JSON.parse(xhr.responseText).detail ?? detail;
        } catch {}
        reject(new Error(detail));
      }
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(formData);
  });
}

export async function searchVideo(
  videoId: string,
  query: string
): Promise<SearchResponse> {
  const formData = new FormData();
  formData.append("video_id", videoId);
  formData.append("query", query);

  const res = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<SearchResponse>(res);
}

export async function listVideos(): Promise<VideoEntry[]> {
  const res = await fetch(`${API_BASE}/api/videos`);
  const data = await handleResponse<{ videos: VideoEntry[] }>(res);
  return data.videos;
}

export function frameImageUrl(videoId: string, filename: string): string {
  return `${API_BASE}/frames/${videoId}/${filename}`;
}
