"use client";

import { useState, useEffect, useCallback } from "react";
import type { SearchModality } from "./SearchBar";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SearchHistoryEntry {
  id: string;
  query: string;
  modality: SearchModality;
  resultCount: number;
  timestamp: number; // epoch ms
}

export interface SavedSearch {
  id: string;
  name: string;
  query: string;
  modality: SearchModality;
  lastRun: number; // epoch ms
}

interface SearchHistoryProps {
  onRerun: (query: string, modality: SearchModality) => void;
  onSave: (query: string, name: string) => void;
}

// ---------------------------------------------------------------------------
// localStorage helpers (SSR-safe)
// ---------------------------------------------------------------------------

const HISTORY_KEY = "vaf_search_history";
const SAVED_KEY = "vaf_saved_searches";
const MAX_HISTORY = 10;
const MAX_SAVED = 20;

function readStorage<T>(key: string, fallback: T): T {
  try {
    if (typeof window === "undefined") return fallback;
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeStorage<T>(key: string, value: T): void {
  try {
    if (typeof window === "undefined") return;
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // quota exceeded or blocked – silently ignore
  }
}

// ---------------------------------------------------------------------------
// Exported utility: call this whenever a search completes
// ---------------------------------------------------------------------------

export function addToSearchHistory(
  query: string,
  modality: SearchModality,
  resultCount: number,
): void {
  const history = readStorage<SearchHistoryEntry[]>(HISTORY_KEY, []);
  const entry: SearchHistoryEntry = {
    id: crypto.randomUUID(),
    query,
    modality,
    resultCount,
    timestamp: Date.now(),
  };
  // Remove duplicate queries with same modality, prepend new entry, cap at MAX
  const filtered = history.filter(
    (h) => !(h.query === query && h.modality === modality),
  );
  writeStorage(HISTORY_KEY, [entry, ...filtered].slice(0, MAX_HISTORY));
}

// ---------------------------------------------------------------------------
// Relative time formatter
// ---------------------------------------------------------------------------

function relativeTime(epoch: number): string {
  const diff = Date.now() - epoch;
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(epoch).toLocaleDateString();
}

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

function ModalityIcon({ modality }: { modality: SearchModality }) {
  if (modality === "image") {
    return (
      <svg className="w-4 h-4 text-blue-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    );
  }
  if (modality === "audio") {
    return (
      <svg className="w-4 h-4 text-purple-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
      </svg>
    );
  }
  return (
    <svg className="w-4 h-4 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SearchHistory({ onRerun, onSave }: SearchHistoryProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [history, setHistory] = useState<SearchHistoryEntry[]>([]);
  const [saved, setSaved] = useState<SavedSearch[]>([]);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [saveName, setSaveName] = useState("");

  // Hydrate from localStorage after mount
  useEffect(() => {
    setHistory(readStorage<SearchHistoryEntry[]>(HISTORY_KEY, []));
    setSaved(readStorage<SavedSearch[]>(SAVED_KEY, []));
  }, []);

  // ---- History actions ----

  const deleteEntry = useCallback(
    (id: string) => {
      const updated = history.filter((h) => h.id !== id);
      setHistory(updated);
      writeStorage(HISTORY_KEY, updated);
    },
    [history],
  );

  const clearHistory = useCallback(() => {
    setHistory([]);
    writeStorage(HISTORY_KEY, []);
  }, []);

  const handleRerun = useCallback(
    (entry: SearchHistoryEntry) => {
      onRerun(entry.query, entry.modality);
    },
    [onRerun],
  );

  // ---- Save actions ----

  const startSave = useCallback((id: string) => {
    setSavingId(id);
    setSaveName("");
  }, []);

  const confirmSave = useCallback(
    (entry: SearchHistoryEntry) => {
      if (!saveName.trim()) return;
      const newSaved: SavedSearch = {
        id: crypto.randomUUID(),
        name: saveName.trim(),
        query: entry.query,
        modality: entry.modality,
        lastRun: entry.timestamp,
      };
      const updated = [newSaved, ...saved].slice(0, MAX_SAVED);
      setSaved(updated);
      writeStorage(SAVED_KEY, updated);
      setSavingId(null);
      setSaveName("");
      onSave(entry.query, newSaved.name);
    },
    [saveName, saved, onSave],
  );

  const runSaved = useCallback(
    (s: SavedSearch) => {
      // Update lastRun timestamp
      const updated = saved.map((item) =>
        item.id === s.id ? { ...item, lastRun: Date.now() } : item,
      );
      setSaved(updated);
      writeStorage(SAVED_KEY, updated);
      onRerun(s.query, s.modality);
    },
    [saved, onRerun],
  );

  const deleteSaved = useCallback(
    (id: string) => {
      const updated = saved.filter((s) => s.id !== id);
      setSaved(updated);
      writeStorage(SAVED_KEY, updated);
    },
    [saved],
  );

  const hasContent = history.length > 0 || saved.length > 0;

  return (
    <div className="w-full">
      {/* Toggle button */}
      <button
        onClick={() => setIsOpen((o) => !o)}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <svg
          className={`w-4 h-4 transition-transform ${isOpen ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        Search History
        {hasContent && (
          <span className="ml-1 text-xs bg-gray-200 text-gray-600 rounded-full px-1.5 py-0.5">
            {history.length}
          </span>
        )}
      </button>

      {/* Collapsible panel */}
      {isOpen && (
        <div className="mt-2 bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          {/* Recent searches */}
          {history.length > 0 && (
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Recent Searches
                </h3>
                <button
                  onClick={clearHistory}
                  className="text-xs text-red-500 hover:text-red-700 transition-colors"
                >
                  Clear history
                </button>
              </div>

              <ul className="space-y-1">
                {history.map((entry) => (
                  <li
                    key={entry.id}
                    className="group flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    {/* Click to rerun */}
                    <button
                      onClick={() => handleRerun(entry)}
                      className="flex items-center gap-2 flex-1 min-w-0 text-left"
                    >
                      <ModalityIcon modality={entry.modality} />
                      <span className="text-sm text-gray-800 truncate">
                        {entry.modality === "text"
                          ? entry.query
                          : `[${entry.modality} search]`}
                      </span>
                      <span className="text-xs text-gray-400 shrink-0">
                        {entry.resultCount} result{entry.resultCount !== 1 ? "s" : ""}
                      </span>
                      <span className="text-xs text-gray-400 shrink-0">
                        {relativeTime(entry.timestamp)}
                      </span>
                    </button>

                    {/* Save prompt (inline) */}
                    {savingId === entry.id ? (
                      <div className="flex items-center gap-1">
                        <input
                          type="text"
                          value={saveName}
                          onChange={(e) => setSaveName(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && confirmSave(entry)}
                          placeholder="Name..."
                          autoFocus
                          className="w-28 text-xs px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-brand-500"
                        />
                        <button
                          onClick={() => confirmSave(entry)}
                          disabled={!saveName.trim()}
                          className="text-xs text-brand-600 hover:text-brand-700 disabled:opacity-40"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setSavingId(null)}
                          className="text-xs text-gray-400 hover:text-gray-600"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <>
                        {/* Star to save */}
                        <button
                          onClick={() => startSave(entry.id)}
                          className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-yellow-500 transition-opacity"
                          title="Save search"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                          </svg>
                        </button>

                        {/* Delete */}
                        <button
                          onClick={() => deleteEntry(entry.id)}
                          className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity"
                          title="Remove from history"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Saved searches */}
          {saved.length > 0 && (
            <div className={`p-4 ${history.length > 0 ? "border-t border-gray-100" : ""}`}>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Saved Searches ({saved.length}/{MAX_SAVED})
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {saved.map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center justify-between gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-100"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{s.name}</p>
                      <p className="text-xs text-gray-400 truncate">
                        {s.modality === "text" ? s.query : `[${s.modality} search]`}
                        {" \u00b7 "}
                        {relativeTime(s.lastRun)}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => runSaved(s)}
                        className="text-xs px-2 py-1 rounded bg-brand-600 text-white hover:bg-brand-700 transition-colors"
                      >
                        Run
                      </button>
                      <button
                        onClick={() => deleteSaved(s.id)}
                        className="text-xs px-2 py-1 rounded text-red-500 hover:bg-red-50 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty state */}
          {!hasContent && (
            <div className="p-6 text-center text-sm text-gray-400">
              No search history yet. Run a search to see it here.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
