"use client";

import { API_BASE_URL } from "@/lib/api";
import { readWorkspaceId } from "@/lib/session";

import React, { useState, useEffect, useCallback } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import ModelCardPreview from "./ModelCardPreview";
import type { ModelCardData, PerformanceMetric } from "./ModelCardPreview";

const API_BASE = API_BASE_URL;
const STORAGE_KEY = "vaf_model_card_draft";

/* ------------------------------------------------------------------ */
/*  localStorage helpers (SSR-safe)                                    */
/* ------------------------------------------------------------------ */

function loadDraft(): ModelCardData | null {
  try {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as ModelCardData;
  } catch {
    return null;
  }
}

function saveDraft(data: ModelCardData): void {
  try {
    if (typeof window === "undefined") return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    /* quota exceeded or private browsing — ignore */
  }
}

/* ------------------------------------------------------------------ */
/*  Default empty card                                                 */
/* ------------------------------------------------------------------ */

function emptyCard(): ModelCardData {
  return {
    modelName: "",
    version: "",
    modelType: "",
    architecture: "",
    trainingDate: "",
    framework: "",
    license: "",
    primaryUseCases: "",
    outOfScope: "",
    targetUsers: "",
    metrics: [],
    knownLimitations: "",
    ethicalConsiderations: "",
    biasFairness: "",
    datasetName: "",
    datasetSize: "",
    datasetDescription: "",
    preprocessingSteps: "",
  };
}

/* ------------------------------------------------------------------ */
/*  Model type options                                                 */
/* ------------------------------------------------------------------ */

const MODEL_TYPES = [
  "Classification",
  "Object Detection",
  "Segmentation",
  "Regression",
  "Generative",
  "NLP / Transformer",
  "Audio / Speech",
  "Multimodal",
  "Other",
] as const;

/* ------------------------------------------------------------------ */
/*  Collapsible section                                                */
/* ------------------------------------------------------------------ */

