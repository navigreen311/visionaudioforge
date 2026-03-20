"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Modal from "@/components/ui/Modal";
import EmptyState from "@/components/ui/EmptyState";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Badge from "@/components/ui/Badge";
import {
  listRules,
  createRule,
  updateRule,
  deleteRule,
  type AlertRule,
  type AlertRuleCondition,
  type AlertRuleAction,
  type AlertRuleCreatePayload,
} from "@/lib/api";

const METRICS = [
  "cpu_usage",
  "memory_usage",
  "disk_usage",
  "error_rate",
  "latency_p99",
  "request_count",
  "gpu_utilization",
  "inference_time",
];

const OPERATORS: { value: AlertRuleCondition["operator"]; label: string }[] = [
  { value: ">", label: "> (greater than)" },
  { value: "<", label: "< (less than)" },
  { value: "==", label: "== (equals)" },
  { value: "!=", label: "!= (not equals)" },
];

const ACTION_TYPES: AlertRuleAction["type"][] = ["webhook", "email", "slack", "log"];

const actionPlaceholders: Record<AlertRuleAction["type"], string> = {
  webhook: "https://example.com/webhook",
  email: "alerts@example.com",
  slack: "https://hooks.slack.com/services/...",
  log: "alert.log",
};

function emptyCondition(): AlertRuleCondition {
  return { metric: METRICS[0], operator: ">", threshold: 0, window_seconds: 60 };
}

function emptyAction(): AlertRuleAction {
  return { type: "log", target: "" };
}

interface RuleFormState {
  name: string;
  conditions: AlertRuleCondition[];
  actions: AlertRuleAction[];
  enabled: boolean;
}

function initialForm(rule?: AlertRule): RuleFormState {
  if (rule) {
    return {
      name: rule.name,
      conditions: rule.conditions.length ? [...rule.conditions] : [emptyCondition()],
      actions: rule.actions.length ? [...rule.actions] : [emptyAction()],
      enabled: rule.enabled,
    };
  }
  return { name: "", conditions: [emptyCondition()], actions: [emptyAction()], enabled: true };
}

function conditionSummary(conditions: AlertRuleCondition[]): string {
  return conditions.map((c) => `${c.metric} ${c.operator} ${c.threshold} (${c.window_seconds}s)`).join(", ");
}

function actionsSummary(actions: AlertRuleAction[]): string {
  return actions.map((a) => a.type).join(", ");
}

