"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { getAlertStats, type AlertSeverity, type AlertStatus } from "@/lib/api";

const severityColors: Record<AlertSeverity, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-yellow-400",
  low: "bg-blue-400",
};

const statusColors: Record<AlertStatus, string> = {
  new: "bg-red-500",
  acknowledged: "bg-yellow-500",
  resolved: "bg-green-500",
  dismissed: "bg-gray-400",
};

const severityBadge: Record<AlertSeverity, "error" | "warning" | "info"> = {
  critical: "error",
  high: "warning",
  medium: "warning",
  low: "info",
};

function StatCard({ label, value, accent }: { label: string; value: number | string; accent?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accent || "text-gray-900"}`}>{value}</p>
    </div>
  );
}

function HorizontalBar({ items }: { items: { label: string; value: number; color: string }[] }) {
  const total = items.reduce((s, i) => s + i.value, 0) || 1;
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-3">
          <span className="w-20 text-sm text-gray-600 capitalize">{item.label}</span>
          <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${item.color} transition-all duration-500`}
              style={{ width: `${Math.max((item.value / total) * 100, 1)}%` }}
            />
          </div>
          <span className="w-10 text-right text-sm font-medium text-gray-700">{item.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function AlertStats() {
  const { data: stats, isLoading, isError } = useQuery({
    queryKey: ["alert-stats"],
    queryFn: getAlertStats,
    refetchInterval: 60_000,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (isError || !stats) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Failed to load alert statistics.
      </div>
    );
  }

  const severityItems = (Object.keys(severityColors) as AlertSeverity[]).map((sev) => ({
    label: sev,
    value: stats.by_severity[sev] || 0,
    color: severityColors[sev],
  }));

  const statusItems = (Object.keys(statusColors) as AlertStatus[]).map((st) => ({
    label: st,
    value: stats.by_status[st] || 0,
    color: statusColors[st],
  }));

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Alerts" value={stats.total} />
        <StatCard label="Critical (24h)" value={stats.critical_24h} accent="text-red-600" />
        <StatCard label="Acknowledged" value={stats.acknowledged} accent="text-yellow-600" />
        <StatCard label="Unresolved" value={stats.unresolved} accent="text-orange-600" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Severity distribution */}
        <Card title="Severity Distribution">
          <HorizontalBar items={severityItems} />
        </Card>

        {/* Status breakdown */}
        <Card title="Status Breakdown">
          <HorizontalBar items={statusItems} />
        </Card>
      </div>

      {/* Recent alerts timeline */}
      <Card title="Recent Alerts (Last 20)">
        {stats.recent.length === 0 ? (
          <p className="text-sm text-gray-500 py-2">No recent alerts.</p>
        ) : (
          <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
            {stats.recent.map((alert) => (
              <div key={alert.id} className="flex items-center gap-3 py-2">
                <Badge variant={severityBadge[alert.severity]}>{alert.severity}</Badge>
                <span className="flex-1 text-sm text-gray-800 truncate">{alert.message}</span>
                <span className="text-xs text-gray-400 whitespace-nowrap">
                  {new Date(alert.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
