"use client";

import ResultCard, { type SearchResult } from "./ResultCard";

interface ResultsGridProps {
  results: SearchResult[];
  queryType: string;
  totalResults: number;
  processingTimeMs: number;
  onResultClick: (result: SearchResult) => void;
}

export default function ResultsGrid({
  results,
  queryType,
  totalResults,
  processingTimeMs,
  onResultClick,
}: ResultsGridProps) {
  if (results.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      <div className="flex items-center justify-between text-sm text-gray-500">
        <p>
          {totalResults} result{totalResults !== 1 ? "s" : ""} found via{" "}
          <span className="font-medium text-gray-700">{queryType}</span> search
        </p>
        <p>{processingTimeMs.toFixed(1)} ms</p>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {results.map((result) => (
          <ResultCard key={result.asset_id} result={result} onClick={onResultClick} />
        ))}
      </div>
    </div>
  );
}