function CollapsibleSection({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="flex w-full items-center justify-between px-6 py-4 text-left"
      >
        <h3 className="text-base font-semibold text-gray-900">{title}</h3>
        <svg
          className={`h-5 w-5 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {open && <div className="border-t border-gray-200 px-6 py-4">{children}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Reusable form field helpers                                        */
/* ------------------------------------------------------------------ */

function TextInput({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      <input
        type={type}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

function TextArea({
  label,
  value,
  onChange,
  placeholder,
  rows = 3,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      <textarea
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        rows={rows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Metrics table                                                      */
/* ------------------------------------------------------------------ */

function MetricsTable({
  metrics,
  onChange,
}: {
  metrics: PerformanceMetric[];
  onChange: (m: PerformanceMetric[]) => void;
}) {
  const updateRow = (idx: number, field: keyof PerformanceMetric, val: string) => {
    const next = [...metrics];
    next[idx] = { ...next[idx], [field]: val };
    onChange(next);
  };

  const addRow = () => {
    onChange([...metrics, { name: "", value: "", dataset: "", notes: "" }]);
  };

  const removeRow = (idx: number) => {
    onChange(metrics.filter((_, i) => i !== idx));
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Performance Metrics
      </label>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border border-gray-200 rounded">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-3 py-2 font-medium text-gray-600">
                Metric Name
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-600">
                Value
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-600">
                Dataset
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-600">
                Notes
              </th>
              <th className="w-10" />
            </tr>
          </thead>
          <tbody>
            {metrics.map((m, idx) => (
              <tr key={idx} className="border-t border-gray-100">
                <td className="px-2 py-1">
                  <input
                    className="w-full rounded border border-gray-200 px-2 py-1 text-sm"
                    value={m.name}
                    onChange={(e) => updateRow(idx, "name", e.target.value)}
                    placeholder="e.g. F1"
                  />
                </td>
                <td className="px-2 py-1">
                  <input
                    className="w-full rounded border border-gray-200 px-2 py-1 text-sm font-mono"
                    value={m.value}
                    onChange={(e) => updateRow(idx, "value", e.target.value)}
                    placeholder="0.95"
                  />
                </td>
                <td className="px-2 py-1">
                  <input
                    className="w-full rounded border border-gray-200 px-2 py-1 text-sm"
                    value={m.dataset}
                    onChange={(e) => updateRow(idx, "dataset", e.target.value)}
                    placeholder="val-set-v2"
                  />
                </td>
                <td className="px-2 py-1">
                  <input
                    className="w-full rounded border border-gray-200 px-2 py-1 text-sm"
                    value={m.notes}
                    onChange={(e) => updateRow(idx, "notes", e.target.value)}
                    placeholder="optional"
                  />
                </td>
                <td className="px-1 py-1 text-center">
                  <button
                    type="button"
                    onClick={() => removeRow(idx)}
                    className="text-red-400 hover:text-red-600 text-lg leading-none"
                    title="Remove row"
                  >
                    &times;
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        type="button"
        onClick={addRow}
        className="mt-2 inline-flex items-center gap-1 rounded-md border border-dashed border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:border-gray-400 hover:text-gray-800 transition-colors"
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
            d="M12 4v16m8-8H4"
          />
        </svg>
        Add Metric Row
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Registry model type (for the selector dropdown)                    */
/* ------------------------------------------------------------------ */

interface RegistryModel {
  id: string;
  name: string;
  version: string;
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export default function ModelCardsTab() {
  const [card, setCard] = useState<ModelCardData>(emptyCard);
  const [models, setModels] = useState<RegistryModel[]>([]);
  const [selectedModelId, setSelectedModelId] = useState("");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  /* Hydrate draft from localStorage on mount */
  useEffect(() => {
    const draft = loadDraft();
    if (draft) setCard(draft);
  }, []);

  /* Persist draft to localStorage on every change */
  useEffect(() => {
    saveDraft(card);
  }, [card]);

  /* Fetch models for selector dropdown */
  useEffect(() => {
    let cancelled = false;
    async function fetchModels() {
      try {
        const resp = await fetch(
          `${API_BASE}/api/registry/models?workspace_id=${readWorkspaceId() ?? ""}&limit=50`,
        );
        if (!resp.ok) return;
        const data = await resp.json();
        const items = data.items ?? data;
        if (!cancelled && Array.isArray(items)) {
          setModels(
            items.map((m: Record<string, unknown>) => ({
              id: String(m.id ?? ""),
              name: String(m.name ?? ""),
              version: String(m.version ?? ""),
            })),
          );
        }
      } catch {
        /* models list is best-effort */
      }
    }
    fetchModels();
    return () => {
      cancelled = true;
    };
  }, []);

  /* Field updater */
  const update = useCallback(
    <K extends keyof ModelCardData>(field: K, value: ModelCardData[K]) => {
      setCard((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  /* ---- Export as JSON download ---- */
  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify(card, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `model-card-${card.modelName || "draft"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  /* ---- Save to Registry (PATCH) ---- */
  const handleSaveToRegistry = async () => {
    if (!selectedModelId) {
      setFeedback({
        type: "error",
        message: "Select a model from the dropdown first.",
      });
      return;
    }
    setSaving(true);
    setFeedback(null);
    try {
      const resp = await fetch(
        `${API_BASE}/api/registry/models/${selectedModelId}/model-card`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(card),
        },
      );
      if (!resp.ok) throw new Error(await resp.text());
      setFeedback({
        type: "success",
        message: "Model card saved to registry.",
      });
    } catch (err: unknown) {
      setFeedback({
        type: "error",
        message:
          err instanceof Error ? err.message : "Failed to save model card.",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Model selector */}
      <Card title="Model Selector">
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select a registered model
            </label>
            <select
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={selectedModelId}
              onChange={(e) => setSelectedModelId(e.target.value)}
            >
              <option value="">-- choose model --</option>
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} (v{m.version})
                </option>
              ))}
            </select>
          </div>
        </div>
        {models.length === 0 && (
          <p className="mt-2 text-xs text-gray-400">
            No models found in registry. You can still fill out the card
            manually.
          </p>
        )}
      </Card>

      {/* Section 1 — Model Details */}
      <CollapsibleSection title="Model Details" defaultOpen>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <TextInput
            label="Name"
            value={card.modelName}
            onChange={(v) => update("modelName", v)}
            placeholder="resnet50-detector"
          />
          <TextInput
            label="Version"
            value={card.version}
            onChange={(v) => update("version", v)}
            placeholder="2.1.0"
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type
            </label>
            <select
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              value={card.modelType}
              onChange={(e) => update("modelType", e.target.value)}
            >
              <option value="">-- select type --</option>
              {MODEL_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <TextInput
            label="Training Date"
            value={card.trainingDate}
            onChange={(v) => update("trainingDate", v)}
            placeholder="2026-01-15"
            type="date"
          />
          <TextInput
            label="Framework"
            value={card.framework}
            onChange={(v) => update("framework", v)}
            placeholder="PyTorch 2.3"
          />
          <TextInput
            label="License"
            value={card.license}
            onChange={(v) => update("license", v)}
            placeholder="Apache-2.0"
          />
        </div>
        <div className="mt-4">
          <TextArea
            label="Architecture"
            value={card.architecture}
            onChange={(v) => update("architecture", v)}
            placeholder="Describe the model architecture..."
          />
        </div>
      </CollapsibleSection>

      {/* Section 2 — Intended Use */}
      <CollapsibleSection title="Intended Use">
        <div className="space-y-4">
          <TextArea
            label="Primary Use Cases"
            value={card.primaryUseCases}
            onChange={(v) => update("primaryUseCases", v)}
            placeholder="Describe the primary intended use cases..."
          />
          <TextArea
            label="Out-of-Scope Uses"
            value={card.outOfScope}
            onChange={(v) => update("outOfScope", v)}
            placeholder="Describe use cases that are out of scope..."
          />
          <TextArea
            label="Target Users"
            value={card.targetUsers}
            onChange={(v) => update("targetUsers", v)}
            placeholder="Who are the intended users?"
          />
        </div>
      </CollapsibleSection>

      {/* Section 3 — Performance */}
      <CollapsibleSection title="Performance">
        <MetricsTable
          metrics={card.metrics}
          onChange={(m) => update("metrics", m)}
        />
      </CollapsibleSection>

      {/* Section 4 — Limitations & Risks */}
      <CollapsibleSection title="Limitations & Risks">
        <div className="space-y-4">
          <TextArea
            label="Known Limitations"
            value={card.knownLimitations}
            onChange={(v) => update("knownLimitations", v)}
            placeholder="Describe known limitations..."
          />
          <TextArea
            label="Ethical Considerations"
            value={card.ethicalConsiderations}
            onChange={(v) => update("ethicalConsiderations", v)}
            placeholder="Ethical considerations for deployment..."
          />
          <TextArea
            label="Bias & Fairness"
            value={card.biasFairness}
            onChange={(v) => update("biasFairness", v)}
            placeholder="Known biases and fairness evaluations..."
          />
        </div>
      </CollapsibleSection>

      {/* Section 5 — Training Data */}
      <CollapsibleSection title="Training Data">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <TextInput
            label="Dataset Name"
            value={card.datasetName}
            onChange={(v) => update("datasetName", v)}
            placeholder="ImageNet-1K"
          />
          <TextInput
            label="Dataset Size"
            value={card.datasetSize}
            onChange={(v) => update("datasetSize", v)}
            placeholder="1.2M images"
          />
        </div>
        <div className="mt-4 space-y-4">
          <TextArea
            label="Description"
            value={card.datasetDescription}
            onChange={(v) => update("datasetDescription", v)}
            placeholder="Describe the training dataset..."
          />
          <TextArea
            label="Preprocessing Steps"
            value={card.preprocessingSteps}
            onChange={(v) => update("preprocessingSteps", v)}
            placeholder="Resizing, normalization, augmentation..."
          />
        </div>
      </CollapsibleSection>

      {/* Action bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-6 py-4">
        <Button variant="secondary" onClick={() => setPreviewOpen(true)}>
          Preview Card
        </Button>
        <Button variant="secondary" onClick={handleExportJSON}>
          Export as JSON
        </Button>
        <Button
          onClick={handleSaveToRegistry}
          loading={saving}
          disabled={saving}
        >
          Save to Registry
        </Button>

        {feedback && (
          <span
            className={`text-sm ${feedback.type === "success" ? "text-green-600" : "text-red-600"}`}
          >
            {feedback.message}
          </span>
        )}
      </div>

      {/* Preview modal */}
      <ModelCardPreview
        cardData={card}
        isOpen={previewOpen}
        onClose={() => setPreviewOpen(false)}
      />
    </div>
  );
}
