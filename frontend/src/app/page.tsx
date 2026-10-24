"use client";

import { useState, useCallback, useRef } from "react";
import {
  uploadVideo,
  searchVideo,
  UploadResponse,
  SearchResponse,
  frameImageUrl,
} from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────
type Stage = "idle" | "uploading" | "ready" | "searching";

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatDuration(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "text-emerald-400",
  medium: "text-amber-400",
  low: "text-rose-400",
};

// ─── Component ────────────────────────────────────────────────────────────────
export default function HomePage() {
  const [stage, setStage] = useState<Stage>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [query, setQuery] = useState("");
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Upload ──────────────────────────────────────────────────────────────────
  const handleFile = useCallback(async (file: File) => {
    setError(null);
    setSearchResult(null);
    setStage("uploading");
    setUploadProgress(0);
    try {
      const result = await uploadVideo(file, (pct) => setUploadProgress(pct));
      setUploadResult(result);
      setStage("ready");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setStage("idle");
    }
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  // ── Search ──────────────────────────────────────────────────────────────────
  const handleSearch = useCallback(async () => {
    if (!uploadResult || !query.trim()) return;
    setError(null);
    setStage("searching");
    try {
      const result = await searchVideo(uploadResult.video_id, query);
      setSearchResult(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setStage("ready");
    }
  }, [uploadResult, query]);

  // ── UI ──────────────────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen bg-[#090e1a] text-white font-sans">
      {/* ── Ambient glow ── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[800px] h-[500px] rounded-full bg-violet-600/20 blur-[120px]" />
        <div className="absolute top-1/2 -left-40 w-[500px] h-[500px] rounded-full bg-indigo-700/15 blur-[120px]" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-cyan-700/10 blur-[120px]" />
      </div>

      <div className="relative z-10 mx-auto max-w-4xl px-4 py-12 sm:py-20">
        {/* ── Header ── */}
        <header className="mb-14 text-center">
          <div className="inline-flex items-center gap-2 mb-4 px-4 py-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 text-violet-300 text-xs font-semibold tracking-widest uppercase">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
            AI-Powered Video Intelligence
          </div>
          <h1 className="text-5xl sm:text-6xl font-extrabold tracking-tight bg-gradient-to-r from-white via-violet-200 to-cyan-400 bg-clip-text text-transparent">
            RecallVision
          </h1>
          <p className="mt-4 text-lg text-slate-400 max-w-xl mx-auto">
            Upload any video and ask questions in plain English.{" "}
            <span className="text-violet-400 font-semibold">Gemini Vision</span> finds the exact moment.
          </p>
        </header>

        {/* ── Upload zone ── */}
        {(stage === "idle" || stage === "uploading") && (
          <section
            id="upload-zone"
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={onDrop}
            onClick={() => stage === "idle" && fileInputRef.current?.click()}
            className={[
              "relative flex flex-col items-center justify-center gap-4",
              "rounded-2xl border-2 border-dashed p-16 cursor-pointer",
              "transition-all duration-300",
              isDragging
                ? "border-violet-400 bg-violet-500/10 scale-[1.01]"
                : "border-slate-700 hover:border-violet-600/60 hover:bg-white/[0.02]",
              stage === "uploading" ? "pointer-events-none cursor-default" : "",
            ].join(" ")}
          >
            <input
              ref={fileInputRef}
              id="file-input"
              type="file"
              accept="video/*"
              className="hidden"
              onChange={onFileChange}
            />

            {stage === "idle" ? (
              <>
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-violet-600/30 to-indigo-600/20 flex items-center justify-center border border-violet-500/20">
                  <svg className="w-9 h-9 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                </div>
                <div className="text-center">
                  <p className="text-lg font-semibold text-slate-200">Drop your video here</p>
                  <p className="text-sm text-slate-500 mt-1">or click to browse · MP4, MOV, AVI, MKV, WebM</p>
                </div>
              </>
            ) : (
              <div className="w-full max-w-sm flex flex-col items-center gap-4">
                <div className="relative w-20 h-20">
                  <svg className="w-20 h-20 -rotate-90" viewBox="0 0 36 36">
                    <circle cx="18" cy="18" r="15.9" fill="none" stroke="#1e1b4b" strokeWidth="3" />
                    <circle
                      cx="18" cy="18" r="15.9" fill="none"
                      stroke="url(#prog)" strokeWidth="3"
                      strokeDasharray={`${uploadProgress} 100`}
                      strokeLinecap="round"
                    />
                    <defs>
                      <linearGradient id="prog" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#7c3aed" />
                        <stop offset="100%" stopColor="#22d3ee" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white">
                    {uploadProgress}%
                  </span>
                </div>
                <p className="text-slate-400 text-sm">Uploading &amp; extracting frames…</p>
              </div>
            )}
          </section>
        )}

        {/* ── Video ready card ── */}
        {(stage === "ready" || stage === "searching") && uploadResult && (
          <section id="video-ready" className="rounded-2xl border border-slate-700/60 bg-white/[0.03] backdrop-blur-sm p-6">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs text-emerald-400 font-semibold uppercase tracking-widest">Video Ready</span>
                </div>
                <h2 className="text-lg font-bold text-white truncate max-w-xs sm:max-w-lg">
                  {uploadResult.filename}
                </h2>
                <div className="flex flex-wrap gap-3 mt-2 text-xs text-slate-500">
                  <span>{uploadResult.frame_count} frames</span>
                  <span>·</span>
                  <span>{uploadResult.metadata.fps} fps</span>
                  <span>·</span>
                  <span>{uploadResult.metadata.width}×{uploadResult.metadata.height}</span>
                  <span>·</span>
                  <span>{formatDuration(uploadResult.metadata.duration_seconds)}</span>
                </div>
              </div>
              <button
                id="change-video-btn"
                onClick={() => { setStage("idle"); setUploadResult(null); setSearchResult(null); setQuery(""); }}
                className="text-xs text-slate-500 hover:text-white border border-slate-700 hover:border-slate-500 px-3 py-1.5 rounded-lg transition-colors"
              >
                Change video
              </button>
            </div>

            {/* Search */}
            <div className="mt-6 flex gap-3">
              <div className="flex-1 relative">
                <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  id="search-input"
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  placeholder='e.g. "Where does the person pick up a red bag?"'
                  disabled={stage === "searching"}
                  className="w-full bg-slate-800/60 border border-slate-700 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 rounded-xl pl-11 pr-4 py-3.5 text-sm text-white placeholder-slate-500 outline-none transition-all disabled:opacity-50"
                />
              </div>
              <button
                id="search-btn"
                onClick={handleSearch}
                disabled={!query.trim() || stage === "searching"}
                className="px-6 py-3.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-violet-900/40 whitespace-nowrap"
              >
                {stage === "searching" ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Searching…
                  </span>
                ) : "Search"}
              </button>
            </div>

            {/* Example queries */}
            <div className="mt-3 flex flex-wrap gap-2">
              {[
                "Show me the opening scene",
                "When does someone enter the room?",
                "Find the moment with the most people",
              ].map((ex) => (
                <button
                  key={ex}
                  onClick={() => setQuery(ex)}
                  className="text-xs text-slate-500 hover:text-violet-300 border border-slate-700/60 hover:border-violet-700/60 px-2.5 py-1 rounded-lg transition-colors"
                >
                  {ex}
                </button>
              ))}
            </div>
          </section>
        )}

        {/* ── Error banner ── */}
        {error && (
          <div id="error-banner" className="mt-6 flex items-start gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-5 py-4">
            <svg className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
            <div>
              <p className="text-sm font-semibold text-rose-300">Something went wrong</p>
              <p className="text-xs text-rose-400/80 mt-0.5">{error}</p>
            </div>
            <button onClick={() => setError(null)} className="ml-auto text-rose-500 hover:text-rose-300">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* ── Search result ── */}
        {searchResult && (
          <section
            id="search-result"
            className={[
              "mt-6 rounded-2xl border backdrop-blur-sm p-6 transition-all",
              searchResult.found
                ? "border-violet-500/30 bg-violet-500/5"
                : "border-slate-700/60 bg-white/[0.02]",
            ].join(" ")}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${searchResult.found ? "bg-violet-500/20" : "bg-slate-700/50"}`}>
                {searchResult.found ? (
                  <svg className="w-4 h-4 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
              </div>
              <div>
                <p className="font-semibold text-white">
                  {searchResult.found ? "Match Found" : "No Match Found"}
                </p>
                <p className="text-xs text-slate-500 italic mt-0.5">&quot;{searchResult.query}&quot;</p>
              </div>
              {searchResult.found && searchResult.timestamp_seconds !== null && (
                <div className="ml-auto text-right">
                  <p className="text-2xl font-bold text-violet-300">
                    {formatDuration(searchResult.timestamp_seconds)}
                  </p>
                  <p className="text-xs text-slate-500">timestamp</p>
                </div>
              )}
            </div>

            {/* Frame preview */}
            {searchResult.found && searchResult.frame_filename && uploadResult && (
              <div className="mb-4 rounded-xl overflow-hidden border border-slate-700/50">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  id="result-frame"
                  src={frameImageUrl(uploadResult.video_id, searchResult.frame_filename)}
                  alt="Matched video frame"
                  className="w-full object-cover max-h-[360px]"
                />
              </div>
            )}

            <p className="text-sm text-slate-300 leading-relaxed">{searchResult.description}</p>

            {searchResult.found && (
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
                <span>
                  Confidence:{" "}
                  <span className={`font-semibold ${CONFIDENCE_COLORS[searchResult.confidence] ?? "text-slate-400"}`}>
                    {searchResult.confidence}
                  </span>
                </span>
                {searchResult.frame_index !== null && (
                  <span>Frame index: {searchResult.frame_index}</span>
                )}
              </div>
            )}
          </section>
        )}

        {/* ── How it works ── */}
        {stage === "idle" && (
          <section id="how-it-works" className="mt-16">
            <p className="text-center text-xs text-slate-600 uppercase tracking-widest mb-8">How it works</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { icon: "📹", title: "1. Upload", desc: "Drop in any video file. Frames are extracted automatically." },
                { icon: "🔍", title: "2. Ask", desc: "Type a natural language question about the video content." },
                { icon: "✨", title: "3. Discover", desc: "Gemini Vision finds the exact moment and shows you the frame." },
              ].map((step) => (
                <div key={step.title} className="rounded-xl border border-slate-800 bg-white/[0.02] p-5 text-center hover:border-slate-700 transition-colors">
                  <div className="text-3xl mb-3">{step.icon}</div>
                  <h3 className="font-semibold text-slate-200 mb-1">{step.title}</h3>
                  <p className="text-sm text-slate-500">{step.desc}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      <footer className="relative z-10 text-center text-xs text-slate-700 pb-8 mt-4">
        RecallVision · Built with Gemini Vision, FastAPI &amp; Next.js
      </footer>
    </main>
  );
}
