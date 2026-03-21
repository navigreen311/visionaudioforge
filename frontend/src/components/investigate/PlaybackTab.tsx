"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import { CaseEvent } from "./EvidenceTab";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PlaybackTabProps {
  caseId: string;
  events: CaseEvent[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const eventDotColors: Record<CaseEvent["type"], string> = {
  camera: "#3B82F6",
  audio: "#10B981",
  alert: "#F59E0B",
  note: "#6B7280",
  detection: "#EF4444",
  evidence: "#8B5CF6",
};

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function parseEventTimestamp(event: CaseEvent, baseTime: number, totalDuration: number): number {
  const eventTime = new Date(event.timestamp).getTime();
  const offset = (eventTime - baseTime) / 1000;
  return Math.max(0, Math.min(offset, totalDuration));
}

// ---------------------------------------------------------------------------
// Audio Waveform (simple canvas peaks)
// ---------------------------------------------------------------------------

interface AudioWaveformProps {
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
}

function AudioWaveform({ currentTime, duration, onSeek }: AudioWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const peaksRef = useRef<number[]>([]);

  // Generate deterministic peaks once
  useEffect(() => {
    const barCount = 120;
    const peaks: number[] = [];
    for (let i = 0; i < barCount; i++) {
      // Simple pseudo-random using sin
      peaks.push(0.2 + 0.8 * Math.abs(Math.sin(i * 0.7 + i * i * 0.01)));
    }
    peaksRef.current = peaks;
  }, []);

  // Draw waveform
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const peaks = peaksRef.current;
    const barCount = peaks.length;
    const barWidth = width / barCount;
    const playProgress = duration > 0 ? currentTime / duration : 0;

    ctx.clearRect(0, 0, width, height);

    for (let i = 0; i < barCount; i++) {
      const x = i * barWidth;
      const barH = peaks[i] * (height * 0.8);
      const y = (height - barH) / 2;
      const progress = i / barCount;

      ctx.fillStyle = progress <= playProgress ? "#6366F1" : "#D1D5DB";
      ctx.fillRect(x + 1, y, barWidth - 2, barH);
    }

    // Playhead line
    const playX = playProgress * width;
    ctx.strokeStyle = "#4F46E5";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(playX, 0);
    ctx.lineTo(playX, height);
    ctx.stroke();
  }, [currentTime, duration]);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas || duration <= 0) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const ratio = x / rect.width;
      onSeek(ratio * duration);
    },
    [duration, onSeek]
  );

  return (
    <canvas
      ref={canvasRef}
      onClick={handleClick}
      className="w-full h-16 rounded-lg bg-gray-50 cursor-pointer"
      style={{ display: "block" }}
    />
  );
}

// ---------------------------------------------------------------------------
// Event Timeline Scrubber (horizontal bar with colored dot markers)
// ---------------------------------------------------------------------------

interface TimelineScrubberProps {
  currentTime: number;
  duration: number;
  events: CaseEvent[];
  baseTime: number;
  onSeek: (time: number) => void;
}

function TimelineScrubber({
  currentTime,
  duration,
  events,
  baseTime,
  onSeek,
}: TimelineScrubberProps) {
  const trackRef = useRef<HTMLDivElement>(null);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const track = trackRef.current;
      if (!track || duration <= 0) return;
      const rect = track.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const ratio = Math.max(0, Math.min(1, x / rect.width));
      onSeek(ratio * duration);
    },
    [duration, onSeek]
  );

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 w-10 text-right">{formatTime(currentTime)}</span>

        <div
          ref={trackRef}
          onClick={handleClick}
          className="flex-1 relative h-6 bg-gray-100 rounded-full cursor-pointer group"
        >
          {/* Progress fill */}
          <div
            className="absolute top-0 left-0 h-full bg-indigo-100 rounded-full pointer-events-none"
            style={{ width: `${progress}%` }}
          />

          {/* Event dots */}
          {events.map((event) => {
            const pos = parseEventTimestamp(event, baseTime, duration);
            const left = duration > 0 ? (pos / duration) * 100 : 0;
            return (
              <div
                key={event.id}
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-white shadow-sm pointer-events-none"
                style={{
                  left: `${left}%`,
                  backgroundColor: eventDotColors[event.type],
                }}
                title={`${event.type}: ${event.summary}`}
              />
            );
          })}

          {/* Playhead */}
          <div
            className="absolute top-0 w-0.5 h-full bg-indigo-600 pointer-events-none"
            style={{ left: `${progress}%` }}
          />
          <div
            className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-indigo-600 border-2 border-white shadow-md pointer-events-none"
            style={{ left: `calc(${progress}% - 8px)` }}
          />
        </div>

        <span className="text-xs text-gray-500 w-10">{formatTime(duration)}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Event List Panel
