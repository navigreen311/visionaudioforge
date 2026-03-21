"use client";

import { useEffect, useRef, useState, useCallback } from "react";

type ConnectionQuality = "Excellent" | "Good" | "Poor" | "Unstable";

interface HealthMetrics {
  fps: number;
  latencyMs: number;
  bitrateKBs: number;
  framesDropped: number;
  quality: ConnectionQuality;
  fpsHistory: number[];
}

interface StreamHealthBarProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  onReconnect?: () => void;
}

const SPARKLINE_POINTS = 10;
const FPS_HISTORY_MAX = 60;

function getQuality(fps: number, unstableStreak: number): ConnectionQuality {
  if (unstableStreak >= 5) return "Unstable";
  if (fps >= 24) return "Excellent";
  if (fps >= 12) return "Good";
  return "Poor";
}

function qualityColor(quality: ConnectionQuality): string {
  switch (quality) {
    case "Excellent":
      return "bg-green-500 text-white";
    case "Good":
      return "bg-amber-500 text-white";
    case "Poor":
      return "bg-red-500 text-white";
    case "Unstable":
      return "bg-red-500 text-white animate-pulse";
  }
}

function sparklineColor(fps: number): string {
  if (fps >= 24) return "#22c55e";
  if (fps >= 12) return "#f59e0b";
  return "#ef4444";
}

function buildSparklinePath(history: number[]): string {
  const points = history.slice(-SPARKLINE_POINTS);
  if (points.length < 2) return "";

  const maxFps = Math.max(...points, 1);
  const width = 80;
  const height = 16;
  const stepX = width / (SPARKLINE_POINTS - 1);

  return points
    .map((val, i) => {
      const x = i * stepX;
      const y = height - (val / maxFps) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export default function StreamHealthBar({
  videoRef,
  onReconnect,
}: StreamHealthBarProps) {
  const [metrics, setMetrics] = useState<HealthMetrics>({
    fps: 0,
    latencyMs: 0,
    bitrateKBs: 0,
    framesDropped: 0,
    quality: "Poor",
    fpsHistory: [],
  });

  const frameTimestampsRef = useRef<number[]>([]);
  const rafIdRef = useRef<number>(0);
  const prevFrameCountRef = useRef<number>(0);
  const prevByteCountRef = useRef<number>(0);
  const prevTimeRef = useRef<number>(0);
  const unstableStreakRef = useRef<number>(0);
  const fpsHistoryRef = useRef<number[]>([]);

  const measureFrame = useCallback(
    (now: number) => {
      const timestamps = frameTimestampsRef.current;
      timestamps.push(now);

      // Keep only timestamps within the last second
      while (timestamps.length > 0 && timestamps[0] < now - 1000) {
        timestamps.shift();
      }

      const currentFps = timestamps.length;

      // Collect video quality info from the video element
      const video = videoRef.current;
      let droppedFrames = 0;
      let latency = 0;
      let bitrate = 0;

      if (video) {
        const quality = video.getVideoPlaybackQuality?.();
        if (quality) {
          droppedFrames = quality.droppedVideoFrames;

          // Estimate FPS-based latency (inverse relationship)
          const totalFrames = quality.totalVideoFrames;
          if (totalFrames > 0 && prevTimeRef.current > 0) {
            const dt = (now - prevTimeRef.current) / 1000;
            if (dt > 0) {
              const newFrames = totalFrames - prevFrameCountRef.current;
              // Rough latency estimate: time between expected and actual frames
              latency = dt > 0 ? Math.round((1000 / Math.max(currentFps, 1)) * 0.5) : 0;

              // Estimate bitrate from video dimensions and fps
              const pixels = (video.videoWidth || 640) * (video.videoHeight || 480);
              // Very rough: ~0.1 bits per pixel per frame at moderate compression
              const estimatedBitsPerSecond = pixels * 0.1 * Math.max(currentFps, 1);
              bitrate = Math.round(estimatedBitsPerSecond / 8 / 1024);

              prevFrameCountRef.current = totalFrames;
            }
          } else {
            prevFrameCountRef.current = quality.totalVideoFrames;
          }
        }
        prevTimeRef.current = now;

        // Check for srcObject to track connection bytes if available
        const stream = video.srcObject as MediaStream | null;
        if (stream) {
          const tracks = stream.getVideoTracks();
          if (tracks.length > 0) {
            const settings = tracks[0].getSettings();
            if (settings.frameRate) {
              // Use track frame rate as a reference for latency
              const expectedFps = settings.frameRate;
              latency = Math.max(
                0,
                Math.round(((expectedFps - currentFps) / expectedFps) * 100)
              );
            }
          }
        }
      }

      // Track unstable streak (fps < 5 for consecutive measurements)
      if (currentFps < 5) {
        unstableStreakRef.current += 1;
      } else {
        unstableStreakRef.current = 0;
      }

      // Update FPS history
      const history = fpsHistoryRef.current;
      history.push(currentFps);
      if (history.length > FPS_HISTORY_MAX) {
        history.shift();
      }

      const quality = getQuality(currentFps, unstableStreakRef.current);

      setMetrics({
        fps: currentFps,
        latencyMs: latency,
        bitrateKBs: bitrate,
        framesDropped: droppedFrames,
        quality,
        fpsHistory: [...history],
      });

      rafIdRef.current = requestAnimationFrame(measureFrame);
    },
    [videoRef]
  );

  useEffect(() => {
    rafIdRef.current = requestAnimationFrame(measureFrame);
    return () => {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, [measureFrame]);

  const sparklinePoints = buildSparklinePath(metrics.fpsHistory);
  const currentSparklineColor = sparklineColor(metrics.fps);

  return (
    <div className="flex items-center gap-4 px-3 py-1.5 bg-gray-900/80 rounded-lg text-xs font-mono text-gray-300 backdrop-blur-sm">
      {/* FPS + sparkline */}
      <div className="flex items-center gap-2">
        <span className="text-gray-500">FPS</span>
        <span className="font-semibold text-white">{metrics.fps}</span>
        {sparklinePoints && (
          <svg
            width={80}
            height={16}
            viewBox="0 0 80 16"
            className="inline-block"
          >
            <polyline
              points={sparklinePoints}
              fill="none"
              stroke={currentSparklineColor}
              strokeWidth={1.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </svg>
        )}
      </div>

      <span className="text-gray-600">|</span>

      {/* Latency */}
      <div className="flex items-center gap-1">
        <span className="text-gray-500">Latency</span>
        <span>{metrics.latencyMs} ms</span>
      </div>

      <span className="text-gray-600">|</span>

      {/* Bitrate */}
      <div className="flex items-center gap-1">
        <span className="text-gray-500">Bitrate</span>
        <span>{metrics.bitrateKBs} KB/s</span>
      </div>

      <span className="text-gray-600">|</span>

      {/* Frames Dropped */}
      <div className="flex items-center gap-1">
        <span className="text-gray-500">Dropped</span>
        <span className={metrics.framesDropped > 0 ? "text-red-400" : ""}>
          {metrics.framesDropped}
        </span>
      </div>

      <span className="text-gray-600">|</span>

      {/* Quality pill */}
      <span
        className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${qualityColor(metrics.quality)}`}
      >
        {metrics.quality}
      </span>

      {/* Reconnect button — only when Unstable */}
      {metrics.quality === "Unstable" && onReconnect && (
        <button
          onClick={onReconnect}
          className="ml-1 px-2 py-0.5 bg-red-600 hover:bg-red-700 text-white rounded text-[10px] font-semibold transition-colors"
        >
          Reconnect
        </button>
      )}
    </div>
  );
}
