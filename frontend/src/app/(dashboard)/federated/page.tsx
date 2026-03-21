"use client";

import { useState, useEffect, useCallback } from "react";
import FederationSelector from "@/components/federated/FederationSelector";
import TrainingControls from "@/components/federated/TrainingControls";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Badge from "@/components/ui/Badge";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FederationStatus =
  | "waiting"
  | "ready"
  | "training"
  | "paused"
  | "completed"
  | "stopped";

interface Participant {
  id: string;
  status: "active" | "idle" | "disconnected";
  samplesContributed: number;
  lastSeen: string;
}

interface RoundMetric {
  round: number;
  accuracy: number;
  loss: number;
  participants: number;
}

interface Federation {
  id: string;
  name: string;
  model_id: string;
  status: FederationStatus;
  current_round: number;
  total_rounds: number;
  aggregation_strategy: string;
  epsilon_spent: number;
  epsilon_budget: number;
  min_participants: number;
  privacy_enabled: boolean;
  participants: Participant[];
  metrics_history: RoundMetric[];
  created_at: number;
}

interface RegistryModel {
  id: string;
  name: string;
  version: string;
  backbone: string;
}

// ---------------------------------------------------------------------------
// Sub-components (privacy, charts, tables)
// ---------------------------------------------------------------------------

