"use client";

import { useEffect, useState, useCallback } from "react";
import Badge from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FederationSummary {
  id: string;
  name: string;
  model_id: string;
  status: "waiting" | "ready" | "training" | "paused" | "completed" | "stopped";
  current_round: number;
  total_rounds: number;
  created_at: number;
}

interface FederationSelectorProps {
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_VARIANT: Record<string, string> = {
  waiting: "neutral",
  ready: "info",
  training: "success",
  paused: "warning",
  completed: "info",
  stopped: "error",
};

function formatDate(epoch: number): string {
  return new Date(epoch * 1000).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function FederationSelector({ selectedId, onSelect }: FederationSelectorProps) {
  const [federations, setFederations] = useState<FederationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  const fetchFederations = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/federated/federations");
      if (!res.ok) throw new Error("Failed to fetch federations");
      const data: FederationSummary[] = await res.json();
      setFederations(data);
    } catch {
      // silently fail -- list stays empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFederations();
  }, [fetchFederations]);

  const selected = federations.find((f) => f.id === selectedId);

  return (
    <div className="relative">
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center justify-between w-full md:w-96 border rounded-lg px-4 py-2.5 text-sm bg-white hover:bg-gray-50 transition-colors"
      >
        {loading ? (
          <span className="flex items-center gap-2 text-gray-400">
            <LoadingSpinner size="sm" />
            Loading federations...
          </span>
        ) : selected ? (
          <span className="flex items-center gap-2 truncate">
            <span className="font-medium truncate">{selected.name}</span>
            <Badge variant={STATUS_VARIANT[selected.status] ?? "neutral"}>
              {selected.status}
            </Badge>
          </span>
        ) : (
          <span className="text-gray-400">Select a federation...</span>
        )}
        <svg
          className={`ml-2 h-4 w-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute z-30 mt-1 w-full md:w-96 max-h-80 overflow-y-auto rounded-lg border bg-white shadow-lg">
          {federations.length === 0 && !loading ? (
            <p className="px-4 py-3 text-sm text-gray-400">No federations yet</p>
          ) : (
            federations.map((fed) => (
              <button
                key={fed.id}
                type="button"
                onClick={() => {
                  onSelect(fed.id);
                  setOpen(false);
                }}
                className={`w-full text-left px-4 py-3 hover:bg-gray-50 border-b last:border-b-0 transition-colors ${
                  fed.id === selectedId ? "bg-brand-50" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm truncate">{fed.name}</span>
                  <Badge variant={STATUS_VARIANT[fed.status] ?? "neutral"}>
                    {fed.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  <span>Model: {fed.model_id}</span>
                  <span>
                    Round {fed.current_round}/{fed.total_rounds}
                  </span>
                  <span>{formatDate(fed.created_at)}</span>
                </div>
              </button>
            ))
          )}

          {/* + New Federation */}
          <button
            type="button"
            onClick={() => {
              onSelect(null);
              setOpen(false);
            }}
            className="w-full text-left px-4 py-3 text-sm font-medium text-brand-600 hover:bg-brand-50 transition-colors border-t"
          >
            + New Federation
          </button>
        </div>
      )}
    </div>
  );
}
