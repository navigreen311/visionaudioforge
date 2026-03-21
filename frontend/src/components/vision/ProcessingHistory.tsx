"use client";

import React, { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "vision_history";
const MAX_ENTRIES = 10;

export interface HistoryEntry {
  id: string;
  thumbnail: string;
  operationType: string;
  timestamp: string;
  inputImage?: string;
  results?: unknown;
}

function getRelativeTime(isoTimestamp: string): string {
  const now = Date.now();
  const then = new Date(isoTimestamp).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

function readHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as HistoryEntry[];
  } catch {
    return [];
  }
}

function writeHistory(entries: HistoryEntry[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

export function addToHistory(entry: HistoryEntry): void {
  const current = readHistory();
  const updated = [entry, ...current.filter((e) => e.id !== entry.id)].slice(
    0,
    MAX_ENTRIES,
  );
  writeHistory(updated);
  window.dispatchEvent(new Event("vision_history_updated"));
}

interface ProcessingHistoryProps {
  onRestore: (entry: HistoryEntry) => void;
}

export default function ProcessingHistory({
  onRestore,
}: ProcessingHistoryProps) {
  const [collapsed, setCollapsed] = useState(true);
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [confirmClear, setConfirmClear] = useState(false);

  const refresh = useCallback(() => {
    setEntries(readHistory());
  }, []);

  useEffect(() => {
    refresh();
    const handler = () => refresh();
    window.addEventListener("vision_history_updated", handler);
    return () => window.removeEventListener("vision_history_updated", handler);
  }, [refresh]);

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
      <button
        type="button"
        onClick={() => setCollapsed((prev) => !prev)}
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-gray-700 hover:bg-gray-50"
      >
        <span className="flex items-center gap-2">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4 text-gray-500"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z"
              clipRule="evenodd"
            />
          </svg>
          Processing History ({entries.length})
        </span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-4 w-4 text-gray-400 transition-transform ${
            collapsed ? "" : "rotate-180"
          }`}
        >
          <path
            fillRule="evenodd"
            d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {!collapsed && (
        <div className="border-t border-gray-100 px-4 py-3">
          {entries.length === 0 ? (
            <p className="text-xs text-gray-400">No processing history yet.</p>
          ) : (
            <>
              <ul className="space-y-2">
                {entries.map((entry) => (
                  <li key={entry.id}>
                    <button
                      type="button"
                      onClick={() => onRestore(entry)}
                      className="flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left hover:bg-gray-50"
                    >
                      <img
                        src={entry.thumbnail}
                        alt=""
                        className="h-8 w-8 rounded border border-gray-200 object-cover"
                      />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-gray-800">
                          {entry.operationType}
                        </p>
                        <p className="text-xs text-gray-400">
                          {getRelativeTime(entry.timestamp)}
                        </p>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
              <div className="mt-3 border-t border-gray-100 pt-2">
                <button
                  type="button"
                  onClick={handleClear}
                  onBlur={() => setConfirmClear(false)}
                  className="text-xs text-red-500 hover:text-red-700"
                >
                  {confirmClear ? "Confirm clear?" : "Clear history"}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
