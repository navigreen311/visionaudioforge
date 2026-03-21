"use client";

import { useState, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SearchContext {
  query: string;
  resultCount: number;
  filters: Record<string, string | boolean | number>;
}

export interface CopilotFilters {
  dateRange?: string;
  assetType?: string;
  minConfidence?: number;
  excludeArchived?: boolean;
  [key: string]: string | boolean | number | undefined;
}

interface CopilotRefinementProps {
  searchContext: SearchContext;
  onFiltersApplied: (filters: CopilotFilters) => void;
}

// ---------------------------------------------------------------------------
// Preset chips
// ---------------------------------------------------------------------------

interface Chip {
  label: string;
  prompt: string;
}

const PRESET_CHIPS: Chip[] = [
  { label: "Only from last 7 days", prompt: "Only show results from the last 7 days" },
  { label: "Only audio files", prompt: "Filter to audio files only" },
  { label: "Higher confidence only", prompt: "Only show results with high confidence scores" },
  { label: "Exclude archived assets", prompt: "Exclude any archived assets from results" },
];

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------

async function requestCopilotFilters(
  message: string,
  context: SearchContext,
): Promise<CopilotFilters> {
  const res = await fetch("/api/agents/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      context: {
        type: "search_refinement",
        query: context.query,
        resultCount: context.resultCount,
        currentFilters: context.filters,
      },
    }),
  });

  if (!res.ok) {
    throw new Error(`Copilot request failed: ${res.status}`);
  }

  const data: { filters?: CopilotFilters; message?: string } = await res.json();

  // If the API returns filters directly, use them. Otherwise fall back to
  // a best-effort parse from known chip prompts.
  if (data.filters && typeof data.filters === "object") {
    return data.filters;
  }

  // Deterministic fallback when the backend doesn't return structured filters
  return inferFiltersFromPrompt(message);
}

function inferFiltersFromPrompt(prompt: string): CopilotFilters {
  const lower = prompt.toLowerCase();
  const filters: CopilotFilters = {};

  if (lower.includes("last 7 days") || lower.includes("past week")) {
    filters.dateRange = "7d";
  }
  if (lower.includes("last 30 days") || lower.includes("past month")) {
    filters.dateRange = "30d";
  }
  if (lower.includes("audio")) {
    filters.assetType = "audio";
  }
  if (lower.includes("image") || lower.includes("photo")) {
    filters.assetType = "image";
  }
  if (lower.includes("video")) {
    filters.assetType = "video";
  }
  if (lower.includes("high confidence") || lower.includes("higher confidence")) {
    filters.minConfidence = 0.8;
  }
  if (lower.includes("archived")) {
    filters.excludeArchived = true;
  }

  return filters;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CopilotRefinement({
  searchContext,
  onFiltersApplied,
}: CopilotRefinementProps) {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [appliedFilters, setAppliedFilters] = useState<CopilotFilters | null>(null);

  const applyRefinement = useCallback(
    async (prompt: string) => {
      if (!prompt.trim() || isLoading) return;

      setIsLoading(true);
      setError(null);

      try {
        const filters = await requestCopilotFilters(prompt.trim(), searchContext);
        setAppliedFilters(filters);
        onFiltersApplied(filters);
        setInput("");
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Something went wrong";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, searchContext, onFiltersApplied],
  );

  const handleChipClick = useCallback(
    (chip: Chip) => {
      applyRefinement(chip.prompt);
    },
    [applyRefinement],
  );

  const handleSubmit = useCallback(() => {
    applyRefinement(input);
  }, [applyRefinement, input]);

  const clearFilters = useCallback(() => {
    setAppliedFilters(null);
    onFiltersApplied({});
  }, [onFiltersApplied]);

  // Readable summary of applied filters
  const filterSummary = appliedFilters
    ? Object.entries(appliedFilters)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ")
    : null;

  return (
    <div className="w-full bg-white border border-gray-200 rounded-xl shadow-sm p-4 space-y-4">
      {/* Applied filters banner */}
      {appliedFilters && filterSummary && (
        <div className="flex items-center justify-between gap-2 px-3 py-2 bg-brand-50 border border-brand-200 rounded-lg">
          <div className="flex items-center gap-2 min-w-0">
            <svg className="w-4 h-4 text-brand-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            <span className="text-sm text-brand-700 truncate">
              Filters applied by Copilot: {filterSummary}
            </span>
          </div>
          <button
            onClick={clearFilters}
            className="text-xs text-brand-600 hover:text-brand-800 shrink-0 font-medium"
          >
            Clear
          </button>
        </div>
      )}

      {/* Prompt */}
      <div>
        <p className="text-sm text-gray-600 mb-2">
          Describe what you want to narrow down...
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder='e.g. "Only show high-confidence audio files from this week"'
            disabled={isLoading}
            className="flex-1 px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent disabled:opacity-50"
          />
          <button
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            className="px-4 py-2.5 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? "Applying..." : "Refine"}
          </button>
        </div>
      </div>

      {/* Preset chips */}
      <div className="flex flex-wrap gap-2">
        {PRESET_CHIPS.map((chip) => (
          <button
            key={chip.label}
            onClick={() => handleChipClick(chip)}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs font-medium rounded-full border border-gray-200 text-gray-600 hover:bg-gray-100 hover:border-gray-300 disabled:opacity-50 transition-colors"
          >
            {chip.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          {error}
        </p>
      )}
    </div>
  );
}
