"use client";

import React from "react";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import type { Alert, AlertSeverity, AlertStatus } from "@/lib/api";

const severityConfig: Record<AlertSeverity, { variant: "error" | "warning" | "info" | "neutral"; label: string }> = {
  critical: { variant: "error", label: "Critical" },
  high: { variant: "warning", label: "High" },
  medium: { variant: "warning", label: "Medium" },
  low: { variant: "info", label: "Low" },
};

const statusConfig: Record<AlertStatus, { variant: "error" | "warning" | "success" | "neutral"; label: string }> = {
  new: { variant: "error", label: "New" },
  acknowledged: { variant: "warning", label: "Acknowledged" },
  resolved: { variant: "success", label: "Resolved" },
  dismissed: { variant: "neutral", label: "Dismissed" },
};

const severityBorder: Record<AlertSeverity, string> = {
  critical: "border-l-red-500",
  high: "border-l-orange-500",
  medium: "border-l-yellow-500",
  low: "border-l-blue-500",
};

interface AlertCardProps {
  alert: Alert;
  onAcknowledge: (id: string) => void;
  onResolve: (id: string) => void;
  onDismiss: (id: string) => void;
  isActioning?: boolean;
}

export default function AlertCard({
  alert,
  onAcknowledge,
  onResolve,
  onDismiss,
  isActioning = false,
}: AlertCardProps) {
  const sev = severityConfig[alert.severity];
  const stat = statusConfig[alert.status];
  const isTerminal = alert.status === "resolved" || alert.status === "dismissed";

  return (
    <div
      className={`rounded-lg border border-gray-200 border-l-4 ${severityBorder[alert.severity]} bg-white shadow-sm p-4 transition-colors hover:bg-gray-50`}
    >
      <div className="flex items-start justify-between gap-4">
        {/* Left: content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant={sev.variant}>{sev.label}</Badge>
            <Badge variant={stat.variant}>{stat.label}</Badge>
            {alert.severity === "critical" && alert.status === "new" && (
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
              </span>
            )}
          </div>
          <p className="text-sm font-medium text-gray-900 truncate">{alert.message}</p>
          <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
            <span>Source: {alert.source}</span>
            <span>{new Date(alert.created_at).toLocaleString()}</span>
          </div>
        </div>

        {/* Right: actions */}
        {!isTerminal && (
          <div className="flex items-center gap-1 flex-shrink-0">
            {alert.status === "new" && (
              <Button
                variant="ghost"
                size="sm"
                disabled={isActioning}
                onClick={() => onAcknowledge(alert.id)}
                title="Acknowledge"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              disabled={isActioning}
              onClick={() => onResolve(alert.id)}
              title="Resolve"
            >
              <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={isActioning}
              onClick={() => onDismiss(alert.id)}
              title="Dismiss"
            >
              <svg className="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
