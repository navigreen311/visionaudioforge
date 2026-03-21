"use client";

import React, { useCallback, useMemo, useState } from "react";
import Button from "@/components/ui/Button";
import api from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type WhisperModel = "tiny" | "base" | "small";
type Language = "auto" | "en" | "es" | "fr" | "de";
type Task = "transcribe" | "translate";

interface WordTimestamp {
  word: string;
  start: number;
  end: number;
}

interface TranscriptionSegment {
  start: number;
  end: number;
  text: string;
}

interface SpeakerSegment {
  speaker: string;
  start: number;
  end: number;
  text?: string;
}

/**
 * Matches the backend response shape from POST /api/audio/transcribe:
 * { transcript, words, language, speakers, duration_sec }
 *
 * Also supports the legacy shape (text, segments) for backward compatibility.
 */
interface TranscriptionResult {
  /** Primary transcript text (backend key: transcript) */
  transcript: string;
  /** Legacy key — some backends return "text" instead */
  text?: string;
  /** Timed segments for SRT generation */
  segments: TranscriptionSegment[];
  /** Word-level timestamps */
  words?: WordTimestamp[];
  /** Detected language code */
  language: string;
  /** Speaker diarization segments */
  speakers: SpeakerSegment[];
  /** Total duration in seconds */
  duration_sec: number;
}

