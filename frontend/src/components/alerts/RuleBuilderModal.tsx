"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import {
  createAL4Rule,
  type AL4Rule,
  type AL4RulePayload,
  type AL4Severity,
  type AL4Condition,
  type AL4ConditionField,
  type AL4Operator,
  type AL4LogicOperator,
  type AL4Cooldown,
  type AL4Actions,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const FIELD_OPTIONS: { value: AL4ConditionField; label: string }[] = [
  { value: "confidence", label: "Confidence" },
  { value: "class", label: "Class" },
  { value: "motion", label: "Motion" },
  { value: "audio_level", label: "Audio Level" },
  { value: "ocr_text", label: "OCR Text" },
  { value: "custom", label: "Custom" },
];

const OPERATOR_OPTIONS: { value: AL4Operator; label: string }[] = [
  { value: ">", label: ">" },
  { value: "<", label: "<" },
  { value: "=", label: "=" },
  { value: "contains", label: "contains" },
  { value: "not_contains", label: "not contains" },
];

const COOLDOWN_OPTIONS: { value: AL4Cooldown; label: string }[] = [
  { value: "none", label: "No cooldown" },
  { value: "1m", label: "1 minute" },
  { value: "5m", label: "5 minutes" },
  { value: "15m", label: "15 minutes" },
  { value: "1h", label: "1 hour" },
];

