"use client";

import React, { useState } from "react";
import Tabs from "@/components/ui/Tabs";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import ThresholdTuningTab from "@/components/evaluation/ThresholdTuningTab";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MatchupResult {
  model_a: string;
  model_b: string;
  winner: string;
  metric_diffs: Record<string, number>;
  scores_a: Record<string, number>;
  scores_b: Record<string, number>;
}

interface TournamentResult {
  matchups: MatchupResult[];
  rankings: string[];
  overall_winner: string;
  wins: Record<string, number>;
}

interface BenchmarkResult {
  results: Record<string, Record<string, number>>;
  ranking: string[];
  duration_ms: number;
}

interface ScorecardData {
  model: string;
  benchmarks: { benchmark_id: string; name: string; scores: Record<string, number> }[];
  avg_scores: Record<string, number>;
  strengths: string[];
  weaknesses: string[];
}

// ---------------------------------------------------------------------------
// Benchmarks Tab
// ---------------------------------------------------------------------------

function BenchmarksTab() {
  const [name, setName] = useState("benchmark-1");
  const [datasetId, setDatasetId] = useState("dataset-001");
  const [modelIdsRaw, setModelIdsRaw] = useState("model-a, model-b, model-c");
  const [metricsRaw, setMetricsRaw] = useState("accuracy, precision, recall, f1");
  const [workspaceId, setWorkspaceId] = useState("00000000-0000-0000-0000-000000000001");
  const [benchmarkId, setBenchmarkId] = useState<string | null>(null);
  const [benchmarkResults, setBenchmarkResults] = useState<BenchmarkResult | null>(null);
  const [scorecard, setScorecard] = useState<ScorecardData | null>(null);
  const [loading, setLoading] = useState(false);

  const parse = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

  async function handleCreate() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/evaluation/benchmarks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          dataset_id: datasetId,
          model_ids: parse(modelIdsRaw),
          metrics: parse(metricsRaw),
          workspace_id: workspaceId,
        }),
      });
      const data = await res.json();
      setBenchmarkId(data.id);
      setBenchmarkResults(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleRun() {
    if (!benchmarkId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/evaluation/benchmarks/${benchmarkId}/run`, {
        method: "POST",
      });
      const data: BenchmarkResult = await res.json();
      setBenchmarkResults(data);
    } finally {
      setLoading(false);
    }
  }

  async function handleScorecard(modelId: string) {
    const res = await fetch(`${API}/api/evaluation/scorecard/${modelId}`);
    const data: ScorecardData = await res.json();
    setScorecard(data);
  }

  return (
    <div className="space-y-6">
      <Card title="Create Benchmark">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Dataset ID</label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Model IDs (comma-separated)</label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={modelIdsRaw}
              onChange={(e) => setModelIdsRaw(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Metrics (comma-separated)</label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={metricsRaw}
              onChange={(e) => setMetricsRaw(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Workspace ID</label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value)}
            />
          </div>
        </div>
        <div className="mt-4 flex gap-3">
          <Button onClick={handleCreate} loading={loading && !benchmarkId}>
            Create Benchmark
          </Button>
          {benchmarkId && (
            <Button variant="secondary" onClick={handleRun} loading={loading && !!benchmarkId}>
              Run Benchmark
            </Button>
          )}
        </div>
        {benchmarkId && (
          <p className="mt-2 text-sm text-gray-500">Benchmark ID: {benchmarkId}</p>
        )}
      </Card>

      {benchmarkResults && (
        <Card title={`Results (${benchmarkResults.duration_ms}ms)`}>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Rank</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Model</th>
                  {Object.keys(Object.values(benchmarkResults.results)[0] || {}).map((m) => (
                    <th key={m} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{m}</th>
                  ))}
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {benchmarkResults.ranking.map((modelId, idx) => (
                  <tr key={modelId} className={idx === 0 ? "bg-green-50" : "hover:bg-gray-50"}>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">#{idx + 1}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{modelId}</td>
                    {Object.values(benchmarkResults.results[modelId] || {}).map((v, i) => (
                      <td key={i} className="px-4 py-3 text-sm text-gray-700">{v}</td>
                    ))}
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleScorecard(modelId)}
                        className="text-sm text-brand-600 hover:text-brand-800 underline"
                      >
                        Scorecard
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {scorecard && (
        <Card title={`Scorecard: ${scorecard.model}`}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            {Object.entries(scorecard.avg_scores).map(([metric, value]) => (
              <div key={metric} className="rounded-lg bg-gray-50 p-3 text-center">
                <p className="text-xs font-medium uppercase text-gray-500">{metric}</p>
                <p className="text-2xl font-bold text-gray-900">{value}</p>
              </div>
            ))}
          </div>
          <div className="flex gap-6">
            <div>
              <h4 className="text-sm font-semibold text-green-700 mb-1">Strengths</h4>
              {scorecard.strengths.length > 0 ? (
                <ul className="list-disc list-inside text-sm text-gray-700">
                  {scorecard.strengths.map((s) => <li key={s}>{s}</li>)}
                </ul>
              ) : (
                <p className="text-sm text-gray-400">None identified yet</p>
              )}
            </div>
            <div>
              <h4 className="text-sm font-semibold text-red-700 mb-1">Weaknesses</h4>
              {scorecard.weaknesses.length > 0 ? (
                <ul className="list-disc list-inside text-sm text-gray-700">
                  {scorecard.weaknesses.map((w) => <li key={w}>{w}</li>)}
                </ul>
              ) : (
                <p className="text-sm text-gray-400">None identified</p>
              )}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tournament Tab
// ---------------------------------------------------------------------------

function TournamentTab() {
  const [modelIdsRaw, setModelIdsRaw] = useState("model-a, model-b, model-c, model-d");
  const [datasetId, setDatasetId] = useState("dataset-001");
  const [result, setResult] = useState<TournamentResult | null>(null);
  const [loading, setLoading] = useState(false);

  const parse = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

  async function handleRun() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/evaluation/tournament`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_ids: parse(modelIdsRaw), dataset_id: datasetId }),
      });
      const data: TournamentResult = await res.json();
      setResult(data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card title="Model Tournament">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Model IDs (comma-separated)</label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={modelIdsRaw}
              onChange={(e) => setModelIdsRaw(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Dataset ID</label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
            />
          </div>
        </div>
        <div className="mt-4">
          <Button onClick={handleRun} loading={loading}>Run Tournament</Button>
        </div>
      </Card>

      {result && (
        <>
          <Card title="Rankings">
            <div className="space-y-2">
              {result.rankings.map((modelId, idx) => (
                <div
                  key={modelId}
                  className={`flex items-center justify-between rounded-lg px-4 py-3 ${
                    idx === 0
                      ? "bg-yellow-50 border border-yellow-200"
                      : "bg-gray-50 border border-gray-200"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`text-lg font-bold ${idx === 0 ? "text-yellow-600" : "text-gray-500"}`}>
                      #{idx + 1}
                    </span>
                    <span className="text-sm font-medium text-gray-900">{modelId}</span>
                    {idx === 0 && (
                      <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-semibold text-yellow-800">
                        Champion
                      </span>
                    )}
                  </div>
                  <span className="text-sm text-gray-600">
                    {result.wins[modelId]} win{result.wins[modelId] !== 1 ? "s" : ""}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Matchups">
            <div className="space-y-3">
              {result.matchups.map((m, idx) => (
                <div key={idx} className="rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-sm font-medium ${m.winner === m.model_a ? "text-green-700" : "text-gray-700"}`}>
                      {m.model_a} {m.winner === m.model_a && "(W)"}
                    </span>
                    <span className="text-xs text-gray-400">vs</span>
                    <span className={`text-sm font-medium ${m.winner === m.model_b ? "text-green-700" : "text-gray-700"}`}>
                      {m.winner === m.model_b && "(W) "}{m.model_b}
                    </span>
                  </div>
                  <div className="grid grid-cols-4 gap-2">
                    {Object.entries(m.metric_diffs).map(([metric, diff]) => (
                      <div key={metric} className="text-center">
                        <p className="text-xs text-gray-500">{metric}</p>
                        <p className={`text-sm font-mono ${diff > 0 ? "text-green-600" : diff < 0 ? "text-red-600" : "text-gray-600"}`}>
                          {diff > 0 ? "+" : ""}{diff.toFixed(4)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function EvaluationPage() {
  const [activeTab, setActiveTab] = useState("benchmarks");

  const tabs = [
    { id: "benchmarks", label: "Benchmarks", content: <BenchmarksTab /> },
    { id: "tournament", label: "Tournament", content: <TournamentTab /> },
    { id: "threshold", label: "Threshold Tuning", content: <ThresholdTuningTab /> },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Evaluation Lab</h1>
        <p className="text-sm text-gray-500 mt-1">
          Benchmark models, run tournaments, and tune decision thresholds.
        </p>
      </div>
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}
