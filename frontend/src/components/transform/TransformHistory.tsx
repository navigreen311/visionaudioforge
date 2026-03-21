"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "vaf_transform_history";
const MAX_ENTRIES = 10;

export interface TransformHistoryEntry {
  id: string;
  operationName: string;
  timestamp: string;
  thumbnail: string; // base64 data URL, 32x32
  inputFilename?: string;
  outputB64?: string;
  outputFilename?: string;
}

interface TransformHistoryProps {
  onRestore: (entry: TransformHistoryEntry) => void;
}

/** Save a transform result to localStorage history. Call after each successful transform. */
export function saveToTransformHistory(
  entry: Omit<TransformHistoryEntry, "id" | "timestamp">,
): void {
  if (typeof window === "undefined") return;

  const raw = localStorage.getItem(STORAGE_KEY);
  const existing: TransformHistoryEntry[] = raw ? JSON.parse(raw) : [];

  const newEntry: TransformHistoryEntry = {
    ...entry,
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: new Date().toISOString(),
  };

  const updated = [newEntry, ...existing].slice(0, MAX_ENTRIES);

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {
    // localStorage full -- evict oldest entries and retry
    const trimmed = updated.slice(0, 5);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  }
}

export default function TransformHistory({
  onRestore,
}: TransformHistoryProps) {
  const [entries, setEntries] = useState<TransformHistoryEntry[]>([]);
  const [open, setOpen] = useState(false);

  const loadEntries = useCallback(() => {
    if (typeof window === "undefined") return;
    const raw = localStorage.getItem(STORAGE_KEY);
    setEntries(raw ? JSON.parse(raw) : []);
  }, []);

  useEffect(() => {
    loadEntries();

    // Re-sync when other tabs or same-page writes update storage
    const handler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) loadEntries();
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, [loadEntries]);

  const clearHistory = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setEntries([]);
  }, []);

  const handleRestore = useCallback(
    (entry: TransformHistoryEntry) => {
      onRestore(entry);
    },
    [onRestore],
  );

  function formatTimestamp(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  if (entries.length === 0 && !open) return null;

  return (
    <div className="w-full rounded-lg border border-gray-200 bg-white">
      {/* Header / toggle */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors rounded-lg"
      >
        <span className="flex items-center gap-2">
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
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          Recent Transforms ({entries.length})
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

      {open && (
        <div className="border-t border-gray-100 px-4 pb-3">
          {entries.length === 0 ? (
            <p className="py-3 text-center text-xs text-gray-400">
              No transforms yet.
            </p>
          ) : (
            <>
              <ul className="divide-y divide-gray-100">
                {entries.map((entry) => (
                  <li key={entry.id}>
                    <button
                      type="button"
                      onClick={() => handleRestore(entry)}
                      className="flex w-full items-center gap-3 py-2.5 text-left hover:bg-gray-50 transition-colors rounded -mx-1 px-1"
                    >
                      {/* Thumbnail */}
                      <div className="h-8 w-8 flex-shrink-0 overflow-hidden rounded bg-gray-100">
                        {entry.thumbnail ? (
                          <img
                            src={entry.thumbnail}
                            alt={entry.operationName}
                            className="h-full w-full object-cover"
                            width={32}
                            height={32}
                          />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-gray-400">
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
                                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                              />
                            </svg>
                          </div>
                        )}
                      </div>

                      {/* Details */}
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-gray-800">
                          {entry.operationName}
                        </p>
                        <p className="text-xs text-gray-400">
                          {formatTimestamp(entry.timestamp)}
                          {entry.inputFilename && (
                            <span className="ml-1">
                              &middot; {entry.inputFilename}
                            </span>
                          )}
                        </p>
                      </div>

                      {/* Arrow */}
                      <svg
                        className="h-4 w-4 flex-shrink-0 text-gray-300"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </button>
                  </li>
                ))}
              </ul>

              {/* Clear history */}
              <div className="mt-2 flex justify-end">
                <button
                  type="button"
                  onClick={clearHistory}
                  className="text-xs text-red-500 hover:text-red-700 transition-colors"
                >
                  Clear history
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