function PrivacyBudgetChart({ spent, budget }: { spent: number; budget: number }) {
  const pct = Math.min((spent / budget) * 100, 100);
  const color =
    pct < 30 ? "bg-green-500" : pct < 70 ? "bg-yellow-500" : "bg-red-500";
  const label = pct < 30 ? "Strong" : pct < 70 ? "Moderate" : "Weak";

  return (
    <div className="rounded-lg border p-4">
      <h3 className="text-sm font-medium text-gray-500 mb-2">Privacy Budget</h3>
      <div className="flex items-end gap-3 mb-2">
        <span className="text-2xl font-bold">{spent.toFixed(2)}</span>
        <span className="text-gray-400 text-sm mb-1">/ {budget.toFixed(2)} epsilon</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3 mb-1">
        <div
          className={`${color} h-3 rounded-full transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 mt-1">
        Privacy level: <span className="font-semibold">{label}</span>
      </p>
    </div>
  );
}

function AccuracyLossChart({ metrics }: { metrics: RoundMetric[] }) {
  if (metrics.length === 0) return null;
  const maxAcc = Math.max(...metrics.map((m) => m.accuracy));
  const chartH = 120;

  return (
    <div className="rounded-lg border p-4">
      <h3 className="text-sm font-medium text-gray-500 mb-3">Accuracy Across Rounds</h3>
      <div className="flex items-end gap-1" style={{ height: chartH }}>
        {metrics.map((m) => {
          const h = (m.accuracy / Math.max(maxAcc, 1)) * chartH;
          return (
            <div key={m.round} className="flex flex-col items-center flex-1">
              <div
                className="w-full bg-brand-600 rounded-t"
                style={{ height: h }}
                title={`R${m.round}: acc ${(m.accuracy * 100).toFixed(1)}% | loss ${m.loss.toFixed(3)}`}
              />
              <span className="text-[10px] text-gray-400 mt-1">{m.round}</span>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-gray-400 mt-2 text-center">Round</p>
    </div>
  );
}

function ParticipantTable({ participants }: { participants: Participant[] }) {
  const statusColor: Record<string, string> = {
    active: "bg-green-100 text-green-800",
    idle: "bg-yellow-100 text-yellow-800",
    disconnected: "bg-red-100 text-red-800",
  };

  return (
    <div className="rounded-lg border overflow-hidden">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left px-4 py-2 font-medium text-gray-500">Participant</th>
            <th className="text-left px-4 py-2 font-medium text-gray-500">Status</th>
            <th className="text-right px-4 py-2 font-medium text-gray-500">Samples</th>
            <th className="text-right px-4 py-2 font-medium text-gray-500">Last Seen</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {participants.map((p) => (
            <tr key={p.id} className="hover:bg-gray-50">
              <td className="px-4 py-2 font-mono text-xs">{p.id}</td>
              <td className="px-4 py-2">
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor[p.status]}`}
                >
                  {p.status}
                </span>
              </td>
              <td className="px-4 py-2 text-right tabular-nums">
                {p.samplesContributed.toLocaleString()}
              </td>
              <td className="px-4 py-2 text-right text-gray-500">{p.lastSeen}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RoundHistoryTable({ metrics }: { metrics: RoundMetric[] }) {
  if (metrics.length === 0) return null;

  return (
    <div className="rounded-lg border overflow-hidden">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left px-4 py-2 font-medium text-gray-500">Round</th>
            <th className="text-right px-4 py-2 font-medium text-gray-500">Accuracy</th>
            <th className="text-right px-4 py-2 font-medium text-gray-500">Loss</th>
            <th className="text-right px-4 py-2 font-medium text-gray-500">Participants</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {[...metrics].reverse().map((m) => (
            <tr key={m.round} className="hover:bg-gray-50">
              <td className="px-4 py-2 font-mono text-xs">R{m.round}</td>
              <td className="px-4 py-2 text-right tabular-nums">
                {(m.accuracy * 100).toFixed(1)}%
              </td>
              <td className="px-4 py-2 text-right tabular-nums">{m.loss.toFixed(4)}</td>
              <td className="px-4 py-2 text-right">{m.participants}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ContributionChart({ participants }: { participants: Participant[] }) {
  const maxSamples = Math.max(...participants.map((p) => p.samplesContributed), 1);

  return (
    <div className="rounded-lg border p-4">
      <h3 className="text-sm font-medium text-gray-500 mb-3">Contribution by Participant</h3>
      <div className="space-y-2">
        {participants.map((p) => {
          const pct = (p.samplesContributed / maxSamples) * 100;
          return (
            <div key={p.id}>
              <div className="flex justify-between text-xs mb-1">
                <span className="font-mono">{p.id}</span>
                <span className="tabular-nums">{p.samplesContributed.toLocaleString()}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-brand-500 h-2 rounded-full transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mock data fallback
// ---------------------------------------------------------------------------

const MOCK_FEDERATION: Federation = {
  id: "fed-001",
  name: "Cross-Site Object Detection",
  model_id: "model-abc-123",
  status: "training",
  current_round: 12,
  total_rounds: 50,
  aggregation_strategy: "fedavg",
  epsilon_spent: 0.24,
  epsilon_budget: 1.0,
  min_participants: 2,
  privacy_enabled: true,
  participants: [
    { id: "site-alpha", status: "active", samplesContributed: 12400, lastSeen: "2 min ago" },
    { id: "site-beta", status: "active", samplesContributed: 8900, lastSeen: "1 min ago" },
    { id: "site-gamma", status: "idle", samplesContributed: 6200, lastSeen: "15 min ago" },
    { id: "site-delta", status: "disconnected", samplesContributed: 3100, lastSeen: "2 hr ago" },
  ],
  metrics_history: Array.from({ length: 12 }, (_, i) => ({
    round: i + 1,
    accuracy: 0.52 + i * 0.035 + Math.random() * 0.01,
    loss: 1.8 - i * 0.12 + Math.random() * 0.05,
    participants: i < 3 ? 2 : i < 8 ? 3 : 4,
  })),
  created_at: Date.now() / 1000 - 86400,
};

// ---------------------------------------------------------------------------
// Status helpers
// ---------------------------------------------------------------------------

const STATUS_VARIANT: Record<string, string> = {
  waiting: "neutral",
  ready: "info",
  training: "success",
  paused: "warning",
  completed: "info",
  stopped: "error",
};

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function FederatedPage() {
  // Federation selector state
  const [selectedFedId, setSelectedFedId] = useState<string | null>(null);
  const [fed, setFed] = useState<Federation | null>(null);
  const [loadingFed, setLoadingFed] = useState(false);

  // Model selector state (FL1)
  const [models, setModels] = useState<RegistryModel[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  // Create form state
  const [formName, setFormName] = useState("");
  const [formModel, setFormModel] = useState("");
  const [formMethod, setFormMethod] = useState("fedavg");
  const [formMinParticipants, setFormMinParticipants] = useState(2);
  const [formPrivacyEnabled, setFormPrivacyEnabled] = useState(true);
  const [formEpsilon, setFormEpsilon] = useState(1.0);
  const [formMaxRounds, setFormMaxRounds] = useState(10);

  // -----------------------------------------------------------------------
  // Fetch registry models (FL1)
  // -----------------------------------------------------------------------
  const fetchModels = useCallback(async () => {
    setLoadingModels(true);
    try {
      const res = await fetch("/api/registry/models/available");
      if (!res.ok) throw new Error("Failed to fetch models");
      const data: RegistryModel[] = await res.json();
      setModels(data);
    } catch {
      // fallback to empty
    } finally {
      setLoadingModels(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  // -----------------------------------------------------------------------
  // Fetch selected federation detail
  // -----------------------------------------------------------------------
  const fetchFederation = useCallback(async (id: string) => {
    setLoadingFed(true);
    try {
      const res = await fetch(`/api/federated/federations/${id}`);
      if (!res.ok) throw new Error("Failed to fetch federation");
      const data: Federation = await res.json();
      setFed(data);
    } catch {
      // fall back to mock for demo
      setFed(MOCK_FEDERATION);
    } finally {
      setLoadingFed(false);
    }
  }, []);

  useEffect(() => {
    if (selectedFedId) {
      fetchFederation(selectedFedId);
    } else {
      setFed(null);
    }
  }, [selectedFedId, fetchFederation]);

  // -----------------------------------------------------------------------
  // Create federation handler
  // -----------------------------------------------------------------------
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/federated/federations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formName,
          model_id: formModel,
          aggregation_strategy: formMethod,
          min_participants: formMinParticipants,
          rounds: formMaxRounds,
          privacy_enabled: formPrivacyEnabled,
          epsilon_budget: formEpsilon,
        }),
      });
      if (!res.ok) throw new Error("Create failed");
      const created: { id: string } = await res.json();
      setSelectedFedId(created.id);
      setFormName("");
      setFormModel("");
    } catch {
      alert("Failed to create federation. Check backend connection.");
    }
  };

  // -----------------------------------------------------------------------
  // Status change handler (from TrainingControls)
  // -----------------------------------------------------------------------
  const handleStatusChange = (newStatus: FederationStatus) => {
    if (fed) {
      setFed({ ...fed, status: newStatus });
    }
  };

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Federated Learning</h1>
        <p className="text-gray-500 mt-1">
          Cross-site collaborative training without sharing raw data
        </p>
      </div>

      {/* Federation Selector (FL2) */}
      <div className="flex items-center gap-4 flex-wrap">
        <FederationSelector selectedId={selectedFedId} onSelect={setSelectedFedId} />
        {fed && (
          <div className="flex items-center gap-3">
            <Badge variant={STATUS_VARIANT[fed.status] ?? "neutral"}>
              {fed.status}
            </Badge>
            <TrainingControls
              federationId={fed.id}
              status={fed.status}
              onStatusChange={handleStatusChange}
            />
          </div>
        )}
      </div>

      {/* Create Federation Form (visible when no federation selected) */}
      {!selectedFedId && (
        <div className="rounded-lg border p-4">
          <h2 className="font-semibold mb-3">Create Federation</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="flex flex-wrap gap-3 items-end">
              {/* Name */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Name</label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="My Federation"
                  className="border rounded px-3 py-1.5 text-sm w-56"
                  required
                />
              </div>

              {/* Model Selector (FL1) -- dropdown instead of text input */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Model</label>
                {loadingModels ? (
                  <div className="flex items-center gap-2 border rounded px-3 py-1.5 text-sm w-56 text-gray-400">
                    <LoadingSpinner size="sm" />
                    Loading...
                  </div>
                ) : (
                  <select
                    value={formModel}
                    onChange={(e) => setFormModel(e.target.value)}
                    className="border rounded px-3 py-1.5 text-sm w-56"
                    required
                  >
                    <option value="">Select a model...</option>
                    {models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} v{m.version} ({m.backbone})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Aggregation */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Aggregation</label>
                <select
                  value={formMethod}
                  onChange={(e) => setFormMethod(e.target.value)}
                  className="border rounded px-3 py-1.5 text-sm"
                >
                  <option value="fedavg">FedAvg</option>
                  <option value="fedprox">FedProx</option>
                  <option value="trimmed_mean">Trimmed Mean</option>
                </select>
              </div>

              {/* Min Participants */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Min Participants</label>
                <input
                  type="number"
                  min={2}
                  max={100}
                  value={formMinParticipants}
                  onChange={(e) => setFormMinParticipants(Number(e.target.value))}
                  className="border rounded px-3 py-1.5 text-sm w-24"
                />
              </div>

              {/* Max Rounds */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Max Rounds</label>
                <input
                  type="number"
                  min={1}
                  max={1000}
                  value={formMaxRounds}
                  onChange={(e) => setFormMaxRounds(Number(e.target.value))}
                  className="border rounded px-3 py-1.5 text-sm w-24"
                />
              </div>
            </div>

            {/* Privacy row */}
            <div className="flex items-center gap-4 flex-wrap">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formPrivacyEnabled}
                  onChange={(e) => setFormPrivacyEnabled(e.target.checked)}
                  className="rounded border-gray-300"
                />
                Differential Privacy
              </label>

              {formPrivacyEnabled && (
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-500">Epsilon:</label>
                  <input
                    type="range"
                    min={0.1}
                    max={10}
                    step={0.1}
                    value={formEpsilon}
                    onChange={(e) => setFormEpsilon(Number(e.target.value))}
                    className="w-32"
                  />
                  <span className="text-sm font-mono w-12 text-right">{formEpsilon.toFixed(1)}</span>
                </div>
              )}
            </div>

            <button
              type="submit"
              className="bg-brand-600 text-white rounded px-4 py-1.5 text-sm font-medium hover:bg-brand-700 transition-colors"
            >
              Create Federation
            </button>
          </form>
        </div>
      )}

      {/* Federation Detail (when selected) */}
      {selectedFedId && loadingFed && (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {selectedFedId && fed && !loadingFed && (
        <>
          {/* Status Overview */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="rounded-lg border p-4">
              <p className="text-xs text-gray-500">Status</p>
              <p className="text-lg font-bold capitalize">{fed.status}</p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-xs text-gray-500">Round</p>
              <p className="text-lg font-bold">
                {fed.current_round} / {fed.total_rounds}
              </p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-xs text-gray-500">Participants</p>
              <p className="text-lg font-bold">{fed.participants.length}</p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-xs text-gray-500">Aggregation</p>
              <p className="text-lg font-bold uppercase">{fed.aggregation_strategy}</p>
            </div>
          </div>

          {/* Privacy + Accuracy charts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <PrivacyBudgetChart spent={fed.epsilon_spent} budget={fed.epsilon_budget} />
            <AccuracyLossChart metrics={fed.metrics_history} />
          </div>

          {/* Contribution chart */}
          {fed.participants.length > 0 && (
            <ContributionChart participants={fed.participants} />
          )}

          {/* Participant Health */}
          <div>
            <h2 className="font-semibold mb-3">Participant Health</h2>
            <ParticipantTable participants={fed.participants} />
          </div>

          {/* Round History */}
          {fed.metrics_history.length > 0 && (
            <div>
              <h2 className="font-semibold mb-3">Round History</h2>
              <RoundHistoryTable metrics={fed.metrics_history} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
