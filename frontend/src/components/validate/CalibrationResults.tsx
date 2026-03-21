"use client";

import React from "react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface CalibrationBin {
  bin_start: number;
  bin_end: number;
  avg_confidence: number;
  accuracy: number;
  count: number;
}

export interface CalibrationData {
  bins: CalibrationBin[];
  ece: number;
  mce: number;
  is_calibrated: boolean;
  /* Extended metrics (optional — populated by enhanced endpoint) */
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1?: number;
  auc_roc?: number;
}

interface CalibrationResultsProps {
  results: CalibrationData;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function eceVariant(ece: number): string {
  if (ece < 0.05) return "success";
  if (ece <= 0.15) return "warning";
  return "error";
}

function eceLabel(ece: number): string {
  if (ece < 0.05) return "Well Calibrated";
  if (ece <= 0.15) return "Acceptable";
  return "Poorly Calibrated";
}

interface StatCardProps {
  label: string;
  value: number | undefined;
  suffix?: React.ReactNode;
}

function StatCard({ label, value, suffix }: StatCardProps) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold text-gray-900">
        {value !== undefined ? value.toFixed(3) : "N/A"}
      </p>
      {suffix}
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function CalibrationResults({ results }: CalibrationResultsProps) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      <StatCard label="Accuracy" value={results.accuracy} />
      <StatCard label="Precision" value={results.precision} />
      <StatCard label="Recall" value={results.recall} />
      <StatCard label="F1 Score" value={results.f1} />
      <StatCard label="AUC-ROC" value={results.auc_roc} />
      <StatCard
        label="ECE"
        value={results.ece}
        suffix={
          <Badge variant={eceVariant(results.ece)} className="mt-1">
            {eceLabel(results.ece)}
          </Badge>
        }
      />
    </div>
  );
}