interface TranscriptionPanelProps {
  audioFile: File | null;
  onSeek?: (time: number) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MODEL_OPTIONS: { value: WhisperModel; label: string }[] = [
  { value: "tiny", label: "Whisper Tiny" },
  { value: "base", label: "Whisper Base" },
  { value: "small", label: "Whisper Small" },
];

const LANGUAGE_OPTIONS: { value: Language; label: string }[] = [
  { value: "auto", label: "Auto-detect" },
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
];

// ---------------------------------------------------------------------------
// SRT generator
// ---------------------------------------------------------------------------

function toSRT(segments: TranscriptionSegment[]): string {
  return segments
    .map((seg, i) => {
      const fmt = (t: number) => {
        const h = Math.floor(t / 3600);
        const m = Math.floor((t % 3600) / 60);
        const s = Math.floor(t % 60);
        const ms = Math.round((t % 1) * 1000);
        return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")},${String(ms).padStart(3, "0")}`;
      };
      return `${i + 1}\n${fmt(seg.start)} --> ${fmt(seg.end)}\n${seg.text.trim()}\n`;
    })
    .join("\n");
}

function downloadBlob(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function formatTimestamp(t: number): string {
  const m = Math.floor(t / 60);
  const s = (t % 60).toFixed(2);
  return `${m}:${Number(s) < 10 ? "0" : ""}${s}`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TranscriptionPanel({
  audioFile,
  onSeek,
}: TranscriptionPanelProps) {
  const [model, setModel] = useState<WhisperModel>("base");
  const [language, setLanguage] = useState<Language>("auto");
  const [task, setTask] = useState<Task>("transcribe");
  const [wordTimestamps, setWordTimestamps] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TranscriptionResult | null>(null);

  /** Resolve the display text from either "transcript" or legacy "text" key */
  const displayText = useMemo(() => {
    if (!result) return "";
    return result.transcript || result.text || "";
  }, [result]);

  // ---- transcribe ----
  const transcribe = useCallback(async () => {
    if (!audioFile) return;
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", audioFile);
      formData.append("model", model);
      if (language !== "auto") formData.append("language", language);
      formData.append("task", task);
      formData.append("word_timestamps", String(wordTimestamps));

      const { data } = await api.post<TranscriptionResult>(
        "/api/audio/transcribe",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      setResult(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Transcription failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [audioFile, model, language, task, wordTimestamps]);

  // ---- copy text ----
  const copyText = useCallback(() => {
    if (!displayText) return;
    navigator.clipboard.writeText(displayText);
  }, [displayText]);

  // ---- downloads ----
  const downloadSRT = useCallback(() => {
    if (!result?.segments) return;
    downloadBlob(toSRT(result.segments), "transcription.srt", "text/srt");
  }, [result]);

  const downloadJSON = useCallback(() => {
    if (!result) return;
    downloadBlob(
      JSON.stringify(result, null, 2),
      "transcription.json",
      "application/json",
    );
  }, [result]);

  const downloadTXT = useCallback(() => {
    if (!displayText) return;
    downloadBlob(displayText, "transcription.txt", "text/plain");
  }, [displayText]);

  // ---- word spans (memoised) ----
  const wordSpans = useMemo(() => {
    if (!result?.words) return null;
    return result.words.map((w, i) => (
      <span
        key={i}
        className="inline-block cursor-pointer rounded px-0.5 hover:bg-brand-100 transition-colors"
        title={`${formatTimestamp(w.start)} - ${formatTimestamp(w.end)}`}
        onClick={() => onSeek?.(w.start)}
      >
        {w.word}{" "}
      </span>
    ));
  }, [result, onSeek]);

  return (
    <div className="space-y-5">
      {/* ---- Controls ---- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Model */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Model
          </label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value as WhisperModel)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          >
            {MODEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Language */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Language
          </label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          >
            {LANGUAGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Task */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Task
          </label>
          <div className="flex gap-4 mt-1">
            <label className="flex items-center gap-1.5 cursor-pointer text-sm text-gray-700">
              <input
                type="radio"
                name="task"
                value="transcribe"
                checked={task === "transcribe"}
                onChange={() => setTask("transcribe")}
                className="h-4 w-4 text-brand-600 focus:ring-brand-500"
              />
              Transcribe
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer text-sm text-gray-700">
              <input
                type="radio"
                name="task"
                value="translate"
                checked={task === "translate"}
                onChange={() => setTask("translate")}
                className="h-4 w-4 text-brand-600 focus:ring-brand-500"
              />
              Translate to English
            </label>
          </div>
        </div>

        {/* Word timestamps */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Options
          </label>
          <label className="flex items-center gap-2 cursor-pointer mt-1">
            <input
              type="checkbox"
              checked={wordTimestamps}
              onChange={(e) => setWordTimestamps(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-sm text-gray-700">Word timestamps</span>
          </label>
        </div>
      </div>

      {/* ---- Transcribe button ---- */}
      <Button
        variant="primary"
        size="md"
        onClick={transcribe}
        loading={loading}
        disabled={!audioFile || loading}
      >
        Transcribe
      </Button>

      {/* ---- Loading skeleton ---- */}
      {loading && (
        <div className="space-y-2 animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4" />
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-5/6" />
          <div className="h-4 bg-gray-200 rounded w-2/3" />
        </div>
      )}

      {/* ---- Error ---- */}
      {error && !loading && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-700">{error}</p>
          <Button
            variant="danger"
            size="sm"
            className="mt-2"
            onClick={transcribe}
          >
            Retry
          </Button>
        </div>
      )}

      {/* ---- Results ---- */}
      {result && !loading && (
        <div className="space-y-4">
          {/* Detected language + duration info bar */}
          {(result.language || result.duration_sec > 0) && (
            <div className="flex items-center gap-4 text-xs text-gray-500">
              {result.language && (
                <span className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 font-medium text-gray-600">
                  Language: {result.language.toUpperCase()}
                </span>
              )}
              {result.duration_sec > 0 && (
                <span>Duration: {result.duration_sec.toFixed(1)}s</span>
              )}
              {result.speakers && result.speakers.length > 0 && (
                <span>Speakers: {result.speakers.length}</span>
              )}
            </div>
          )}

          {/* Full transcript */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Full Transcript
            </label>
            <textarea
              readOnly
              value={displayText}
              rows={6}
              className="w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-800 resize-y focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
          </div>

          {/* Word-by-word display */}
          {wordSpans && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Word-by-Word (click to seek, hover for timestamp)
              </label>
              <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm leading-relaxed text-gray-800 max-h-48 overflow-y-auto">
                {wordSpans}
              </div>
            </div>
          )}

          {/* Speaker segments */}
          {result.speakers && result.speakers.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Speaker Segments
              </label>
              <div className="rounded-lg border border-gray-200 bg-white max-h-40 overflow-y-auto divide-y divide-gray-100">
                {result.speakers.map((seg, i) => (
                  <button
                    key={i}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 transition-colors flex items-center gap-2"
                    onClick={() => onSeek?.(seg.start)}
                  >
                    <span className="inline-block rounded bg-brand-100 px-1.5 py-0.5 text-xs font-medium text-brand-700">
                      {seg.speaker}
                    </span>
                    <span className="text-gray-500 text-xs tabular-nums">
                      {formatTimestamp(seg.start)} - {formatTimestamp(seg.end)}
                    </span>
                    {seg.text && (
                      <span className="text-gray-700 truncate">{seg.text}</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Export buttons */}
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" onClick={copyText}>
              Copy Text
            </Button>
            <Button variant="secondary" size="sm" onClick={downloadSRT}>
              Download SRT
            </Button>
            <Button variant="secondary" size="sm" onClick={downloadJSON}>
              Download JSON
            </Button>
            <Button variant="secondary" size="sm" onClick={downloadTXT}>
              Download TXT
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
