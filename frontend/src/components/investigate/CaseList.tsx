"use client";

import React, { useState } from "react";
import Badge from "@/components/ui/Badge";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CaseData {
  id: string;
  type: string;
  timestamp: string | null;
  payload: {
    name: string;
    description: string;
    status: string;
    priority?: string;
    assignee?: string;
    tags?: string[];
  };
  workspace_id: string;
  evidenceCount?: number;
}

interface CaseListProps {
  cases: CaseData[];
  selectedId: string | null;
  onSelect: (caseItem: CaseData) => void;
  /** When provided, renders a "New Case" action in the header. */
  onNewCase?: () => void;
  /** Shows a loading placeholder in place of the list. */
  loading?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const PRIORITY_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-amber-500",
  medium: "bg-blue-500",
  low: "bg-gray-400",
};

const STATUS_VARIANT: Record<string, string> = {
  open: "success",
  active: "info",
  under_review: "warning",
  closed: "neutral",
};

function statusLabel(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

function relativeTime(iso: string | null): string {
  if (!iso) return "N/A";
  const diff = Date.now() - new Date(iso).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

function initials(name: string | undefined): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CaseList({
  cases,
  selectedId,
  onSelect,
  onNewCase,
  loading = false,
}: CaseListProps) {
  const [search, setSearch] = useState("");

  const filtered = cases.filter((c) =>
    c.payload.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900">Cases</h2>
          {onNewCase && (
            <button
              type="button"
              onClick={onNewCase}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 transition-colors"
            >
              New Case
            </button>
          )}
        </div>
        <input
          type="text"
          placeholder="Search cases..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
        />
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 text-center px-4">
            <p className="text-sm text-gray-500">Loading cases...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center px-4">
            <p className="text-sm text-gray-500">No cases found</p>
            <p className="text-xs text-gray-400 mt-1">Create a new case to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filtered.map((caseItem) => {
              const isSelected = selectedId === caseItem.id;
              const priorityKey = caseItem.payload.priority || "medium";
              const statusKey = caseItem.payload.status || "open";

              return (
                <div
                  key={caseItem.id}
                  onClick={() => onSelect(caseItem)}
                  className={`p-4 cursor-pointer transition-colors hover:bg-gray-50 ${
                    isSelected
                      ? "bg-blue-50 border-l-4 border-blue-500"
                      : "border-l-4 border-transparent"
                  }`}
                >
                  {/* Row 1: priority dot + title + status badge */}
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                        PRIORITY_DOT[priorityKey] || PRIORITY_DOT.medium
                      }`}
                      title={`Priority: ${priorityKey}`}
                    />
                    <h3 className="text-sm font-semibold text-gray-900 truncate flex-1">
                      {truncate(caseItem.payload.name, 35)}
                    </h3>
                    <Badge variant={STATUS_VARIANT[statusKey] || "neutral"}>
                      {statusLabel(statusKey)}
                    </Badge>
                  </div>

                  {/* Row 2: event count chip + assignee avatar + relative time */}
                  <div className="flex items-center gap-3 mt-2">
                    {caseItem.evidenceCount !== undefined && caseItem.evidenceCount > 0 && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 text-gray-600 px-2 py-0.5 text-xs font-medium">
                        <svg
                          className="w-3 h-3"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                          />
                        </svg>
                        {caseItem.evidenceCount}
                      </span>
                    )}

                    {caseItem.payload.assignee && (
                      <div
                        className="w-6 h-6 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-[10px] font-semibold flex-shrink-0"
                        title={caseItem.payload.assignee}
                      >
                        {initials(caseItem.payload.assignee)}
                      </div>
                    )}

                    <span className="ml-auto text-xs text-gray-400">
                      {relativeTime(caseItem.timestamp)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
