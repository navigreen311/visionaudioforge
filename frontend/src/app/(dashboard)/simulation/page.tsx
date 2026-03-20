"use client";

import React, { useState } from "react";
import Tabs from "@/components/ui/Tabs";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ScenarioResult {
  scenario_id: string;
  type: string;
  events: Record<string, unknown>[];
  duration_s: number;
  description: string;
}

interface SimulationResult {
  simulation_id: string;
  events_injected: number;
  alerts_triggered: number;
  duration_s: number;
  timeline: Record<string, unknown>[];
}

interface StressTestResult {
  test_id: string;
  target_module: string;
  total_requests: number;
  successful: number;
  failed: number;
  throughput_rps: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  latency_p99_ms: number;
  error_rate: number;
  memory_delta_mb: number;
  duration_s: number;
}

interface EdgeCaseResult {
  model_name: string;
  test_cases: { case: string; status: string; error: string | null }[];
  passed: number;
  failed: number;
  edge_cases_found: string[];
}

interface SimulationReport {
  simulation_id: string;
  scenario: Record<string, unknown>;
  results: Record<string, unknown>;
  alerts: Record<string, unknown>[];
  missed_detections: string[];
  false_alarms: string[];
  recommendations: string[];
}

// ---------------------------------------------------------------------------
// Scenarios Tab
// ---------------------------------------------------------------------------

const SCENARIO_TYPES = [
  { value: "intrusion", label: "Intrusion Detection" },
  { value: "equipment_failure", label: "Equipment Failure" },
  { value: "crowd_formation", label: "Crowd Formation" },
  { value: "fire_smoke", label: "Fire / Smoke" },
  { value: "package_left", label: "Unattended Package" },
  { value: "medical_emergency", label: "Medical Emergency" },
];

