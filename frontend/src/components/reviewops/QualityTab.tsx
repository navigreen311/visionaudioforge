"use client";

import React, { useState, useEffect, useCallback } from "react";
import Card from "@/components/ui/Card";
import ConfusionMatrixHeatmap from "./ConfusionMatrixHeatmap";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface QualitySummary {
  inter_rater_agreement: number;
  rejection_rate: number;
  escalation_rate: number;
  avg_quality_score: number;
}

interface AccuracyPoint {
  date: string;
  accuracy: number;
}

interface DisagreementCase {
  task_id: string;
  task_type: string;
  reviewer_a: string;
  reviewer_b: string;
  decision_a: string;
  decision_b: string;
  resolved: boolean;
}

interface ConfusionMatrix {
  labels: string[];
  values: number[][];
}

interface QualityResponse {
  summary: QualitySummary;
  accuracy_trend: AccuracyPoint[];
  disagreements: DisagreementCase[];
  confusion_matrix: ConfusionMatrix;
}

/* ------------------------------------------------------------------ */
/*  Summary Card                                                       */
/* ------------------------------------------------------------------ */

function MetricCard({
  label,
  value,
  suffix,
  color,
}: {
  label: string;
  value: number;
  suffix: string;
  color: "blue" | "red" | "yellow" | "green";
}) {
  const colorMap = {
    blue: "bg-blue-50 border-blue-200 text-blue-700",
    red: "bg-red-50 border-red-200 text-red-700",
    yellow: "bg-amber-50 border-amber-200 text-amber-700",
    green: "bg-green-50 border-green-200 text-green-700",
  } as const;

  return (
    <div
      className={`rounded-lg border px-4 py-3 text-center ${colorMap[color]}`}
    >
      <p className="text-xs font-medium uppercase text-gray-500">{label}</p>
      <p className="text-2xl font-bold">
        {value.toFixed(1)}
        {suffix}
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Accuracy Trend SVG Chart (14-day line)                             */
/* ------------------------------------------------------------------ */

const CHART_W = 600;
const CHART_H = 200;
const PAD = { top: 20, right: 20, bottom: 30, left: 45 };

function AccuracyTrendChart({ data }: { data: AccuracyPoint[] }) {
  if (data.length === 0) return null;

  const innerW = CHART_W - PAD.left - PAD.right;
  const innerH = CHART_H - PAD.top - PAD.bottom;

  const yMin = 0.7;
  const yMax = 1.0;
  const threshold = 0.9;

  const toX = (i: number) =>
    PAD.left + (i / Math.max(data.length - 1, 1)) * innerW;
  const toY = (v: number) =>
    PAD.top + ((yMax - v) / (yMax - yMin)) * innerH;

  const linePath = data
    .map((p, i) => `${i === 0 ? "M" : "L"} ${toX(i).toFixed(1)} ${toY(p.accuracy).toFixed(1)}`)
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${CHART_W} ${CHART_H}`}
      className="w-full max-w-[600px]"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Grid lines */}
      {[0.7, 0.8, 0.9, 1.0].map((v) => (
        <g key={v}>
          <line
            x1={PAD.left}
            y1={toY(v)}
            x2={CHART_W - PAD.right}
            y2={toY(v)}
            stroke="#e5e7eb"
            strokeDasharray={v === threshold ? "none" : "4 2"}
          />
          <text
            x={PAD.left - 6}
            y={toY(v)}
            textAnchor="end"
            dominantBaseline="central"
            fontSize={10}
            className="fill-gray-400"
          >
            {(v * 100).toFixed(0)}%
          </text>
        </g>
      ))}

      {/* 90% threshold line */}
      <line
        x1={PAD.left}
        y1={toY(threshold)}
        x2={CHART_W - PAD.right}
        y2={toY(threshold)}
        stroke="#ef4444"
        strokeWidth={1.5}
        strokeDasharray="6 3"
      />
      <text
        x={CHART_W - PAD.right + 2}
        y={toY(threshold)}
        dominantBaseline="central"
        fontSize={9}
        className="fill-red-500"
        fontWeight={600}
      >
        90%
      </text>

      {/* Data line */}
      <path d={linePath} fill="none" stroke="#3b82f6" strokeWidth={2} />

      {/* Data dots */}
      {data.map((p, i) => (
        <circle
          key={p.date}
          cx={toX(i)}
          cy={toY(p.accuracy)}
          r={3}
          fill={p.accuracy >= threshold ? "#3b82f6" : "#ef4444"}
          stroke="white"
          strokeWidth={1}
        />
      ))}

      {/* X-axis labels (show every other day) */}
      {data.map((p, i) =>
        i % 2 === 0 ? (
          <text
            key={`xl-${p.date}`}
            x={toX(i)}
            y={CHART_H - 6}
            textAnchor="middle"
            fontSize={9}
            className="fill-gray-400"
          >
            {p.date.slice(5)}
          </text>
        ) : null,
      )}
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function QualityTab() {
  const [data, setData] = useState<QualityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<"week" | "month">("week");
  const [cellDetail, setCellDetail] = useState<{
    row: string;
    col: string;
    value: number;
  } | null>(null);

  /* ---- Fetch quality data ---- */
  useEffect(() => {
    let cancelled = false;

    async function fetchQuality() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${API}/api/reviewops/quality?range=${range}`,
        );
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const json: QualityResponse = await res.json();
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load quality data");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchQuality();
    return () => {
      cancelled = true;
    };
  }, [range]);

  /* ---- Tie-break handler ---- */
  const handleTieBreak = useCallback(
    async (taskId: string, verdict: "approve" | "reject") => {
      try {
        const res = await fetch(
          `${API}/api/reviewops/quality/tiebreak`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task_id: taskId, verdict }),
          },
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        // Mark resolved locally
        setData((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            disagreements: prev.disagreements.map((d) =>
              d.task_id === taskId ? { ...d, resolved: true } : d,
            ),
          };
        });
      } catch {
        // Silently fail for stub — in production, show toast
      }
    },
    [],
  );

  /* ---- Confusion matrix cell click ---- */
  const handleCellClick = useCallback(
    (detail: { row: string; col: string; value: number }) => {
      setCellDetail(detail);
    },
    [],
  );

  /* ---- Render ---- */
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-brand-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Range selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-600">Range:</span>
        {(["week", "month"] as const).map((r) => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
              range === r
                ? "bg-brand-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {r === "week" ? "Last 7 Days" : "Last 30 Days"}
          </button>
        ))}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Inter-Rater Agreement"
          value={data.summary.inter_rater_agreement}
          suffix="%"
          color="blue"
        />
        <MetricCard
          label="Rejection Rate"
          value={data.summary.rejection_rate}
          suffix="%"
          color="red"
        />
        <MetricCard
          label="Escalation Rate"
          value={data.summary.escalation_rate}
          suffix="%"
          color="yellow"
        />
        <MetricCard
          label="Avg Quality Score"
          value={data.summary.avg_quality_score}
          suffix="%"
          color="green"
        />
      </div>

      {/* Accuracy Trend */}
      <Card title="Accuracy Trend (14-Day)">
        <AccuracyTrendChart data={data.accuracy_trend} />
        <p className="mt-2 text-xs text-gray-400">
          Red dashed line = 90% threshold. Dots below threshold shown in red.
        </p>
      </Card>

      {/* Confusion Matrix */}
      <Card title="Label Confusion Matrix">
        <div className="flex flex-col items-center gap-4">
          <ConfusionMatrixHeatmap
            labels={data.confusion_matrix.labels}
            values={data.confusion_matrix.values}
            onCellClick={handleCellClick}
          />
          {cellDetail && (
            <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-800">
              <span className="font-semibold">
                Actual &ldquo;{cellDetail.row}&rdquo; predicted as &ldquo;{cellDetail.col}&rdquo;
              </span>
              : {cellDetail.value} occurrences
            </div>
          )}
        </div>
      </Card>

      {/* Disagreement Cases */}
      <Card title="Disagreement Cases">
        {data.disagreements.length === 0 ? (
          <p className="text-sm text-gray-500">No disagreements found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {[
                    "Task",
                    "Type",
                    "Reviewer A",
                    "Reviewer B",
                    "Decision A",
                    "Decision B",
                    "Actions",
                  ].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {data.disagreements.map((d) => (
                  <tr key={d.task_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {d.task_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {d.task_type}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {d.reviewer_a}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {d.reviewer_b}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800">
                        {d.decision_a}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">
                        {d.decision_b}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {d.resolved ? (
                        <span className="text-xs font-medium text-gray-400">
                          Resolved
                        </span>
                      ) : (
                        <div className="flex gap-1">
                          <button
                            onClick={() => handleTieBreak(d.task_id, "approve")}
                            className="rounded bg-green-600 px-2 py-1 text-xs font-medium text-white hover:bg-green-700 transition-colors"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleTieBreak(d.task_id, "reject")}
                            className="rounded bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 transition-colors"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
