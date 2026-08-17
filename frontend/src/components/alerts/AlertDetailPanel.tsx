"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import type {
  Alert,
  AlertStatus,
  AlertSeverity,
  AlertHistoryEntry,
} from "@/lib/api";
import {
  patchAlertStatus,
  getAlertHistory,
  escalateAlert,
  type EscalationConfig,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Severity / status display configs (mirrors AlertCard conventions)
// ---------------------------------------------------------------------------

const severityConfig: Record<
  AlertSeverity,
  { variant: string; label: string }
> = {
  critical: { variant: "error", label: "Critical" },
  high: { variant: "warning", label: "High" },
  medium: { variant: "warning", label: "Medium" },
  low: { variant: "info", label: "Low" },
};

const statusConfig: Record<AlertStatus, { variant: string; label: string }> = {
  new: { variant: "error", label: "Firing" },
  acknowledged: { variant: "warning", label: "Acknowledged" },
  resolved: { variant: "success", label: "Resolved" },
  dismissed: { variant: "neutral", label: "Dismissed" },
};

// ---------------------------------------------------------------------------
// Escalation modal (inline)
// ---------------------------------------------------------------------------

interface EscalationModalProps {
  alertId: string;
  onClose: () => void;
  onSubmit: (alertId: string, assignee: string, note: string) => void;
  isSubmitting: boolean;
}

function EscalationModal({
  alertId,
  onClose,
  onSubmit,
  isSubmitting,
}: EscalationModalProps) {
  const [assignee, setAssignee] = useState("");
  const [note, setNote] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignee.trim()) return;
    onSubmit(alertId, assignee.trim(), note.trim());
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        role="presentation"
      />
      <div className="relative z-10 w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Escalate Alert
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="escalation-assignee"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Assignee <span className="text-red-500">*</span>
            </label>
            <input
              id="escalation-assignee"
              type="text"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              placeholder="e.g. ops-lead, jane.doe"
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
              autoFocus
            />
          </div>
          <div>
            <label
              htmlFor="escalation-note"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Note
            </label>
            <textarea
              id="escalation-note"
              rows={3}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              placeholder="Optional context for the assignee..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={!assignee.trim() || isSubmitting}
              loading={isSubmitting}
              className="bg-amber-500 hover:bg-amber-600 text-white border-transparent"
            >
              Escalate
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Evidence preview
// ---------------------------------------------------------------------------

interface EvidencePreviewProps {
  evidence: Alert["evidence"];
  alertId: string;
}

function EvidencePreview({ evidence, alertId }: EvidencePreviewProps) {
  if (!evidence || evidence.type === "none") {
    return (
      <p className="text-sm text-gray-400 italic">No evidence attached.</p>
    );
  }

  return (
    <div className="space-y-2">
      {evidence.type === "image" && evidence.thumbnail_url && (
        <img
          src={evidence.thumbnail_url}
          alt="Alert evidence thumbnail"
          className="w-full rounded-md border border-gray-200 object-cover max-h-48"
        />
      )}
      {evidence.type === "video" && evidence.url && (
        <video
          src={evidence.url}
          controls
          className="w-full rounded-md border border-gray-200 max-h-48"
        >
          <track kind="captions" />
        </video>
      )}
      <a
        href={`/investigate?alert=${alertId}`}
        className="inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-700"
      >
        <svg
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        Open in Investigate
      </a>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Alert history list
// ---------------------------------------------------------------------------

interface AlertHistoryListProps {
  ruleId: string;
}

function AlertHistoryList({ ruleId }: AlertHistoryListProps) {
  const { data: history = [], isLoading } = useQuery<AlertHistoryEntry[]>({
    queryKey: ["alert-history", ruleId],
    queryFn: () => getAlertHistory(ruleId),
    enabled: !!ruleId,
  });

  if (isLoading) {
    return <p className="text-xs text-gray-400">Loading history...</p>;
  }

  if (history.length === 0) {
    return (
      <p className="text-xs text-gray-400 italic">
        No prior triggers for this rule.
      </p>
    );
  }

  return (
    <ul className="space-y-1">
      {history.map((entry) => {
        const st = statusConfig[entry.status] ?? {
          variant: "neutral",
          label: entry.status,
        };
        return (
          <li
            key={entry.id}
            className="flex items-center justify-between text-xs text-gray-600"
          >
            <span>{new Date(entry.created_at).toLocaleString()}</span>
            <Badge variant={st.variant}>{st.label}</Badge>
          </li>
        );
      })}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

interface AlertDetailPanelProps {
  alert: Alert | null;
  isOpen: boolean;
  onClose: () => void;
  onStatusChange: (id: string, status: AlertStatus) => void;
}

// Stub case list — replace with real API when cases feature ships
const STUB_CASES = [
  { id: "case-1", name: "Case #1 — Camera outage" },
  { id: "case-2", name: "Case #2 — Suspicious activity" },
  { id: "case-3", name: "Case #3 — Equipment failure" },
];

export default function AlertDetailPanel({
  alert,
  isOpen,
  onClose,
  onStatusChange,
}: AlertDetailPanelProps) {
  const queryClient = useQueryClient();
  const panelRef = useRef<HTMLDivElement>(null);
  const [showEscalationModal, setShowEscalationModal] = useState(false);
  const [caseDropdownOpen, setCaseDropdownOpen] = useState(false);

  // ---- Body scroll lock ----
  useEffect(() => {
    if (!isOpen) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [isOpen]);

  // ---- Escape key handler ----
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (showEscalationModal) {
          setShowEscalationModal(false);
        } else {
          onClose();
        }
      }
    },
    [onClose, showEscalationModal],
  );

  useEffect(() => {
    if (!isOpen) return;
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleKeyDown]);

  // ---- Mutations ----
  const acknowledgeMutation = useMutation({
    mutationFn: (id: string) => patchAlertStatus(id, "acknowledged"),
    onSuccess: (data) => {
      onStatusChange(data.id, data.status);
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const escalateMutation = useMutation({
    mutationFn: ({
      alertId,
      config,
    }: {
      alertId: string;
      config: EscalationConfig;
    }) => escalateAlert(alertId, config),
    onSuccess: () => {
      setShowEscalationModal(false);
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const dismissMutation = useMutation({
    mutationFn: (id: string) => patchAlertStatus(id, "dismissed"),
    onSuccess: (data) => {
      onStatusChange(data.id, data.status);
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  // ---- Handlers ----
  const handleAcknowledge = () => {
    if (alert) acknowledgeMutation.mutate(alert.id);
  };

  const handleEscalate = (
    alertId: string,
    assignee: string,
    note: string,
  ) => {
    escalateMutation.mutate({
      alertId,
      config: {
        levels: [
          {
            after_minutes: 0,
            action: `assign:${assignee}${note ? ` | note:${note}` : ""}`,
          },
        ],
      },
    });
  };

  const handleDismiss = () => {
    if (alert) dismissMutation.mutate(alert.id);
  };

  const handleAddToCase = (caseId: string) => {
    // TODO: Wire to real case association API when available
    setCaseDropdownOpen(false);
    console.info(`[AlertDetailPanel] Add alert ${alert?.id} to case ${caseId}`);
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // ---- Render ----
  if (!alert) return null;

  const sev = severityConfig[alert.severity];
  const stat = statusConfig[alert.status];
  const isActioning =
    acknowledgeMutation.isPending ||
    escalateMutation.isPending ||
    dismissMutation.isPending;

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/30 transition-opacity duration-300 ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={handleBackdropClick}
        role="presentation"
      />

      {/* Slide-over panel */}
      <div
        ref={panelRef}
        className={`fixed inset-y-0 right-0 z-50 flex w-[400px] max-w-full flex-col bg-white shadow-2xl transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
        role="dialog"
        aria-modal="true"
        aria-label="Alert details"
      >
        {/* ========== A. Header ========== */}
        <div className="flex items-start justify-between gap-3 border-b border-gray-200 px-5 py-4">
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={sev.variant}>{sev.label}</Badge>
              <Badge variant={stat.variant}>{stat.label}</Badge>
            </div>
            <p className="text-sm font-semibold text-gray-900 break-words">
              {alert.message}
            </p>
            <p className="text-xs text-gray-500">
              {new Date(alert.created_at).toLocaleString()}
            </p>
          </div>
          <button
            type="button"
            className="mt-1 rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            onClick={onClose}
            aria-label="Close panel"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
          {/* ========== B. Context ========== */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              Context
            </h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Rule</dt>
                <dd className="font-medium text-gray-900 text-right">
                  {alert.rule_name ?? alert.rule_id.slice(0, 12)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Threshold</dt>
                <dd className="font-medium text-gray-900">
                  {alert.threshold}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Metric value</dt>
                <dd className="font-medium text-gray-900">
                  {alert.metric_value}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Source</dt>
                <dd className="font-medium text-gray-900">
                  {alert.source ?? "\u2014"}
                </dd>
              </div>
            </dl>
          </section>

          {/* ========== C. Evidence preview ========== */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              Evidence
            </h3>
            <EvidencePreview evidence={alert.evidence} alertId={alert.id} />
          </section>

          {/* ========== D. Actions ========== */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
              Actions
            </h3>
            <div className="flex flex-wrap gap-2">
              {/* Acknowledge */}
              <Button
                size="sm"
                disabled={
                  isActioning || alert.status === "acknowledged"
                }
                loading={acknowledgeMutation.isPending}
                onClick={handleAcknowledge}
                className="bg-green-600 hover:bg-green-700 text-white border-transparent"
              >
                Acknowledge
              </Button>

              {/* Escalate */}
              <Button
                size="sm"
                disabled={isActioning}
                onClick={() => setShowEscalationModal(true)}
                className="bg-amber-500 hover:bg-amber-600 text-white border-transparent"
              >
                Escalate
              </Button>

              {/* Dismiss */}
              <Button
                size="sm"
                variant="secondary"
                disabled={
                  isActioning || alert.status === "dismissed"
                }
                loading={dismissMutation.isPending}
                onClick={handleDismiss}
              >
                Dismiss
              </Button>

              {/* Add to Case dropdown */}
              <div className="relative">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={isActioning}
                  onClick={() => setCaseDropdownOpen((prev) => !prev)}
                >
                  Add to Case &#9662;
                </Button>
                {caseDropdownOpen && (
                  <div className="absolute left-0 top-full mt-1 z-10 w-56 rounded-md border border-gray-200 bg-white py-1 shadow-lg">
                    {STUB_CASES.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        className="block w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
                        onClick={() => handleAddToCase(c.id)}
                      >
                        {c.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* ========== E. Alert history ========== */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              Rule History (last 5)
            </h3>
            <AlertHistoryList ruleId={alert.rule_id} />
          </section>
        </div>
      </div>

      {/* Escalation modal */}
      {showEscalationModal && (
        <EscalationModal
          alertId={alert.id}
          onClose={() => setShowEscalationModal(false)}
          onSubmit={handleEscalate}
          isSubmitting={escalateMutation.isPending}
        />
      )}
    </>
  );
}
