"use client";

import React, { useCallback, useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Types & constants
// ---------------------------------------------------------------------------

export interface AudioHistoryEntry {
  id: string;
  filename: string;
  operationType: string;
  timestamp: string;
  duration?: number;
}

const STORAGE_KEY = "audio_history";
const MAX_ENTRIES = 10;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Returns a human-readable relative timestamp such as "2 min ago".
 */
export function timeAgo(dateString: string): string {
  const now = Date.now();
  const then = new Date(dateString).getTime();
  const diffSeconds = Math.max(0, Math.floor((now - then) / 1000));

  if (diffSeconds < 60) return "just now";
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes} min ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} hr ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
}

function readHistory(): AudioHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as AudioHistoryEntry[];
  } catch {
    return [];
  }
}

function writeHistory(entries: AudioHistoryEntry[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

/**
 * Adds a new entry to audio history in localStorage.
 * Prepends the entry, assigns a generated id, and trims to 10 entries.
 */
export function addAudioHistory(
  entry: Omit<AudioHistoryEntry, "id">,
): AudioHistoryEntry {
  const newEntry: AudioHistoryEntry = { ...entry, id: generateId() };
  const history = readHistory();
  history.unshift(newEntry);
  writeHistory(history.slice(0, MAX_ENTRIES));
  return newEntry;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface AudioHistoryProps {
  onRestore: (entry: AudioHistoryEntry) => void;
}

export default function AudioHistory({ onRestore }: AudioHistoryProps) {
  const [open, setOpen] = useState(false);
  const [entries, setEntries] = useState<AudioHistoryEntry[]>([]);
  const [confirmClear, setConfirmClear] = useState(false);

  // Sync from localStorage on mount and when panel opens
  useEffect(() => {
    setEntries(readHistory());
  }, [open]);

  // Listen for storage events from other tabs
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setEntries(readHistory());
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  const handleClear = useCallback(() => {
    if (!confirmClear) {
      setConfirmClear(true);
      return;
    }
    writeHistory([]);
    setEntries([]);
    setConfirmClear(false);
  }, [confirmClear]);

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {/* Header / toggle */}
      <button
        className="flex w-full items-center justify-between px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
        onClick={() => {
          setOpen((v) => !v);
          setConfirmClear(false);
        }}
      >
        <span className="flex items-center gap-1.5">
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          Analysis History
          {entries.length > 0 && (
            <span className="ml-1 rounded-full bg-brand-100 text-brand-700 px-1.5 text-xs font-medium">
              {entries.length}
            </span>
          )}
        </span>
        <svg
          className={`h-4 w-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Collapsible body */}
      {open && (
        <div className="border-t border-gray-100 px-3 py-2 space-y-1">
          {entries.length === 0 ? (
            <p className="text-xs text-gray-500 py-2 text-center">
              No analysis history yet
            </p>
          ) : (
            <>
              <ul className="space-y-1 max-h-60 overflow-y-auto">
                {entries.map((entry) => (
                  <li key={entry.id}>
                    <button
                      className="w-full text-left rounded-md px-2 py-1.5 hover:bg-gray-50 transition-colors group"
                      onClick={() => onRestore(entry)}
                    >
                      <p className="text-sm font-medium text-gray-800 truncate group-hover:text-brand-700">
                        {entry.filename}
                      </p>
                      <p className="text-xs text-gray-500 flex items-center gap-1.5">
                        <span className="inline-block rounded bg-gray-100 px-1.5 py-0.5 text-gray-600">
                          {entry.operationType}
                        </span>
                        <span>{timeAgo(entry.timestamp)}</span>
                        {entry.duration !== undefined && (
                          <span>{entry.duration.toFixed(1)}s</span>
                        )}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>

              {/* Clear history */}
              <button
                className="mt-1 w-full rounded-md px-2 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
                onClick={handleClear}
              >
                {confirmClear
                  ? "Confirm clear? Click again"
                  : "Clear history"}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
