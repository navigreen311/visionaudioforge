"use client";

import React from "react";
import type { KPIs } from "@/lib/api";

interface KPICardsProps {
  kpis: KPIs | null;
}

interface KPICardData {
  label: string;
  value: string;
  trend: number;
  unit?: string;
}

function trendArrow(trend: number): React.ReactNode {
  if (trend > 0) {
    return (
      <span className="inline-flex items-center text-green-600 text-[10px] font-medium">
        <svg className="h-3 w-3 mr-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 15l7-7 7 7" />
        </svg>
        +{Math.abs(trend).toFixed(1)}%
      </span>
    );
  }
  if (trend < 0) {
    return (
      <span className="inline-flex items-center text-red-600 text-[10px] font-medium">
        <svg className="h-3 w-3 mr-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 9l-7 7-7-7" />
        </svg>
        {Math.abs(trend).toFixed(1)}%
      </span>
    );
  }
  return (
    <span className="text-gray-400 text-[10px] font-medium">0.0%</span>
  );
}

export default function KPICards({ kpis }: KPICardsProps) {
  const cards: KPICardData[] = kpis
    ? [
        {
          label: "Avg Response",
          value: `${kpis.avg_response_time_seconds.toFixed(0)}s`,
          trend: kpis.response_time_trend,
        },
        {
          label: "Resolution Rate",
          value: `${kpis.resolution_rate_pct.toFixed(1)}%`,
          trend: kpis.resolution_rate_trend,
        },
        {
          label: "False Alarm Rate",
          value: `${kpis.false_alarm_rate_pct.toFixed(1)}%`,
          trend: kpis.false_alarm_trend,
        },
        {
          label: "Incidents Today",
          value: String(kpis.incidents_today),
          trend: kpis.incidents_today_trend,
        },
      ]
    : [
        { label: "Avg Response", value: "--", trend: 0 },
        { label: "Resolution Rate", value: "--", trend: 0 },
        { label: "False Alarm Rate", value: "--", trend: 0 },
        { label: "Incidents Today", value: "--", trend: 0 },
      ];

  return (
    <div className="space-y-2">
      <h3 className="px-3 py-2 text-sm font-semibold text-gray-900 border-b border-gray-200">
        KPIs
      </h3>
      <div className="grid grid-cols-2 gap-2 px-3 pb-2">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-gray-200 bg-white p-2.5"
          >
            <p className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">
              {card.label}
            </p>
            <p className="text-lg font-bold text-gray-900 leading-none">
              {card.value}
            </p>
            <div className="mt-1">{trendArrow(card.trend)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
