"use client";

import Link from "next/link";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import StatusIndicator from "@/components/ui/StatusIndicator";
import EmptyState from "@/components/ui/EmptyState";

const stats = [
  { icon: "\uD83D\uDCF9", label: "Active Streams", value: 0, trend: "+0%" },
  { icon: "\uD83E\uDD16", label: "Models in Production", value: 0, trend: "+0%" },
  { icon: "\uD83D\uDD14", label: "Open Alerts", value: 0, trend: "0" },
  { icon: "\uD83D\uDCC1", label: "Total Assets", value: 0, trend: "+0" },
];

const quickActions = [
  { icon: "\uD83D\uDCF9", label: "Start Capture", href: "/capture" },
  { icon: "\uD83D\uDCC2", label: "Upload Media", href: "/assets" },
  { icon: "\u2699\uFE0F", label: "Build Pipeline", href: "/pipeline" },
  { icon: "\uD83E\uDD16", label: "Ask Copilot", href: "/agents" },
];

const modules = [
  { name: "Capture", status: "Active" },
  { name: "Vision", status: "Active" },
  { name: "Audio", status: "Active" },
  { name: "Transform", status: "Active" },
  { name: "Train", status: "Coming Soon" },
  { name: "Validate", status: "Coming Soon" },
  { name: "Search", status: "Active" },
  { name: "Alerts", status: "Active" },
  { name: "Pipeline", status: "Active" },
  { name: "Investigate", status: "Coming Soon" },
  { name: "Agents", status: "Coming Soon" },
  { name: "Assets", status: "Active" },
  { name: "Evaluation", status: "Coming Soon" },
  { name: "Settings", status: "Active" },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Overview of your VisionAudioForge workspace
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <div className="flex items-center gap-4">
              <span className="text-3xl">{stat.icon}</span>
              <div>
                <p className="text-sm text-gray-500">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                <p className="text-xs text-gray-400">{stat.trend}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Recent Activity + Quick Actions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Activity */}
        <Card title="Recent Activity">
          <EmptyState
            icon={<span className="text-2xl">{"\uD83D\uDCCB"}</span>}
            title="No recent activity"
            description="Activity from your workspace will appear here."
          />
        </Card>

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
          {modules.map((mod) => (
            <div
              key={mod.name}
              className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3"
            >
              <span className="text-sm font-medium text-gray-700">
                {mod.name}
              </span>
              <Badge
                variant={mod.status === "Active" ? "success" : "neutral"}
              >
                {mod.status}
              </Badge>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
