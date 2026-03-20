"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AlertCard from "./AlertCard";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import Button from "@/components/ui/Button";
import {
  listAlerts,
  acknowledgeAlert,
  resolveAlert,
  dismissAlert,
  type Alert,
  type AlertFilters,
  type AlertSeverity,
  type AlertStatus,
} from "@/lib/api";

const SEVERITY_ORDER: Record<AlertSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function sortAlerts(alerts: Alert[]): Alert[] {
  return [...alerts].sort((a, b) => {
    const sevDiff = SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
    if (sevDiff !== 0) return sevDiff;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

export default function AlertInbox() {
  const queryClient = useQueryClient();
  const prevCountRef = useRef(0);

  const [filters, setFilters] = useState<AlertFilters>({});
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  const buildFilters = useCallback((): AlertFilters => {
    const f: AlertFilters = {};
    if (severityFilter) f.severity = severityFilter as AlertSeverity;
    if (statusFilter) f.status = statusFilter as AlertStatus;
    if (startDate) f.start_date = startDate;
    if (endDate) f.end_date = endDate;
    return f;
  }, [severityFilter, statusFilter, startDate, endDate]);

  useEffect(() => {
    setFilters(buildFilters());
  }, [buildFilters]);

  const { data: alerts = [], isLoading, isError } = useQuery({
    queryKey: ["alerts", filters],
    queryFn: () => listAlerts(filters),
    refetchInterval: 30_000,
  });

  // Sound/visual indicator for new critical alerts
  useEffect(() => {
    if (!alerts.length) return;
    const criticalNew = alerts.filter((a) => a.severity === "critical" && a.status === "new").length;
    if (criticalNew > prevCountRef.current && prevCountRef.current !== 0) {
      // Play a subtle notification sound for new critical alerts
      try {
        const ctx = new AudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 880;
        osc.type = "sine";
        gain.gain.value = 0.15;
        osc.start();
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
        osc.stop(ctx.currentTime + 0.5);
      } catch {
        // Audio not available
      }
    }
    prevCountRef.current = criticalNew;
  }, [alerts]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["alerts"] });

  const ackMutation = useMutation({ mutationFn: acknowledgeAlert, onSuccess: invalidate });
  const resolveMutation = useMutation({ mutationFn: resolveAlert, onSuccess: invalidate });
  const dismissMutation = useMutation({ mutationFn: dismissAlert, onSuccess: invalidate });

  const isActioning = ackMutation.isPending || resolveMutation.isPending || dismissMutation.isPending;

  const sorted = sortAlerts(alerts);

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-gray-200 bg-white p-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Severity</label>
          <select
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="">All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
          <select
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All</option>
            <option value="new">New</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">From</label>
          <input
            type="date"
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">To</label>
          <input
            type="date"
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setSeverityFilter("");
            setStatusFilter("");
            setStartDate("");
            setEndDate("");
          }}
        >
          Clear filters
        </Button>
      </div>

      {/* Alert list */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load alerts. Please try again.
        </div>
      )}

      {!isLoading && !isError && sorted.length === 0 && (
        <EmptyState
          title="No alerts"
          description="No alerts match the current filters."
        />
      )}

      <div className="space-y-2 max-h-[calc(100vh-320px)] overflow-y-auto pr-1">
        {sorted.map((alert) => (
          <AlertCard
            key={alert.id}
            alert={alert}
            onAcknowledge={(id) => ackMutation.mutate(id)}
            onResolve={(id) => resolveMutation.mutate(id)}
            onDismiss={(id) => dismissMutation.mutate(id)}
            isActioning={isActioning}
          />
        ))}
      </div>
    </div>
  );
}
