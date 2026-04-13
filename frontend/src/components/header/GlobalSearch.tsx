"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import SearchResultsDropdown, {
  type SearchResults,
} from "./SearchResultsDropdown";

export default function GlobalSearch() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResults>({});
  const [open, setOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const [loading, setLoading] = useState(false);

  // Flatten items for keyboard navigation
  const flatItems = useMemo(() => {
    const items: { url: string }[] = [];
    for (const list of Object.values(results)) {
      for (const item of list) {
        items.push({ url: item.url });
      }
    }
    return items;
  }, [results]);

  // Debounced fetch
  useEffect(() => {
    if (!query.trim()) {
      setResults({});
      setOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await api.get("/api/search/global", {
          params: { q: query },
        });
        setResults(res.data);
        setOpen(true);
        setHighlightIndex(-1);
      } catch {
        setResults({});
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // "/" shortcut to focus
  useEffect(() => {
    function handleSlash(e: KeyboardEvent) {
      const tag = document.activeElement?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if (e.key === "/") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    window.addEventListener("keydown", handleSlash);
    return () => window.removeEventListener("keydown", handleSlash);
  }, []);

  // Click outside closes
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const navigate = useCallback(
    (url: string) => {
      setOpen(false);
      setQuery("");
      router.push(url);
    },
    [router],
  );

  const handleSeeAll = useCallback(() => {
    navigate(`/search?q=${encodeURIComponent(query)}`);
  }, [navigate, query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIndex((prev) =>
        prev < flatItems.length - 1 ? prev + 1 : 0,
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIndex((prev) =>
        prev > 0 ? prev - 1 : flatItems.length - 1,
      );
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (highlightIndex >= 0 && highlightIndex < flatItems.length) {
        navigate(flatItems[highlightIndex].url);
      } else if (query.trim()) {
        handleSeeAll();
      }
    } else if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    }
  };

  return (
    <div ref={containerRef} className="hidden md:block relative">
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => {
          if (query.trim() && Object.keys(results).length > 0) setOpen(true);
        }}
        onKeyDown={handleKeyDown}
        placeholder="Search...  /"
        className="w-64 focus:w-80 transition-all duration-200 rounded-lg border border-gray-300 bg-gray-50 px-4 py-1.5 text-sm placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
      />
      <svg
        className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 pointer-events-none"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>

      {open && query.trim() && (
        <SearchResultsDropdown
          results={results}
          query={query}
          highlightIndex={highlightIndex}
          onSelect={navigate}
          onSeeAll={handleSeeAll}
        />
      )}
    </div>
  );
}
