"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { getAlertStatsSummary, type AlertStatsSummary } from "@/lib/api";

interface StatCardProps {
  label: string;
  count: number;
  trend: number;
  colorClass: string;
  bgClass: string;
  borderClass: string;
}

function TrendArrow({ trend }: { trend: number }) {
  if (trend === 0) {
    return <span className="text-xs text-gray-400">--</span>;
  }
  if (trend > 0) {
    return (
      <span className="inline-flex items-center text-xs font-medium text-red-600">
        <svg className="mr-0.5 h-3 w-3" viewBox="0 0 12 12" fill="currentColor">
          <path d="M6 2l4 5H2z" />
        </svg>
        +{trend}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center text-xs font-medium text-green-600">
      <svg className="mr-0.5 h-3 w-3" viewBox="0 0 12 12" fill="currentColor">
        <path d="M6 10l4-5H2z" />
      </svg>
      {trend}
    </span>
  );
}

function StatCard({ label, count, trend, colorClass, bgClass, borderClass }: StatCardProps) {
  return (
    <div className={`rounded-lg border ${borderClass} ${bgClass} p-4 shadow-sm`}>
      <p className="text-sm font-medium text-gray-600">{label}</p>
      <div className="mt-1 flex items-baseline gap-2">
        <span className={`text-3xl font-bold ${colorClass}`}>{count}</span>
        <TrendArrow trend={trend} />
      </div>
    </div>
  );
}

export default function AlertStatsSummary() {
  const { data: stats, isLoading } = useQuery<AlertStatsSummary>({
    queryKey: ["alert-stats-summary"],
    queryFn: getAlertStatsSummary,
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-lg border border-gray-200 bg-gray-50" />
        ))}
      </div>
    );
  }

  const safeStats: AlertStatsSummary = stats ?? {
    critical: 0,
    critical_trend: 0,
    warning: 0,
    warning_trend: 0,
    info: 0,
    info_trend: 0,
    acknowledged_today: 0,
    acknowledged_today_trend: 0,
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        label="Critical"
        count={safeStats.critical}
        trend={safeStats.critical_trend}
        colorClass="text-red-600"
        bgClass="bg-red-50"
        borderClass="border-red-200"
      />
      <StatCard
        label="Warning"
        count={safeStats.warning}
        trend={safeStats.warning_trend}
        colorClass="text-amber-600"
        bgClass="bg-amber-50"
        borderClass="border-amber-200"
      />
      <StatCard
        label="Info"
        count={safeStats.info}
        trend={safeStats.info_trend}
        colorClass="text-blue-600"
        bgClass="bg-blue-50"
        borderClass="border-blue-200"
      />
      <StatCard
        label="Acknowledged Today"
        count={safeStats.acknowledged_today}
        trend={safeStats.acknowledged_today_trend}
        colorClass="text-green-600"
        bgClass="bg-green-50"
        borderClass="border-green-200"
      />
    </div>
  );
}
