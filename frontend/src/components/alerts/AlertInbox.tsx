"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AlertCard from "./AlertCard";
import AlertFilterBar from "./AlertFilterBar";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
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

function sortAlerts(alerts: Alert[] | undefined | null): Alert[] {
  const safeAlerts = alerts ?? [];
  return [...safeAlerts].sort((a, b) => {
    const sevDiff = SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
    if (sevDiff !== 0) return sevDiff;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

export default function AlertInbox() {
  const queryClient = useQueryClient();
  const prevCountRef = useRef(0);

  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const filters = useMemo((): AlertFilters => {
    const f: AlertFilters = {};
    if (severityFilter) f.severity = severityFilter as AlertSeverity;
    if (statusFilter) f.status = statusFilter as AlertStatus;
    if (startDate) f.start_date = startDate;
    if (endDate) f.end_date = endDate;
    if (searchQuery) f.search = searchQuery;
    return f;
  }, [severityFilter, statusFilter, startDate, endDate, searchQuery]);

  const { data: alertsResponse, isLoading, isError } = useQuery({
    queryKey: ["alerts", filters],
    queryFn: () => listAlerts(filters),
    refetchInterval: 30_000,
  });

  const alerts: Alert[] = alertsResponse?.items ?? [];

  // Sound/visual indicator for new critical alerts
  useEffect(() => {
    if (!alerts.length) return;
    const criticalNew = alerts.filter(
      (a) => a.severity === "critical" && a.status === "new",
    ).length;
    if (criticalNew > prevCountRef.current && prevCountRef.current !== 0) {
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

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["alerts"] });
    queryClient.invalidateQueries({ queryKey: ["alert-stats-summary"] });
  };

  const ackMutation = useMutation({ mutationFn: acknowledgeAlert, onSuccess: invalidate });
  const resolveMutation = useMutation({ mutationFn: resolveAlert, onSuccess: invalidate });
  const dismissMutation = useMutation({ mutationFn: dismissAlert, onSuccess: invalidate });

  const isActioning = ackMutation.isPending || resolveMutation.isPending || dismissMutation.isPending;

  const sorted = sortAlerts(alerts);

  const allSelected = sorted.length > 0 && selectedIds.size === sorted.length;

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(sorted.map((a) => a.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleBulkAcknowledge = () => {
    selectedIds.forEach((id) => ackMutation.mutate(id));
    setSelectedIds(new Set());
  };

  const handleBulkDismiss = () => {
    selectedIds.forEach((id) => dismissMutation.mutate(id));
    setSelectedIds(new Set());
  };

  const handleClearFilters = () => {
    setSeverityFilter("");
    setStatusFilter("");
    setStartDate("");
    setEndDate("");
    setSearchQuery("");
    setSelectedIds(new Set());
  };

  return (
    <div className="space-y-4">
      <AlertFilterBar
        severityFilter={severityFilter}
        statusFilter={statusFilter}
        startDate={startDate}
        endDate={endDate}
        searchQuery={searchQuery}
        selectedCount={selectedIds.size}
        totalCount={sorted.length}
        allSelected={allSelected}
        onSeverityChange={setSeverityFilter}
        onStatusChange={setStatusFilter}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
        onSearchChange={setSearchQuery}
        onSelectAll={handleSelectAll}
        onBulkAcknowledge={handleBulkAcknowledge}
        onBulkDismiss={handleBulkDismiss}
        onClearFilters={handleClearFilters}
      />

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

      <div className="space-y-2 max-h-[calc(100vh-420px)] overflow-y-auto pr-1">
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
