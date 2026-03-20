"use client";

import { useState } from "react";
import SearchBar, { type SearchModality } from "@/components/search/SearchBar";
import ResultsGrid from "@/components/search/ResultsGrid";
import type { SearchResult } from "@/components/search/ResultCard";

interface SearchResponse {
  results: SearchResult[];
  query_type: string;
  total_results: number;
  processing_time_ms: number;
}

export default function SearchPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (query: string, modality: SearchModality, file?: File) => {
    setIsLoading(true);
    setError(null);

    try {
      let response: Response;

      if (modality === "text") {
        response = await fetch("/api/search/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, modality: "text", k: 20 }),
        });
      } else {
        const formData = new FormData();
        if (file) formData.append("file", file);
        formData.append("modality", modality);
        formData.append("k", "20");

        response = await fetch("/api/search/query", {
          method: "POST",
          body: formData,
        });
      }

      if (!response.ok) {
        throw new Error(`Search failed with status ${response.status}`);
      }

      const data: SearchResponse = await response.json();
      setSearchResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setSearchResponse(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Cross-Modal Search</h1>
        <p className="text-gray-500 mt-1">
          Search across images, audio, and video using natural language or visual similarity.
        </p>
      </div>

      {/* Search Bar */}
      <SearchBar onSearch={handleSearch} isLoading={isLoading} />

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Results */}
      {searchResponse && (
        <ResultsGrid
          results={searchResponse.results}
          queryType={searchResponse.query_type}
          totalResults={searchResponse.total_results}
          processingTimeMs={searchResponse.processing_time_ms}
          onResultClick={setSelectedResult}
        />
      )}

      {/* Empty state */}
      {!searchResponse && !isLoading && !error && (
        <div className="flex items-center justify-center min-h-[40vh]">
          <div className="text-center space-y-3">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <p className="text-gray-500">Upload and index assets to enable cross-modal search</p>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {selectedResult && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setSelectedResult(null)}
        >
          <div
            className="bg-white rounded-xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal header */}
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <h3 className="font-semibold text-gray-900">Asset Details</h3>
              <button
                onClick={() => setSelectedResult(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal body */}
            <div className="p-6 space-y-4">
              <div className="aspect-video bg-gray-100 rounded-lg flex items-center justify-center">
                {selectedResult.asset_type === "audio" ? (
                  <svg className="w-16 h-16 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                ) : (
                  <svg className="w-16 h-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                )}
              </div>

              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-gray-500">Asset ID</dt>
                  <dd className="font-mono text-gray-900 text-xs mt-0.5">{selectedResult.asset_id}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Type</dt>
                  <dd className="text-gray-900 mt-0.5 capitalize">{selectedResult.asset_type}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Filename</dt>
                  <dd className="text-gray-900 mt-0.5">{selectedResult.filename || "N/A"}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Similarity Score</dt>
                  <dd className="text-gray-900 mt-0.5">{(selectedResult.score * 100).toFixed(1)}%</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-gray-500">Path</dt>
                  <dd className="font-mono text-gray-900 text-xs mt-0.5 break-all">
                    {selectedResult.path || "N/A"}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
