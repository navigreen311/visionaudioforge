"use client";

import { useCallback, useEffect, useState } from "react";
import ParticipantTable from "@/components/federated/ParticipantTable";
import AddParticipantModal from "@/components/federated/AddParticipantModal";
import type { FLParticipant } from "@/components/federated/ParticipantTable";
import { API_BASE_URL } from "@/lib/api";
import { readWorkspaceId } from "@/lib/session";

const API = `${API_BASE_URL}/api/federated`;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
//
// This page used to render `MOCK_FEDERATION`: a "Cross-Site Object Detection"
// run at round 12 of 50, three named sites with sample counts and accuracies,
// and a spent privacy budget of 0.24. All of it invented, all of it on screen,
// while /api/federated served the real thing. The four handlers below carried
// comments naming the endpoints they would call "in production" - each of those
// endpoints existed.

interface RoundMetric {
  round: number;
  accuracy: number;
  loss: number;
  participants: number;
}

interface ParticipantPayload {
  site: string;
  name: string;
  data_size: number;
  status: string;
  rounds_contributed: number;
  samples_contributed: number;
}

interface FederationPayload {
  id: string;
  name: string;
  model_id: string;
  aggregation_strategy: string;
  min_participants: number;
  total_rounds: number;
  current_round: number;
  status: string;
  privacy_budget: number;
  privacy_epsilon_spent: number;
  participants: ParticipantPayload[] | number;
}

interface RoundPayload {
  round_number?: number;
  round?: number;
  accuracy?: number | null;
  loss?: number | null;
  participants?: number | null;
}

/**
 * The participant table's shape, from the server's.
 *
 * `localAccuracy` and `dataQuality` are not returned by anything and are not
 * recorded anywhere - they were columns invented alongside the mock rows. They
 * are dropped rather than filled in. `contributionPct` is real: a site's share
 * of the samples contributed so far.
 */
function toParticipants(payload: ParticipantPayload[]): FLParticipant[] {
  const total = payload.reduce((sum, p) => sum + (p.samples_contributed || 0), 0);
  return payload.map((p) => ({
    id: p.site,
    name: p.name,
    status: (p.status as FLParticipant["status"]) ?? "active",
    samples: p.samples_contributed || p.data_size || 0,
    contributionPct: total ? Math.round((1000 * p.samples_contributed) / total) / 10 : 0,
  }));
}

// ---------------------------------------------------------------------------
// Charts
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
  const [fed, setFed] = useState<FederationPayload | null>(null);
  const [rounds, setRounds] = useState<RoundMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formName, setFormName] = useState("");
  const [formModel, setFormModel] = useState("");
  const [formMethod, setFormMethod] = useState("fedavg");
  const [showAddModal, setShowAddModal] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const listRes = await fetch(
        `${API}/federations?workspace_id=${readWorkspaceId()}`,
      );
      if (!listRes.ok) throw new Error(`HTTP ${listRes.status}`);
      const list: FederationPayload[] = await listRes.json();

      if (list.length === 0) {
        setFed(null);
        setRounds([]);
        return;
      }

      // The page shows one federation. Until it has a selector, that is the
      // most recent one rather than an invented one.
      const detailRes = await fetch(`${API}/federations/${list[list.length - 1].id}`);
      if (!detailRes.ok) throw new Error(`HTTP ${detailRes.status}`);
      const detail: FederationPayload = await detailRes.json();
      setFed(detail);

      const roundsRes = await fetch(`${API}/federations/${detail.id}/rounds`);
      if (roundsRes.ok) {
        const raw: RoundPayload[] = await roundsRes.json();
        setRounds(
          raw.map((r, index) => ({
            round: r.round_number ?? r.round ?? index + 1,
            accuracy: r.accuracy ?? 0,
            loss: r.loss ?? 0,
            participants: r.participants ?? 0,
          })),
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load federations.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    // Was `alert("Would create federation ...")`. POST /federations is real.
    setError(null);
    try {
      const res = await fetch(`${API}/federations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_id: readWorkspaceId(),
          name: formName,
          model_id: formModel,
          aggregation_strategy: formMethod,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setFormName("");
      setFormModel("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the federation.");
    }
  };

  const handleRetry = async (siteId: string) => {
    if (!fed) return;
    try {
      await fetch(`${API}/federations/${fed.id}/participants/${siteId}/reconnect`, {
        method: "POST",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reconnect the site.");
    }
  };

  const handleRemove = async (siteId: string) => {
    if (!fed) return;
    try {
      await fetch(`${API}/federations/${fed.id}/participants/${siteId}`, {
        method: "DELETE",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove the site.");
    }
  };

  const participants = Array.isArray(fed?.participants)
    ? toParticipants(fed.participants)
    : [];

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

      {error && <p className="text-sm text-red-600">{error}</p>}

      {loading && <p className="text-sm text-gray-500">Loading federations&hellip;</p>}

      {!loading && !fed && (
        <p className="text-sm text-gray-500">
          No federations in this workspace yet. Create one above to begin
          cross-site training.
        </p>
      )}

      {fed && (
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
              <p className="text-lg font-bold">{participants.length}</p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-xs text-gray-500">Aggregation</p>
              <p className="text-lg font-bold uppercase">{fed.aggregation_strategy}</p>
            </div>
          </div>

          {/* Privacy + Metrics row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <PrivacyGauge
              spent={fed.privacy_epsilon_spent}
              budget={fed.privacy_budget}
            />
            <MetricsChart metrics={rounds} />
          </div>

          {/* Participants */}
          <div>
            <h2 className="font-semibold mb-3">Participant Health</h2>
            <ParticipantTable
              federationId={fed.id}
              participants={participants}
              onAddParticipant={() => setShowAddModal(true)}
              onRetry={handleRetry}
              onRemove={handleRemove}
            />
          </div>

          {/* Add Participant Modal */}
          <AddParticipantModal
            isOpen={showAddModal}
            onClose={() => setShowAddModal(false)}
            federationId={fed.id}
            onParticipantAdded={() => {
              setShowAddModal(false);
              void load();
            }}
          />
        </>
      )}
    </div>
  );
}
