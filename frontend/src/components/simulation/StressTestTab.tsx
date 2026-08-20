'use client';

import { API_BASE_URL } from "@/lib/api";

import React, { useState, useCallback, useRef, useEffect } from 'react';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';

const API_BASE = API_BASE_URL;

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type TargetType = 'all_pipelines' | 'specific_pipeline' | 'api_endpoint';
type RequestType = 'vision' | 'audio' | 'pipeline' | 'custom';
type TestStatus = 'idle' | 'running' | 'completed' | 'failed';

interface ThroughputPoint {
  ts: number;
  sent: number;
  completed: number;
  failed: number;
}

interface LatencyPoint {
  ts: number;
  avg_ms: number;
  p95_ms: number;
  p99_ms: number;
}

interface StressTestSummary {
  total_requests: number;
  successful: number;
  failed: number;
  rps_peak: number;
  avg_latency_ms: number;
  p99_latency_ms: number;
  success_rate: number;
}

interface StressTestConfig {
  target: TargetType;
  target_name: string;
  concurrency: number;
  ramp_up_seconds: number;
  duration_seconds: number;
  request_type: RequestType;
}

interface StressTestStatusResponse {
  id: string;
  status: TestStatus;
  elapsed_seconds: number;
  throughput: ThroughputPoint[];
  latency: LatencyPoint[];
  summary: StressTestSummary | null;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const TARGET_OPTIONS: { value: TargetType; label: string }[] = [
  { value: 'all_pipelines', label: 'All Pipelines' },
  { value: 'specific_pipeline', label: 'Specific Pipeline' },
  { value: 'api_endpoint', label: 'API Endpoint' },
];

const REQUEST_TYPES: { value: RequestType; label: string }[] = [
  { value: 'vision', label: 'Vision' },
  { value: 'audio', label: 'Audio' },
  { value: 'pipeline', label: 'Pipeline' },
  { value: 'custom', label: 'Custom' },
];

const SLA_P99_MS = 500;

/* ------------------------------------------------------------------ */
/*  SVG Chart helpers                                                  */
/* ------------------------------------------------------------------ */

interface LineConfig {
  dataKey: keyof ThroughputPoint | keyof LatencyPoint;
  color: string;
  label: string;
}

function buildPolyline(
  data: Record<string, number>[],
  dataKey: string,
  width: number,
  height: number,
  maxY: number,
): string {
  if (data.length === 0) return '';
  const xStep = width / Math.max(data.length - 1, 1);
  return data
    .map((d, i) => {
      const x = i * xStep;
      const y = height - (((d[dataKey] as number) ?? 0) / maxY) * height;
      return `${x},${y}`;
    })
    .join(' ');
}

function SvgLineChart({
  data,
  lines,
  width = 560,
  height = 200,
  title,
}: {
  data: Record<string, number>[];
  lines: LineConfig[];
  width?: number;
  height?: number;
  title: string;
}) {
  const padding = { top: 10, right: 10, bottom: 24, left: 50 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const allValues = data.flatMap((d) =>
    lines.map((l) => (d[l.dataKey as string] as number) ?? 0),
  );
  const maxY = Math.max(...allValues, 1) * 1.1;

  const yTicks = 4;
  const yStep = maxY / yTicks;

  return (
    <div>
      <h4 className="mb-1 text-sm font-medium text-gray-700">{title}</h4>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        role="img"
        aria-label={title}
      >
        {/* Y-axis labels */}
        {Array.from({ length: yTicks + 1 }, (_, i) => {
          const val = i * yStep;
          const y = padding.top + chartH - (val / maxY) * chartH;
          return (
            <text
              key={i}
              x={padding.left - 6}
              y={y + 3}
              textAnchor="end"
              className="fill-gray-400"
              fontSize={9}
            >
              {val >= 1000 ? `${(val / 1000).toFixed(1)}k` : Math.round(val)}
            </text>
          );
        })}

        {/* Grid lines */}
        {Array.from({ length: yTicks + 1 }, (_, i) => {
          const val = i * yStep;
          const y = padding.top + chartH - (val / maxY) * chartH;
          return (
            <line
              key={i}
              x1={padding.left}
              y1={y}
              x2={padding.left + chartW}
              y2={y}
              stroke="#e5e7eb"
              strokeWidth={0.5}
            />
          );
        })}

        {/* Data lines */}
        <g transform={`translate(${padding.left},${padding.top})`}>
          {lines.map((line) => (
            <polyline
              key={line.dataKey as string}
              points={buildPolyline(data, line.dataKey as string, chartW, chartH, maxY)}
              fill="none"
              stroke={line.color}
              strokeWidth={2}
            />
          ))}
        </g>

        {/* Legend */}
        {lines.map((line, i) => (
          <g key={line.dataKey as string} transform={`translate(${padding.left + i * 120}, ${height - 6})`}>
            <rect width={10} height={3} fill={line.color} y={-3} rx={1} />
            <text x={14} fontSize={9} className="fill-gray-600">
              {line.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function StressTestTab() {
  /* Config state */
  const [target, setTarget] = useState<TargetType>('all_pipelines');
  const [targetName, setTargetName] = useState('');
  const [concurrency, setConcurrency] = useState(10);
  const [rampUp, setRampUp] = useState(10);
  const [duration, setDuration] = useState(60);
  const [requestType, setRequestType] = useState<RequestType>('vision');

  /* Results state */
  const [testId, setTestId] = useState<string | null>(null);
  const [status, setStatus] = useState<TestStatus>('idle');
  const [throughput, setThroughput] = useState<ThroughputPoint[]>([]);
  const [latency, setLatency] = useState<LatencyPoint[]>([]);
  const [summary, setSummary] = useState<StressTestSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* Cleanup polling on unmount */
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  /* ---- Poll for status ---- */
  const pollStatus = useCallback(
    (id: string) => {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/simulation/stress-test/${id}/status`);
          if (!res.ok) throw new Error(`Status ${res.status}`);
          const data: StressTestStatusResponse = await res.json();
          setThroughput(data.throughput);
          setLatency(data.latency);
          setSummary(data.summary);
          setStatus(data.status);

          if (data.status === 'completed' || data.status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Polling failed');
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }, 1000);
    },
    [],
  );

  /* ---- Launch test ---- */
  const handleRunTest = useCallback(async () => {
    setError(null);
    setStatus('running');
    setThroughput([]);
    setLatency([]);
    setSummary(null);

    const config: StressTestConfig = {
      target,
      target_name: targetName || target,
      concurrency,
      ramp_up_seconds: rampUp,
      duration_seconds: duration,
      request_type: requestType,
    };

    try {
      const res = await fetch(`${API_BASE}/api/simulation/stress-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body: { id: string; status: string } = await res.json();
      setTestId(body.id);
      pollStatus(body.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start test');
      setStatus('failed');
    }
  }, [target, targetName, concurrency, rampUp, duration, requestType, pollStatus]);

  /* ---- Derived ---- */
  const isRunning = status === 'running';
  const showResults = throughput.length > 0 || latency.length > 0 || summary !== null;

  const passed =
    summary !== null &&
    summary.success_rate > 95 &&
    summary.p99_latency_ms < SLA_P99_MS;

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="space-y-6">
      {/* ---------- Configuration Card ---------- */}
      <Card title="Stress Test Configuration">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {/* Target */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Target
            </label>
            <select
              value={target}
              onChange={(e) => setTarget(e.target.value as TargetType)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              disabled={isRunning}
            >
              {TARGET_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          {/* Target name (shown for specific / endpoint) */}
          {target !== 'all_pipelines' && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                {target === 'specific_pipeline' ? 'Pipeline Name' : 'Endpoint URL'}
              </label>
              <input
                type="text"
                value={targetName}
                onChange={(e) => setTargetName(e.target.value)}
                placeholder={
                  target === 'specific_pipeline'
                    ? 'e.g. object-detection'
                    : 'e.g. /api/vision/detect'
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                disabled={isRunning}
              />
            </div>
          )}

          {/* Concurrency slider */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Concurrency: {concurrency}
            </label>
            <input
              type="range"
              min={1}
              max={100}
              value={concurrency}
              onChange={(e) => setConcurrency(Number(e.target.value))}
              className="w-full accent-blue-600"
              disabled={isRunning}
            />
            <div className="mt-0.5 flex justify-between text-xs text-gray-400">
              <span>1</span>
              <span>50</span>
              <span>100</span>
            </div>
          </div>

          {/* Ramp-up time */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Ramp-up Time (s)
            </label>
            <input
              type="number"
              min={0}
              max={300}
              value={rampUp}
              onChange={(e) => setRampUp(Number(e.target.value))}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              disabled={isRunning}
            />
          </div>

          {/* Duration */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Duration (s)
            </label>
            <input
              type="number"
              min={5}
              max={3600}
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              disabled={isRunning}
            />
          </div>

          {/* Request type */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Request Type
            </label>
            <select
              value={requestType}
              onChange={(e) => setRequestType(e.target.value as RequestType)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              disabled={isRunning}
            >
              {REQUEST_TYPES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Run button */}
        <div className="mt-6">
          <Button
            onClick={handleRunTest}
            disabled={isRunning}
            loading={isRunning}
            variant="primary"
          >
            {isRunning ? 'Running...' : 'Run Stress Test'}
          </Button>
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-600">{error}</p>
        )}
      </Card>

      {/* ---------- Live Results ---------- */}
      {showResults && (
        <>
          {/* Charts */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card title="Throughput">
              <SvgLineChart
                title="Requests over time"
                data={throughput as unknown as Record<string, number>[]}
                lines={[
                  { dataKey: 'sent' as keyof ThroughputPoint, color: '#3b82f6', label: 'Sent' },
                  { dataKey: 'completed' as keyof ThroughputPoint, color: '#22c55e', label: 'Completed' },
                  { dataKey: 'failed' as keyof ThroughputPoint, color: '#ef4444', label: 'Failed' },
                ]}
              />
            </Card>

            <Card title="Latency">
              <SvgLineChart
                title="Latency over time (ms)"
                data={latency as unknown as Record<string, number>[]}
                lines={[
                  { dataKey: 'avg_ms' as keyof LatencyPoint, color: '#3b82f6', label: 'Avg' },
                  { dataKey: 'p95_ms' as keyof LatencyPoint, color: '#f59e0b', label: 'p95' },
                  { dataKey: 'p99_ms' as keyof LatencyPoint, color: '#ef4444', label: 'p99' },
                ]}
              />
            </Card>
          </div>

          {/* Summary stats + badge */}
          {summary && (
            <Card title="Summary">
              <div className="mb-4 flex items-center gap-3">
                <span className="text-sm font-medium text-gray-700">Result:</span>
                <Badge variant={passed ? 'success' : 'error'}>
                  {passed ? 'PASS' : 'FAIL'}
                </Badge>
                {!passed && (
                  <span className="text-xs text-gray-500">
                    (Requires &gt;95% success rate and p99 &lt; {SLA_P99_MS}ms)
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
                <StatBox label="Total Requests" value={summary.total_requests.toLocaleString()} />
                <StatBox
                  label="Successful"
                  value={summary.successful.toLocaleString()}
                  accent="text-green-600"
                />
                <StatBox
                  label="Failed"
                  value={summary.failed.toLocaleString()}
                  accent="text-red-600"
                />
                <StatBox label="Peak RPS" value={summary.rps_peak.toFixed(1)} />
                <StatBox label="Avg Latency" value={`${summary.avg_latency_ms.toFixed(1)}ms`} />
                <StatBox
                  label="p99 Latency"
                  value={`${summary.p99_latency_ms.toFixed(1)}ms`}
                  accent={summary.p99_latency_ms >= SLA_P99_MS ? 'text-red-600' : undefined}
                />
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Stat box helper                                                    */
/* ------------------------------------------------------------------ */

function StatBox({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-lg font-semibold ${accent ?? 'text-gray-900'}`}>{value}</p>
    </div>
  );
}
