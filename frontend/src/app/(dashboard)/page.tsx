"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import StatusIndicator from "@/components/ui/StatusIndicator";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import api from "@/lib/api";

// Shared components (created by other agents — stub imports)
import CopilotQuickAsk from "@/components/shared/CopilotQuickAsk";
import TimeRangeSelector from "@/components/shared/TimeRangeSelector";
import SparklineChart from "@/components/shared/SparklineChart";
import GettingStarted from "@/components/shared/GettingStarted";
import ActivityFeed from "@/components/shared/ActivityFeed";
import ActiveJobs from "@/components/shared/ActiveJobs";
import CircularGauge from "@/components/shared/CircularGauge";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface StatItem {
  icon: string;
  label: string;
  value: number;
  trend: string;
  sparkline: number[];
}

interface DashboardStatsResponse {
  stats: StatItem[];
}

interface RuntimeMetrics {
  // null when the host does not report it - see /api/runtime/metrics.
  gpu: number | null;
  cpu: number | null;
  storage: number | null;
}

type TimeRange = "1d" | "7d" | "30d" | "90d";

// ---------------------------------------------------------------------------
// Static Data
// ---------------------------------------------------------------------------

const defaultStats: StatItem[] = [
  { icon: "\uD83D\uDCF9", label: "Active Streams", value: 0, trend: "+0%", sparkline: [] },
  { icon: "\uD83E\uDD16", label: "Models in Production", value: 0, trend: "+0%", sparkline: [] },
  { icon: "\uD83D\uDD14", label: "Open Alerts", value: 0, trend: "0", sparkline: [] },
  { icon: "\uD83D\uDCC1", label: "Total Assets", value: 0, trend: "+0", sparkline: [] },
];

const quickActions = [
  { icon: "\uD83D\uDCF9", label: "Start Capture", href: "/capture" },
  { icon: "\uD83D\uDCC2", label: "Upload Media", href: "/assets" },
  { icon: "\u2699\uFE0F", label: "Build Pipeline", href: "/pipeline" },
  { icon: "\uD83E\uDD16", label: "Ask Copilot", href: "/agents" },
];

interface ModuleEntry {
  name: string;
  status: "Active" | "Coming Soon";
  href?: string;
}

