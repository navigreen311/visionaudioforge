"use client";

import { useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GraphFilterState {
  nodeTypes: Set<string>;
  edgeTypes: Set<string>;
  searchTerm: string;
  timeRange: { start: string; end: string } | null;
}

interface GraphFiltersProps {
  availableNodeTypes: string[];
  availableEdgeTypes: string[];
  filters: GraphFilterState;
  onFiltersChange: (filters: GraphFilterState) => void;
  onSearch: (term: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const NODE_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  person: { label: "Person", color: "bg-blue-500" },
  object: { label: "Object", color: "bg-green-500" },
  location: { label: "Location", color: "bg-orange-500" },
  event: { label: "Event", color: "bg-red-500" },
  vehicle: { label: "Vehicle", color: "bg-purple-500" },
};

export default function GraphFilters({
  availableNodeTypes,
  availableEdgeTypes,
  filters,
  onFiltersChange,
  onSearch,
}: GraphFiltersProps) {
  const [searchInput, setSearchInput] = useState(filters.searchTerm);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchInput);
  };

  const toggleNodeType = (type: string) => {
    const next = new Set(filters.nodeTypes);
    if (next.has(type)) {
      next.delete(type);
    } else {
      next.add(type);
    }
    onFiltersChange({ ...filters, nodeTypes: next });
  };

  const toggleEdgeType = (type: string) => {
    const next = new Set(filters.edgeTypes);
    if (next.has(type)) {
      next.delete(type);
    } else {
      next.add(type);
    }
    onFiltersChange({ ...filters, edgeTypes: next });
  };

  const handleTimeChange = (field: "start" | "end", value: string) => {
    const current = filters.timeRange || { start: "", end: "" };
    const next = { ...current, [field]: value };
    onFiltersChange({
      ...filters,
      timeRange: next.start || next.end ? next : null,
    });
  };

  const clearFilters = () => {
    setSearchInput("");
    onFiltersChange({
      nodeTypes: new Set(availableNodeTypes),
      edgeTypes: new Set(availableEdgeTypes),
      searchTerm: "",
      timeRange: null,
    });
    onSearch("");
  };

  return (
    <div className="space-y-4 p-4">
      {/* Search */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-2">Search</h3>
        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search entities..."
            className="flex-1 rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm hover:bg-blue-500"
          >
            Go
          </button>
        </form>
      </div>

      {/* Node Type Filters */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-2">Node Types</h3>
        <div className="space-y-1">
          {availableNodeTypes.map((type) => {
            const meta = NODE_TYPE_LABELS[type] || {
              label: type,
              color: "bg-gray-500",
            };
            const isActive = filters.nodeTypes.has(type);
            return (
              <label
                key={type}
                className="flex items-center gap-2 text-sm cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={() => toggleNodeType(type)}
                  className="rounded border-gray-600"
                />
                <span className={`w-3 h-3 rounded-full ${meta.color}`} />
                <span className={isActive ? "text-gray-200" : "text-gray-500"}>
                  {meta.label}
                </span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Edge Type Filters */}
      {availableEdgeTypes.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-400 mb-2">
            Edge Types
          </h3>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {availableEdgeTypes.map((type) => {
              const isActive = filters.edgeTypes.has(type);
              return (
                <label
                  key={type}
                  className="flex items-center gap-2 text-sm cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={() => toggleEdgeType(type)}
                    className="rounded border-gray-600"
                  />
                  <span
                    className={isActive ? "text-gray-200" : "text-gray-500"}
                  >
                    {type}
                  </span>
                </label>
              );
            })}
          </div>
        </div>
      )}

      {/* Time Range */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-2">Time Range</h3>
        <div className="space-y-2">
          <input
            type="datetime-local"
            value={filters.timeRange?.start || ""}
            onChange={(e) => handleTimeChange("start", e.target.value)}
            className="w-full rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
          />
          <input
            type="datetime-local"
            value={filters.timeRange?.end || ""}
            onChange={(e) => handleTimeChange("end", e.target.value)}
            className="w-full rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Clear */}
      <button
        onClick={clearFilters}
        className="w-full py-1.5 rounded border border-gray-600 text-gray-400 text-sm hover:bg-gray-800 hover:text-gray-200"
      >
        Clear All Filters
      </button>
    </div>
  );
}
