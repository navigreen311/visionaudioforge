"use client";

import { useState, useMemo } from "react";
import type { GraphNode } from "./GraphCanvas";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PropertyEntry {
  key: string;
  value: string;
}

interface AddRelationshipModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
  nodes: GraphNode[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const RELATIONSHIP_TYPES = [
  "carried",
  "conducted",
  "drove",
  "entered",
  "exited",
  "met_with",
  "observed_at",
  "owns",
  "passenger_of",
  "present_at",
  "related_to",
  "spoke_with",
  "traveled_to",
  "witnessed",
] as const;

// ---------------------------------------------------------------------------
// Searchable Select
// ---------------------------------------------------------------------------

interface SearchableSelectProps {
  label: string;
  nodes: GraphNode[];
  selectedId: string;
  onSelect: (id: string) => void;
}

function SearchableSelect({
  label,
  nodes,
  selectedId,
  onSelect,
}: SearchableSelectProps) {
  const [search, setSearch] = useState("");
  const [isOpen, setIsOpen] = useState(false);

  const filtered = useMemo(() => {
    if (!search.trim()) return nodes;
    const q = search.toLowerCase();
    return nodes.filter(
      (n) =>
        n.label.toLowerCase().includes(q) ||
        n.type.toLowerCase().includes(q)
    );
  }, [nodes, search]);

  const selectedNode = nodes.find((n) => n.id === selectedId);

  const typeColor: Record<string, string> = {
    person: "text-blue-400",
    object: "text-green-400",
    location: "text-orange-400",
    event: "text-red-400",
    vehicle: "text-purple-400",
  };

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-gray-400 mb-1">
        {label}
      </label>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full text-left rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
      >
        {selectedNode ? (
          <span>
            <span className={typeColor[selectedNode.type] ?? "text-gray-400"}>
              [{selectedNode.type}]
            </span>{" "}
            {selectedNode.label}
          </span>
        ) : (
          <span className="text-gray-500">Select entity...</span>
        )}
      </button>

      {isOpen && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-600 rounded shadow-lg max-h-48 overflow-hidden flex flex-col">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search..."
            className="px-3 py-1.5 bg-gray-900 border-b border-gray-600 text-sm text-gray-200 placeholder-gray-500 focus:outline-none"
            autoFocus
          />
          <div className="overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="px-3 py-2 text-sm text-gray-500">
                No entities found
              </div>
            ) : (
              filtered.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => {
                    onSelect(n.id);
                    setIsOpen(false);
                    setSearch("");
                  }}
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-700 flex items-center gap-2 ${
                    n.id === selectedId ? "bg-gray-700" : ""
                  }`}
                >
                  <span
                    className={`text-xs font-medium ${typeColor[n.type] ?? "text-gray-400"}`}
                  >
                    [{n.type}]
                  </span>
                  <span className="text-gray-200">{n.label}</span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AddRelationshipModal({
  isOpen,
  onClose,
  onCreated,
  nodes,
}: AddRelationshipModalProps) {
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [relationType, setRelationType] = useState<
    (typeof RELATIONSHIP_TYPES)[number]
  >(RELATIONSHIP_TYPES[0]);
  const [customRelation, setCustomRelation] = useState("");
  const [useCustom, setUseCustom] = useState(false);
  const [properties, setProperties] = useState<PropertyEntry[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const resetForm = () => {
    setSourceId("");
    setTargetId("");
    setRelationType(RELATIONSHIP_TYPES[0]);
    setCustomRelation("");
    setUseCustom(false);
    setProperties([]);
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const addProperty = () => {
    setProperties((prev) => [...prev, { key: "", value: "" }]);
  };

  const updateProperty = (
    index: number,
    field: "key" | "value",
    val: string
  ) => {
    setProperties((prev) =>
      prev.map((p, i) => (i === index ? { ...p, [field]: val } : p))
    );
  };

  const removeProperty = (index: number) => {
    setProperties((prev) => prev.filter((_, i) => i !== index));
  };

  const effectiveRelation = useCustom
    ? customRelation.trim()
    : relationType;

  const canSubmit =
    sourceId &&
    targetId &&
    sourceId !== targetId &&
    effectiveRelation.length > 0;

  const handleSubmit = async () => {
    if (!canSubmit) {
      setError("Please select two different entities and a relationship type");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    const propsObj: Record<string, string> = {};
    for (const p of properties) {
      if (p.key.trim()) {
        propsObj[p.key.trim()] = p.value;
      }
    }

    try {
      const res = await fetch("/api/knowledge-graph/edges", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_id: sourceId,
          target_id: targetId,
          relation: effectiveRelation,
          properties: propsObj,
        }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || "Failed to create relationship");
      }

      resetForm();
      onCreated();
      onClose();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create relationship"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={handleClose} />

      {/* Modal */}
      <div className="relative bg-gray-900 border border-gray-700 rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-100">
              Add Relationship
            </h2>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-200 text-lg"
            >
              x
            </button>
          </div>

          {/* From Entity */}
          <SearchableSelect
            label="From Entity"
            nodes={nodes}
            selectedId={sourceId}
            onSelect={setSourceId}
          />

          {/* Relationship Type */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Relationship Type
            </label>
            <div className="flex gap-2">
              <select
                value={useCustom ? "__custom__" : relationType}
                onChange={(e) => {
                  if (e.target.value === "__custom__") {
                    setUseCustom(true);
                  } else {
                    setUseCustom(false);
                    setRelationType(
                      e.target.value as (typeof RELATIONSHIP_TYPES)[number]
                    );
                  }
                }}
                className="flex-1 rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              >
                {RELATIONSHIP_TYPES.map((rt) => (
                  <option key={rt} value={rt}>
                    {rt}
                  </option>
                ))}
                <option value="__custom__">Custom...</option>
              </select>
            </div>
            {useCustom && (
              <input
                type="text"
                value={customRelation}
                onChange={(e) => setCustomRelation(e.target.value)}
                placeholder="Custom relationship type..."
                className="w-full mt-2 rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
                autoFocus
              />
            )}
          </div>

          {/* To Entity */}
          <SearchableSelect
            label="To Entity"
            nodes={nodes}
            selectedId={targetId}
            onSelect={setTargetId}
          />

          {/* Properties */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Properties
            </label>
            <div className="space-y-2">
              {properties.map((prop, idx) => (
                <div key={idx} className="flex gap-2 items-center">
                  <input
                    type="text"
                    value={prop.key}
                    onChange={(e) => updateProperty(idx, "key", e.target.value)}
                    placeholder="Key"
                    className="flex-1 rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  />
                  <input
                    type="text"
                    value={prop.value}
                    onChange={(e) =>
                      updateProperty(idx, "value", e.target.value)
                    }
                    placeholder="Value"
                    className="flex-1 rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => removeProperty(idx)}
                    className="text-gray-400 hover:text-red-400 text-sm px-1"
                  >
                    x
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addProperty}
              className="mt-2 text-sm text-blue-400 hover:text-blue-300"
            >
              + Add property
            </button>
          </div>

          {/* Same-entity warning */}
          {sourceId && targetId && sourceId === targetId && (
            <div className="text-sm text-yellow-400 bg-yellow-900/20 border border-yellow-800 rounded px-3 py-2">
              Source and target must be different entities
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded px-3 py-2">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 rounded border border-gray-600 text-gray-400 text-sm hover:bg-gray-800"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting || !canSubmit}
              className="px-4 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? "Creating..." : "Create Relationship"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
