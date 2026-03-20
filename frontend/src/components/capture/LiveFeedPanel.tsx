"use client";

import { useEffect, useRef, useCallback } from "react";
import type { SourceType } from "./SourceSwitcher";

interface Detection {
  label: string;
  bbox: [number, number, number, number];
  confidence: number;
}

interface AnalysisResult {
  frame_id: number;
  analysis: {
    brightness: number;
    motion_detected: boolean;
    resolution: [number, number];
  };
  detections: Detection[];
}

interface LiveFeedPanelProps {
  sourceType: SourceType;
  stream: MediaStream | null;
  analysisResult: AnalysisResult | null;
  onFrame?: (base64: string) => void;
}

export default function LiveFeedPanel({
  sourceType,
  stream,
  analysisResult,
  onFrame,
}: LiveFeedPanelProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Attach stream to video element
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
    return () => {
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [stream]);

  // Send frames at 5 FPS
  useEffect(() => {
    if (!stream || !onFrame || sourceType === "microphone") return;

    intervalRef.current = setInterval(() => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState < 2) return;

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.drawImage(video, 0, 0);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.6);
      const base64 = dataUrl.split(",")[1];
      onFrame(base64);
    }, 200); // 5 FPS

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [stream, onFrame, sourceType]);

  // Draw AI overlay
  const drawOverlay = useCallback(() => {
    const overlay = overlayRef.current;
    const video = videoRef.current;
    if (!overlay || !video || !analysisResult) return;

    overlay.width = video.videoWidth || 640;
    overlay.height = video.videoHeight || 480;
    const ctx = overlay.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, overlay.width, overlay.height);

    // Draw motion indicator
    if (analysisResult.analysis.motion_detected) {
      ctx.strokeStyle = "#ef4444";
      ctx.lineWidth = 3;
      ctx.strokeRect(4, 4, overlay.width - 8, overlay.height - 8);
      ctx.fillStyle = "#ef4444";
      ctx.font = "14px sans-serif";
      ctx.fillText("MOTION DETECTED", 10, 24);
    }

    // Draw detection bboxes
    for (const det of analysisResult.detections) {
      const [x, y, w, h] = det.bbox;
      ctx.strokeStyle = "#22c55e";
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);
      ctx.fillStyle = "#22c55e";
      ctx.font = "12px sans-serif";
      ctx.fillText(
        `${det.label} ${(det.confidence * 100).toFixed(0)}%`,
        x,
        y - 4
      );
    }
  }, [analysisResult]);

  useEffect(() => {
    drawOverlay();
  }, [drawOverlay]);

  if (sourceType === "microphone") {
    return null; // Audio handled separately by AudioMeter
  }

  return (
    <div className="relative w-full bg-black rounded-lg overflow-hidden" style={{ aspectRatio: "16/9" }}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-contain"
      />
      {/* Hidden canvas for frame capture */}
      <canvas ref={canvasRef} className="hidden" />
      {/* Overlay canvas for AI results */}
      <canvas
        ref={overlayRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
      />
    </div>
  );
}
