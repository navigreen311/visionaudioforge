"use client";

import React, { useRef, useEffect, useState, useCallback } from "react";
import type { Stream, GridLayout } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface StreamCellProps {
  stream: Stream;
  onRemove: (streamId: string) => void;
  gridSize: GridLayout;
}

interface HealthStats {
  fpsHistory: number[];
  latencyMs: number;
  quality: "good" | "fair" | "poor";
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const QUALITY_COLORS: Record<HealthStats["quality"], string> = {
  good: "bg-green-500 text-green-50",
  fair: "bg-yellow-500 text-yellow-50",
  poor: "bg-red-500 text-red-50",
};

function qualityFromFps(fps: number): HealthStats["quality"] {
  if (fps >= 24) return "good";
  if (fps >= 15) return "fair";
  return "poor";
}

/* ---- Tiny FPS sparkline ---- */
function FPSSparkline({ data }: { data: number[] }) {
  const max = Math.max(...data, 30);
  const w = 60;
  const h = 16;
  const step = w / Math.max(data.length - 1, 1);

  const points = data
    .map((v, i) => `${i * step},${h - (v / max) * h}`)
    .join(" ");

  return (
    <svg width={w} height={h} className="block">
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="text-green-400"
      />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function StreamCell({
  stream,
  onRemove,
  gridSize,
}: StreamCellProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [aiEnabled, setAiEnabled] = useState(true);
  const [isHovered, setIsHovered] = useState(false);
  const [health, setHealth] = useState<HealthStats>({
    fpsHistory: [stream.fps],
    latencyMs: 0,
    quality: qualityFromFps(stream.fps),
  });

  /* ---- Simulate health updates ---- */
  useEffect(() => {
    const interval = setInterval(() => {
      setHealth((prev) => {
        const jitter = Math.random() * 4 - 2; // +/- 2
        const newFps = Math.max(0, Math.round(stream.fps + jitter));
        const latency = Math.round(20 + Math.random() * 60);
        const history = [...prev.fpsHistory, newFps].slice(-20);
        return {
          fpsHistory: history,
          latencyMs: latency,
          quality: qualityFromFps(newFps),
        };
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [stream.fps]);

  /* ---- AI overlay placeholder (draws bounding boxes when enabled) ---- */
  useEffect(() => {
    if (!aiEnabled || !canvasRef.current) return;
    const ctx = canvasRef.current.getContext("2d");
    if (!ctx) return;

    const canvas = canvasRef.current;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!aiEnabled) return;
      // Placeholder: draw a sample detection box
      ctx.strokeStyle = "rgba(34, 197, 94, 0.8)";
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      const bx = canvas.width * 0.2;
      const by = canvas.height * 0.3;
      const bw = canvas.width * 0.3;
      const bh = canvas.height * 0.4;
      ctx.strokeRect(bx, by, bw, bh);
      ctx.setLineDash([]);

      ctx.fillStyle = "rgba(34, 197, 94, 0.8)";
      ctx.font = "10px sans-serif";
      ctx.fillText("person 0.94", bx + 2, by - 4);
    };

    draw();
    return () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    };
  }, [aiEnabled]);

  /* ---- Snapshot ---- */
  const handleSnapshot = useCallback(() => {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth || 640;
    canvas.height = videoRef.current.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(videoRef.current, 0, 0);
    const link = document.createElement("a");
    link.download = `${stream.name.replace(/\s+/g, "_")}_snapshot.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }, [stream.name]);

  /* ---- Fullscreen ---- */
  const handleFullscreen = useCallback(() => {
    const el = videoRef.current?.parentElement?.parentElement;
    if (!el) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      el.requestFullscreen?.();
    }
  }, []);

  /* ---- Determine compact mode for small grids ---- */
  const isCompact = gridSize === "3x3" || gridSize === "4x4" || gridSize === "1+5";

  return (
    <div
      className="relative flex flex-col rounded-lg bg-gray-900 h-full min-h-[120px] overflow-hidden group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* ---- Video feed ---- */}
      <div className="relative flex-1 bg-gradient-to-br from-gray-800 to-gray-900">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="absolute inset-0 h-full w-full object-cover"
        />

        {/* Placeholder when no real feed */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <svg
            className="h-12 w-12 text-gray-600 opacity-20"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1}
              d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
        </div>

        {/* ---- AI overlay canvas ---- */}
        <canvas
          ref={canvasRef}
          width={640}
          height={480}
          className={`absolute inset-0 h-full w-full pointer-events-none ${
            aiEnabled ? "opacity-100" : "opacity-0"
          } transition-opacity`}
        />
      </div>

      {/* ---- Bottom overlay: name + zone ---- */}
      <div className="absolute bottom-0 left-0 right-0 flex items-end justify-between px-2 py-1.5 bg-gradient-to-t from-black/70 to-transparent">
        {/* Name (bottom-left) */}
        <div className="flex items-center gap-1.5 min-w-0">
          <span
            className={`h-2 w-2 rounded-full flex-shrink-0 ${
              stream.status === "online"
                ? "bg-green-500"
                : stream.status === "degraded"
                ? "bg-yellow-500"
                : "bg-gray-400"
            }`}
          />
          <span
            className={`font-medium text-white truncate ${
              isCompact ? "text-[10px] max-w-[80px]" : "text-xs max-w-[140px]"
            }`}
          >
            {stream.name}
          </span>
        </div>

        {/* Zone badge (bottom-right) */}
        <span
          className={`rounded-full bg-white/20 backdrop-blur-sm px-2 py-0.5 font-medium text-white flex-shrink-0 ${
            isCompact ? "text-[9px]" : "text-[10px]"
          }`}
        >
          Lobby
        </span>
      </div>

      {/* ---- Health bar ---- */}
      <div
        className={`absolute top-0 left-0 right-0 flex items-center gap-2 px-2 py-1 bg-gradient-to-b from-black/60 to-transparent ${
          isCompact ? "gap-1" : "gap-2"
        }`}
      >
        <FPSSparkline data={health.fpsHistory} />
        <span className="text-[10px] text-gray-300 font-mono">
          {health.latencyMs}ms
        </span>
        <span
          className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase ${
            QUALITY_COLORS[health.quality]
          }`}
        >
          {health.quality}
        </span>
      </div>

      {/* ---- Hover toolbar ---- */}
      <div
        className={`absolute top-8 right-1 flex flex-col gap-1 transition-opacity ${
          isHovered ? "opacity-100" : "opacity-0"
        }`}
      >
        {/* AI toggle */}
        <button
          onClick={() => setAiEnabled((v) => !v)}
          title={aiEnabled ? "Disable AI overlay" : "Enable AI overlay"}
          className={`rounded p-1.5 backdrop-blur-sm transition-colors ${
            aiEnabled
              ? "bg-brand-600/80 text-white"
              : "bg-black/40 text-gray-300 hover:bg-black/60"
          }`}
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
        </button>

        {/* Fullscreen */}
        <button
          onClick={handleFullscreen}
          title="Toggle fullscreen"
          className="rounded bg-black/40 p-1.5 text-gray-300 backdrop-blur-sm hover:bg-black/60 transition-colors"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
            />
          </svg>
        </button>

        {/* Snapshot */}
        <button
          onClick={handleSnapshot}
          title="Take snapshot"
          className="rounded bg-black/40 p-1.5 text-gray-300 backdrop-blur-sm hover:bg-black/60 transition-colors"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
        </button>

        {/* Remove */}
        <button
          onClick={() => onRemove(stream.id)}
          title="Remove stream"
          className="rounded bg-red-600/70 p-1.5 text-white backdrop-blur-sm hover:bg-red-600 transition-colors"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      {/* ---- Primary badge ---- */}
      {stream.is_primary && (
        <div className="absolute top-8 left-1 rounded bg-brand-600 px-1.5 py-0.5 text-[10px] font-bold text-white uppercase tracking-wide">
          Primary
        </div>
      )}
    </div>
  );
}
