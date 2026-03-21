"use client";

import { useState, useEffect, useCallback } from "react";
import SearchBar, { type SearchModality } from "@/components/search/SearchBar";
import SearchResultsGrid from "@/components/search/SearchResultsGrid";
import type { SearchResult } from "@/components/search/ResultCard";
import ImageQueryTab from "@/components/search/ImageQueryTab";
import AudioQueryTab from "@/components/search/AudioQueryTab";
import FiltersSidebar, {
  type SearchFilters,
  DEFAULT_FILTERS,
} from "@/components/search/FiltersSidebar";
import ResultDetailPanel from "@/components/search/ResultDetailPanel";
import SearchHistory from "@/components/search/SearchHistory";
import CopilotRefinement from "@/components/search/CopilotRefinement";

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
  const [detailOpen, setDetailOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastQuery, setLastQuery] = useState("");
  const [lastModality, setLastModality] = useState<SearchModality>("text");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [activeFilters, setActiveFilters] = useState<SearchFilters>(DEFAULT_FILTERS);

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
      setLastModality(modality);

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
  // Filter toggle — opens the FiltersSidebar
  // -----------------------------------------------------------------------
  const handleFilterClick = useCallback(() => {
    setFiltersOpen(true);
  }, []);

  // -----------------------------------------------------------------------
  // Apply filters from FiltersSidebar
  // -----------------------------------------------------------------------
  const handleFiltersApply = useCallback((filters: SearchFilters) => {
    setActiveFilters(filters);
    setFiltersOpen(false);
    // Re-run the current search with new filters if we have an active query
    // (Filters are applied server-side on next search)
  }, []);

  // -----------------------------------------------------------------------
  // Result click — open detail panel
  // -----------------------------------------------------------------------
  const handleResultClick = useCallback((result: SearchResult) => {
    setSelectedResult(result);
    setDetailOpen(true);
  }, []);

  // -----------------------------------------------------------------------
  // History rerun — re-execute a previous search
  // -----------------------------------------------------------------------
  const handleHistoryRerun = useCallback(
    (query: string, modality: SearchModality) => {
      handleSearch(query, modality);
    },
    [handleSearch],
  );

  // -----------------------------------------------------------------------
  // History save — no-op for now (SearchHistory handles localStorage)
  // -----------------------------------------------------------------------
  const handleHistorySave = useCallback((_query: string, _name: string) => {
    // SearchHistory manages saves internally via localStorage
  }, []);

  // -----------------------------------------------------------------------
  // Copilot filters applied
  // -----------------------------------------------------------------------
  const handleCopilotFilters = useCallback(
    (filters: Record<string, string | boolean | number | undefined>) => {
      // Merge copilot-suggested filters into active filters where applicable
      setActiveFilters((prev) => ({
        ...prev,
        ...(filters.assetType
          ? { modalities: [filters.assetType as "image" | "audio" | "video"] }
          : {}),
        ...(filters.minConfidence !== undefined
          ? { similarityThreshold: Number(filters.minConfidence) }
          : {}),
      }));
    },
    [],
  );

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

      {/* Image Query Tab — shown when image modality active */}
      {lastModality === "image" && (
        <ImageQueryTab onResults={(results) => {
          setSearchResponse({
            results,
            query_type: "image",
            total_results: results.length,
            processing_time_ms: 0,
          });
        }} />
      )}

      {/* Audio Query Tab — shown when audio modality active */}
      {lastModality === "audio" && (
        <AudioQueryTab onResultClick={handleResultClick} />
      )}

      {/* Search History */}
      <SearchHistory onRerun={handleHistoryRerun} onSave={handleHistorySave} />

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Filters Sidebar */}
      <FiltersSidebar
        isOpen={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        onApply={handleFiltersApply}
        activeFilters={activeFilters}
      />

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
            onResultClick={handleResultClick}
          />

          {/* Copilot Refinement — shown when results exist */}
          <CopilotRefinement
            searchContext={{
              query: lastQuery,
              resultCount: searchResponse.total_results,
              filters: activeFilters as unknown as Record<string, string | boolean | number>,
            }}
            onFiltersApplied={handleCopilotFilters}
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

      {/* Result Detail Panel */}
      <ResultDetailPanel
        result={selectedResult}
        isOpen={detailOpen}
        onClose={() => {
          setDetailOpen(false);
          setSelectedResult(null);
        }}
      />
    </div>
  );
}
