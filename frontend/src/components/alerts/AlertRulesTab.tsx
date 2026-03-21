"use client";

import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import RuleBuilderModal from "./RuleBuilderModal";
import {
  listAL4Rules,
  deleteAL4Rule,
  duplicateAL4Rule,
  toggleAL4Rule,
  type AL4Rule,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const severityBadge: Record<
  AL4Rule["severity"],
  { variant: string; label: string }
> = {
  critical: { variant: "error", label: "Critical" },
  warning: { variant: "warning", label: "Warning" },
  info: { variant: "info", label: "Info" },
};

function conditionSummaryText(rule: AL4Rule): string {
  if (rule.conditions.length === 0) return "No conditions";
  const parts = rule.conditions.map((c) => {
    const opLabel =
      c.operator === "contains"
        ? "contains"
        : c.operator === "not_contains"
          ? "not contains"
          : c.operator;
    return `${c.field} ${opLabel} ${c.value}`;
  });
  return parts.join(` ${rule.logic_operator} `);
}

function channelIcons(rule: AL4Rule): React.ReactNode[] {
  const icons: React.ReactNode[] = [];

  if (rule.actions.email.enabled) {
    icons.push(
      <span
        key="email"
        title="Email"
        className="inline-flex items-center justify-center h-6 w-6 rounded bg-blue-100 text-blue-700"
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
          />
        </svg>
      </span>,
    );
  }

  if (rule.actions.slack.enabled) {
    icons.push(
      <span
        key="slack"
        title="Slack"
        className="inline-flex items-center justify-center h-6 w-6 rounded bg-purple-100 text-purple-700"
      >
        <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M5.042 15.165a2.528 2.528 0 01-2.52 2.523A2.528 2.528 0 010 15.165a2.527 2.527 0 012.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 012.521-2.52 2.527 2.527 0 012.521 2.52v6.313A2.528 2.528 0 018.834 24a2.528 2.528 0 01-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 01-2.521-2.52A2.528 2.528 0 018.834 0a2.528 2.528 0 012.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 012.521 2.521 2.528 2.528 0 01-2.521 2.521H2.522A2.528 2.528 0 010 8.834a2.528 2.528 0 012.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 012.522-2.521A2.528 2.528 0 0124 8.834a2.528 2.528 0 01-2.522 2.521h-2.522V8.834zm-1.27 0a2.528 2.528 0 01-2.523 2.521 2.527 2.527 0 01-2.52-2.521V2.522A2.527 2.527 0 0115.163 0a2.528 2.528 0 012.523 2.522v6.312zM15.163 18.956a2.528 2.528 0 012.523 2.522A2.528 2.528 0 0115.163 24a2.527 2.527 0 01-2.52-2.522v-2.522h2.52zm0-1.27a2.527 2.527 0 01-2.52-2.523 2.527 2.527 0 012.52-2.52h6.315A2.528 2.528 0 0124 15.163a2.528 2.528 0 01-2.522 2.523h-6.315z" />
        </svg>
      </span>,
    );
  }

  if (rule.actions.webhook.enabled) {
    icons.push(
      <span
        key="webhook"
        title="Webhook"
        className="inline-flex items-center justify-center h-6 w-6 rounded bg-green-100 text-green-700"
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
          />
        </svg>
      </span>,
    );
  }

  return icons;
}

// ---------------------------------------------------------------------------
// Toggle Switch
// ---------------------------------------------------------------------------

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (val: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
        checked ? "bg-brand-600" : "bg-gray-300"
      } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
          checked ? "translate-x-4" : "translate-x-1"
        }`}
      />
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function AlertRulesTab() {
  const queryClient = useQueryClient();
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AL4Rule | undefined>();

  // ---- Queries ----
  const {
    data: rules = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["al4-rules"],
    queryFn: listAL4Rules,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["al4-rules"] });

  // ---- Mutations ----
  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      toggleAL4Rule(id, enabled),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAL4Rule,
    onSuccess: invalidate,
  });

  const duplicateMutation = useMutation({
    mutationFn: duplicateAL4Rule,
    onSuccess: invalidate,
  });

  // ---- Handlers ----
  const openCreate = () => {
    setEditingRule(undefined);
    setBuilderOpen(true);
  };

  const openEdit = (rule: AL4Rule) => {
    setEditingRule(rule);
    setBuilderOpen(true);
  };

  const closeBuilder = () => {
    setBuilderOpen(false);
    setEditingRule(undefined);
  };

  const handleSaved = () => {
    invalidate();
    closeBuilder();
  };

  const handleDelete = (rule: AL4Rule) => {
    if (confirm(`Delete rule "${rule.name}"?`)) {
      deleteMutation.mutate(rule.id);
    }
  };

  // ---- Render ----
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Alert Rules</h2>
        <Button onClick={openCreate}>+ New Rule</Button>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load alert rules. Please try again.
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && rules.length === 0 && (
        <EmptyState
          title="No alert rules"
          description="Create your first alert rule to start monitoring."
          action={{ label: "+ New Rule", onClick: openCreate }}
        />
      )}

      {/* Rules list */}
      {!isLoading && !isError && rules.length > 0 && (
        <div className="space-y-3">
          {rules.map((rule) => {
            const sev = severityBadge[rule.severity];
            const icons = channelIcons(rule);

            return (
              <div
                key={rule.id}
                className="rounded-lg border border-gray-200 bg-white shadow-sm p-4 hover:shadow-md transition-shadow"
              >
                {/* Top row: name + toggle */}
                <div className="flex items-center justify-between gap-3 mb-2">
                  <div className="flex items-center gap-3 min-w-0">
                    <h3 className="text-sm font-semibold text-gray-900 truncate">
                      {rule.name}
                    </h3>
                    <Toggle
                      checked={rule.enabled}
                      disabled={toggleMutation.isPending}
                      onChange={(enabled) =>
                        toggleMutation.mutate({ id: rule.id, enabled })
                      }
                    />
                  </div>
                  <Badge variant={sev.variant}>{sev.label}</Badge>
                </div>

                {/* Condition summary */}
                <p className="text-xs text-gray-500 mb-2 truncate">
                  {conditionSummaryText(rule)}
                </p>

                {/* Bottom row: channels + trigger count + actions */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {/* Channel icons */}
                    <div className="flex items-center gap-1">{icons}</div>

                    {/* Trigger count */}
                    <span className="text-xs text-gray-400">
                      {rule.trigger_count} time{rule.trigger_count !== 1 ? "s" : ""} in{" "}
                      {rule.trigger_window_days} day
                      {rule.trigger_window_days !== 1 ? "s" : ""}
                    </span>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEdit(rule)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={duplicateMutation.isPending}
                      onClick={() => duplicateMutation.mutate(rule.id)}
                    >
                      Duplicate
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={deleteMutation.isPending}
                      onClick={() => handleDelete(rule)}
                    >
                      <span className="text-red-600">Delete</span>
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Rule Builder Modal */}
      <RuleBuilderModal
        isOpen={builderOpen}
        onClose={closeBuilder}
        onSaved={handleSaved}
        editingRule={editingRule}
      />
    </div>
  );
}
