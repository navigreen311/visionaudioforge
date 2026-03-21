"use client";

import React from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SimulationResultData {
  /** Model robustness score 0-100. */
  robustnessScore: number;
  /** Total detections. */
  detections: number;
  /** Number of false alarms. */
  falseAlarms: number;
  /** Number of missed events. */
  missed: number;
  /** Total events in the simulation. */
  totalEvents: number;
  /** Duration in seconds. */
  durationS: number;
  /** Simulation ID for reference. */
  simulationId: string;
}

interface SimulationResultsProps {
  data: SimulationResultData;
  onOpenEvaluate?: () => void;
  onCreateCase?: () => void;
  onReRun?: () => void;
  onSaveTemplate?: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  if (score >= 40) return "text-orange-500";
  return "text-red-600";
}

function scoreBg(score: number): string {
  if (score >= 80) return "bg-green-50 border-green-200";
  if (score >= 60) return "bg-yellow-50 border-yellow-200";
  if (score >= 40) return "bg-orange-50 border-orange-200";
  return "bg-red-50 border-red-200";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SimulationResults({
  data,
  onOpenEvaluate,
  onCreateCase,
  onReRun,
  onSaveTemplate,
}: SimulationResultsProps) {
  const detectionRate =
    data.totalEvents > 0 ? ((data.detections / data.totalEvents) * 100).toFixed(1) : "0.0";
  const falseAlarmRate =
    data.totalEvents > 0 ? ((data.falseAlarms / data.totalEvents) * 100).toFixed(1) : "0.0";
  const missedRate =
    data.totalEvents > 0 ? ((data.missed / data.totalEvents) * 100).toFixed(1) : "0.0";

  return (
    <div className="space-y-6">
      {/* Robustness Score */}
      <Card>
        <div className="flex flex-col items-center py-4">
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
            Model Robustness Score
          </p>
          <div
            className={`flex items-center justify-center h-28 w-28 rounded-full border-4 ${scoreBg(data.robustnessScore)}`}
          >
            <span className={`text-4xl font-bold ${scoreColor(data.robustnessScore)}`}>
              {data.robustnessScore}
            </span>
          </div>
          <p className="mt-2 text-xs text-gray-400 font-mono">
            ID: {data.simulationId}
          </p>
        </div>
      </Card>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="text-center py-2">
            <p className="text-xs font-medium uppercase text-gray-500 mb-1">Detections</p>
            <p className="text-3xl font-bold text-blue-600">{data.detections}</p>
            <p className="text-xs text-gray-400 mt-1">{detectionRate}% of events</p>
          </div>
        </Card>

        <Card>
          <div className="text-center py-2">
            <p className="text-xs font-medium uppercase text-gray-500 mb-1">False Alarms</p>
            <p className="text-3xl font-bold text-orange-500">{data.falseAlarms}</p>
            <p className="text-xs text-gray-400 mt-1">{falseAlarmRate}% rate</p>
          </div>
        </Card>

        <Card>
          <div className="text-center py-2">
            <p className="text-xs font-medium uppercase text-gray-500 mb-1">Missed</p>
            <p className="text-3xl font-bold text-red-600">{data.missed}</p>
            <p className="text-xs text-gray-400 mt-1">{missedRate}% rate</p>
          </div>
        </Card>
      </div>

      {/* Action buttons */}
      <Card title="Actions">
        <div className="flex flex-wrap gap-3">
          <Button variant="primary" onClick={onOpenEvaluate}>
            Open in Evaluate
          </Button>
          <Button variant="secondary" onClick={onCreateCase}>
            Create Case
          </Button>
          <Button variant="secondary" onClick={onReRun}>
            Re-run
          </Button>
          <Button variant="ghost" onClick={onSaveTemplate}>
            Save as Template
          </Button>
        </div>
      </Card>
    </div>
  );
}