// ---------------------------------------------------------------------------

interface EventListPanelProps {
  events: CaseEvent[];
  currentTime: number;
  baseTime: number;
  duration: number;
  onSeek: (time: number) => void;
}

function EventListPanel({
  events,
  currentTime,
  baseTime,
  duration,
  onSeek,
}: EventListPanelProps) {
  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  return (
    <div className="space-y-1 max-h-48 overflow-y-auto">
      {sorted.map((event) => {
        const eventSec = parseEventTimestamp(event, baseTime, duration);
        const isCurrent = Math.abs(eventSec - currentTime) < 2;

        return (
          <div
            key={event.id}
            onClick={() => onSeek(eventSec)}
            className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
              isCurrent
                ? "bg-indigo-50 border border-indigo-200"
                : "hover:bg-gray-50 border border-transparent"
            }`}
          >
            <div
              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: eventDotColors[event.type] }}
            />
            <div className="flex-1 min-w-0">
              <p className={`text-xs truncate ${isCurrent ? "text-indigo-900 font-medium" : "text-gray-700"}`}>
                {event.summary}
              </p>
            </div>
            <span className="text-xs text-gray-400 flex-shrink-0">
              {formatTime(eventSec)}
            </span>
            <Badge variant={isCurrent ? "info" : "neutral"}>{event.type}</Badge>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Playlist Selector
// ---------------------------------------------------------------------------

interface PlaylistSelectorProps {
  clips: { id: string; label: string }[];
  activeClipId: string;
  onSelect: (clipId: string) => void;
}

function PlaylistSelector({ clips, activeClipId, onSelect }: PlaylistSelectorProps) {
  if (clips.length <= 1) return null;

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1">
      <span className="text-xs font-semibold text-gray-600 flex-shrink-0">Clips:</span>
      {clips.map((clip) => (
        <button
          key={clip.id}
          onClick={() => onSelect(clip.id)}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors flex-shrink-0 ${
            activeClipId === clip.id
              ? "bg-indigo-600 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          {clip.label}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main PlaybackTab component
// ---------------------------------------------------------------------------

export default function PlaybackTab({ caseId, events }: PlaybackTabProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const animationRef = useRef<number>(0);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(120); // default 2 min
  const [activeClipId, setActiveClipId] = useState("default");

  // Derive base time from the earliest event
  const baseTime = events.length > 0
    ? Math.min(...events.map((e) => new Date(e.timestamp).getTime()))
    : Date.now();

  // Derive clips from video/camera events
  const videoEvents = events.filter((e) => e.type === "camera" && e.mediaUrl);
  const clips = videoEvents.length > 0
    ? videoEvents.map((e, i) => ({ id: e.id, label: `Clip ${i + 1}`, url: e.mediaUrl }))
    : [{ id: "default", label: "No video", url: undefined }];

  const activeClip = clips.find((c) => c.id === activeClipId) ?? clips[0];

  // Sync playback time from video element
  const syncTime = useCallback(() => {
    const video = videoRef.current;
    if (video && !video.paused) {
      setCurrentTime(video.currentTime);
      animationRef.current = requestAnimationFrame(syncTime);
    }
  }, []);

  // Clean up animation frame on unmount
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  const handlePlay = useCallback(() => {
    const video = videoRef.current;
    if (video) {
      video.play().catch(() => {
        // autoplay may be blocked
      });
      setIsPlaying(true);
      animationRef.current = requestAnimationFrame(syncTime);
    } else {
      // No video: simulate playback with interval
      setIsPlaying(true);
    }
  }, [syncTime]);

  const handlePause = useCallback(() => {
    const video = videoRef.current;
    if (video) {
      video.pause();
    }
    setIsPlaying(false);
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
  }, []);

  // Simulated playback when no video
  useEffect(() => {
    if (!isPlaying || activeClip.url) return;

    const interval = window.setInterval(() => {
      setCurrentTime((prev) => {
        if (prev >= duration) {
          setIsPlaying(false);
          return duration;
        }
        return prev + 0.25;
      });
    }, 250);

    return () => {
      window.clearInterval(interval);
    };
  }, [isPlaying, activeClip.url, duration]);

  const handleSeek = useCallback(
    (time: number) => {
      const clamped = Math.max(0, Math.min(time, duration));
      setCurrentTime(clamped);
      const video = videoRef.current;
      if (video) {
        video.currentTime = clamped;
      }
    },
    [duration]
  );

  const handleVideoLoadedMetadata = useCallback(() => {
    const video = videoRef.current;
    if (video && video.duration && isFinite(video.duration)) {
      setDuration(video.duration);
    }
  }, []);

  const handleVideoEnded = useCallback(() => {
    setIsPlaying(false);
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
  }, []);

  const handleClipSelect = useCallback((clipId: string) => {
    setActiveClipId(clipId);
    setCurrentTime(0);
    setIsPlaying(false);
  }, []);

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-6">
        <div className="text-4xl mb-3 opacity-40">{"\u25B6\uFE0F"}</div>
        <p className="text-sm text-gray-500">No playback data</p>
        <p className="text-xs text-gray-400 mt-1">
          Add media events to this case to enable synchronized playback (Case {caseId})
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Playlist selector */}
      <PlaylistSelector
        clips={clips.map((c) => ({ id: c.id, label: c.label }))}
        activeClipId={activeClipId}
        onSelect={handleClipSelect}
      />

      {/* Video player */}
      <div className="bg-black rounded-lg overflow-hidden flex-shrink-0" style={{ aspectRatio: "16/9" }}>
        {activeClip.url ? (
          <video
            ref={videoRef}
            src={activeClip.url}
            className="w-full h-full object-contain"
            preload="metadata"
            onLoadedMetadata={handleVideoLoadedMetadata}
            onEnded={handleVideoEnded}
            onTimeUpdate={() => setCurrentTime(videoRef.current?.currentTime ?? 0)}
          >
            Your browser does not support the video element.
          </video>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-gray-500 text-sm">No video selected</span>
          </div>
        )}
      </div>

      {/* Transport controls */}
      <div className="flex items-center justify-center gap-2">
        <Button
          size="sm"
          variant="ghost"
          onClick={() => handleSeek(Math.max(0, currentTime - 10))}
          title="Rewind 10s"
        >
          -10s
        </Button>
        <Button
          size="sm"
          onClick={isPlaying ? handlePause : handlePlay}
        >
          {isPlaying ? "Pause" : "Play"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => handleSeek(Math.min(duration, currentTime + 10))}
          title="Forward 10s"
        >
          +10s
        </Button>
      </div>

      {/* Audio waveform */}
      <div>
        <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1">
          Audio Waveform
        </h4>
        <AudioWaveform
          currentTime={currentTime}
          duration={duration}
          onSeek={handleSeek}
        />
      </div>

      {/* Timeline scrubber with event markers */}
      <div>
        <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1">
          Event Timeline
        </h4>
        <TimelineScrubber
          currentTime={currentTime}
          duration={duration}
          events={events}
          baseTime={baseTime}
          onSeek={handleSeek}
        />
      </div>

      {/* Event list panel */}
      <div>
        <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1">
          Events
        </h4>
        <EventListPanel
          events={events}
          currentTime={currentTime}
          baseTime={baseTime}
          duration={duration}
          onSeek={handleSeek}
        />
      </div>
    </div>
  );
}
