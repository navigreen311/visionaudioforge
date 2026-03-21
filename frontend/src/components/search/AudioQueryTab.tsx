"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import ResultsGrid from "./ResultsGrid";
import { type SearchResult } from "./ResultCard";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type InputMode = "upload" | "record";
type MatchType = "similar_sounds" | "same_speech_content" | "same_speaker";

interface AudioQueryTabProps {
  onResultClick?: (result: SearchResult) => void;
}

interface SearchResponse {
  results: SearchResult[];
  total: number;
  processing_time_ms: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const RECORD_DURATION_S = 5;

const MATCH_TYPE_OPTIONS: { value: MatchType; label: string }[] = [
  { value: "similar_sounds", label: "Similar sounds" },
  { value: "same_speech_content", label: "Same speech content" },
  { value: "same_speaker", label: "Same speaker" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Convert a Blob to a base64-encoded string (without the data-url prefix). */
function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      // Strip "data:<mime>;base64," prefix
      resolve(result.split(",")[1] ?? "");
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/** Draw a simple peaks waveform on a canvas from an AudioBuffer. */
function drawWaveform(canvas: HTMLCanvasElement, buffer: AudioBuffer): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const data = buffer.getChannelData(0);
  const width = canvas.width;
  const height = canvas.height;
  const step = Math.ceil(data.length / width);

  ctx.fillStyle = "#111827";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#8b5cf6";
  ctx.lineWidth = 1;

  const mid = height / 2;

  for (let i = 0; i < width; i++) {
    let min = 1.0;
    let max = -1.0;
    for (let j = 0; j < step; j++) {
      const sample = data[i * step + j];
      if (sample === undefined) break;
      if (sample < min) min = sample;
      if (sample > max) max = sample;
    }
    ctx.beginPath();
    ctx.moveTo(i, mid + min * mid);
    ctx.lineTo(i, mid + max * mid);
    ctx.stroke();
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AudioQueryTab({ onResultClick }: AudioQueryTabProps) {
  // --- input mode ---
  const [inputMode, setInputMode] = useState<InputMode>("upload");

  // --- upload state ---
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadAudioUrl, setUploadAudioUrl] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const uploadInputRef = useRef<HTMLInputElement>(null);

  // --- recording state ---
  const [isRecording, setIsRecording] = useState(false);
  const [countdown, setCountdown] = useState(RECORD_DURATION_S);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const [micError, setMicError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const countdownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const waveCanvasRef = useRef<HTMLCanvasElement>(null);

  // --- options ---
  const [matchType, setMatchType] = useState<MatchType>("similar_sounds");
  const [trimSilence, setTrimSilence] = useState(true);

  // --- search state ---
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);

  // ---------------------------------------------------------------------------
  // Cleanup on unmount
  // ---------------------------------------------------------------------------

  useEffect(() => {
    return () => {
      // Stop media recorder if running
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
      }
      // Stop mic stream tracks
      streamRef.current?.getTracks().forEach((t) => t.stop());
      // Close audio context
      if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
        audioCtxRef.current.close();
      }
      // Clear countdown timer
      if (countdownTimerRef.current) {
        clearInterval(countdownTimerRef.current);
      }
      // Revoke object urls
      if (uploadAudioUrl) URL.revokeObjectURL(uploadAudioUrl);
      if (recordedUrl) URL.revokeObjectURL(recordedUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------------------
  // Upload handlers
  // ---------------------------------------------------------------------------

  const handleFileSelect = useCallback(
    (file: File) => {
      setUploadedFile(file);
      if (uploadAudioUrl) URL.revokeObjectURL(uploadAudioUrl);
      setUploadAudioUrl(URL.createObjectURL(file));
      setSearchResults(null);
      setSearchError(null);
    },
    [uploadAudioUrl],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith("audio/")) {
        handleFileSelect(file);
      }
    },
    [handleFileSelect],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  // ---------------------------------------------------------------------------
  // Recording handlers
  // ---------------------------------------------------------------------------

  const stopRecording = useCallback(() => {
    if (countdownTimerRef.current) {
      clearInterval(countdownTimerRef.current);
      countdownTimerRef.current = null;
    }
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setIsRecording(false);
  }, []);

  const startRecording = useCallback(async () => {
    setMicError(null);
    setRecordedBlob(null);
    setSearchResults(null);
    setSearchError(null);
    if (recordedUrl) URL.revokeObjectURL(recordedUrl);
    setRecordedUrl(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        setRecordedBlob(blob);
        const url = URL.createObjectURL(blob);
        setRecordedUrl(url);

        // Decode audio and draw waveform on canvas
        try {
          const ctx = audioCtxRef.current ?? new AudioContext();
          audioCtxRef.current = ctx;
          const arrayBuf = await blob.arrayBuffer();
          const audioBuffer = await ctx.decodeAudioData(arrayBuf);
          if (waveCanvasRef.current) {
            drawWaveform(waveCanvasRef.current, audioBuffer);
          }
        } catch {
          // Waveform drawing is best-effort
        }
      };

      recorder.start();
      setIsRecording(true);
      setCountdown(RECORD_DURATION_S);

      // Countdown timer
      let remaining = RECORD_DURATION_S;
      countdownTimerRef.current = setInterval(() => {
        remaining -= 1;
        setCountdown(remaining);
        if (remaining <= 0) {
          stopRecording();
        }
      }, 1000);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Could not access microphone. Please allow microphone access.";
      setMicError(message);
    }
  }, [recordedUrl, stopRecording]);

  // ---------------------------------------------------------------------------
  // Search
  // ---------------------------------------------------------------------------

  const hasAudioSource =
    inputMode === "upload" ? uploadedFile !== null : recordedBlob !== null;

  const handleSearch = useCallback(async () => {
    setIsSearching(true);
    setSearchError(null);
    setSearchResults(null);

    try {
      const sourceBlob =
        inputMode === "upload" ? uploadedFile : recordedBlob;
      if (!sourceBlob) return;

      const query_audio_b64 = await blobToBase64(sourceBlob);

      const res = await fetch("/api/search/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query_audio_b64,
          match_type: matchType,
          trim_silence: trimSilence,
        }),
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "Unknown error");
        throw new Error(`Search failed (${res.status}): ${text}`);
      }

      const data: SearchResponse = await res.json();
      setSearchResults(data);
    } catch (err) {
      setSearchError(
        err instanceof Error ? err.message : "An unexpected error occurred.",
      );
    } finally {
      setIsSearching(false);
    }
  }, [inputMode, uploadedFile, recordedBlob, matchType, trimSilence]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Input Mode Toggle */}
      <div className="flex gap-2">
        {(
          [
            { value: "upload", label: "Upload File" },
            { value: "record", label: "Record from Mic" },
          ] as const
        ).map((mode) => (
          <button
            key={mode.value}
            onClick={() => {
              setInputMode(mode.value);
              setSearchResults(null);
              setSearchError(null);
            }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              inputMode === mode.value
                ? "bg-brand-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {mode.label}
          </button>
        ))}
      </div>

      {/* Upload Mode */}
      {inputMode === "upload" && (
        <div className="space-y-3">
          {/* Dropzone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => uploadInputRef.current?.click()}
            className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors cursor-pointer ${
              isDragOver
                ? "border-brand-500 bg-brand-50"
                : uploadedFile
                  ? "border-green-400 bg-green-50"
                  : "border-gray-300 bg-gray-50 hover:border-gray-400"
            }`}
          >
            <svg
              className="mb-2 h-8 w-8 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
              />
            </svg>
            {uploadedFile ? (
              <p className="text-sm font-medium text-green-700">
                {uploadedFile.name}{" "}
                <span className="text-green-500">
                  ({(uploadedFile.size / 1024).toFixed(1)} KB)
                </span>
              </p>
            ) : (
              <>
                <p className="text-sm text-gray-600">
                  <span className="font-medium text-brand-600">
                    Click to upload
                  </span>{" "}
                  or drag and drop
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  WAV, MP3, FLAC, OGG supported
                </p>
              </>
            )}
            <input
              ref={uploadInputRef}
              type="file"
              accept="audio/*"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileSelect(file);
              }}
              className="hidden"
            />
          </div>

          {/* Audio preview player */}
          {uploadAudioUrl && (
            <audio src={uploadAudioUrl} controls className="w-full" />
          )}
        </div>
      )}

      {/* Record Mode */}
      {inputMode === "record" && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            {!isRecording ? (
              <Button onClick={startRecording} disabled={isRecording}>
                Record {RECORD_DURATION_S} seconds
              </Button>
            ) : (
              <Button variant="danger" onClick={stopRecording}>
                Stop
              </Button>
            )}

            {isRecording && (
              <span className="flex items-center gap-2 text-sm text-red-600">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                </span>
                Recording... {countdown}s
              </span>
            )}
          </div>

          {/* Mic permission error */}
          {micError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {micError}
            </div>
          )}

          {/* Waveform canvas (shows after recording) */}
          {recordedBlob && (
            <Card title="Recorded Waveform">
              <canvas
                ref={waveCanvasRef}
                width={600}
                height={120}
                className="w-full h-[120px] rounded-lg bg-gray-900"
              />
            </Card>
          )}

          {/* Recorded audio player */}
          {recordedUrl && (
            <audio src={recordedUrl} controls className="w-full" />
          )}
        </div>
      )}

      {/* Options */}
      <Card title="Search Options">
        <div className="flex flex-wrap items-center gap-6">
          {/* Match type */}
          <div className="flex flex-col gap-1">
            <label
              htmlFor="match-type-select"
              className="text-xs font-medium text-gray-500 uppercase tracking-wide"
            >
              Match type
            </label>
            <select
              id="match-type-select"
              value={matchType}
              onChange={(e) => setMatchType(e.target.value as MatchType)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            >
              {MATCH_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Trim silence toggle */}
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Trim silence
            </span>
            <button
              onClick={() => setTrimSilence((prev) => !prev)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                trimSilence ? "bg-brand-600" : "bg-gray-300"
              }`}
              role="switch"
              aria-checked={trimSilence}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  trimSilence ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </div>
      </Card>

      {/* Search button */}
      <Button
        size="lg"
        loading={isSearching}
        disabled={!hasAudioSource || isSearching || isRecording}
        onClick={handleSearch}
        className="w-full"
      >
        {isSearching ? "Searching..." : "Search by audio"}
      </Button>

      {/* Error with retry */}
      {searchError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-700">{searchError}</p>
          <Button
            variant="secondary"
            size="sm"
            className="mt-3"
            onClick={handleSearch}
          >
            Retry
          </Button>
        </div>
      )}

      {/* Loading skeleton */}
      {isSearching && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="aspect-square rounded-lg bg-gray-200" />
              <div className="mt-2 h-4 w-3/4 rounded bg-gray-200" />
              <div className="mt-1 h-3 w-1/2 rounded bg-gray-200" />
            </div>
          ))}
        </div>
      )}

      {/* Results */}
      {searchResults && !isSearching && (
        <ResultsGrid
          results={searchResults.results}
          queryType="audio"
          totalResults={searchResults.total}
          processingTimeMs={searchResults.processing_time_ms}
          onResultClick={onResultClick ?? (() => {})}
        />
      )}
    </div>
  );
}
