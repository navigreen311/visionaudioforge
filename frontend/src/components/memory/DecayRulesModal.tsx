"use client";

import { useState, useEffect, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DecayRule {
  id: string;
  name: string;
  category: string;
  older_than_days: number;
  importance_below: number;
  reduce_by: number;
  every_n_days: number;
  min_floor: number;
  enabled: boolean;
}

type DecayRuleFormData = Omit<DecayRule, "id">;

const CATEGORIES = [
  "general",
  "vision",
  "audio",
  "pipeline",
  "investigation",
  "annotation",
  "agent",
  "system",
];

const STORAGE_KEY = "vaf_decay_rules";
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Persistence helpers
// ---------------------------------------------------------------------------

function loadRules(): DecayRule[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as DecayRule[];
  } catch {
    return [];
  }
}

function saveRules(rules: DecayRule[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(rules));
}

function generateId(): string {
  return `rule-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// ---------------------------------------------------------------------------
// Default form state
// ---------------------------------------------------------------------------

const DEFAULT_FORM: DecayRuleFormData = {
  name: "",
  category: "general",
  older_than_days: 30,
  importance_below: 0.5,
  reduce_by: 10,
  every_n_days: 7,
  min_floor: 0.1,
  enabled: true,
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function RuleForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel,
}: {
  initial: DecayRuleFormData;
  onSubmit: (data: DecayRuleFormData) => void;
  onCancel: () => void;
  submitLabel: string;
}) {
  const [form, setForm] = useState<DecayRuleFormData>(initial);

  const update = <K extends keyof DecayRuleFormData>(
    key: K,
    value: DecayRuleFormData[K],
  ) => setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="space-y-3 rounded-lg border border-gray-600 bg-gray-900 p-4">
      {/* Name */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-400">
          Rule name
        </label>
        <input
          type="text"
          value={form.name}
          onChange={(e) => update("name", e.target.value)}
          className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 focus:border-indigo-500 focus:outline-none"
          placeholder="e.g. Stale vision memories"
        />
      </div>

      {/* Category */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-400">
          Category
        </label>
        <select
          value={form.category}
          onChange={(e) => update("category", e.target.value)}
          className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 focus:border-indigo-500 focus:outline-none"
        >
          {CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
      </div>

      {/* Older than N days */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-400">
          Older than (days)
        </label>
        <input
          type="number"
          min={1}
          value={form.older_than_days}
          onChange={(e) => update("older_than_days", Number(e.target.value))}
          className="w-24 rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 focus:border-indigo-500 focus:outline-none"
        />
      </div>

      {/* Importance below slider */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-400">
          Importance below: {(form.importance_below * 100).toFixed(0)}%
        </label>
        <input
          type="range"
          min={0}
          max={100}
          value={form.importance_below * 100}
          onChange={(e) =>
            update("importance_below", Number(e.target.value) / 100)
          }
          className="w-full"
        />
      </div>

      {/* Reduce by N every N days */}
      <div className="flex items-center gap-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-400">
            Reduce by (%)
          </label>
          <input
            type="number"
            min={1}
            max={100}
            value={form.reduce_by}
            onChange={(e) => update("reduce_by", Number(e.target.value))}
            className="w-20 rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 focus:border-indigo-500 focus:outline-none"
          />
        </div>
        <span className="mt-5 text-sm text-gray-400">every</span>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-400">
            Days
          </label>
          <input
            type="number"
            min={1}
            value={form.every_n_days}
            onChange={(e) => update("every_n_days", Number(e.target.value))}
            className="w-20 rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 focus:border-indigo-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Min floor slider */}
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-400">
          Minimum floor: {(form.min_floor * 100).toFixed(0)}%
        </label>
        <input
          type="range"
          min={0}
          max={100}
          value={form.min_floor * 100}
          onChange={(e) => update("min_floor", Number(e.target.value) / 100)}
          className="w-full"
        />
      </div>

      {/* Buttons */}
      <div className="flex gap-2 pt-2">
        <button
          onClick={() => {
            if (!form.name.trim()) return;
            onSubmit(form);
          }}
          disabled={!form.name.trim()}
          className="rounded bg-indigo-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {submitLabel}
        </button>
        <button
          onClick={onCancel}
          className="rounded bg-gray-700 px-4 py-1.5 text-xs text-gray-300 hover:bg-gray-600"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

interface DecayRulesModalProps {
  open: boolean;
  onClose: () => void;
}

export default function DecayRulesModal({ open, onClose }: DecayRulesModalProps) {
  const [rules, setRules] = useState<DecayRule[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<string | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    if (open) {
      setRules(loadRules());
      setShowAddForm(false);
      setEditingId(null);
      setRunResult(null);
    }
  }, [open]);

  // Persist on change
  const persist = useCallback((updated: DecayRule[]) => {
    setRules(updated);
    saveRules(updated);
  }, []);

  const handleAdd = useCallback(
    (data: DecayRuleFormData) => {
      const rule: DecayRule = { ...data, id: generateId() };
      persist([...rules, rule]);
      setShowAddForm(false);
    },
    [rules, persist],
  );

  const handleEdit = useCallback(
    (id: string, data: DecayRuleFormData) => {
      persist(rules.map((r) => (r.id === id ? { ...data, id } : r)));
      setEditingId(null);
    },
    [rules, persist],
  );

  const handleDelete = useCallback(
    (id: string) => {
      persist(rules.filter((r) => r.id !== id));
    },
    [rules, persist],
  );

  const handleToggle = useCallback(
    (id: string) => {
      persist(
        rules.map((r) =>
          r.id === id ? { ...r, enabled: !r.enabled } : r,
        ),
      );
    },
    [rules, persist],
  );

  const handleRunNow = useCallback(async () => {
    setRunning(true);
    setRunResult(null);
    try {
      const enabledRules = rules.filter((r) => r.enabled);
      const res = await fetch(`${API_BASE}/api/memory/apply-rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rules: enabledRules }),
      });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      const data: { applied: number; affected: number } = await res.json();
      setRunResult(
        `Applied ${data.applied} rule(s), ${data.affected} memorie(s) affected.`,
      );
    } catch (err) {
      setRunResult(
        err instanceof Error ? err.message : "Failed to run rules",
      );
    } finally {
      setRunning(false);
    }
  }, [rules]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-gray-700 bg-gray-850 p-6 shadow-2xl">
        {/* Header */}
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-100">
            Memory Decay Rules
          </h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-gray-200"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M5 5l10 10M15 5L5 15" />
            </svg>
          </button>
        </div>

        {/* Run rules button */}
        <div className="mb-4 flex items-center gap-3">
          <button
            onClick={handleRunNow}
            disabled={running || rules.filter((r) => r.enabled).length === 0}
            className="rounded bg-amber-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-amber-500 disabled:opacity-50"
          >
            {running ? "Running..." : "Run Rules Now"}
          </button>
          <button
            onClick={() => {
              setShowAddForm(true);
              setEditingId(null);
            }}
            className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
          >
            + Add Rule
          </button>
          {runResult && (
            <span className="text-xs text-gray-400">{runResult}</span>
          )}
        </div>

        {/* Add form */}
        {showAddForm && (
          <div className="mb-4">
            <RuleForm
              initial={DEFAULT_FORM}
              onSubmit={handleAdd}
              onCancel={() => setShowAddForm(false)}
              submitLabel="Add Rule"
            />
          </div>
        )}

        {/* Rules list */}
        {rules.length === 0 && !showAddForm && (
          <div className="py-10 text-center text-sm text-gray-500">
            No decay rules configured. Click &quot;+ Add Rule&quot; to create
            one.
          </div>
        )}

        <div className="space-y-3">
          {rules.map((rule) => {
            if (editingId === rule.id) {
              const { id: _id, ...formData } = rule;
              return (
                <RuleForm
                  key={rule.id}
                  initial={formData}
                  onSubmit={(data) => handleEdit(rule.id, data)}
                  onCancel={() => setEditingId(null)}
                  submitLabel="Save"
                />
              );
            }

            return (
              <div
                key={rule.id}
                className={`flex items-center justify-between rounded-lg border p-3 ${
                  rule.enabled
                    ? "border-gray-600 bg-gray-800"
                    : "border-gray-700 bg-gray-800/50 opacity-60"
                }`}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-200">
                      {rule.name}
                    </span>
                    <span className="rounded bg-gray-700 px-1.5 py-0.5 text-xs text-gray-400">
                      {rule.category}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-500">
                    Older than {rule.older_than_days}d, importance &lt;{" "}
                    {(rule.importance_below * 100).toFixed(0)}% &rarr; reduce{" "}
                    {rule.reduce_by}% every {rule.every_n_days}d (floor:{" "}
                    {(rule.min_floor * 100).toFixed(0)}%)
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {/* Enabled toggle */}
                  <button
                    onClick={() => handleToggle(rule.id)}
                    className={`relative h-5 w-9 rounded-full transition-colors ${
                      rule.enabled ? "bg-green-600" : "bg-gray-600"
                    }`}
                    title={rule.enabled ? "Enabled" : "Disabled"}
                  >
                    <span
                      className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                        rule.enabled ? "left-[18px]" : "left-0.5"
                      }`}
                    />
                  </button>
                  <button
                    onClick={() => {
                      setEditingId(rule.id);
                      setShowAddForm(false);
                    }}
                    className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-gray-200"
                    title="Edit"
                  >
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 14 14"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <path d="M8.5 2.5l3 3M1.5 9.5l6-6 3 3-6 6H1.5v-3z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDelete(rule.id)}
                    className="rounded p-1 text-gray-400 hover:bg-red-900 hover:text-red-300"
                    title="Delete"
                  >
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 14 14"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <path d="M3 3l8 8M11 3l-8 8" />
                    </svg>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
