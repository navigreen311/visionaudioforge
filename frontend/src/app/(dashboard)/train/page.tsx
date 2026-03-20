"use client";

import { useState, Fragment } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listModels,
  registerModel,
  updateModelStatus,
  compareModels,
  ModelRecord,
  ModelCreatePayload,
  CompareResult,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"; // default dev workspace

const STATUS_COLORS: Record<string, string> = {
  registered: "bg-blue-100 text-blue-800",
  staging: "bg-yellow-100 text-yellow-800",
  production: "bg-green-100 text-green-800",
  archived: "bg-gray-100 text-gray-600",
};

const BACKBONE_OPTIONS = [
  "ResNet50",
  "ResNet101",
  "VGG16",
  "EfficientNet-B0",
  "ViT-B/32",
  "CLIP-ViT-L/14",
  "CSPDarknet",
  "MobileNetV3",
  "Swin-T",
  "ConvNeXt-B",
];

type TabKey = "models" | "experiments" | "datasets";

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function TrainPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("models");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Train &amp; Registry</h1>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {(["models", "experiments", "datasets"] as TabKey[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm capitalize ${
                activeTab === tab
                  ? "border-brand-600 text-brand-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === "models" && <ModelsTab />}
      {activeTab === "experiments" && <StubTab label="Experiments" />}
      {activeTab === "datasets" && <StubTab label="Datasets" />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stub tab
// ---------------------------------------------------------------------------

function StubTab({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center min-h-[40vh]">
      <div className="text-center">
        <p className="text-gray-400 text-lg">{label} module coming soon.</p>
        <span className="mt-2 inline-block px-3 py-1 bg-yellow-50 text-yellow-700 text-sm rounded-full border border-yellow-200">
          Not Implemented
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Models Tab
// ---------------------------------------------------------------------------

function ModelsTab() {
  const queryClient = useQueryClient();

  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [selectedModel, setSelectedModel] = useState<ModelRecord | null>(null);
  const [compareSelection, setCompareSelection] = useState<string[]>([]);
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["models", statusFilter],
    queryFn: () => listModels(WORKSPACE_ID, statusFilter || undefined),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updateModelStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      setSelectedModel(null);
    },
  });

  const compareMutation = useMutation({
    mutationFn: ({ a, b }: { a: string; b: string }) => compareModels(a, b),
    onSuccess: (result) => setCompareResult(result),
  });

  function handleCompare() {
    if (compareSelection.length === 2) {
      compareMutation.mutate({ a: compareSelection[0], b: compareSelection[1] });
    }
  }

  function toggleCompareSelect(id: string) {
    setCompareSelection((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  }

  const models = data?.items ?? [];

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => setShowRegisterModal(true)}
          className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium"
        >
          Register Model
        </button>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="registered">Registered</option>
          <option value="staging">Staging</option>
          <option value="production">Production</option>
          <option value="archived">Archived</option>
        </select>

        {compareSelection.length === 2 && (
          <button
            onClick={handleCompare}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium"
          >
            Compare Selected
          </button>
        )}
      </div>

      {/* Table */}
      {isLoading && <p className="text-gray-400">Loading models...</p>}
      {error && <p className="text-red-500">Failed to load models.</p>}

      {!isLoading && (
        <div className="overflow-x-auto bg-white rounded-xl shadow border border-gray-100">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Cmp</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Name</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Version</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Backbone</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Registered</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {models.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    No models found.
                  </td>
                </tr>
              )}
              {models.map((m) => (
                <tr
                  key={m.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => setSelectedModel(m)}
                >
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={compareSelection.includes(m.id)}
                      onChange={() => toggleCompareSelect(m.id)}
                    />
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900">{m.name}</td>
                  <td className="px-4 py-3 text-gray-600">{m.version}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={m.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-600">{m.backbone ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(m.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 space-x-2" onClick={(e) => e.stopPropagation()}>
                    {m.status === "registered" && (
                      <ActionBtn
                        label="Promote"
                        onClick={() => statusMutation.mutate({ id: m.id, status: "staging" })}
                      />
                    )}
                    {m.status === "staging" && (
                      <ActionBtn
                        label="Promote"
                        onClick={() => statusMutation.mutate({ id: m.id, status: "production" })}
                      />
                    )}
                    {m.status !== "archived" && (
                      <ActionBtn
                        label="Archive"
                        variant="danger"
                        onClick={() => statusMutation.mutate({ id: m.id, status: "archived" })}
                      />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail panel */}
      {selectedModel && (
        <ModelDetailPanel
          model={selectedModel}
          onClose={() => setSelectedModel(null)}
          onStatusChange={(s) => statusMutation.mutate({ id: selectedModel.id, status: s })}
        />
      )}

      {/* Compare result */}
      {compareResult && (
        <ComparePanel result={compareResult} onClose={() => setCompareResult(null)} />
      )}

      {/* Register modal */}
      {showRegisterModal && (
        <RegisterModal
          onClose={() => setShowRegisterModal(false)}
          onRegistered={() => {
            queryClient.invalidateQueries({ queryKey: ["models"] });
            setShowRegisterModal(false);
          }}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {status}
    </span>
  );
}

function ActionBtn({
  label,
  onClick,
  variant = "default",
}: {
  label: string;
  onClick: () => void;
  variant?: "default" | "danger";
}) {
  const cls =
    variant === "danger"
      ? "text-red-600 hover:text-red-800"
      : "text-brand-600 hover:text-brand-800";
  return (
    <button onClick={onClick} className={`text-xs font-medium ${cls}`}>
      {label}
    </button>
  );
}

function ModelDetailPanel({
  model,
  onClose,
  onStatusChange,
}: {
  model: ModelRecord;
  onClose: () => void;
  onStatusChange: (status: string) => void;
}) {
  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6 space-y-4">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{model.name}</h3>
          <p className="text-sm text-gray-500">Version {model.version}</p>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">
          &times;
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Status</span>
          <div className="mt-1">
            <StatusBadge status={model.status} />
          </div>
        </div>
        <div>
          <span className="text-gray-500">Backbone</span>
          <p className="mt-1 font-medium">{model.backbone ?? "—"}</p>
        </div>
        <div>
          <span className="text-gray-500">Registered</span>
          <p className="mt-1">{new Date(model.created_at).toLocaleString()}</p>
        </div>
        <div>
          <span className="text-gray-500">Updated</span>
          <p className="mt-1">{new Date(model.updated_at).toLocaleString()}</p>
        </div>
      </div>

      {/* Metrics */}
      {model.metrics && Object.keys(model.metrics).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Metrics</h4>
          <div className="bg-gray-50 rounded-lg p-3 grid grid-cols-3 gap-2 text-sm">
            {Object.entries(model.metrics).map(([k, v]) => (
              <div key={k}>
                <span className="text-gray-500">{k}</span>
                <p className="font-mono font-medium">{String(v)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-2">
        {model.status === "registered" && (
          <button
            onClick={() => onStatusChange("staging")}
            className="px-3 py-1.5 bg-yellow-500 text-white rounded-lg text-sm hover:bg-yellow-600"
          >
            Promote to Staging
          </button>
        )}
        {model.status === "staging" && (
          <button
            onClick={() => onStatusChange("production")}
            className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700"
          >
            Promote to Production
          </button>
        )}
        {model.status !== "archived" && (
          <button
            onClick={() => onStatusChange("archived")}
            className="px-3 py-1.5 bg-gray-500 text-white rounded-lg text-sm hover:bg-gray-600"
          >
            Archive
          </button>
        )}
      </div>
    </div>
  );
}

function ComparePanel({
  result,
  onClose,
}: {
  result: CompareResult;
  onClose: () => void;
}) {
  const keys = Object.keys(result.metric_diffs);

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6 space-y-4">
      <div className="flex justify-between items-start">
        <h3 className="text-lg font-semibold text-gray-900">Model Comparison</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">
          &times;
        </button>
      </div>

      <div className="flex gap-6 text-sm">
        <div>
          <span className="text-gray-500">Model A:</span>{" "}
          <strong>{result.model_a.name} v{result.model_a.version}</strong>
        </div>
        <div>
          <span className="text-gray-500">Model B:</span>{" "}
          <strong>{result.model_b.name} v{result.model_b.version}</strong>
        </div>
      </div>

      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-gray-500">Metric</th>
            <th className="px-4 py-2 text-left font-medium text-gray-500">Model A</th>
            <th className="px-4 py-2 text-left font-medium text-gray-500">Model B</th>
            <th className="px-4 py-2 text-left font-medium text-gray-500">Diff</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {keys.map((k) => {
            const d = result.metric_diffs[k];
            const diffColor =
              d.diff === null ? "" : d.diff > 0 ? "text-green-600" : d.diff < 0 ? "text-red-600" : "";
            return (
              <tr key={k}>
                <td className="px-4 py-2 font-medium">{k}</td>
                <td className="px-4 py-2 font-mono">{d.model_a ?? "—"}</td>
                <td className="px-4 py-2 font-mono">{d.model_b ?? "—"}</td>
                <td className={`px-4 py-2 font-mono ${diffColor}`}>
                  {d.diff !== null ? (d.diff > 0 ? `+${d.diff}` : d.diff) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RegisterModal({
  onClose,
  onRegistered,
}: {
  onClose: () => void;
  onRegistered: () => void;
}) {
  const [name, setName] = useState("");
  const [version, setVersion] = useState("");
  const [backbone, setBackbone] = useState(BACKBONE_OPTIONS[0]);
  const [metricsJson, setMetricsJson] = useState("{}");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (payload: ModelCreatePayload) => registerModel(payload),
    onSuccess: () => onRegistered(),
    onError: () => setError("Failed to register model."),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    let metrics: Record<string, number | string> = {};
    try {
      metrics = JSON.parse(metricsJson);
    } catch {
      setError("Invalid JSON for metrics.");
      return;
    }
    mutation.mutate({
      name,
      version,
      backbone,
      metrics,
      workspace_id: WORKSPACE_ID,
    });
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">Register Model</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. resnet50-classifier"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
            <input
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. 1.0.0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Backbone</label>
            <select
              value={backbone}
              onChange={(e) => setBackbone(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              {BACKBONE_OPTIONS.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Metrics (JSON)</label>
            <textarea
              value={metricsJson}
              onChange={(e) => setMetricsJson(e.target.value)}
              rows={4}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
              placeholder='{"accuracy": 0.95, "f1": 0.92}'
            />
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 bg-brand-600 text-white rounded-lg text-sm hover:bg-brand-700 disabled:opacity-50"
            >
              {mutation.isPending ? "Registering..." : "Register"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