function ScenariosTab() {
  const [scenarioType, setScenarioType] = useState("intrusion");
  const [eventCount, setEventCount] = useState(8);
  const [durationS, setDurationS] = useState(30);
  const [scenario, setScenario] = useState<ScenarioResult | null>(null);
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleGenerateAndRun() {
    setLoading(true);
    try {
      // Generate scenario
      const genRes = await fetch(`${API}/api/simulation/scenarios/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: scenarioType,
          params: { event_count: eventCount, duration_s: durationS },
        }),
      });
      const genData: ScenarioResult = await genRes.json();
      setScenario(genData);

      // Run simulation
      const runRes = await fetch(`${API}/api/simulation/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_id: "00000000-0000-0000-0000-000000000001",
          scenario: genData,
        }),
      });
      const runData: SimulationResult = await runRes.json();
      setSimResult(runData);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card title="Generate Scenario">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Scenario Type</label>
            <select
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={scenarioType}
              onChange={(e) => setScenarioType(e.target.value)}
            >
              {SCENARIO_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Event Count</label>
            <input
              type="number"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={eventCount}
              onChange={(e) => setEventCount(parseInt(e.target.value, 10) || 5)}
              min={1}
              max={50}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Duration (seconds)</label>
            <input
              type="number"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={durationS}
              onChange={(e) => setDurationS(parseInt(e.target.value, 10) || 30)}
              min={5}
              max={300}
            />
          </div>
        </div>
        <div className="mt-4">
          <Button onClick={handleGenerateAndRun} loading={loading}>
            Generate &amp; Run
          </Button>
        </div>
      </Card>

      {scenario && (
        <Card title={`Scenario: ${scenario.description}`}>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="rounded-lg bg-gray-50 p-3 text-center">
              <p className="text-xs font-medium uppercase text-gray-500">Type</p>
              <p className="text-lg font-bold text-gray-900">{scenario.type}</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3 text-center">
              <p className="text-xs font-medium uppercase text-gray-500">Events</p>
              <p className="text-lg font-bold text-gray-900">{scenario.events.length}</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3 text-center">
              <p className="text-xs font-medium uppercase text-gray-500">Duration</p>
              <p className="text-lg font-bold text-gray-900">{scenario.duration_s}s</p>
            </div>
          </div>
        </Card>
      )}

      {simResult && (
        <Card title="Simulation Results">
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="rounded-lg bg-blue-50 p-3 text-center">
              <p className="text-xs font-medium uppercase text-blue-600">Events Injected</p>
              <p className="text-2xl font-bold text-blue-900">{simResult.events_injected}</p>
            </div>
            <div className="rounded-lg bg-red-50 p-3 text-center">
              <p className="text-xs font-medium uppercase text-red-600">Alerts Triggered</p>
              <p className="text-2xl font-bold text-red-900">{simResult.alerts_triggered}</p>
            </div>
            <div className="rounded-lg bg-green-50 p-3 text-center">
              <p className="text-xs font-medium uppercase text-green-600">Duration</p>
              <p className="text-2xl font-bold text-green-900">{simResult.duration_s}s</p>
            </div>
            <div className="rounded-lg bg-purple-50 p-3 text-center">
              <p className="text-xs font-medium uppercase text-purple-600">Sim ID</p>
              <p className="text-xs font-mono text-purple-900 break-all">{simResult.simulation_id}</p>
            </div>
          </div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Timeline</h4>
          <div className="max-h-64 overflow-y-auto space-y-1">
            {simResult.timeline.map((entry, idx) => {
              const ev = entry.event as Record<string, unknown>;
              const isAlert = ev?.type === "alert_triggered";
              return (
                <div
                  key={idx}
                  className={`rounded px-3 py-2 text-xs font-mono ${
                    isAlert ? "bg-red-50 text-red-800 border-l-4 border-red-500" : "bg-gray-50 text-gray-700"
                  }`}
                >
                  <span className="text-gray-400 mr-2">#{(entry.seq as number) ?? idx + 1}</span>
                  <span className="font-semibold">{ev?.type as string}</span>
                  {ev?.confidence !== undefined && (
                    <span className="ml-2 text-gray-500">conf={String(ev.confidence)}</span>
                  )}
                  {ev?.severity && (
                    <span className="ml-2 text-red-600">severity={String(ev.severity)}</span>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stress Test Tab
// ---------------------------------------------------------------------------

function StressTestTab() {
  const [targetModule, setTargetModule] = useState("vision");
  const [concurrent, setConcurrent] = useState(50);
  const [duration, setDuration] = useState(60);
  const [payloadType, setPayloadType] = useState("medium");
  const [result, setResult] = useState<StressTestResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleRun() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/simulation/stress-test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_module: targetModule,
          concurrent_requests: concurrent,
          duration_s: duration,
          payload_type: payloadType,
        }),
      });
      const data: StressTestResult = await res.json();
      setResult(data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card title="Stress Test Configuration">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Target Module</label>
            <select
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={targetModule}
              onChange={(e) => setTargetModule(e.target.value)}
            >
              {["vision", "audio", "pipeline", "search"].map((m) => (
                <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Payload Type</label>
            <select
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={payloadType}
              onChange={(e) => setPayloadType(e.target.value)}
            >
              {["small", "medium", "large"].map((p) => (
                <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Concurrent Requests: {concurrent}
            </label>
            <input
              type="range"
              className="w-full"
              min={10}
              max={1000}
              step={10}
              value={concurrent}
              onChange={(e) => setConcurrent(parseInt(e.target.value, 10))}
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>10</span><span>500</span><span>1000</span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Duration: {duration}s
            </label>
            <input
              type="range"
              className="w-full"
              min={30}
              max={300}
              step={10}
              value={duration}
              onChange={(e) => setDuration(parseInt(e.target.value, 10))}
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>30s</span><span>150s</span><span>300s</span>
            </div>
          </div>
        </div>
        <div className="mt-4">
          <Button onClick={handleRun} loading={loading}>Run Stress Test</Button>
        </div>
      </Card>

      {result && (
        <Card title={`Results — ${result.target_module} (${result.duration_s}s)`}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <StatBox label="Throughput" value={`${result.throughput_rps} req/s`} color="blue" />
            <StatBox label="Total Requests" value={String(result.total_requests)} color="gray" />
            <StatBox label="Error Rate" value={`${(result.error_rate * 100).toFixed(2)}%`} color={result.error_rate > 0.05 ? "red" : "green"} />
            <StatBox label="Memory Delta" value={`${result.memory_delta_mb} MB`} color="purple" />
          </div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Latency Distribution</h4>
          <div className="space-y-2">
            <LatencyBar label="p50" value={result.latency_p50_ms} max={result.latency_p99_ms} />
            <LatencyBar label="p95" value={result.latency_p95_ms} max={result.latency_p99_ms} />
            <LatencyBar label="p99" value={result.latency_p99_ms} max={result.latency_p99_ms} />
          </div>
        </Card>
      )}
    </div>
  );
}

function StatBox({ label, value, color }: { label: string; value: string; color: string }) {
  const colorMap: Record<string, string> = {
    blue: "bg-blue-50 text-blue-900",
    green: "bg-green-50 text-green-900",
    red: "bg-red-50 text-red-900",
    purple: "bg-purple-50 text-purple-900",
    gray: "bg-gray-50 text-gray-900",
  };
  return (
    <div className={`rounded-lg p-3 text-center ${colorMap[color] || colorMap.gray}`}>
      <p className="text-xs font-medium uppercase opacity-70">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}

function LatencyBar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-medium text-gray-500 w-8">{label}</span>
      <div className="flex-1 h-4 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-brand-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-gray-700 w-20 text-right">{value.toFixed(2)} ms</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Edge Cases Tab
// ---------------------------------------------------------------------------

function EdgeCasesTab() {
  const [modelName, setModelName] = useState("yolov8-nano");
  const [result, setResult] = useState<EdgeCaseResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleRun() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/simulation/edge-cases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_name: modelName }),
      });
      const data: EdgeCaseResult = await res.json();
      setResult(data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card title="Edge Case Suite">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Model Name</label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
            />
          </div>
          <Button onClick={handleRun} loading={loading}>Run Suite</Button>
        </div>
      </Card>

      {result && (
        <Card title={`Results: ${result.model_name} (${result.passed} passed, ${result.failed} failed)`}>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="rounded-lg bg-green-50 p-3 text-center">
              <p className="text-xs font-medium uppercase text-green-600">Passed</p>
              <p className="text-2xl font-bold text-green-900">{result.passed}</p>
            </div>
            <div className="rounded-lg bg-red-50 p-3 text-center">
              <p className="text-xs font-medium uppercase text-red-600">Failed</p>
              <p className="text-2xl font-bold text-red-900">{result.failed}</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3 text-center">
              <p className="text-xs font-medium uppercase text-gray-600">Total</p>
              <p className="text-2xl font-bold text-gray-900">{result.test_cases.length}</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Test Case</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {result.test_cases.map((tc) => (
                  <tr key={tc.case} className={tc.status === "failed" ? "bg-red-50" : "hover:bg-gray-50"}>
                    <td className="px-4 py-3 text-sm font-mono text-gray-900">{tc.case}</td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                          tc.status === "passed"
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {tc.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">{tc.error || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Reports Tab
// ---------------------------------------------------------------------------

function ReportsTab() {
  const [simId, setSimId] = useState("");
  const [report, setReport] = useState<SimulationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFetch() {
    if (!simId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/simulation/report/${simId}`);
      if (!res.ok) {
        setError(`Report not found (${res.status})`);
        setReport(null);
        return;
      }
      const data: SimulationReport = await res.json();
      setReport(data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card title="Simulation Report">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Simulation ID</label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={simId}
              onChange={(e) => setSimId(e.target.value)}
              placeholder="Enter simulation ID..."
            />
          </div>
          <Button onClick={handleFetch} loading={loading}>Get Report</Button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </Card>

      {report && (
        <>
          <Card title="Scenario">
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg bg-gray-50 p-3 text-center">
                <p className="text-xs font-medium uppercase text-gray-500">Type</p>
                <p className="text-lg font-bold text-gray-900">{String(report.scenario.type)}</p>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 text-center">
                <p className="text-xs font-medium uppercase text-gray-500">Events</p>
                <p className="text-lg font-bold text-gray-900">{String(report.results.events_injected)}</p>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 text-center">
                <p className="text-xs font-medium uppercase text-gray-500">Alerts</p>
                <p className="text-lg font-bold text-gray-900">{String(report.results.alerts_triggered)}</p>
              </div>
            </div>
          </Card>

          {report.alerts.length > 0 && (
            <Card title="Alerts Fired">
              <div className="space-y-2">
                {report.alerts.map((a, idx) => (
                  <div key={idx} className="flex items-center justify-between rounded-lg bg-red-50 px-4 py-2 border-l-4 border-red-500">
                    <span className="text-sm font-medium text-red-800">{String(a.rule)}</span>
                    <span className="text-xs text-red-600">{String(a.severity)}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {report.missed_detections.length > 0 && (
            <Card title="Missed Detections">
              <ul className="list-disc list-inside text-sm text-red-700">
                {report.missed_detections.map((m) => <li key={m}>{m}</li>)}
              </ul>
            </Card>
          )}

          <Card title="Recommendations">
            <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
              {report.recommendations.map((r, idx) => <li key={idx}>{r}</li>)}
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function SimulationPage() {
  const [activeTab, setActiveTab] = useState("scenarios");

  const tabs = [
    { id: "scenarios", label: "Scenarios", content: <ScenariosTab /> },
    { id: "stress", label: "Stress Test", content: <StressTestTab /> },
    { id: "edge", label: "Edge Cases", content: <EdgeCasesTab /> },
    { id: "reports", label: "Reports", content: <ReportsTab /> },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Simulation Lab</h1>
        <p className="text-sm text-gray-500 mt-1">
          Generate synthetic incidents, run stress tests, and evaluate model robustness.
        </p>
      </div>
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}