const SEVERITY_OPTIONS: { value: AL4Severity; label: string; color: string }[] = [
  { value: "critical", label: "Critical", color: "bg-red-600 text-white border-red-600" },
  { value: "warning", label: "Warning", color: "bg-yellow-500 text-white border-yellow-500" },
  { value: "info", label: "Info", color: "bg-blue-500 text-white border-blue-500" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateId(): string {
  return Math.random().toString(36).substring(2, 9);
}

function emptyCondition(): AL4Condition {
  return {
    id: generateId(),
    field: "confidence",
    operator: ">",
    value: "",
  };
}

function emptyActions(): AL4Actions {
  return {
    email: { enabled: false, address: "" },
    slack: { enabled: false, webhook_url: "" },
    webhook: { enabled: false, post_url: "" },
    auto_clip: false,
  };
}

interface FormState {
  name: string;
  severity: AL4Severity;
  conditions: AL4Condition[];
  logicOperator: AL4LogicOperator;
  cooldown: AL4Cooldown;
  actions: AL4Actions;
}

function formFromRule(rule?: AL4Rule): FormState {
  if (rule) {
    return {
      name: rule.name,
      severity: rule.severity,
      conditions: rule.conditions.length > 0 ? [...rule.conditions] : [emptyCondition()],
      logicOperator: rule.logic_operator,
      cooldown: rule.cooldown,
      actions: {
        email: { ...rule.actions.email },
        slack: { ...rule.actions.slack },
        webhook: { ...rule.actions.webhook },
        auto_clip: rule.actions.auto_clip,
      },
    };
  }
  return {
    name: "",
    severity: "warning",
    conditions: [emptyCondition()],
    logicOperator: "AND",
    cooldown: "none",
    actions: emptyActions(),
  };
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface RuleBuilderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
  editingRule?: AL4Rule;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RuleBuilderModal({
  isOpen,
  onClose,
  onSaved,
  editingRule,
}: RuleBuilderModalProps) {
  const [form, setForm] = useState<FormState>(formFromRule());

  // Reset form when modal opens / editingRule changes
  useEffect(() => {
    if (isOpen) {
      setForm(formFromRule(editingRule));
    }
  }, [isOpen, editingRule]);

  const saveMutation = useMutation({
    mutationFn: (payload: AL4RulePayload) => createAL4Rule(payload),
    onSuccess: () => onSaved(),
  });

  const handleSave = useCallback(() => {
    const payload: AL4RulePayload = {
      name: form.name.trim(),
      severity: form.severity,
      conditions: form.conditions,
      logic_operator: form.logicOperator,
      cooldown: form.cooldown,
      actions: form.actions,
      enabled: true,
    };
    saveMutation.mutate(payload);
  }, [form, saveMutation]);

  // ---- Condition helpers ----
  const updateCondition = (idx: number, partial: Partial<AL4Condition>) => {
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

  const addCondition = () => {
    setForm((prev) => ({
      ...prev,
      conditions: [...prev.conditions, emptyCondition()],
    }));
  };

  const canSave = form.name.trim().length > 0 && form.conditions.length > 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={editingRule ? "Edit Rule" : "New Alert Rule"}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            loading={saveMutation.isPending}
            disabled={!canSave}
          >
            Save Rule
          </Button>
        </>
      }
    >
      <div className="space-y-5 max-h-[70vh] overflow-y-auto pr-1">
        {/* Rule Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Rule Name
          </label>
          <input
            type="text"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            placeholder="e.g. Low Confidence Detection"
            value={form.name}
            onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
          />
        </div>

        {/* Severity */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Severity
          </label>
          <div className="flex gap-2">
            {SEVERITY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setForm((p) => ({ ...p, severity: opt.value }))}
                className={`px-4 py-1.5 rounded-md text-sm font-medium border transition-colors ${
                  form.severity === opt.value
                    ? opt.color
                    : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Condition Builder */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Conditions
          </label>
          <div className="space-y-2">
            {form.conditions.map((cond, idx) => (
              <div key={cond.id}>
                {/* AND/OR selector between conditions */}
                {idx > 0 && (
                  <div className="flex items-center justify-center my-1">
                    <select
                      className="rounded border border-gray-300 px-2 py-0.5 text-xs font-medium text-gray-600"
                      value={form.logicOperator}
                      onChange={(e) =>
                        setForm((p) => ({
                          ...p,
                          logicOperator: e.target.value as AL4LogicOperator,
                        }))
                      }
                    >
                      <option value="AND">AND</option>
                      <option value="OR">OR</option>
                    </select>
                  </div>
                )}
                <div className="flex items-center gap-2 rounded border border-gray-200 p-2 bg-gray-50">
                  {/* Field */}
                  <select
                    className="rounded border border-gray-300 px-2 py-1 text-sm flex-1"
                    value={cond.field}
                    onChange={(e) =>
                      updateCondition(idx, {
                        field: e.target.value as AL4ConditionField,
                      })
                    }
                  >
                    {FIELD_OPTIONS.map((f) => (
                      <option key={f.value} value={f.value}>
                        {f.label}
                      </option>
                    ))}
                  </select>

                  {/* Operator */}
                  <select
                    className="rounded border border-gray-300 px-2 py-1 text-sm w-28"
                    value={cond.operator}
                    onChange={(e) =>
                      updateCondition(idx, {
                        operator: e.target.value as AL4Operator,
                      })
                    }
                  >
                    {OPERATOR_OPTIONS.map((op) => (
                      <option key={op.value} value={op.value}>
                        {op.label}
                      </option>
                    ))}
                  </select>

                  {/* Value */}
                  <input
                    type="text"
                    className="rounded border border-gray-300 px-2 py-1 text-sm w-24"
                    placeholder="Value"
                    value={cond.value}
                    onChange={(e) =>
                      updateCondition(idx, { value: e.target.value })
                    }
                  />

                  {/* Remove */}
                  {form.conditions.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeCondition(idx)}
                      className="text-gray-400 hover:text-red-500 transition-colors"
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
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={addCondition}
            className="mt-2 text-sm text-brand-600 hover:text-brand-700 font-medium"
          >
            + Add Condition
          </button>
        </div>

        {/* Cooldown */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Cooldown
          </label>
          <select
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            value={form.cooldown}
            onChange={(e) =>
              setForm((p) => ({ ...p, cooldown: e.target.value as AL4Cooldown }))
            }
          >
            {COOLDOWN_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Actions / Delivery */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Actions
          </label>
          <div className="space-y-3">
            {/* Email */}
            <div className="rounded border border-gray-200 p-3 bg-gray-50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Email</span>
                <ToggleSwitch
                  checked={form.actions.email.enabled}
                  onChange={(val) =>
                    setForm((p) => ({
                      ...p,
                      actions: {
                        ...p.actions,
                        email: { ...p.actions.email, enabled: val },
                      },
                    }))
                  }
                />
              </div>
              {form.actions.email.enabled && (
                <input
                  type="email"
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  placeholder="alerts@example.com"
                  value={form.actions.email.address}
                  onChange={(e) =>
                    setForm((p) => ({
                      ...p,
                      actions: {
                        ...p.actions,
                        email: { ...p.actions.email, address: e.target.value },
                      },
                    }))
                  }
                />
              )}
            </div>

            {/* Slack */}
            <div className="rounded border border-gray-200 p-3 bg-gray-50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Slack</span>
                <ToggleSwitch
                  checked={form.actions.slack.enabled}
                  onChange={(val) =>
                    setForm((p) => ({
                      ...p,
                      actions: {
                        ...p.actions,
                        slack: { ...p.actions.slack, enabled: val },
                      },
                    }))
                  }
                />
              </div>
              {form.actions.slack.enabled && (
                <input
                  type="url"
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  placeholder="https://hooks.slack.com/services/..."
                  value={form.actions.slack.webhook_url}
                  onChange={(e) =>
                    setForm((p) => ({
                      ...p,
                      actions: {
                        ...p.actions,
                        slack: { ...p.actions.slack, webhook_url: e.target.value },
                      },
                    }))
                  }
                />
              )}
            </div>

            {/* Webhook */}
            <div className="rounded border border-gray-200 p-3 bg-gray-50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Webhook</span>
                <ToggleSwitch
                  checked={form.actions.webhook.enabled}
                  onChange={(val) =>
                    setForm((p) => ({
                      ...p,
                      actions: {
                        ...p.actions,
                        webhook: { ...p.actions.webhook, enabled: val },
                      },
                    }))
                  }
                />
              </div>
              {form.actions.webhook.enabled && (
                <input
                  type="url"
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  placeholder="https://example.com/webhook"
                  value={form.actions.webhook.post_url}
                  onChange={(e) =>
                    setForm((p) => ({
                      ...p,
                      actions: {
                        ...p.actions,
                        webhook: { ...p.actions.webhook, post_url: e.target.value },
                      },
                    }))
                  }
                />
              )}
            </div>

            {/* Auto-clip */}
            <div className="rounded border border-gray-200 p-3 bg-gray-50">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">
                  Auto-create evidence clip
                </span>
                <ToggleSwitch
                  checked={form.actions.auto_clip}
                  onChange={(val) =>
                    setForm((p) => ({
                      ...p,
                      actions: { ...p.actions, auto_clip: val },
                    }))
                  }
                />
              </div>
            </div>
          </div>
        </div>

        {/* Mutation error */}
        {saveMutation.isError && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            Failed to save rule. Please try again.
          </div>
        )}
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Small toggle used inside the modal
// ---------------------------------------------------------------------------

function ToggleSwitch({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (val: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
        checked ? "bg-brand-600" : "bg-gray-300"
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
          checked ? "translate-x-4" : "translate-x-1"
        }`}
      />
    </button>
  );
}
