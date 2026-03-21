"use client";

import { useState, useEffect, useCallback } from "react";
import SearchBar, { type SearchModality } from "@/components/search/SearchBar";
import SearchResultsGrid from "@/components/search/SearchResultsGrid";
import type { SearchResult } from "@/components/search/ResultCard";

// ---------------------------------------------------------------------------
// Placeholder imports — these components will be built by other agents.
// Uncomment and wire in once they land on their feature branches.
// ---------------------------------------------------------------------------
// import ImageQueryTab from "@/components/search/ImageQueryTab";
// import AudioQueryTab from "@/components/search/AudioQueryTab";
// import FiltersSidebar from "@/components/search/FiltersSidebar";
// import ResultDetailPanel from "@/components/search/ResultDetailPanel";
// import SearchHistory from "@/components/search/SearchHistory";
// import CopilotRefinement from "@/components/search/CopilotRefinement";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface IndexStatus {
  images: number;
  audio: number;
  videos: number;
  total: number;
}

interface SearchResponseData {
  results: SearchResult[];
  query_type: string;
  total_results: number;
  processing_time_ms: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SearchPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [searchResponse, setSearchResponse] = useState<SearchResponseData | null>(null);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  // Index status
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null);
  const [indexLoading, setIndexLoading] = useState(true);

  // -----------------------------------------------------------------------
  // Fetch index status on mount
  // -----------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;

    async function fetchIndexStatus() {
      try {
        const res = await fetch("/api/search/index-status");
        if (!res.ok) throw new Error("Failed to load index status");
        const data: IndexStatus = await res.json();
        if (!cancelled) setIndexStatus(data);
      } catch {
        if (!cancelled) {
          setIndexStatus({ images: 0, audio: 0, videos: 0, total: 0 });
        }
      } finally {
        if (!cancelled) setIndexLoading(false);
      }
    }

    fetchIndexStatus();
    return () => {
      cancelled = true;
    };
  }, []);

  // -----------------------------------------------------------------------
  // Search handler
  // -----------------------------------------------------------------------
  const handleSearch = useCallback(
    async (query: string, modality: SearchModality, file?: File) => {
      setIsLoading(true);
      setError(null);
      setLastQuery(query);

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

        const data: SearchResponseData = await response.json();
        setSearchResponse(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Search failed");
        setSearchResponse(null);
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  // -----------------------------------------------------------------------
  // Filter toggle (placeholder until FiltersSidebar lands)
  // -----------------------------------------------------------------------
  const handleFilterClick = useCallback(() => {
    setShowFilters((prev) => !prev);
  }, []);

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Cross-Modal Search</h1>
        <p className="text-gray-500 mt-1">
          Search across images, audio, and video using natural language or visual similarity.
        </p>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Index Status Bar (S1)                                              */}
      {/* ----------------------------------------------------------------- */}
      {!indexLoading && indexStatus && (
        <>
          {indexStatus.total === 0 ? (
            <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm text-amber-800">
                  No assets indexed yet. Index your media to enable cross-modal search.
                </p>
              </div>
              <a
                href="/assets"
                className="text-sm font-medium text-amber-700 hover:text-amber-900 whitespace-nowrap"
              >
                Index more &rarr;
              </a>
            </div>
          ) : (
            <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  <span className="font-medium text-gray-900">{indexStatus.images}</span> images
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-purple-500" />
                  <span className="font-medium text-gray-900">{indexStatus.audio}</span> audio
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-red-500" />
                  <span className="font-medium text-gray-900">{indexStatus.videos}</span> videos
                </span>
                <span className="text-gray-400">|</span>
                <span>
                  <span className="font-medium text-gray-900">{indexStatus.total}</span> total indexed
                </span>
              </div>
              <a
                href="/assets"
                className="text-sm font-medium text-brand-600 hover:text-brand-700 whitespace-nowrap"
              >
                Index more &rarr;
              </a>
            </div>
          )}
        </>
      )}

      {/* Search Bar */}
      <SearchBar onSearch={handleSearch} isLoading={isLoading} />

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Filters sidebar placeholder */}
      {showFilters && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-500">
          FiltersSidebar placeholder -- will be provided by another agent.
        </div>
      )}

      {/* Results (S2) */}
      {searchResponse && searchResponse.results.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-400">
            Searched via <span className="font-medium">{searchResponse.query_type}</span> in{" "}
            {searchResponse.processing_time_ms.toFixed(1)} ms
          </p>
          <SearchResultsGrid
            results={searchResponse.results}
            query={lastQuery}
            onFilterClick={handleFilterClick}
            onResultClick={setSelectedResult}
          />
        </div>
      )}

      {/* No results after search */}
      {searchResponse && searchResponse.results.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No results found. Try different keywords or upload a reference file.</p>
        </div>
      )}

      {/* Empty state — before any search */}
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
                ) : selectedResult.asset_type === "video" ? (
                  <svg className="w-16 h-16 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
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

              {/* Tags */}
              {(selectedResult.tags ?? []).length > 0 && (
                <div>
                  <dt className="text-sm text-gray-500 mb-1">Tags</dt>
                  <div className="flex flex-wrap gap-1">
                    {(selectedResult.tags ?? []).map((tag) => (
                      <span
                        key={tag}
                        className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
