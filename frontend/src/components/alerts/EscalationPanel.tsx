"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import { listEscalations, escalateAlert, type EscalationConfig } from "@/lib/api";

const DEFAULT_ESCALATION_CONFIG: EscalationConfig = {
  levels: [
    { after_minutes: 5, action: "notify_team_lead" },
    { after_minutes: 15, action: "notify_manager" },
    { after_minutes: 30, action: "page_oncall" },
  ],
};

export default function EscalationPanel() {
  const queryClient = useQueryClient();
  const [escalatingId, setEscalatingId] = useState<string | null>(null);

  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ["alert-escalations"],
    queryFn: listEscalations,
    refetchInterval: 30000,
  });

  const escalateMutation = useMutation({
    mutationFn: ({ alertId, config }: { alertId: string; config: EscalationConfig }) =>
      escalateAlert(alertId, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-escalations"] });
      setEscalatingId(null);
    },
  });

  const handleEscalate = (alertId: string) => {
    setEscalatingId(alertId);
    escalateMutation.mutate({ alertId, config: DEFAULT_ESCALATION_CONFIG });
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <EmptyState
        title="No escalations needed"
        description="All alerts are either acknowledged or within their initial response window."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Alerts Needing Escalation</h2>
        <Badge variant="warning">{alerts.length} pending</Badge>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Alert ID</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Severity</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Created</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Escalation Level</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {(alerts as Record<string, unknown>[]).map((alert) => {
              const payload = (alert.payload || {}) as Record<string, unknown>;
              const level = (payload.escalation_level as number) ?? -1;
              const sevVariant =
                alert.severity === "critical"
                  ? "danger"
                  : alert.severity === "high"
                    ? "warning"
                    : "info";

              return (
                <tr key={alert.id as string} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">
                    {(alert.id as string).slice(0, 8)}...
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={sevVariant as "danger" | "warning" | "info"}>
                      {(alert.severity as string).toUpperCase()}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{alert.status as string}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {new Date(alert.created_at as string).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    {level >= 0 ? (
                      <Badge variant="warning">Level {level}</Badge>
                    ) : (
                      <span className="text-gray-400">Not escalated</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      size="sm"
                      variant="primary"
                      loading={escalatingId === (alert.id as string)}
                      onClick={() => handleEscalate(alert.id as string)}
                    >
                      Escalate
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
