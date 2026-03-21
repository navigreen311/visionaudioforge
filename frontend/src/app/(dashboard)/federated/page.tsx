"use client";

import { useState } from "react";
import ParticipantTable from "@/components/federated/ParticipantTable";
import AddParticipantModal from "@/components/federated/AddParticipantModal";
import type { FLParticipant } from "@/components/federated/ParticipantTable";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RoundMetric {
  round: number;
  accuracy: number;
  loss: number;
  participants: number;
}

interface Federation {
  id: string;
  name: string;
  status: "created" | "training" | "stopped";
  currentRound: number;
  maxRounds: number;
  aggregationMethod: string;
  epsilonSpent: number;
  epsilonBudget: number;
  participants: FLParticipant[];
  metricsHistory: RoundMetric[];
}

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_FEDERATION: Federation = {
  id: "fed-001",
  name: "Cross-Site Object Detection",
  status: "training",
  currentRound: 12,
  maxRounds: 50,
  aggregationMethod: "fedavg",
  epsilonSpent: 0.24,
  epsilonBudget: 1.0,
  participants: [
    {
      id: "site-alpha",
      name: "Alpha Campus",
      status: "active",
      samples: 12400,
      contributionPct: 40.5,
      localAccuracy: 0.912,
      dataQuality: 0.95,
    },
    {
      id: "site-beta",
      name: "Beta Research Lab",
      status: "active",
      samples: 8900,
      contributionPct: 29.1,
      localAccuracy: 0.887,
      dataQuality: 0.91,
    },
    {
      id: "site-gamma",
      name: "Gamma Clinic",
      status: "idle",
      samples: 6200,
      contributionPct: 20.3,
      localAccuracy: 0.845,
      dataQuality: 0.78,
    },
    {
      id: "site-delta",
      name: "Delta Edge Node",
      status: "disconnected",
      samples: 3100,
      contributionPct: 10.1,
      localAccuracy: 0.791,
      dataQuality: 0.62,
    },
  ],
  metricsHistory: Array.from({ length: 12 }, (_, i) => ({
    round: i + 1,
    accuracy: 0.52 + i * 0.035 + Math.random() * 0.01,
    loss: 1.8 - i * 0.12 + Math.random() * 0.05,
    participants: i < 3 ? 2 : i < 8 ? 3 : 4,
  })),
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PrivacyGauge({ spent, budget }: { spent: number; budget: number }) {
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
        <div className={`${color} h-3 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-gray-500 mt-1">
        Privacy level: <span className="font-semibold">{label}</span>
      </p>
    </div>
  );
}

function MetricsChart({ metrics }: { metrics: RoundMetric[] }) {
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
                title={`R${m.round}: ${(m.accuracy * 100).toFixed(1)}%`}
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

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function FederatedPage() {
  const [fed, setFed] = useState<Federation>(MOCK_FEDERATION);
  const [formName, setFormName] = useState("");
  const [formModel, setFormModel] = useState("");
  const [formMethod, setFormMethod] = useState("fedavg");
  const [showAddModal, setShowAddModal] = useState(false);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    // In production: POST /api/federated/create
    alert(`Would create federation "${formName}" with model ${formModel}`);
  };

  const handleRetry = (siteId: string) => {
    // In production: POST /api/federated/federations/{id}/participants/{site}/reconnect
    setFed((prev) => ({
      ...prev,
      participants: prev.participants.map((p) =>
        p.id === siteId ? { ...p, status: "active" as const } : p
      ),
    }));
  };

  const handleRemove = (siteId: string) => {
    // In production: DELETE /api/federated/federations/{id}/participants/{site}
    setFed((prev) => ({
      ...prev,
      participants: prev.participants.filter((p) => p.id !== siteId),
    }));
  };

  const handleViewLogs = (siteId: string) => {
    // In production: navigate to log viewer
    alert(`View logs for ${siteId}`);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Federated Learning</h1>
        <p className="text-gray-500 mt-1">
          Cross-site collaborative training without sharing raw data
        </p>
      </div>

      {/* Create Federation Form */}
      <div className="rounded-lg border p-4">
        <h2 className="font-semibold mb-3">Create Federation</h2>
        <form onSubmit={handleCreate} className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Name</label>
            <input
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="My Federation"
              className="border rounded px-3 py-1.5 text-sm w-56"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Model ID</label>
            <input
              type="text"
              value={formModel}
              onChange={(e) => setFormModel(e.target.value)}
              placeholder="model-abc-123"
              className="border rounded px-3 py-1.5 text-sm w-44"
            />
          </div>
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
          <button
            type="submit"
            className="bg-brand-600 text-white rounded px-4 py-1.5 text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            Create
          </button>
        </form>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-lg border p-4">
          <p className="text-xs text-gray-500">Status</p>
          <p className="text-lg font-bold capitalize">{fed.status}</p>
        </div>
        <div className="rounded-lg border p-4">
          <p className="text-xs text-gray-500">Round</p>
          <p className="text-lg font-bold">
            {fed.currentRound} / {fed.maxRounds}
          </p>
        </div>
        <div className="rounded-lg border p-4">
          <p className="text-xs text-gray-500">Participants</p>
          <p className="text-lg font-bold">{fed.participants.length}</p>
        </div>
        <div className="rounded-lg border p-4">
          <p className="text-xs text-gray-500">Aggregation</p>
          <p className="text-lg font-bold uppercase">{fed.aggregationMethod}</p>
        </div>
      </div>

      {/* Privacy + Metrics row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <PrivacyGauge spent={fed.epsilonSpent} budget={fed.epsilonBudget} />
        <MetricsChart metrics={fed.metricsHistory} />
      </div>

      {/* Participants — enhanced table */}
      <div>
        <h2 className="font-semibold mb-3">Participant Health</h2>
        <ParticipantTable
          federationId={fed.id}
          participants={fed.participants}
          onAddParticipant={() => setShowAddModal(true)}
          onRetry={handleRetry}
          onRemove={handleRemove}
          onViewLogs={handleViewLogs}
        />
      </div>

      {/* Add Participant Modal */}
      <AddParticipantModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        federationId={fed.id}
        onParticipantAdded={() => {
          // In production: re-fetch participants
          setShowAddModal(false);
        }}
      />
    </div>
  );
}
