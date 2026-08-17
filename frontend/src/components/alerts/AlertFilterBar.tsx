"use client";

import React, { useState } from "react";
import type { AlertSeverity, AlertStatus } from "@/lib/api";
import Button from "@/components/ui/Button";

interface AlertFilterBarProps {
  severityFilter: string;
  statusFilter: string;
  startDate: string;
  endDate: string;
  searchQuery: string;
  selectedCount: number;
  totalCount: number;
  allSelected: boolean;
  onSeverityChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onStartDateChange: (value: string) => void;
  onEndDateChange: (value: string) => void;
  onSearchChange: (value: string) => void;
  onSelectAll: (checked: boolean) => void;
  onBulkAcknowledge: () => void;
  onBulkDismiss: () => void;
  onClearFilters: () => void;
}

type SeverityPill = { label: string; value: string };
type StatusPill = { label: string; value: string };

const SEVERITY_PILLS: SeverityPill[] = [
  { label: "All", value: "" },
  { label: "Critical", value: "critical" },
  { label: "Warning", value: "high" },
  { label: "Info", value: "medium" },
];

const STATUS_PILLS: StatusPill[] = [
  { label: "All", value: "" },
  { label: "Open", value: "new" },
  { label: "Acknowledged", value: "acknowledged" },
  { label: "Dismissed", value: "dismissed" },
];

function Pill({
  label,
  active,
  onClick,
  colorClass,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  colorClass?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
        active
          ? `${colorClass ?? "bg-gray-800 text-white"}`
          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
      }`}
    >
      {label}
    </button>
  );
}

const SEVERITY_COLORS: Record<string, string> = {
  "": "bg-gray-800 text-white",
  critical: "bg-red-600 text-white",
  high: "bg-amber-500 text-white",
  medium: "bg-blue-500 text-white",
};

const STATUS_COLORS: Record<string, string> = {
  "": "bg-gray-800 text-white",
  new: "bg-red-500 text-white",
  acknowledged: "bg-yellow-500 text-white",
  dismissed: "bg-gray-500 text-white",
};

export default function AlertFilterBar({
  severityFilter,
  statusFilter,
  startDate,
  endDate,
  searchQuery,
  selectedCount,
  totalCount,
  allSelected,
  onSeverityChange,
  onStatusChange,
  onStartDateChange,
  onEndDateChange,
  onSearchChange,
  onSelectAll,
  onBulkAcknowledge,
  onBulkDismiss,
  onClearFilters,
}: AlertFilterBarProps) {
  const showBulkActions = selectedCount > 0;

  return (
    <div className="space-y-3 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      {/* Row 1: Severity + Status pills */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-gray-500 mr-1">Severity:</span>
          {SEVERITY_PILLS.map((pill) => (
            <Pill
              key={pill.value}
              label={pill.label}
              active={severityFilter === pill.value}
              onClick={() => onSeverityChange(pill.value)}
              colorClass={SEVERITY_COLORS[pill.value]}
            />
          ))}
        </div>
        <div className="h-5 w-px bg-gray-200" />
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-gray-500 mr-1">Status:</span>
          {STATUS_PILLS.map((pill) => (
            <Pill
              key={pill.value}
              label={pill.label}
              active={statusFilter === pill.value}
              onClick={() => onStatusChange(pill.value)}
              colorClass={STATUS_COLORS[pill.value]}
            />
          ))}
        </div>
      </div>

      {/* Row 2: Date range + search + select all */}
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">From</label>
          <input
            type="date"
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            value={startDate}
            onChange={(e) => onStartDateChange(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">To</label>
          <input
            type="date"
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            value={endDate}
            onChange={(e) => onEndDateChange(e.target.value)}
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">Search</label>
          <input
            type="text"
            placeholder="Search alerts..."
            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 pb-0.5">
          <label className="flex items-center gap-1.5 cursor-pointer text-sm text-gray-600">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              checked={allSelected}
              onChange={(e) => onSelectAll(e.target.checked)}
            />
            Select All
          </label>
        </div>
        <Button variant="ghost" size="sm" onClick={onClearFilters}>
          Clear
        </Button>
      </div>

      {/* Bulk actions toolbar */}
      {showBulkActions && (
        <div className="flex items-center gap-3 rounded-md bg-blue-50 border border-blue-200 px-3 py-2">
          <span className="text-sm font-medium text-blue-800">
            {selectedCount} alert{selectedCount !== 1 ? "s" : ""} selected
          </span>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={onBulkAcknowledge}>
              Acknowledge
            </Button>
            <Button variant="ghost" size="sm" onClick={onBulkDismiss}>
              Dismiss
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