export default function RuleBuilder() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | undefined>();
  const [form, setForm] = useState<RuleFormState>(initialForm());

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["alert-rules"],
    queryFn: listRules,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["alert-rules"] });

  const createMutation = useMutation({ mutationFn: (p: AlertRuleCreatePayload) => createRule(p), onSuccess: () => { invalidate(); closeModal(); } });
  const updateMutation = useMutation({ mutationFn: ({ id, payload }: { id: string; payload: Partial<AlertRuleCreatePayload> }) => updateRule(id, payload), onSuccess: () => { invalidate(); closeModal(); } });
  const deleteMutation = useMutation({ mutationFn: deleteRule, onSuccess: invalidate });
  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => updateRule(id, { enabled }),
    onSuccess: invalidate,
  });

  const openCreate = () => {
    setEditingRule(undefined);
    setForm(initialForm());
    setModalOpen(true);
  };

  const openEdit = (rule: AlertRule) => {
    setEditingRule(rule);
    setForm(initialForm(rule));
    setModalOpen(true);
  };

  const closeModal = useCallback(() => {
    setModalOpen(false);
    setEditingRule(undefined);
  }, []);

  const handleSave = () => {
    const payload: AlertRuleCreatePayload = {
      name: form.name,
      conditions: form.conditions,
      actions: form.actions,
      enabled: form.enabled,
    };
    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const updateCondition = (idx: number, partial: Partial<AlertRuleCondition>) => {
    setForm((prev) => {
      const conditions = [...prev.conditions];
      conditions[idx] = { ...conditions[idx], ...partial };
      return { ...prev, conditions };
    });
  };

  const removeCondition = (idx: number) => {
    setForm((prev) => ({
      ...prev,
      conditions: prev.conditions.filter((_, i) => i !== idx),
    }));
  };

  const updateAction = (idx: number, partial: Partial<AlertRuleAction>) => {
    setForm((prev) => {
      const actions = [...prev.actions];
      actions[idx] = { ...actions[idx], ...partial };
      return { ...prev, actions };
    });
  };

  const removeAction = (idx: number) => {
    setForm((prev) => ({
      ...prev,
      actions: prev.actions.filter((_, i) => i !== idx),
    }));
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Alert Rules</h2>
        <Button onClick={openCreate}>Create Rule</Button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {!isLoading && rules.length === 0 && (
        <EmptyState
          title="No rules configured"
          description="Create an alert rule to start monitoring."
          action={{ label: "Create Rule", onClick: openCreate }}
        />
      )}

      {!isLoading && rules.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Name</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Conditions</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Actions</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">Enabled</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{rule.name}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">
                    {conditionSummary(rule.conditions)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {rule.actions.map((a, i) => (
                        <Badge key={i} variant="info">{a.type}</Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => toggleMutation.mutate({ id: rule.id, enabled: !rule.enabled })}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                        rule.enabled ? "bg-brand-600" : "bg-gray-300"
                      }`}
                    >
                      <span
                        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                          rule.enabled ? "translate-x-4" : "translate-x-1"
                        }`}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(rule)}>
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          if (confirm("Delete this rule?")) deleteMutation.mutate(rule.id);
                        }}
                      >
                        <span className="text-red-600">Delete</span>
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={closeModal}
        title={editingRule ? "Edit Rule" : "Create Rule"}
        footer={
          <>
            <Button variant="secondary" onClick={closeModal}>
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              loading={isSaving}
              disabled={!form.name.trim() || form.conditions.length === 0}
            >
              {editingRule ? "Update" : "Create"}
            </Button>
          </>
        }
      >
        <div className="space-y-5 max-h-[60vh] overflow-y-auto">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rule Name</label>
            <input
              type="text"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              placeholder="e.g. High CPU Alert"
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            />
          </div>

          {/* Conditions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">Conditions</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setForm((p) => ({ ...p, conditions: [...p.conditions, emptyCondition()] }))}
              >
                + Add Condition
              </Button>
            </div>
            <div className="space-y-2">
              {form.conditions.map((cond, idx) => (
                <div key={idx} className="flex items-center gap-2 rounded border border-gray-200 p-2 bg-gray-50">
                  <select
                    className="rounded border border-gray-300 px-2 py-1 text-sm flex-1"
                    value={cond.metric}
                    onChange={(e) => updateCondition(idx, { metric: e.target.value })}
                  >
                    {METRICS.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                  <select
                    className="rounded border border-gray-300 px-2 py-1 text-sm w-28"
                    value={cond.operator}
                    onChange={(e) => updateCondition(idx, { operator: e.target.value as AlertRuleCondition["operator"] })}
                  >
                    {OPERATORS.map((op) => (
                      <option key={op.value} value={op.value}>{op.label}</option>
                    ))}
                  </select>
                  <input
                    type="number"
                    className="rounded border border-gray-300 px-2 py-1 text-sm w-20"
                    placeholder="Value"
                    value={cond.threshold}
                    onChange={(e) => updateCondition(idx, { threshold: parseFloat(e.target.value) || 0 })}
                  />
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      className="rounded border border-gray-300 px-2 py-1 text-sm w-16"
                      placeholder="Window"
                      value={cond.window_seconds}
                      onChange={(e) => updateCondition(idx, { window_seconds: parseInt(e.target.value) || 60 })}
                    />
                    <span className="text-xs text-gray-500">sec</span>
                  </div>
                  {form.conditions.length > 1 && (
                    <button
                      onClick={() => removeCondition(idx)}
                      className="text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">Actions</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setForm((p) => ({ ...p, actions: [...p.actions, emptyAction()] }))}
              >
                + Add Action
              </Button>
            </div>
            <div className="space-y-2">
              {form.actions.map((action, idx) => (
                <div key={idx} className="flex items-center gap-2 rounded border border-gray-200 p-2 bg-gray-50">
                  <select
                    className="rounded border border-gray-300 px-2 py-1 text-sm w-28"
                    value={action.type}
                    onChange={(e) => updateAction(idx, { type: e.target.value as AlertRuleAction["type"] })}
                  >
                    {ACTION_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                  <input
                    type="text"
                    className="rounded border border-gray-300 px-2 py-1 text-sm flex-1"
                    placeholder={actionPlaceholders[action.type]}
                    value={action.target}
                    onChange={(e) => updateAction(idx, { target: e.target.value })}
                  />
                  {form.actions.length > 1 && (
                    <button
                      onClick={() => removeAction(idx)}
                      className="text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Enabled toggle */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700">Enabled</label>
            <button
              type="button"
              onClick={() => setForm((p) => ({ ...p, enabled: !p.enabled }))}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                form.enabled ? "bg-brand-600" : "bg-gray-300"
              }`}
            >
              <span
                className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                  form.enabled ? "translate-x-4" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
