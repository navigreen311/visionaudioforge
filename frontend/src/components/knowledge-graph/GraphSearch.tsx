"use client";

import { useState, useEffect, useRef, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AutocompleteSuggestion {
  id: string;
  label: string;
  type: string;
}

interface SearchResult {
  node_ids: string[];
  total: number;
}

interface GraphSearchProps {
  onHighlight: (nodeIds: string[]) => void;
  onClear: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GraphSearch({ onHighlight, onClear }: GraphSearchProps) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<AutocompleteSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [resultCount, setResultCount] = useState<number | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounced autocomplete
  const fetchAutocomplete = useCallback((q: string) => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (!q.trim()) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    debounceTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(
          `/api/knowledge-graph/autocomplete?q=${encodeURIComponent(q)}`
        );
        if (res.ok) {
          const data: AutocompleteSuggestion[] = await res.json();
          setSuggestions(data);
          setShowSuggestions(data.length > 0);
        }
      } catch {
        // Silently ignore autocomplete failures
      }
    }, 300);
  }, []);

  // Cleanup debounce timer
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const handleInputChange = (value: string) => {
    setQuery(value);
    fetchAutocomplete(value);
  };

  const handleSearch = async (searchQuery?: string) => {
    const q = searchQuery ?? query;
    if (!q.trim()) return;

    setIsSearching(true);
    setShowSuggestions(false);

    try {
      const res = await fetch(
        `/api/knowledge-graph/search?q=${encodeURIComponent(q)}`
      );
      if (res.ok) {
        const data: SearchResult = await res.json();
        onHighlight(data.node_ids);
        setResultCount(data.total);
      }
    } catch {
      setResultCount(0);
      onHighlight([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch();
  };

  const handleSuggestionClick = (suggestion: AutocompleteSuggestion) => {
    setQuery(suggestion.label);
    setShowSuggestions(false);
    handleSearch(suggestion.label);
  };

  const handleClear = () => {
    setQuery("");
    setSuggestions([]);
    setShowSuggestions(false);
    setResultCount(null);
    onClear();
  };

  const typeColorMap: Record<string, string> = {
    person: "text-blue-400",
    object: "text-green-400",
    location: "text-orange-400",
    event: "text-red-400",
    vehicle: "text-purple-400",
  };

  return (
    <div className="relative">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => handleInputChange(e.target.value)}
            onFocus={() => {
              if (suggestions.length > 0) setShowSuggestions(true);
            }}
            placeholder="Search entities..."
            className="w-full rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />

          {/* Autocomplete dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div
              ref={dropdownRef}
              className="absolute z-50 top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-600 rounded shadow-lg max-h-48 overflow-y-auto"
            >
              {suggestions.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => handleSuggestionClick(s)}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-700 flex items-center gap-2"
                >
                  <span
                    className={`text-xs font-medium ${typeColorMap[s.type] ?? "text-gray-400"}`}
                  >
                    [{s.type}]
                  </span>
                  <span className="text-gray-200">{s.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={isSearching || !query.trim()}
          className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSearching ? "..." : "Go"}
        </button>
      </form>

      {/* Search results bar */}
      {resultCount !== null && (
        <div className="flex items-center justify-between mt-2 px-1">
          <span className="text-xs text-gray-400">
            {resultCount} result{resultCount !== 1 ? "s" : ""} found
          </span>
          <button
            type="button"
            onClick={handleClear}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            Clear search
          </button>
        </div>
      )}
    </div>
  );
}
