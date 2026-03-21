"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AudioPlayerProps {
  audioFile: File | null;
}

interface AudioMeta {
  duration: number;
  sampleRate: number;
  numberOfChannels: number;
}

type ZoomLevel = 1 | 2 | 4;
type PlaybackSpeed = 0.5 | 1 | 1.5 | 2;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/**
 * Downsample an AudioBuffer into an array of peak amplitudes suitable for
 * waveform rendering. Each entry represents the max absolute amplitude in a
 * window of `samplesPerPixel` samples (across all channels).
 */
function extractPeaks(
  buffer: AudioBuffer,
  samplesPerPixel: number,
): Float32Array {
  const length = buffer.length;
  const numPeaks = Math.ceil(length / samplesPerPixel);
  const peaks = new Float32Array(numPeaks);
  const channels = buffer.numberOfChannels;

  for (let ch = 0; ch < channels; ch++) {
    const data = buffer.getChannelData(ch);
    for (let i = 0; i < numPeaks; i++) {
      const start = i * samplesPerPixel;
      const end = Math.min(start + samplesPerPixel, length);
      let peak = 0;
      for (let j = start; j < end; j++) {
        const abs = Math.abs(data[j]);
        if (abs > peak) peak = abs;
      }
      // Keep the max across channels
      if (peak > peaks[i]) peaks[i] = peak;
    }
  }

  return peaks;
}

// ---------------------------------------------------------------------------
// Waveform drawing
// ---------------------------------------------------------------------------

function drawWaveform(
  canvas: HTMLCanvasElement,
  peaks: Float32Array,
  scrollLeft: number,
): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const dpr = window.devicePixelRatio || 1;
  const cssWidth = canvas.clientWidth;
  const cssHeight = canvas.clientHeight;

  canvas.width = cssWidth * dpr;
  canvas.height = cssHeight * dpr;
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, cssWidth, cssHeight);

  const midY = cssHeight / 2;
  ctx.fillStyle = "#3B82F6";

  // Only draw the visible portion
  const startPx = Math.floor(scrollLeft);
  const endPx = Math.min(startPx + cssWidth, peaks.length);

  for (let i = startPx; i < endPx; i++) {
    const x = i - scrollLeft;
    const h = peaks[i] * midY;
    ctx.fillRect(x, midY - h, 1, h * 2 || 1);
  }
}

function drawPlayhead(
  canvas: HTMLCanvasElement,
  progress: number,
  totalPeaks: number,
  scrollLeft: number,
): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const cssWidth = canvas.clientWidth;
  const cssHeight = canvas.clientHeight;
  const peakX = progress * totalPeaks;
  const x = peakX - scrollLeft;

  if (x < 0 || x > cssWidth) return;

  ctx.strokeStyle = "#EF4444";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(x, 0);
  ctx.lineTo(x, cssHeight);
  ctx.stroke();
}

// ---------------------------------------------------------------------------
// SVG Icons
// ---------------------------------------------------------------------------

