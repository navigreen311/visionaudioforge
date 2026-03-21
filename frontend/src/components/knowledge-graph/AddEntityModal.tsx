"use client";

import { useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type NodeType = "person" | "object" | "location" | "event" | "vehicle";

interface PropertyEntry {
  key: string;
  value: string;
}

interface AddEntityModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const NODE_TYPES: { value: NodeType; label: string; color: string }[] = [
  { value: "person", label: "Person", color: "bg-blue-600 hover:bg-blue-500" },
  { value: "object", label: "Object", color: "bg-green-600 hover:bg-green-500" },
  { value: "location", label: "Location", color: "bg-orange-600 hover:bg-orange-500" },
  { value: "event", label: "Event", color: "bg-red-600 hover:bg-red-500" },
  { value: "vehicle", label: "Vehicle", color: "bg-purple-600 hover:bg-purple-500" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AddEntityModal({
  isOpen,
  onClose,
  onCreated,
}: AddEntityModalProps) {
  const [nodeType, setNodeType] = useState<NodeType>("person");
  const [label, setLabel] = useState("");
  const [properties, setProperties] = useState<PropertyEntry[]>([]);
  const [source, setSource] = useState("");
  const [linkedAssets, setLinkedAssets] = useState<string[]>([]);
  const [assetInput, setAssetInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const resetForm = () => {
    setNodeType("person");
    setLabel("");
    setProperties([]);
    setSource("");
    setLinkedAssets([]);
    setAssetInput("");
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

  const addLinkedAsset = () => {
    const trimmed = assetInput.trim();
    if (trimmed && !linkedAssets.includes(trimmed)) {
      setLinkedAssets((prev) => [...prev, trimmed]);
      setAssetInput("");
    }
  };

  const removeLinkedAsset = (asset: string) => {
    setLinkedAssets((prev) => prev.filter((a) => a !== asset));
  };

  const handleSubmit = async () => {
    if (!label.trim()) {
      setError("Label is required");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    // Build properties object from key-value pairs
    const propsObj: Record<string, string> = {};
    for (const p of properties) {
      if (p.key.trim()) {
        propsObj[p.key.trim()] = p.value;
      }
    }

    // Add source and linked assets as properties
    if (source.trim()) {
      propsObj["source"] = source.trim();
    }
    if (linkedAssets.length > 0) {
      propsObj["linked_assets"] = linkedAssets.join(",");
    }

    try {
      const res = await fetch("/api/knowledge-graph/nodes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          label: label.trim(),
          node_type: nodeType,
          properties: propsObj,
        }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || "Failed to create entity");
      }

      resetForm();
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create entity");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-gray-900 border border-gray-700 rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-100">
              Add Entity
            </h2>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-200 text-lg"
            >
              x
            </button>
          </div>

          {/* Node Type */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Node Type
            </label>
            <div className="flex flex-wrap gap-2">
              {NODE_TYPES.map((nt) => (
                <button
                  key={nt.value}
                  type="button"
                  onClick={() => setNodeType(nt.value)}
                  className={`px-3 py-1.5 rounded text-sm text-white transition-colors ${
                    nodeType === nt.value
                      ? nt.color + " ring-2 ring-white/30"
                      : "bg-gray-700 hover:bg-gray-600"
                  }`}
                >
                  {nt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Label */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Label <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Entity name..."
              className="w-full rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

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

          {/* Source */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Source
            </label>
            <input
              type="text"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="e.g. CCTV Cam 3, Witness statement..."
              className="w-full rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Linked Assets */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Linked Assets
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={assetInput}
                onChange={(e) => setAssetInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addLinkedAsset();
                  }
                }}
                placeholder="Asset ID or name..."
                className="flex-1 rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
              <button
                type="button"
                onClick={addLinkedAsset}
                className="px-3 py-1.5 rounded bg-gray-700 text-gray-300 text-sm hover:bg-gray-600"
              >
                Add
              </button>
            </div>
            {linkedAssets.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {linkedAssets.map((asset) => (
                  <span
                    key={asset}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-gray-700 text-xs text-gray-300"
                  >
                    {asset}
                    <button
                      type="button"
                      onClick={() => removeLinkedAsset(asset)}
                      className="text-gray-400 hover:text-red-400"
                    >
                      x
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

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
              disabled={isSubmitting || !label.trim()}
              className="px-4 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? "Creating..." : "Create Entity"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
