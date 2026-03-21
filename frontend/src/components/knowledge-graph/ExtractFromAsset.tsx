"use client";

import { useState, useEffect, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Asset {
  id: string;
  name: string;
  type: string;
  thumbnail_url?: string;
}

type ExtractionMode = "persons" | "objects" | "locations" | "events";

interface ExtractedEntity {
  id: string;
  label: string;
  type: string;
  confidence: number;
  merge_suggestion?: string;
}

interface ExtractFromAssetProps {
  isOpen: boolean;
  onClose: () => void;
  onEntitiesAdded: (entities: ExtractedEntity[]) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const EXTRACTION_MODES: { key: ExtractionMode; label: string; color: string }[] = [
  { key: "persons", label: "Persons", color: "bg-blue-500" },
  { key: "objects", label: "Objects", color: "bg-green-500" },
  { key: "locations", label: "Locations", color: "bg-orange-500" },
  { key: "events", label: "Events", color: "bg-red-500" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ExtractFromAsset({
  isOpen,
  onClose,
  onEntitiesAdded,
}: ExtractFromAssetProps) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string>("");
  const [modes, setModes] = useState<Set<ExtractionMode>>(
    new Set(["persons", "objects", "locations", "events"]),
  );
  const [confidence, setConfidence] = useState(60);
  const [extracting, setExtracting] = useState(false);
  const [extracted, setExtracted] = useState<ExtractedEntity[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loadingAssets, setLoadingAssets] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch assets on open
  useEffect(() => {
    if (!isOpen) return;
    setLoadingAssets(true);
    setError(null);
    fetch("/api/assets")
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to fetch assets: ${r.status}`);
        return r.json();
      })
      .then((data: Asset[] | { items: Asset[] }) => {
        const list = Array.isArray(data) ? data : data.items ?? [];
        setAssets(list);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoadingAssets(false));
  }, [isOpen]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setExtracted([]);
      setSelected(new Set());
      setSelectedAssetId("");
      setError(null);
    }
  }, [isOpen]);

  const toggleMode = useCallback((mode: ExtractionMode) => {
    setModes((prev) => {
      const next = new Set(prev);
      if (next.has(mode)) {
        next.delete(mode);
      } else {
        next.add(mode);
      }
      return next;
    });
  }, []);

  const handleExtract = useCallback(async () => {
    if (!selectedAssetId || modes.size === 0) return;
    setExtracting(true);
    setError(null);
    try {
      const res = await fetch("/api/knowledge-graph/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset_id: selectedAssetId,
          modes: Array.from(modes),
          min_confidence: confidence / 100,
        }),
      });
      if (!res.ok) throw new Error(`Extraction failed: ${res.status}`);
      const data = (await res.json()) as { entities: ExtractedEntity[] };
      setExtracted(data.entities);
      // Pre-select all entities at or above threshold
      setSelected(
        new Set(
          data.entities
            .filter((e) => e.confidence >= confidence / 100)
            .map((e) => e.id),
        ),
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
    } finally {
      setExtracting(false);
    }
  }, [selectedAssetId, modes, confidence]);

  const toggleEntity = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    if (selected.size === extracted.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(extracted.map((e) => e.id)));
    }
  }, [selected.size, extracted]);

  const handleAddSelected = useCallback(() => {
    const entitiesToAdd = extracted.filter((e) => selected.has(e.id));
    onEntitiesAdded(entitiesToAdd);
    onClose();
  }, [extracted, selected, onEntitiesAdded, onClose]);

  const confidenceBadgeColor = (conf: number): string => {
    if (conf >= 0.8) return "bg-green-600";
    if (conf >= 0.5) return "bg-yellow-600";
    return "bg-red-600";
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-gray-100">
            Extract Entities from Asset
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 text-xl leading-none"
            title="Close"
          >
            x
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          {error && (
            <div className="bg-red-900/40 border border-red-700 rounded px-3 py-2 text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Asset selector */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Select Asset
            </label>
            {loadingAssets ? (
              <p className="text-sm text-gray-500">Loading assets...</p>
            ) : (
              <select
                value={selectedAssetId}
                onChange={(e) => setSelectedAssetId(e.target.value)}
                className="w-full rounded bg-gray-800 border border-gray-600 px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              >
                <option value="">-- Choose an asset --</option>
                {assets.map((asset) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.name} ({asset.type})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Extraction modes */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Extraction Modes
            </label>
            <div className="flex flex-wrap gap-3">
              {EXTRACTION_MODES.map(({ key, label, color }) => (
                <label
                  key={key}
                  className="flex items-center gap-2 text-sm cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={modes.has(key)}
                    onChange={() => toggleMode(key)}
                    className="rounded border-gray-600"
                  />
                  <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
                  <span className={modes.has(key) ? "text-gray-200" : "text-gray-500"}>
                    {label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Confidence slider */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Minimum Confidence: {confidence}%
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={confidence}
              onChange={(e) => setConfidence(Number(e.target.value))}
              className="w-full accent-blue-500"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Extract button */}
          <button
            onClick={handleExtract}
            disabled={!selectedAssetId || modes.size === 0 || extracting}
            className="w-full py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {extracting ? "Extracting..." : "Extract Entities"}
          </button>

          {/* Preview panel */}
          {extracted.length > 0 && (
            <div className="border border-gray-700 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-gray-300">
                  Extracted Entities ({extracted.length})
                </h3>
                <button
                  onClick={toggleAll}
                  className="text-xs text-blue-400 hover:text-blue-300"
                >
                  {selected.size === extracted.length ? "Deselect All" : "Select All"}
                </button>
              </div>

              <div className="space-y-2 max-h-52 overflow-y-auto">
                {extracted.map((entity) => (
                  <label
                    key={entity.id}
                    className="flex items-center gap-3 bg-gray-800 rounded px-3 py-2 cursor-pointer hover:bg-gray-750"
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(entity.id)}
                      onChange={() => toggleEntity(entity.id)}
                      className="rounded border-gray-600"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-200 truncate">
                          {entity.label}
                        </span>
                        <span className="text-xs text-gray-500 capitalize">
                          {entity.type}
                        </span>
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded text-white ${confidenceBadgeColor(entity.confidence)}`}
                        >
                          {Math.round(entity.confidence * 100)}%
                        </span>
                      </div>
                      {entity.merge_suggestion && (
                        <p className="text-xs text-yellow-400 mt-0.5">
                          Merge suggestion: {entity.merge_suggestion}
                        </p>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        {extracted.length > 0 && (
          <div className="px-6 py-4 border-t border-gray-700 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded border border-gray-600 text-gray-400 text-sm hover:bg-gray-800 hover:text-gray-200"
            >
              Cancel
            </button>
            <button
              onClick={handleAddSelected}
              disabled={selected.size === 0}
              className="px-4 py-2 rounded bg-green-600 text-white text-sm font-medium hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Add Selected to Graph ({selected.size})
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