function PlayIcon() {
  return (
    <svg
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M6 4h4v16H6zm8 0h4v16h-4z" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AudioPlayer({ audioFile }: AudioPlayerProps) {
  // Refs
  const audioRef = useRef<HTMLAudioElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const animFrameRef = useRef<number>(0);
  const audioCtxRef = useRef<AudioContext | null>(null);

  // State
  const [audioBuffer, setAudioBuffer] = useState<AudioBuffer | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [speed, setSpeed] = useState<PlaybackSpeed>(1);
  const [zoom, setZoom] = useState<ZoomLevel>(1);
  const [isDecoding, setIsDecoding] = useState(false);
  const [meta, setMeta] = useState<AudioMeta | null>(null);

  // Derived
  const baseSamplesPerPixel = 256;
  const samplesPerPixel = baseSamplesPerPixel / zoom;

  const peaks = useMemo(() => {
    if (!audioBuffer) return null;
    return extractPeaks(audioBuffer, samplesPerPixel);
  }, [audioBuffer, samplesPerPixel]);

  const totalWaveformWidth = peaks ? peaks.length : 0;

  // -----------------------------------------------------------------------
  // Decode audio file
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (!audioFile) {
      setAudioBuffer(null);
      setMeta(null);
      setCurrentTime(0);
      setIsPlaying(false);
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
        setAudioUrl(null);
      }
      return;
    }

    let cancelled = false;

    const decode = async () => {
      setIsDecoding(true);
      setAudioBuffer(null);
      setMeta(null);
      setCurrentTime(0);
      setIsPlaying(false);

      // Create object URL for the <audio> element
      const url = URL.createObjectURL(audioFile);
      setAudioUrl(url);

      try {
        const arrayBuffer = await audioFile.arrayBuffer();
        const ctx = new AudioContext();
        audioCtxRef.current = ctx;
        const decoded = await ctx.decodeAudioData(arrayBuffer);

        if (!cancelled) {
          setAudioBuffer(decoded);
          setMeta({
            duration: decoded.duration,
            sampleRate: decoded.sampleRate,
            numberOfChannels: decoded.numberOfChannels,
          });
        }
      } catch (err) {
        console.error("Failed to decode audio file:", err);
      } finally {
        if (!cancelled) setIsDecoding(false);
      }
    };

    decode();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioFile]);

  // Revoke old object URL when it changes
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  // Clean up AudioContext on unmount
  useEffect(() => {
    return () => {
      if (audioCtxRef.current) {
        audioCtxRef.current.close().catch(() => {});
        audioCtxRef.current = null;
      }
    };
  }, []);

  // -----------------------------------------------------------------------
  // Animation loop — draw waveform + playhead
  // -----------------------------------------------------------------------
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !peaks) return;

    let running = true;

    const tick = () => {
      if (!running) return;

      const scrollLeft = wrapperRef.current?.scrollLeft ?? 0;
      drawWaveform(canvas, peaks, scrollLeft);

      // Draw playhead
      const audio = audioRef.current;
      if (audio && meta) {
        const progress = audio.currentTime / meta.duration;
        drawPlayhead(canvas, progress, peaks.length, scrollLeft);
        setCurrentTime(audio.currentTime);
      }

      animFrameRef.current = requestAnimationFrame(tick);
    };

    animFrameRef.current = requestAnimationFrame(tick);

    return () => {
      running = false;
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [peaks, meta]);

  // -----------------------------------------------------------------------
  // Playback controls
  // -----------------------------------------------------------------------
  const togglePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    // Resume AudioContext if suspended (browser autoplay policy)
    if (audioCtxRef.current?.state === "suspended") {
      audioCtxRef.current.resume().catch(() => {});
    }

    if (audio.paused) {
      audio.play().catch(() => {});
      setIsPlaying(true);
    } else {
      audio.pause();
      setIsPlaying(false);
    }
  }, []);

  // Sync volume
  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = volume;
  }, [volume]);

  // Sync playback speed
  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = speed;
  }, [speed]);

  // -----------------------------------------------------------------------
  // Click-to-seek on waveform
  // -----------------------------------------------------------------------
  const handleCanvasClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const audio = audioRef.current;
      const canvas = canvasRef.current;
      if (!audio || !canvas || !meta || !peaks) return;

      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const scrollLeft = wrapperRef.current?.scrollLeft ?? 0;
      const peakIndex = clickX + scrollLeft;
      const progress = peakIndex / peaks.length;
      audio.currentTime = progress * meta.duration;
      setCurrentTime(audio.currentTime);
    },
    [meta, peaks],
  );

  // -----------------------------------------------------------------------
  // Audio element event handlers
  // -----------------------------------------------------------------------
  const handleEnded = useCallback(() => {
    setIsPlaying(false);
  }, []);

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  if (!audioFile) return null;

  return (
    <div className="w-full rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Hidden audio element */}
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          preload="auto"
          onEnded={handleEnded}
          className="hidden"
        />
      )}

      {/* Loading state */}
      {isDecoding && (
        <div className="flex items-center justify-center gap-2 p-6">
          <svg
            className="h-5 w-5 animate-spin text-blue-500"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
          <span className="text-sm text-gray-600">Decoding audio...</span>
        </div>
      )}

      {/* Waveform */}
      {peaks && !isDecoding && (
        <div className="p-3">
          {/* Zoom controls */}
          <div className="mb-2 flex items-center gap-1">
            <span className="mr-1 text-xs text-gray-500">Zoom:</span>
            {([1, 2, 4] as ZoomLevel[]).map((level) => (
              <button
                key={level}
                onClick={() => setZoom(level)}
                className={`rounded px-2 py-0.5 text-xs font-medium transition-colors ${
                  zoom === level
                    ? "bg-blue-500 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {level}x
              </button>
            ))}
          </div>

          {/* Scrollable waveform container */}
          <div
            ref={wrapperRef}
            className="overflow-x-auto rounded bg-gray-900"
            style={{ height: 80 }}
          >
            <canvas
              ref={canvasRef}
              onClick={handleCanvasClick}
              className="block cursor-crosshair"
              style={{
                width: totalWaveformWidth,
                height: 80,
                minWidth: "100%",
              }}
            />
          </div>
        </div>
      )}

      {/* Controls row */}
      {meta && !isDecoding && (
        <div className="flex items-center gap-3 border-t border-gray-100 px-3 py-2">
          {/* Play / Pause */}
          <button
            onClick={togglePlayPause}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 text-white transition-colors hover:bg-blue-600"
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? <PauseIcon /> : <PlayIcon />}
          </button>

          {/* Time display */}
          <span className="min-w-[90px] text-xs tabular-nums text-gray-700">
            {formatTime(currentTime)} / {formatTime(meta.duration)}
          </span>

          {/* Volume */}
          <div className="flex items-center gap-1.5">
            <svg
              className="h-4 w-4 text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.536 8.464a5 5 0 010 7.072M12 6.253v11.494l-4.5-3.75H4.5A1.5 1.5 0 013 12.497v-1a1.5 1.5 0 011.5-1.5H7.5l4.5-3.75z"
              />
            </svg>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={volume}
              onChange={(e) => setVolume(parseFloat(e.target.value))}
              className="h-1 w-20 cursor-pointer accent-blue-500"
            />
          </div>

          {/* Speed selector */}
          <select
            value={speed}
            onChange={(e) => setSpeed(parseFloat(e.target.value) as PlaybackSpeed)}
            className="rounded border border-gray-300 bg-white px-1.5 py-0.5 text-xs text-gray-700"
          >
            <option value={0.5}>0.5x</option>
            <option value={1}>1x</option>
            <option value={1.5}>1.5x</option>
            <option value={2}>2x</option>
          </select>
        </div>
      )}

      {/* File info strip */}
      {meta && !isDecoding && audioFile && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-gray-100 px-3 py-2 text-xs text-gray-500">
          <span className="font-medium text-gray-700 truncate max-w-[200px]">
            {audioFile.name}
          </span>
          <span>{formatTime(meta.duration)}</span>
          <span>{meta.sampleRate.toLocaleString()} Hz</span>
          <span>
            {meta.numberOfChannels} {meta.numberOfChannels === 1 ? "channel" : "channels"}
          </span>
          <span>{formatFileSize(audioFile.size)}</span>
        </div>
      )}
    </div>
  );
}
