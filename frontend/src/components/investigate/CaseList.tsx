"use client";

import React, { useState } from "react";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";

export interface CaseData {
  id: string;
  type: string;
  timestamp: string | null;
  payload: {
    name: string;
    description: string;
    status: string;
  };
  workspace_id: string;
  evidenceCount?: number;
}

interface CaseListProps {
  cases: CaseData[];
  selectedCaseId: string | null;
  onSelectCase: (caseItem: CaseData) => void;
  onNewCase: () => void;
  loading: boolean;
}

export default function CaseList({
  cases,
  selectedCaseId,
  onSelectCase,
  onNewCase,
  loading,
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
          <Button size="sm" onClick={onNewCase}>
            + New Case
          </Button>
        </div>
        <input
          type="text"
          placeholder="Search cases..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
        />
      </div>

      {/* Case list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin h-6 w-6 border-2 border-brand-600 border-t-transparent rounded-full" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center px-4">
            <p className="text-sm text-gray-500">No cases found</p>
            <p className="text-xs text-gray-400 mt-1">Create a new case to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filtered.map((caseItem) => (
              <div
                key={caseItem.id}
                onClick={() => onSelectCase(caseItem)}
                className={`p-4 cursor-pointer transition-colors hover:bg-gray-50 ${
                  selectedCaseId === caseItem.id ? "bg-brand-50 border-l-2 border-brand-500" : ""
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-sm font-medium text-gray-900 truncate">
                    {caseItem.payload.name}
                  </h3>
                  <Badge
                    variant={caseItem.payload.status === "open" ? "success" : "neutral"}
                  >
                    {caseItem.payload.status}
                  </Badge>
                </div>
                <p className="text-xs text-gray-500 truncate">
                  {caseItem.payload.description}
                </p>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                  <span>
                    {caseItem.timestamp
                      ? new Date(caseItem.timestamp).toLocaleDateString()
                      : "N/A"}
                  </span>
                  {caseItem.evidenceCount !== undefined && (
                    <span>{caseItem.evidenceCount} evidence items</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
