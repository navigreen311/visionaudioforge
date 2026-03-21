"use client";

import { useState } from "react";
import ResultCard, { type SearchResult } from "./ResultCard";

type SortOption = "relevance" | "date" | "name" | "size";
type ViewMode = "grid" | "list";

interface SearchResultsGridProps {
  results: SearchResult[];
  query: string;
  onFilterClick: () => void;
  onResultClick: (result: SearchResult) => void;
}

function sortResults(results: SearchResult[], sort: SortOption): SearchResult[] {
  const sorted = [...results];
  switch (sort) {
    case "relevance":
      return sorted.sort((a, b) => b.score - a.score);
    case "date":
      return sorted.sort((a, b) => {
        const da = a.created_at ?? "";
        const db = b.created_at ?? "";
        return db.localeCompare(da);
      });
    case "name":
      return sorted.sort((a, b) => (a.filename ?? "").localeCompare(b.filename ?? ""));
    case "size":
      return sorted.sort((a, b) => (b.size_bytes ?? 0) - (a.size_bytes ?? 0));
    default:
      return sorted;
  }
}

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "relevance", label: "Relevance" },
  { value: "date", label: "Date" },
  { value: "name", label: "Name" },
  { value: "size", label: "Size" },
];

export default function SearchResultsGrid({
  results,
  query,
  onFilterClick,
  onResultClick,
}: SearchResultsGridProps) {
  const [sortBy, setSortBy] = useState<SortOption>("relevance");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");

  const sorted = sortResults(results, sortBy);

  if (results.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No results found for &ldquo;{query}&rdquo;</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Results header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <p className="text-sm text-gray-700">
          <span className="font-semibold">{results.length}</span>{" "}
          result{results.length !== 1 ? "s" : ""} for{" "}
          <span className="font-medium text-gray-900">&ldquo;{query}&rdquo;</span>
        </p>

        <div className="flex items-center gap-3">
          {/* Sort dropdown */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* View toggle */}
          <div className="flex border border-gray-300 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode("grid")}
              className={`px-2.5 py-1.5 text-sm transition-colors ${
                viewMode === "grid"
                  ? "bg-brand-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
              title="Grid view"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={`px-2.5 py-1.5 text-sm transition-colors ${
                viewMode === "list"
                  ? "bg-brand-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
              title="List view"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>

          {/* Filter button */}
          <button
            onClick={onFilterClick}
            className="flex items-center gap-1.5 text-sm font-medium text-gray-600 border border-gray-300 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            Filters
          </button>
        </div>
      </div>

      {/* Grid / List */}
      {viewMode === "grid" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sorted.map((result) => (
            <ResultCard key={result.asset_id} result={result} onClick={onResultClick} />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {sorted.map((result) => (
            <ListRow key={result.asset_id} result={result} onClick={onResultClick} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* List-view row                                                       */
/* ------------------------------------------------------------------ */

interface ListRowProps {
  result: SearchResult;
  onClick: (result: SearchResult) => void;
}

function getScoreColor(score: number): string {
  const pct = Math.round(score * 100);
  if (pct >= 80) return "bg-green-100 text-green-700";
  if (pct >= 60) return "bg-amber-100 text-amber-700";
  return "bg-gray-100 text-gray-600";
}

const modalityColors: Record<string, string> = {
  image: "bg-blue-100 text-blue-700",
  audio: "bg-purple-100 text-purple-700",
  video: "bg-red-100 text-red-700",
};

function ListRow({ result, onClick }: ListRowProps) {
  const scorePercent = Math.round(result.score * 100);

  return (
    <div
      onClick={() => onClick(result)}
      className="flex items-center gap-4 bg-white border border-gray-200 rounded-lg px-4 py-3 hover:shadow-sm transition-shadow cursor-pointer"
    >
      {/* Icon */}
      <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
        {result.asset_type === "image" ? (
          <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        ) : result.asset_type === "audio" ? (
          <svg className="w-5 h-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
          </svg>
        ) : (
          <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        )}
      </div>

      {/* Filename */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{result.filename || "Untitled"}</p>
        <p className="text-xs text-gray-400 truncate">{result.path || result.asset_id}</p>
      </div>

      {/* Modality badge */}
      <span
        className={`text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0 ${
          modalityColors[result.asset_type] ?? "bg-gray-100 text-gray-600"
        }`}
      >
        {result.asset_type}
      </span>

      {/* Score */}
      <span className={`text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0 ${getScoreColor(result.score)}`}>
        {scorePercent}%
      </span>

      {/* Tags */}
      {(result.tags ?? []).slice(0, 2).map((tag) => (
        <span key={tag} className="hidden md:inline text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded flex-shrink-0">
          {tag}
        </span>
      ))}
    </div>
  );
}
