"use client";

import { useState, useCallback, useRef } from "react";
import ResultsGrid from "./ResultsGrid";
import type { SearchResult } from "./ResultCard";
import api from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SearchMode = "similar" | "description";

interface ImageSearchResponse {
  results: SearchResult[];
  query_type: string;
  total_results: number;
  processing_time_ms: number;
}

interface ImageQueryTabProps {
  onResults?: (results: SearchResult[]) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      // Strip the data:*;base64, prefix
      const base64 = dataUrl.split(",")[1];
      resolve(base64);
    };
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });
}

// ---------------------------------------------------------------------------
// Skeleton loader
// ---------------------------------------------------------------------------

function ResultsSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-5 w-48 bg-gray-200 rounded animate-pulse" />
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-gray-200 overflow-hidden">
            <div className="aspect-square bg-gray-200 animate-pulse" />
            <div className="p-3 space-y-2">
              <div className="h-4 w-3/4 bg-gray-200 rounded animate-pulse" />
              <div className="h-3 w-1/2 bg-gray-100 rounded animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ImageQueryTab({ onResults }: ImageQueryTabProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [mode, setMode] = useState<SearchMode>("similar");
  const [description, setDescription] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ImageSearchResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ---- File selection ----

  const handleFileSelected = useCallback((selected: File) => {
    setFile(selected);
    setError(null);
    setResponse(null);

    const objectUrl = URL.createObjectURL(selected);
    setPreview(objectUrl);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped && dropped.type.startsWith("image/")) {
        handleFileSelected(dropped);
      }
    },
    [handleFileSelected],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) handleFileSelected(selected);
    },
    [handleFileSelected],
  );

  const clearFile = useCallback(() => {
    setFile(null);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    setResponse(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, [preview]);

  // ---- Search ----

  const handleSearch = async () => {
    if (!file) return;

    setIsLoading(true);
    setError(null);

    try {
      const queryImageB64 = await fileToBase64(file);

      const payload: Record<string, unknown> = {
        query_image_b64: queryImageB64,
        modality_filter: "image",
        k: 20,
      };

      if (mode === "description" && description.trim()) {
        payload.query = description.trim();
      }

      const { data } = await api.post<ImageSearchResponse>(
        "/api/search/query",
        payload,
      );

      setResponse(data);
      onResults?.(data.results);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Search failed. Please try again.";
      setError(message);
      setResponse(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = () => {
    handleSearch();
  };

  const handleResultClick = useCallback((_result: SearchResult) => {
    // Placeholder for future detail modal integration
  }, []);

  // ---- Render ----

  const canSearch =
    file !== null && (mode === "similar" || description.trim().length > 0);

  return (
    <div className="space-y-6">
      {/* Dropzone */}
      {!preview ? (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors cursor-pointer ${
            isDragOver
              ? "border-brand-500 bg-brand-50"
              : "border-gray-300 bg-gray-50 hover:border-gray-400"
          }`}
        >
          {/* Upload icon */}
          <svg
            className="mb-3 h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <p className="text-sm text-gray-600 text-center">
            <span className="font-medium text-brand-600">
              Upload an image
            </span>{" "}
            to find visually similar assets
          </p>
          <p className="mt-1 text-xs text-gray-400">
            Drag and drop or click to browse
          </p>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleInputChange}
            className="hidden"
          />
        </div>
      ) : (
        /* Preview */
        <div className="relative rounded-xl border border-gray-200 overflow-hidden bg-gray-50">
          <div className="flex items-center justify-center p-4 max-h-64 sm:max-h-80">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={preview}
              alt="Uploaded query image"
              className="max-h-56 sm:max-h-72 rounded-lg object-contain"
            />
          </div>

          {/* File info bar */}
          <div className="flex items-center justify-between px-4 py-2 bg-white border-t border-gray-200">
            <span className="text-sm text-gray-600 truncate max-w-[60%]">
              {file?.name}
            </span>
            <button
              onClick={clearFile}
              className="text-sm text-red-500 hover:text-red-700 font-medium transition-colors"
            >
              Remove
            </button>
          </div>
        </div>
      )}

      {/* Mode toggle */}
      {file && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <button
              onClick={() => setMode("similar")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                mode === "similar"
                  ? "bg-brand-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              Find similar images
            </button>
            <button
              onClick={() => setMode("description")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                mode === "description"
                  ? "bg-brand-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              Find images matching this description
            </button>
          </div>

          {/* Description text field */}
          {mode === "description" && (
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && canSearch && handleSearch()}
              placeholder="Describe what you want to find..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            />
          )}

          {/* Search button */}
          <button
            onClick={handleSearch}
            disabled={!canSearch || isLoading}
            className="w-full sm:w-auto px-6 py-3 bg-brand-600 text-white rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? "Searching..." : "Search by image"}
          </button>
        </div>
      )}

      {/* Error with retry */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 flex items-center justify-between gap-4">
          <p className="text-sm text-red-700">{error}</p>
          <button
            onClick={handleRetry}
            className="shrink-0 text-sm font-medium text-red-600 hover:text-red-800 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && <ResultsSkeleton />}

      {/* Results */}
      {!isLoading && response && (
        <ResultsGrid
          results={response.results}
          queryType={response.query_type}
          totalResults={response.total_results}
          processingTimeMs={response.processing_time_ms}
          onResultClick={handleResultClick}
        />
      )}

      {/* Empty results */}
      {!isLoading && response && response.results.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center space-y-2">
            <svg
              className="w-12 h-12 text-gray-300 mx-auto"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm text-gray-500">
              No similar images found. Try a different image or description.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