const modules: ModuleEntry[] = [
  { name: "Capture", status: "Active", href: "/capture" },
  { name: "Vision", status: "Active", href: "/vision" },
  { name: "Audio", status: "Active", href: "/audio" },
  { name: "Transform", status: "Active", href: "/transform" },
  { name: "Train", status: "Coming Soon" },
  { name: "Validate", status: "Coming Soon" },
  { name: "Search", status: "Active", href: "/search" },
  { name: "Alerts", status: "Active", href: "/alerts" },
  { name: "Pipeline", status: "Active", href: "/pipeline" },
  { name: "Investigate", status: "Coming Soon" },
  { name: "Agents", status: "Coming Soon" },
  { name: "Assets", status: "Active", href: "/assets" },
  { name: "Evaluation", status: "Coming Soon" },
  { name: "Settings", status: "Active", href: "/settings" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>("7d");
  const [stats, setStats] = useState<StatItem[]>(defaultStats);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<RuntimeMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(true);
  const [metricsError, setMetricsError] = useState<string | null>(null);

  // Fetch dashboard stats when timeRange changes
  const fetchStats = useCallback(async (range: TimeRange) => {
    setStatsLoading(true);
    setStatsError(null);
    try {
      const res = await api.get(
        `/api/dashboard/stats?range=${range}`,
      );
      const d = res.data;
      setStats([
        { icon: "\uD83D\uDCF9", label: "Active Streams", value: d.active_streams ?? 0, trend: "+0%", sparkline: d.streams_history ?? [] },
        { icon: "\uD83E\uDD16", label: "Models in Production", value: d.models_production ?? 0, trend: "+0%", sparkline: d.models_history ?? [] },
        { icon: "\uD83D\uDD14", label: "Open Alerts", value: d.open_alerts ?? 0, trend: "0", sparkline: d.alerts_history ?? [] },
        { icon: "\uD83D\uDCC1", label: "Total Assets", value: d.total_assets ?? 0, trend: "+0", sparkline: d.assets_history ?? [] },
      ]);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to load stats";
      setStatsError(message);
      setStats(defaultStats);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats(timeRange);
  }, [timeRange, fetchStats]);

  // Fetch runtime metrics every 30 seconds
  useEffect(() => {
    let cancelled = false;

    const fetchMetrics = async () => {
      try {
        const res = await api.get<RuntimeMetrics>("/api/runtime/metrics");
        if (!cancelled) {
          setMetrics(res.data);
          setMetricsError(null);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const message =
            err instanceof Error ? err.message : "Failed to load metrics";
          setMetricsError(message);
        }
      } finally {
        if (!cancelled) {
          setMetricsLoading(false);
        }
      }
    };

    fetchMetrics();
    const intervalId = setInterval(fetchMetrics, 30_000);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Overview of your VisionAudioForge workspace
        </p>
      </div>

      {/* Copilot Quick Ask */}
      <CopilotQuickAsk />

      {/* Time Range Selector */}
      <TimeRangeSelector
        value={timeRange}
        onChange={(range: string) => setTimeRange(range as TimeRange)}
      />

      {/* Stats Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statsLoading ? (
          <div className="col-span-full flex items-center justify-center py-8">
            <LoadingSpinner />
          </div>
        ) : statsError ? (
          <div className="col-span-full rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {statsError}
          </div>
        ) : (
          stats.map((stat) => (
            <Card key={stat.label}>
              <div className="flex items-center gap-4">
                <span className="text-3xl">{stat.icon}</span>
                <div className="flex-1">
                  <p className="text-sm text-gray-500">{stat.label}</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {stat.value}
                  </p>
                  <p className="text-xs text-gray-400">{stat.trend}</p>
                </div>
                {stat.sparkline.length > 0 && (
                  <div className="h-10 w-20">
                    <SparklineChart data={stat.sparkline} />
                  </div>
                )}
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Getting Started */}
      <GettingStarted />

      {/* Activity Feed + Quick Actions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Activity Feed */}
        <ActivityFeed />

        {/* Quick Actions */}
        <Card title="Quick Actions">
          <div className="grid grid-cols-2 gap-3">
            {quickActions.map((action) => (
              <Link
                key={action.href}
                href={action.href}
                className="flex flex-col items-center gap-2 rounded-lg border border-gray-200 p-4 hover:bg-gray-50 hover:border-brand-300 transition-colors"
              >
                <span className="text-2xl">{action.icon}</span>
                <span className="text-sm font-medium text-gray-700">
                  {action.label}
                </span>
              </Link>
            ))}
          </div>
        </Card>
      </div>

      {/* Active Jobs */}
      <ActiveJobs />

      {/* Resource Usage */}
      <Card title="Resource Usage">
        {metricsLoading ? (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner />
          </div>
        ) : metricsError ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {metricsError}
          </div>
        ) : metrics ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            <div className="flex flex-col items-center gap-2">
              <CircularGauge value={metrics.gpu} label="GPU" />
            </div>
            <div className="flex flex-col items-center gap-2">
              <CircularGauge value={metrics.cpu} label="CPU" />
            </div>
            <div className="flex flex-col items-center gap-2">
              <CircularGauge value={metrics.storage} label="Storage" />
            </div>
          </div>
        ) : null}
      </Card>

      {/* System Health */}
      <Card title="System Health">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <StatusIndicator status="online" />
            <span className="text-sm font-medium text-gray-700">
              All Systems Operational
            </span>
          </div>
          <a
            href="/api/health"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-brand-600 hover:text-brand-700"
          >
            View health endpoint
          </a>
        </div>
      </Card>

      {/* Module Status Grid */}
      <Card title="Module Status">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((mod) => {
            const isActive = mod.status === "Active";
            const content = (
              <div className="flex items-center justify-between w-full">
                <span className="text-sm font-medium text-gray-700">
                  {mod.name}
                </span>
                <div className="flex items-center gap-2">
                  <Badge variant={isActive ? "success" : "neutral"}>
                    {mod.status}
                  </Badge>
                  {isActive && (
                    <span className="text-gray-400 text-sm">&rarr;</span>
                  )}
                </div>
              </div>
            );

            if (isActive && mod.href) {
              return (
                <Link
                  key={mod.name}
                  href={mod.href}
                  className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3 hover:bg-gray-50 transition-colors"
                >
                  {content}
                </Link>
              );
            }

            return (
              <div
                key={mod.name}
                className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3 cursor-default"
                title="This module is in development"
              >
                {content}
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
