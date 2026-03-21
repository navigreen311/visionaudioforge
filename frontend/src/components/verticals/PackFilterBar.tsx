"use client";

import React from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ViewMode = "all" | "installed";

interface PackFilterBarProps {
  onSearchChange: (value: string) => void;
  onCategoryChange: (category: string) => void;
  onViewChange: (view: ViewMode) => void;
  totalCount: number;
  filteredCount: number;
  searchQuery?: string;
  activeCategory?: string;
  activeView?: ViewMode;
}

// ---------------------------------------------------------------------------
// Category pills
// ---------------------------------------------------------------------------

const CATEGORIES = [
  "All",
  "Public Safety",
  "Healthcare",
  "Customer Service",
  "Retail",
  "Manufacturing",
  "Media",
  "Education",
] as const;

type Category = (typeof CATEGORIES)[number];

function CategoryPill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
        active
          ? "bg-brand-600 text-white"
          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
      }`}
    >
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PackFilterBar({
  onSearchChange,
  onCategoryChange,
  onViewChange,
  totalCount,
  filteredCount,
  searchQuery = "",
  activeCategory = "All",
  activeView = "all",
}: PackFilterBarProps) {
  return (
    <div className="space-y-3 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      {/* Row 1: View toggle + search + count */}
      <div className="flex flex-wrap items-center gap-3">
        {/* View tabs */}
        <div className="flex rounded-lg border border-gray-200 overflow-hidden">
          <button
            type="button"
            onClick={() => onViewChange("all")}
            className={`px-4 py-1.5 text-sm font-medium transition-colors ${
              activeView === "all"
                ? "bg-brand-600 text-white"
                : "bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            All Packs
          </button>
          <button
            type="button"
            onClick={() => onViewChange("installed")}
            className={`px-4 py-1.5 text-sm font-medium transition-colors border-l border-gray-200 ${
              activeView === "installed"
                ? "bg-brand-600 text-white"
                : "bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            Installed
          </button>
        </div>

        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400"
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
            <input
              type="text"
              placeholder="Search packs..."
              className="w-full rounded-md border border-gray-300 pl-9 pr-3 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
            />
          </div>
        </div>

        {/* Pack count */}
        <span className="text-sm text-gray-500 whitespace-nowrap">
          {filteredCount === totalCount
            ? `${totalCount} pack${totalCount !== 1 ? "s" : ""}`
            : `${filteredCount} of ${totalCount} packs`}
        </span>
      </div>

      {/* Row 2: Category pills */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs font-medium text-gray-500 mr-1">Category:</span>
        {CATEGORIES.map((cat) => (
          <CategoryPill
            key={cat}
            label={cat}
            active={activeCategory === cat}
            onClick={() => onCategoryChange(cat)}
          />
        ))}
      </div>
    </div>
  );
}
