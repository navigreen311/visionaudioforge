"use client";

import { API_BASE_URL } from "@/lib/api";

import { useEffect, useState, useCallback } from "react";

const API = API_BASE_URL;

interface RegistryModel {
  id: string;
  name: string;
  version: string;
  backbone: string | null;
  status: string;
  description: string | null;
  metrics: Record<string, number> | null;
  tags: string[] | null;
  created_at: string;
}

interface ModelSelectorProps {
  onSelect: (model: RegistryModel) => void;
}

export default function ModelSelector({ onSelect }: ModelSelectorProps) {
  const [models, setModels] = useState<RegistryModel[]>([]);
  const [selected, setSelected] = useState<RegistryModel | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchModels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/registry/models?workspace_id=00000000-0000-0000-0000-000000000000`);
      if (!res.ok) throw new Error(`Failed to fetch models: ${res.status}`);
      const data = await res.json();
      const items: RegistryModel[] = data.items ?? data;
      setModels(items);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load models";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const model = models.find((m) => m.id === e.target.value) ?? null;
    setSelected(model);
    if (model) onSelect(model);
  };

  const statusColor = (status: string): string => {
    switch (status) {
      case "production":
        return "bg-green-100 text-green-700";
      case "staging":
        return "bg-blue-100 text-blue-700";
      case "archived":
        return "bg-gray-100 text-gray-500";
      default:
        return "bg-yellow-100 text-yellow-700";
    }
  };

  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Model
      </label>

      {error && (
        <p className="text-xs text-red-500 mb-1">
          {error}{" "}
          <button onClick={fetchModels} className="underline">
            Retry
          </button>
        </p>
      )}

      <select
        value={selected?.id ?? ""}
        onChange={handleChange}
        disabled={loading}
        className="w-full max-w-md rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none disabled:opacity-50"
      >
        <option value="">
          {loading ? "Loading models..." : "Select a model..."}
        </option>
        {models.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name} v{m.version}
            {m.backbone ? ` (${m.backbone})` : ""}
            {" "}- {m.status}
          </option>
        ))}
      </select>

      {/* Metadata card */}
      {selected && (
        <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 p-4 max-w-md">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-semibold text-gray-800">
              {selected.name}
            </h3>
            <span
              className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(selected.status)}`}
            >
              {selected.status}
            </span>
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-600">
            <dt className="font-medium">Version</dt>
            <dd>{selected.version}</dd>

            <dt className="font-medium">Backbone</dt>
            <dd>{selected.backbone ?? "N/A"}</dd>

            <dt className="font-medium">ID</dt>
            <dd className="truncate" title={selected.id}>
              {selected.id}
            </dd>

            {selected.description && (
              <>
                <dt className="font-medium">Description</dt>
                <dd className="col-span-1">{selected.description}</dd>
              </>
            )}
          </dl>

          {selected.tags && selected.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {selected.tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-block rounded bg-brand-100 px-2 py-0.5 text-xs text-brand-700"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {selected.metrics && Object.keys(selected.metrics).length > 0 && (
            <div className="mt-2 border-t border-gray-200 pt-2">
              <p className="text-xs font-medium text-gray-500 mb-1">Metrics</p>
              <div className="flex flex-wrap gap-3">
                {Object.entries(selected.metrics).map(([key, val]) => (
                  <div key={key} className="text-xs">
                    <span className="text-gray-500">{key}:</span>{" "}
                    <span className="font-medium text-gray-800">
                      {typeof val === "number" ? val.toFixed(4) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
