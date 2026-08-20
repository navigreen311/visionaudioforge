"use client";

import { API_BASE_URL } from "@/lib/api";
import { readWorkspaceId } from "@/lib/session";

import React, { useCallback, useEffect, useState } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import BracketView, {
  MatchupRound,
} from "@/components/evaluation/BracketView";

const API = API_BASE_URL;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RegistryModel {
  id: string;
  name: string;
}

interface DatasetOption {
  id: string;
  name: string;
}

interface TournamentBracketResponse {
  id: string;
  title: string;
  metric: string;
  rounds: MatchupRound[];
  winner: string;
  created_at: string;
}

interface TournamentHistoryEntry {
  id: string;
  title: string;
  winner: string;
  model_count: number;
  metric: string;
  created_at: string;
}

const METRICS = [
  { value: "accuracy", label: "Accuracy" },
  { value: "precision", label: "Precision" },
  { value: "recall", label: "Recall" },
  { value: "f1", label: "F1 Score" },
  { value: "latency_ms", label: "Latency (ms)" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function calcRounds(modelCount: number): number {
  if (modelCount < 2) return 0;
  return Math.ceil(Math.log2(modelCount));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TournamentTab() {
  // Setup state
  const [title, setTitle] = useState("");
  const [models, setModels] = useState<RegistryModel[]>([]);
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);
  const [metric, setMetric] = useState("accuracy");
  const [datasets, setDatasets] = useState<DatasetOption[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Bracket state
  const [bracketResult, setBracketResult] =
    useState<TournamentBracketResponse | null>(null);

  // History state
  const [history, setHistory] = useState<TournamentHistoryEntry[]>([]);

  const rounds = calcRounds(selectedModelIds.length);

  // -----------------------------------------------------------------------
  // Data fetching
  // -----------------------------------------------------------------------

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch(
        `${API}/api/registry/models?workspace_id=${readWorkspaceId() ?? ""}`,
      );
      if (!res.ok) throw new Error("failed");
      const data = await res.json();
      const items: RegistryModel[] = (data.items ?? data).map(
        (m: Record<string, string>) => ({
          id: m.id ?? m.name,
          name: m.name,
        }),
      );
      setModels(items);
    } catch {
      // Fallback models when registry unavailable
      setModels([
        { id: "resnet-50", name: "resnet-50" },
        { id: "efficientnet-b0", name: "efficientnet-b0" },
        { id: "yolov8-nano", name: "yolov8-nano" },
        { id: "mobilenet-v3", name: "mobilenet-v3" },
        { id: "vit-base", name: "vit-base" },
        { id: "clip-rn50", name: "clip-rn50" },
        { id: "dino-v2", name: "dino-v2" },
        { id: "swin-tiny", name: "swin-tiny" },
      ]);
    }
  }, []);

  const fetchDatasets = useCallback(async () => {
    try {
      const res = await fetch(
        `${API}/api/datasets?workspace_id=${readWorkspaceId() ?? ""}`,
      );
      if (!res.ok) throw new Error("failed");
      const data = await res.json();
      const items: DatasetOption[] = (data.items ?? data).map(
        (d: Record<string, string>) => ({
          id: d.id ?? d.name,
          name: d.name,
        }),
      );
      setDatasets(items);
      if (items.length > 0 && !datasetId) {
        setDatasetId(items[0].id);
      }
    } catch {
      const fallback: DatasetOption[] = [
        { id: "dataset-001", name: "COCO-val-2024" },
        { id: "dataset-002", name: "ImageNet-mini" },
        { id: "dataset-003", name: "Custom-Surveillance" },
      ];
      setDatasets(fallback);
      if (!datasetId) setDatasetId(fallback[0].id);
    }
  }, [datasetId]);

  useEffect(() => {
    void fetchModels();
    void fetchDatasets();
  }, [fetchModels, fetchDatasets]);

  // -----------------------------------------------------------------------
  // Model selection
  // -----------------------------------------------------------------------

  function toggleModel(id: string) {
    setSelectedModelIds((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id],
    );
  }

  // -----------------------------------------------------------------------
  // Start tournament
  // -----------------------------------------------------------------------

  async function handleStart() {
    if (selectedModelIds.length < 4) return;
    setLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(`${API}/api/evaluation/tournament/bracket`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title || "Untitled Tournament",
          model_ids: selectedModelIds,
          dataset_id: datasetId,
          metric,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        setFetchError(
          typeof err.detail === "string" ? err.detail : JSON.stringify(err),
        );
        return;
      }
      const data: TournamentBracketResponse = await res.json();
      setBracketResult(data);

      // Append to local history
      setHistory((prev) => [
        {
          id: data.id,
          title: data.title,
          winner: data.winner,
          model_count: selectedModelIds.length,
          metric: data.metric,
          created_at: data.created_at,
        },
        ...prev,
      ]);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  const canStart = selectedModelIds.length >= 4 && !!datasetId;

  return (
    <div className="space-y-6">
      {/* Setup panel */}
      <Card title="Tournament Setup">
        <div className="space-y-5">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tournament Title
            </label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              placeholder="e.g. Q1 Model Shootout"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          {/* Model multi-select */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select Models{" "}
              <span className="text-gray-400 font-normal">
                (min 4 &mdash; {selectedModelIds.length} selected)
              </span>
            </label>
            <div className="flex flex-wrap gap-2">
              {models.map((m) => {
                const selected = selectedModelIds.includes(m.id);
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => toggleModel(m.id)}
                    className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                      selected
                        ? "bg-brand-600 text-white border-brand-600"
                        : "bg-white text-gray-700 border-gray-300 hover:border-brand-400"
                    }`}
                  >
                    {m.name}
                  </button>
                );
              })}
            </div>
            {selectedModelIds.length > 0 && selectedModelIds.length < 4 && (
              <p className="mt-1 text-xs text-red-500">
                Select at least 4 models to run a tournament.
              </p>
            )}
          </div>

          {/* Metric + Dataset + Rounds row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Primary Metric
              </label>
              <select
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                value={metric}
                onChange={(e) => setMetric(e.target.value)}
              >
                {METRICS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Dataset
              </label>
              <select
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                value={datasetId}
                onChange={(e) => setDatasetId(e.target.value)}
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Rounds (auto)
              </label>
              <div className="flex items-center h-[38px] rounded-md bg-gray-100 px-3 text-sm font-medium text-gray-700">
                {rounds > 0
                  ? `${rounds} round${rounds > 1 ? "s" : ""}`
                  : "\u2014"}
              </div>
            </div>
          </div>

          {/* Start button */}
          <div className="flex items-center gap-4">
            <Button
              onClick={handleStart}
              loading={loading}
              disabled={!canStart}
            >
              Start Tournament
            </Button>
            {fetchError && (
              <p className="text-sm text-red-600">{fetchError}</p>
            )}
          </div>
        </div>
      </Card>

      {/* Bracket view */}
      {bracketResult && (
        <Card title={`Bracket: ${bracketResult.title}`}>
          <BracketView
            rounds={bracketResult.rounds}
            winner={bracketResult.winner}
          />
        </Card>
      )}

      {/* Tournament history */}
      {history.length > 0 && (
        <Card title="Tournament History">
          <div className="divide-y divide-gray-200">
            {history.map((h) => (
              <div
                key={h.id}
                className="flex items-center justify-between py-3 first:pt-0 last:pb-0"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{h.title}</p>
                  <p className="text-xs text-gray-500">
                    {h.model_count} models &middot; {h.metric} &middot;{" "}
                    {h.created_at}
                  </p>
                </div>
                <span className="inline-flex items-center rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-semibold text-green-700 border border-green-200">
                  Winner: {h.winner}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
