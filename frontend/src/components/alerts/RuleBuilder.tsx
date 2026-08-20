"use client";

import React, { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import EmptyState from "@/components/ui/EmptyState";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import Badge from "@/components/ui/Badge";
import {
  listRules,
  createRule,
  updateRule,
  deleteRule,
  testDeliveryChannel,
  type AlertRule,
  type AlertRuleCondition,
  type AlertRuleAction,
  type AlertRuleCreatePayload,
  type EscalationLevel,
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
  "motion_score",
  "noise_level",
];

const OPERATORS: { value: AlertRuleCondition["operator"]; label: string }[] = [
  { value: ">", label: "> (greater than)" },
  { value: "<", label: "< (less than)" },
  { value: "==", label: "== (equals)" },
  { value: "!=", label: "!= (not equals)" },
];

const ACTION_TYPES: AlertRuleAction["type"][] = ["webhook", "email", "slack", "discord", "sms", "log"];

const actionPlaceholders: Record<AlertRuleAction["type"], string> = {
  webhook: "https://example.com/webhook",
  email: "alerts@example.com",
  slack: "https://hooks.slack.com/services/...",
  discord: "https://discord.com/api/webhooks/...",
  sms: "+1234567890",
  log: "alert.log",
};

type ConditionType = "threshold" | "compound" | "temporal" | "cross_modal";
type CompoundOperator = "AND" | "OR";

interface CompoundConditionGroup {
  id: string;
  type: ConditionType;
  operator?: CompoundOperator;
  // Threshold fields
  metric?: string;
  thresholdOperator?: AlertRuleCondition["operator"];
  thresholdValue?: number;
  // Temporal fields
  windowSeconds?: number;
  minOccurrences?: number;
  // Cross-modal fields
  requireBoth?: boolean;
  // Children (for compound)
  children?: CompoundConditionGroup[];
}

function generateId(): string {
  return Math.random().toString(36).substring(2, 9);
}

function emptyThresholdGroup(): CompoundConditionGroup {
  return {
    id: generateId(),
    type: "threshold",
    metric: METRICS[0],
    thresholdOperator: ">",
    thresholdValue: 0,
  };
}

function emptyCompoundGroup(): CompoundConditionGroup {
  return {
    id: generateId(),
    type: "compound",
    operator: "AND",
    children: [emptyThresholdGroup(), emptyThresholdGroup()],
  };
}

function emptyTemporalGroup(): CompoundConditionGroup {
  return {
    id: generateId(),
    type: "temporal",
    metric: METRICS[0],
    thresholdOperator: ">",
    thresholdValue: 0,
    windowSeconds: 60,
    minOccurrences: 3,
  };
}

function emptyCrossModalGroup(): CompoundConditionGroup {
  return {
    id: generateId(),
    type: "cross_modal",
    requireBoth: true,
    children: [
      { ...emptyThresholdGroup(), metric: "motion_score" },
      { ...emptyThresholdGroup(), metric: "noise_level" },
    ],
  };
}

function emptyAction(): AlertRuleAction {
  return { type: "log", target: "" };
}

function groupToApiCondition(group: CompoundConditionGroup): Record<string, unknown> {
  if (group.type === "threshold") {
    return {
      type: "threshold",
      metric: group.metric,
      operator: group.thresholdOperator,
      value: group.thresholdValue,
    };
  }
  if (group.type === "compound") {
    return {
      type: "compound",
      operator: group.operator,
      conditions: (group.children || []).map(groupToApiCondition),
    };
  }
  if (group.type === "temporal") {
    return {
      type: "temporal",
      condition: {
        type: "threshold",
        metric: group.metric,
        operator: group.thresholdOperator,
        value: group.thresholdValue,
      },
      window_seconds: group.windowSeconds,
      min_occurrences: group.minOccurrences,
    };
  }
  if (group.type === "cross_modal") {
    const children = group.children || [];
    return {
      type: "cross_modal",
      vision_condition: children[0] ? groupToApiCondition(children[0]) : {},
      audio_condition: children[1] ? groupToApiCondition(children[1]) : {},
      require_both: group.requireBoth,
    };
  }
  return {};
}

interface RuleFormState {
  name: string;
  conditionType: ConditionType;
  conditionGroup: CompoundConditionGroup;
  actions: AlertRuleAction[];
  enabled: boolean;
  escalationLevels: EscalationLevel[];
}

function initialForm(rule?: AlertRule): RuleFormState {
  if (rule) {
    return {
      name: rule.name,
      conditionType: "threshold",
      conditionGroup: emptyThresholdGroup(),
      actions: rule.actions.length ? [...rule.actions] : [emptyAction()],
      enabled: rule.enabled,
      escalationLevels: [],
    };
  }
  return {
    name: "",
    conditionType: "threshold",
    conditionGroup: emptyThresholdGroup(),
    actions: [emptyAction()],
    enabled: true,
    escalationLevels: [],
  };
}

function conditionSummary(conditions: AlertRuleCondition[] | Record<string, unknown>): string {
  if (Array.isArray(conditions)) {
    return conditions.map((c) => `${c.metric} ${c.operator} ${c.threshold}`).join(", ");
  }
  const cond = conditions as Record<string, unknown>;
  if (cond.type === "compound") {
    return `${cond.operator} compound (${((cond.conditions as unknown[]) || []).length} sub-conditions)`;
  }
  if (cond.type === "temporal") {
    return `temporal: ${(cond as Record<string, unknown>).min_occurrences}x in ${(cond as Record<string, unknown>).window_seconds}s`;
  }
  if (cond.type === "cross_modal") {
    return `cross-modal (${(cond as Record<string, unknown>).require_both ? "AND" : "OR"})`;
  }
  return `${cond.metric} ${cond.operator} ${cond.value}`;
}

function actionsSummary(actions: AlertRuleAction[]): string {
  return actions.map((a) => a.type).join(", ");
}

// ---------------------------------------------------------------------------
// Condition Editor sub-component
// ---------------------------------------------------------------------------

function ConditionEditor({
  group,
  onChange,
  onRemove,
  depth = 0,
}: {
  group: CompoundConditionGroup;
  onChange: (updated: CompoundConditionGroup) => void;
  onRemove?: () => void;
  depth?: number;
}) {
  const borderColor = depth === 0 ? "border-gray-200" : depth === 1 ? "border-blue-200" : "border-purple-200";
  const bgColor = depth === 0 ? "bg-gray-50" : depth === 1 ? "bg-blue-50" : "bg-purple-50";

  if (group.type === "threshold") {
    return (
      <div className={`flex items-center gap-2 rounded border ${borderColor} p-2 ${bgColor}`}>
        <select
          className="rounded border border-gray-300 px-2 py-1 text-sm flex-1"
          value={group.metric}
          onChange={(e) => onChange({ ...group, metric: e.target.value })}
        >
          {METRICS.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select
          className="rounded border border-gray-300 px-2 py-1 text-sm w-28"
          value={group.thresholdOperator}
          onChange={(e) => onChange({ ...group, thresholdOperator: e.target.value as AlertRuleCondition["operator"] })}
        >
          {OPERATORS.map((op) => (
            <option key={op.value} value={op.value}>{op.label}</option>
          ))}
        </select>
        <input
          type="number"
          className="rounded border border-gray-300 px-2 py-1 text-sm w-20"
          placeholder="Value"
          value={group.thresholdValue ?? 0}
          onChange={(e) => onChange({ ...group, thresholdValue: parseFloat(e.target.value) || 0 })}
        />
        {onRemove && (
          <button onClick={onRemove} className="text-gray-400 hover:text-red-500 transition-colors">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    );
  }

  if (group.type === "compound") {
    return (
      <div className={`rounded border-2 ${borderColor} p-3 ${bgColor} space-y-2`}>
        <div className="flex items-center gap-2 mb-2">
          <Badge variant={group.operator === "AND" ? "warning" : "info"}>
            {group.operator}
          </Badge>
          <select
            className="rounded border border-gray-300 px-2 py-1 text-sm"
            value={group.operator}
            onChange={(e) => onChange({ ...group, operator: e.target.value as CompoundOperator })}
          >
            <option value="AND">AND (all must match)</option>
            <option value="OR">OR (any can match)</option>
          </select>
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              onChange({
                ...group,
                children: [...(group.children || []), emptyThresholdGroup()],
              })
            }
          >
            + Add Condition
          </Button>
          {onRemove && (
            <button onClick={onRemove} className="ml-auto text-gray-400 hover:text-red-500">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
        {(group.children || []).map((child, idx) => (
          <ConditionEditor
            key={child.id}
            group={child}
            depth={depth + 1}
            onChange={(updated) => {
              const newChildren = [...(group.children || [])];
              newChildren[idx] = updated;
              onChange({ ...group, children: newChildren });
            }}
            onRemove={
              (group.children || []).length > 2
                ? () => {
                    onChange({
                      ...group,
                      children: (group.children || []).filter((_, i) => i !== idx),
                    });
                  }
                : undefined
            }
          />
        ))}
      </div>
    );
  }

  if (group.type === "temporal") {
    return (
      <div className={`rounded border-2 border-amber-200 p-3 bg-amber-50 space-y-2`}>
        <div className="flex items-center gap-2 mb-1">
          <Badge variant="warning">Temporal</Badge>
          <span className="text-sm text-gray-600">Trigger if condition fires</span>
          <input
            type="number"
            className="rounded border border-gray-300 px-2 py-1 text-sm w-16"
            value={group.minOccurrences ?? 3}
            onChange={(e) => onChange({ ...group, minOccurrences: parseInt(e.target.value) || 1 })}
          />
          <span className="text-sm text-gray-600">times within</span>
          <input
            type="number"
            className="rounded border border-gray-300 px-2 py-1 text-sm w-16"
            value={group.windowSeconds ?? 60}
            onChange={(e) => onChange({ ...group, windowSeconds: parseInt(e.target.value) || 10 })}
          />
          <span className="text-sm text-gray-600">seconds</span>
          {onRemove && (
            <button onClick={onRemove} className="ml-auto text-gray-400 hover:text-red-500">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select
            className="rounded border border-gray-300 px-2 py-1 text-sm flex-1"
            value={group.metric}
            onChange={(e) => onChange({ ...group, metric: e.target.value })}
          >
            {METRICS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <select
            className="rounded border border-gray-300 px-2 py-1 text-sm w-28"
            value={group.thresholdOperator}
            onChange={(e) => onChange({ ...group, thresholdOperator: e.target.value as AlertRuleCondition["operator"] })}
          >
            {OPERATORS.map((op) => (
              <option key={op.value} value={op.value}>{op.label}</option>
            ))}
          </select>
          <input
            type="number"
            className="rounded border border-gray-300 px-2 py-1 text-sm w-20"
            value={group.thresholdValue ?? 0}
            onChange={(e) => onChange({ ...group, thresholdValue: parseFloat(e.target.value) || 0 })}
          />
        </div>
      </div>
    );
  }

  // cross_modal
  return (
    <div className={`rounded border-2 border-green-200 p-3 bg-green-50 space-y-2`}>
      <div className="flex items-center gap-2 mb-1">
        <Badge variant="success">Cross-Modal</Badge>
        <select
          className="rounded border border-gray-300 px-2 py-1 text-sm"
          value={group.requireBoth ? "both" : "either"}
          onChange={(e) => onChange({ ...group, requireBoth: e.target.value === "both" })}
        >
          <option value="both">Require BOTH (AND)</option>
          <option value="either">Require EITHER (OR)</option>
        </select>
        {onRemove && (
          <button onClick={onRemove} className="ml-auto text-gray-400 hover:text-red-500">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-gray-500">Vision Condition</label>
        {(group.children || [])[0] && (
          <ConditionEditor
            group={(group.children || [])[0]}
            depth={depth + 1}
            onChange={(updated) => {
              const children = [...(group.children || [])];
              children[0] = updated;
              onChange({ ...group, children });
            }}
          />
        )}
      </div>
      <div className="space-y-1">
        <label className="text-xs font-medium text-gray-500">Audio Condition</label>
        {(group.children || [])[1] && (
          <ConditionEditor
            group={(group.children || [])[1]}
            depth={depth + 1}
            onChange={(updated) => {
              const children = [...(group.children || [])];
              children[1] = updated;
              onChange({ ...group, children });
            }}
          />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function RuleBuilder() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | undefined>();
  const [form, setForm] = useState<RuleFormState>(initialForm());
  const [testingChannel, setTestingChannel] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);

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
    setTestResult(null);
  }, []);

  const handleSave = () => {
    const conditions = groupToApiCondition(form.conditionGroup);
    const payload: AlertRuleCreatePayload = {
      name: form.name,
      conditions,
      actions: form.actions,
      enabled: form.enabled,
    };
    if (form.escalationLevels.length > 0) {
      payload.escalation_config = { levels: form.escalationLevels };
    }
    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleTestDelivery = async (idx: number) => {
    const action = form.actions[idx];
    setTestingChannel(idx);
    setTestResult(null);
    try {
      const config: Record<string, unknown> = {};
      if (action.type === "webhook") config.url = action.target;
      else if (action.type === "email") config.to = action.target;
      else if (action.type === "slack") config.webhook_url = action.target;
      else if (action.type === "discord") config.webhook_url = action.target;
      else if (action.type === "sms") config.to = action.target;

      const result = await testDeliveryChannel(action.type, config);
      setTestResult(`${result.status}: ${result.note || `Status ${result.status_code}`}`);
    } catch (err: unknown) {
      setTestResult(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setTestingChannel(null);
    }
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

  const setConditionType = (type: ConditionType) => {
    let group: CompoundConditionGroup;
    switch (type) {
      case "compound":
        group = emptyCompoundGroup();
        break;
      case "temporal":
        group = emptyTemporalGroup();
        break;
      case "cross_modal":
        group = emptyCrossModalGroup();
        break;
      default:
        group = emptyThresholdGroup();
    }
    setForm((prev) => ({ ...prev, conditionType: type, conditionGroup: group }));
  };

  const addEscalationLevel = () => {
    setForm((prev) => ({
      ...prev,
      escalationLevels: [
        ...prev.escalationLevels,
        { after_minutes: (prev.escalationLevels.length + 1) * 5, action: "notify_team" },
      ],
    }));
  };

  const updateEscalationLevel = (idx: number, partial: Partial<EscalationLevel>) => {
    setForm((prev) => {
      const levels = [...prev.escalationLevels];
      levels[idx] = { ...levels[idx], ...partial };
      return { ...prev, escalationLevels: levels };
    });
  };

  const removeEscalationLevel = (idx: number) => {
    setForm((prev) => ({
      ...prev,
      escalationLevels: prev.escalationLevels.filter((_, i) => i !== idx),
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
              disabled={!form.name.trim()}
            >
              {editingRule ? "Update" : "Create"}
            </Button>
          </>
        }
      >
        <div className="space-y-5 max-h-[70vh] overflow-y-auto">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Rule Name</label>
            <input
              type="text"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              placeholder="e.g. High CPU + Memory Compound Alert"
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            />
          </div>

          {/* Condition Type Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Condition Type</label>
            <div className="flex gap-2 flex-wrap">
              {(["threshold", "compound", "temporal", "cross_modal"] as ConditionType[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setConditionType(t)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium border transition-colors ${
                    form.conditionType === t
                      ? "bg-brand-600 text-white border-brand-600"
                      : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  {t === "cross_modal" ? "Cross-Modal" : t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Condition Editor */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Conditions</label>
            <ConditionEditor
              group={form.conditionGroup}
              onChange={(updated) => setForm((p) => ({ ...p, conditionGroup: updated }))}
            />
          </div>

          {/* Actions / Delivery Channels */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">Delivery Channels</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setForm((p) => ({ ...p, actions: [...p.actions, emptyAction()] }))}
              >
                + Add Channel
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
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleTestDelivery(idx)}
                    loading={testingChannel === idx}
                    disabled={!action.target && action.type !== "log"}
                  >
                    Test
                  </Button>
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
            {testResult && (
              <div className="mt-2 text-sm px-3 py-2 rounded bg-gray-100 text-gray-700">
                {testResult}
              </div>
            )}
          </div>

          {/* Escalation Policy */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">Escalation Policy</label>
              <Button variant="ghost" size="sm" onClick={addEscalationLevel}>
                + Add Level
              </Button>
            </div>
            {form.escalationLevels.length === 0 && (
              <p className="text-sm text-gray-400">No escalation levels configured.</p>
            )}
            <div className="space-y-2">
              {form.escalationLevels.map((level, idx) => (
                <div key={idx} className="flex items-center gap-2 rounded border border-orange-200 p-2 bg-orange-50">
                  <span className="text-sm text-gray-600 whitespace-nowrap">After</span>
                  <input
                    type="number"
                    className="rounded border border-gray-300 px-2 py-1 text-sm w-16"
                    value={level.after_minutes}
                    onChange={(e) =>
                      updateEscalationLevel(idx, { after_minutes: parseInt(e.target.value) || 1 })
                    }
                  />
                  <span className="text-sm text-gray-600">min:</span>
                  <input
                    type="text"
                    className="rounded border border-gray-300 px-2 py-1 text-sm flex-1"
                    placeholder="e.g. notify_team_lead, page_oncall"
                    value={level.action}
                    onChange={(e) => updateEscalationLevel(idx, { action: e.target.value })}
                  />
                  <button
                    onClick={() => removeEscalationLevel(idx)}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
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
