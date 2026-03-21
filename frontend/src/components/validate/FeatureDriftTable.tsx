"use client";

import React, { useState } from "react";
import Badge from "@/components/ui/Badge";
import DistributionChart from "./DistributionChart";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface DriftFeature {
  feature: string;
  reference_mean: number;
  current_mean: number;
  drift_score: number;
  status: "stable" | "minor" | "major";
  ref_distribution: number[];
  cur_distribution: number[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const STATUS_CONFIG: Record<string, { label: string; variant: string }> = {
  stable: { label: "Stable", variant: "success" },
  minor: { label: "Minor Drift", variant: "warning" },
  major: { label: "Major Drift", variant: "error" },
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

interface FeatureDriftTableProps {
  features: DriftFeature[];
}

export default function FeatureDriftTable({ features }: FeatureDriftTableProps) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const sorted = [...features].sort((a, b) => b.drift_score - a.drift_score);

  const toggleRow = (featureName: string) => {
    setExpandedRow((prev) => (prev === featureName ? null : featureName));
  };

  if (sorted.length === 0) {
    return (
      <p className="text-sm text-gray-500">No feature drift data available.</p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">
              Feature
            </th>
            <th className="px-4 py-3 text-right font-medium text-gray-600 hidden sm:table-cell">
              Ref Mean
            </th>
            <th className="px-4 py-3 text-right font-medium text-gray-600 hidden sm:table-cell">
              Cur Mean
            </th>
            <th className="px-4 py-3 text-right font-medium text-gray-600">
              Drift Score
            </th>
            <th className="px-4 py-3 text-center font-medium text-gray-600">
              Status
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {sorted.map((feat) => {
            const cfg = STATUS_CONFIG[feat.status] ?? STATUS_CONFIG.stable;
            const isExpanded = expandedRow === feat.feature;

            return (
              <React.Fragment key={feat.feature}>
                <tr
                  className="cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => toggleRow(feat.feature)}
                  role="button"
                  tabIndex={0}
                  aria-expanded={isExpanded}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      toggleRow(feat.feature);
                    }
                  }}
                >
                  <td className="px-4 py-3 font-medium text-gray-900">
                    <span className="flex items-center gap-2">
                      <svg
                        className={`h-3.5 w-3.5 text-gray-400 transition-transform ${
                          isExpanded ? "rotate-90" : ""
                        }`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                      {feat.feature}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700 hidden sm:table-cell">
                    {feat.reference_mean.toFixed(4)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700 hidden sm:table-cell">
                    {feat.current_mean.toFixed(4)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-gray-900">
                    {feat.drift_score.toFixed(4)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge variant={cfg.variant}>{cfg.label}</Badge>
                  </td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan={5} className="bg-gray-50 px-4 py-4">
                      <p className="mb-2 text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Distribution Comparison &mdash; {feat.feature}
                      </p>
                      <DistributionChart
                        refDistribution={feat.ref_distribution}
                        curDistribution={feat.cur_distribution}
                        featureName={feat.feature}
                      />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
