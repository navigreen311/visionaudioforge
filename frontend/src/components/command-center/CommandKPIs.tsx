"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import type { KPIs } from "@/lib/api";
import { getKPIs } from "@/lib/api";

interface KPICardData {
  label: string;
  value: string;
  trend: number;
  delta: string;
}

const POLL_INTERVAL_MS = 30_000;

function trendIndicator(trend: number): React.ReactNode {
  if (trend > 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-green-600 text-[10px] font-medium">
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 15l7-7 7 7" />
        </svg>
      </span>
    );
  }
  if (trend < 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-red-600 text-[10px] font-medium">
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 9l-7 7-7-7" />
        </svg>
      </span>
    );
  }
  return (
    <span className="text-gray-400 text-[10px] font-medium">&mdash;</span>
  );
}

function buildCards(kpis: KPIs): KPICardData[] {
  return [
    {
      label: "Avg Response",
      value: `${kpis.avg_response_time_seconds.toFixed(0)}s`,
      trend: kpis.response_time_trend,
      delta: `${kpis.response_time_trend > 0 ? "+" : ""}${kpis.response_time_trend.toFixed(1)}%`,
    },
    {
      label: "Resolution Rate",
      value: `${kpis.resolution_rate_pct.toFixed(1)}%`,
      trend: kpis.resolution_rate_trend,
      delta: `${kpis.resolution_rate_trend > 0 ? "+" : ""}${kpis.resolution_rate_trend.toFixed(1)}%`,
    },
    {
      label: "False Alarm Rate",
      value: `${kpis.false_alarm_rate_pct.toFixed(1)}%`,
      trend: kpis.false_alarm_trend,
      delta: `${kpis.false_alarm_trend > 0 ? "+" : ""}${kpis.false_alarm_trend.toFixed(1)}%`,
    },
    {
      label: "Incidents Today",
      value: String(kpis.incidents_today),
      trend: kpis.incidents_today_trend,
      delta: `${kpis.incidents_today_trend > 0 ? "+" : ""}${kpis.incidents_today_trend.toFixed(1)}%`,
    },
  ];
}

const EMPTY_CARDS: KPICardData[] = [
  { label: "Avg Response", value: "--", trend: 0, delta: "0.0%" },
  { label: "Resolution Rate", value: "--", trend: 0, delta: "0.0%" },
  { label: "False Alarm Rate", value: "--", trend: 0, delta: "0.0%" },
  { label: "Incidents Today", value: "--", trend: 0, delta: "0.0%" },
];

export default function CommandKPIs() {
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [error, setError] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchKpis = useCallback(async () => {
    try {
      const data = await getKPIs();
      setKpis(data);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    fetchKpis();
    intervalRef.current = setInterval(fetchKpis, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchKpis]);

  const cards = kpis ? buildCards(kpis) : EMPTY_CARDS;

  return (
    <div className="space-y-2">
      <h3 className="px-3 py-2 text-sm font-semibold text-gray-900 border-b border-gray-200">
        KPIs
        {error && (
          <span className="ml-2 text-[10px] text-red-500 font-normal">
            (fetch error)
          </span>
        )}
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
            <div className="mt-1 flex items-center gap-1">
              {trendIndicator(card.trend)}
              <span
                className={`text-[10px] font-medium ${
                  card.trend > 0
                    ? "text-green-600"
                    : card.trend < 0
                      ? "text-red-600"
                      : "text-gray-400"
                }`}
              >
                {card.delta}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
