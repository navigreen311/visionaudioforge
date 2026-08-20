"use client";

import React from "react";

export interface SearchResultItem {
  id: string;
  title: string;
  subtitle: string;
  icon: string;
  url: string;
}

export type SearchResults = Record<string, SearchResultItem[]>;

const CATEGORY_COLORS: Record<string, string> = {
  assets: "#185FA5",
  pipelines: "#3C3489",
  alerts: "#A32D2D",
  cases: "#0F6E56",
  memory: "#854F0B",
};

interface SearchResultsDropdownProps {
  results: SearchResults;
  query: string;
  /**
   * Whether a request is still in flight.
   *
   * Without this the empty branch below rendered "No results for 'x'" the
   * moment the operator stopped typing - an answer, and usually the wrong one,
   * given before the search had returned. `GlobalSearch` tracked the state and
   * then discarded it with `void loading;`.
   */
  loading?: boolean;
  highlightIndex: number;
  onSelect: (url: string) => void;
  onSeeAll: () => void;
}

export default function SearchResultsDropdown({
  results,
  query,
  loading = false,
  highlightIndex,
  onSelect,
  onSeeAll,
}: SearchResultsDropdownProps) {
  const allItems = React.useMemo(() => {
    const items: { category: string; item: SearchResultItem }[] = [];
    for (const [cat, list] of Object.entries(results)) {
      for (const item of list) {
        items.push({ category: cat, item });
      }
    }
    return items;
  }, [results]);

  const hasResults = allItems.length > 0;

  if (!hasResults) {
    return (
      <div className="absolute top-full right-0 mt-1 w-[400px] max-h-[400px] overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg z-50 p-4">
        <p className="text-sm text-gray-500" role="status" aria-live="polite">
          {loading ? (
            <>Searching for &apos;{query}&apos;&hellip;</>
          ) : (
            <>No results for &apos;{query}&apos;</>
          )}
        </p>
      </div>
    );
  }

  let flatIndex = 0;

  return (
    <div className="absolute top-full right-0 mt-1 w-[400px] max-h-[400px] overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg z-50">
      {Object.entries(results).map(([category, items]) => (
        <div key={category}>
          <div
            className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider"
            style={{ color: CATEGORY_COLORS[category] || "#6B7280" }}
          >
            {category}
          </div>
          {items.map((item) => {
            const currentIndex = flatIndex++;
            return (
              <button
                key={item.id}
                onClick={() => onSelect(item.url)}
                className={`w-full text-left px-3 py-2 flex flex-col hover:bg-gray-50 ${
                  currentIndex === highlightIndex ? "bg-gray-100" : ""
                }`}
              >
                <span className="text-sm font-medium text-gray-900 truncate">
                  {item.title}
                </span>
                <span className="text-xs text-gray-500 truncate">
                  {item.subtitle}
                </span>
              </button>
            );
          })}
        </div>
      ))}

      <button
        onClick={onSeeAll}
        className="w-full border-t border-gray-200 px-3 py-2 text-sm text-brand-600 hover:bg-gray-50 font-medium text-center"
      >
        See all results
      </button>
    </div>
  );
}
