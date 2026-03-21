"use client";

import React, { useState, useCallback } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type EdgeCategory = "Vision" | "Audio" | "System";
type ModificationType = "Brightness" | "Noise" | "Blur" | "Crop" | "Compression";
type ResultStatus = "pass" | "fail" | "degraded";

interface EdgeCaseResult {
  status: ResultStatus;
  scoreBefore: number;
  scoreAfter: number;
  confidenceDrop: number;
}

interface EdgeCaseDefinition {
  id: string;
  name: string;
  description: string;
  category: EdgeCategory;
  custom?: boolean;
  modificationType?: ModificationType;
  intensity?: number;
}

interface EdgeCaseRunState {
  loading: boolean;
  result: EdgeCaseResult | null;
  error: string | null;
}

interface CustomEdgeCaseForm {
  name: string;
  description: string;
  category: EdgeCategory;
  modificationType: ModificationType;
  intensity: number;
}

/* ------------------------------------------------------------------ */
/*  Built-in edge cases                                                */
/* ------------------------------------------------------------------ */

const BUILT_IN_EDGE_CASES: EdgeCaseDefinition[] = [
  {
    id: "low-light",
    name: "Low Light",
    description:
      "Tests model accuracy on images captured in near-darkness or heavy underexposure conditions.",
    category: "Vision",
  },
  {
    id: "heavy-occlusion",
    name: "Heavy Occlusion",
    description:
      "Evaluates detection when target objects are 60%+ obscured by other objects.",
    category: "Vision",
  },
  {
    id: "motion-blur",
    name: "Motion Blur",
    description:
      "Applies directional motion blur simulating fast camera or subject movement.",
    category: "Vision",
  },
  {
    id: "extreme-crowd",
    name: "Extreme Crowd",
    description:
      "Stress-tests detection and tracking in scenes with 100+ overlapping subjects.",
    category: "Vision",
  },
  {
    id: "background-noise",
    name: "Background Noise",
    description:
      "Adds ambient noise (traffic, crowd chatter, wind) to audio at varying SNR levels.",
    category: "Audio",
  },
  {
    id: "silent-audio",
    name: "Silent Audio",
    description:
      "Tests handling of fully silent or near-silent audio streams with no speech content.",
    category: "Audio",
  },
  {
    id: "very-long-audio",
    name: "Very Long Audio",
    description:
      "Validates processing stability and memory usage on audio clips exceeding 30 minutes.",
    category: "Audio",
  },
  {
    id: "adversarial-image",
    name: "Adversarial Image",
    description:
      "Applies adversarial perturbations (FGSM-style) designed to fool classification models.",
    category: "Vision",
  },
  {
    id: "out-of-distribution",
    name: "Out-of-Distribution",
    description:
      "Presents inputs from domains not seen during training to test model robustness.",
    category: "System",
  },
  {
    id: "network-dropout",
    name: "Network Dropout",
    description:
      "Simulates intermittent network failures during inference API calls.",
    category: "System",
  },
];

/* ------------------------------------------------------------------ */
/*  Category badge                                                     */
/* ------------------------------------------------------------------ */

const CATEGORY_STYLES: Record<EdgeCategory, string> = {
  Vision: "bg-purple-100 text-purple-800",
  Audio: "bg-blue-100 text-blue-800",
  System: "bg-amber-100 text-amber-800",
};

function CategoryBadge({ category }: { category: EdgeCategory }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${CATEGORY_STYLES[category]}`}
    >
      {category}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Result indicator                                                   */
/* ------------------------------------------------------------------ */

function ResultIndicator({ result }: { result: EdgeCaseResult }) {
  const config: Record<ResultStatus, { icon: string; label: string; color: string }> = {
    pass: { icon: "\u2713", label: "Pass", color: "text-green-600 bg-green-50 border-green-200" },
    fail: { icon: "\u2717", label: "Fail", color: "text-red-600 bg-red-50 border-red-200" },
    degraded: { icon: "!", label: "Degraded", color: "text-amber-600 bg-amber-50 border-amber-200" },
  };
  const c = config[result.status];

  return (
    <div className={`mt-4 rounded-lg border p-3 ${c.color}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-lg font-bold">
          {c.icon} {c.label}
        </span>
        <span className="text-xs font-medium">
          Confidence drop: {result.confidenceDrop.toFixed(1)}%
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-gray-500">Before:</span>{" "}
          <span className="font-mono font-medium">{result.scoreBefore.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-gray-500">After:</span>{" "}
          <span className="font-mono font-medium">{result.scoreAfter.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Edge Case Card                                                     */
/* ------------------------------------------------------------------ */

function EdgeCaseCard({
  edgeCase,
  runState,
  onRun,
}: {
  edgeCase: EdgeCaseDefinition;
  runState: EdgeCaseRunState;
  onRun: () => void;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm p-5 flex flex-col">
      <div className="flex items-start justify-between mb-2">
        <h4 className="text-sm font-semibold text-gray-900">{edgeCase.name}</h4>
        <CategoryBadge category={edgeCase.category} />
      </div>
      <p className="text-xs text-gray-500 leading-relaxed flex-1">
        {edgeCase.description}
      </p>
      {edgeCase.custom && edgeCase.modificationType && (
        <div className="mt-2 text-xs text-gray-400">
          {edgeCase.modificationType} @ {edgeCase.intensity ?? 0}% intensity
        </div>
      )}
      <div className="mt-3">
        <Button
          size="sm"
          variant="secondary"
          onClick={onRun}
          loading={runState.loading}
          disabled={runState.loading}
        >
          Run
        </Button>
      </div>
      {runState.error && (
        <p className="mt-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded px-2 py-1">
          {runState.error}
        </p>
      )}
      {runState.result && <ResultIndicator result={runState.result} />}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Custom Edge Case Modal                                             */
/* ------------------------------------------------------------------ */

const CATEGORIES: EdgeCategory[] = ["Vision", "Audio", "System"];
const MODIFICATION_TYPES: ModificationType[] = [
  "Brightness",
  "Noise",
  "Blur",
  "Crop",
  "Compression",
];

function CustomEdgeCaseModal({
  open,
  onClose,
  onCreate,
}: {
  open: boolean;
  onClose: () => void;
  onCreate: (form: CustomEdgeCaseForm) => void;
}) {
  const [form, setForm] = useState<CustomEdgeCaseForm>({
    name: "",
    description: "",
    category: "Vision",
    modificationType: "Brightness",
    intensity: 50,
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!form.name.trim() || !form.description.trim()) return;
      onCreate(form);
      setForm({
        name: "",
        description: "",
        category: "Vision",
        modificationType: "Brightness",
        intensity: 50,
      });
    },
    [form, onCreate],
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Panel */}
      <div className="relative w-full max-w-lg rounded-xl bg-white shadow-xl p-6 mx-4">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-semibold text-gray-900">
            Create Custom Edge Case
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              placeholder="e.g. Severe JPEG Compression"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              required
              rows={2}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              placeholder="Describe the edge case scenario..."
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Category
            </label>
            <select
              value={form.category}
              onChange={(e) =>
                setForm({ ...form, category: e.target.value as EdgeCategory })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Modification type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Modification Type
            </label>
            <select
              value={form.modificationType}
              onChange={(e) =>
                setForm({
                  ...form,
                  modificationType: e.target.value as ModificationType,
                })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            >
              {MODIFICATION_TYPES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {/* Intensity slider */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-sm font-medium text-gray-700">
                Intensity
              </label>
              <span className="text-sm font-bold text-gray-900 font-mono">
                {form.intensity}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              value={form.intensity}
              onChange={(e) =>
                setForm({ ...form, intensity: parseInt(e.target.value, 10) })
              }
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">Create</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function EdgeCasesTab() {
  const [customCases, setCustomCases] = useState<EdgeCaseDefinition[]>([]);
  const [runStates, setRunStates] = useState<Record<string, EdgeCaseRunState>>({});
  const [modalOpen, setModalOpen] = useState(false);

  const allCases = [...BUILT_IN_EDGE_CASES, ...customCases];

  /* ---- Get / init run state for a given edge case ---- */
  const getRunState = useCallback(
    (id: string): EdgeCaseRunState =>
      runStates[id] ?? { loading: false, result: null, error: null },
    [runStates],
  );

  /* ---- Run an edge case ---- */
  const handleRun = useCallback(
    async (edgeCase: EdgeCaseDefinition) => {
      const id = edgeCase.id;
      setRunStates((prev) => ({
        ...prev,
        [id]: { loading: true, result: null, error: null },
      }));

      try {
        const res = await fetch(`${API}/api/simulation/edge-case`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            id: edgeCase.id,
            name: edgeCase.name,
            category: edgeCase.category,
            custom: edgeCase.custom ?? false,
            modification_type: edgeCase.modificationType ?? null,
            intensity: edgeCase.intensity ?? null,
          }),
        });

        if (!res.ok) {
          const detail = await res.text();
          throw new Error(detail || `HTTP ${res.status}`);
        }

        const data: EdgeCaseResult = await res.json();
        setRunStates((prev) => ({
          ...prev,
          [id]: { loading: false, result: data, error: null },
        }));
      } catch (err) {
        setRunStates((prev) => ({
          ...prev,
          [id]: {
            loading: false,
            result: null,
            error: err instanceof Error ? err.message : "Unknown error",
          },
        }));
      }
    },
    [],
  );

  /* ---- Create custom edge case ---- */
  const handleCreateCustom = useCallback((form: CustomEdgeCaseForm) => {
    const id = `custom-${Date.now()}`;
    const newCase: EdgeCaseDefinition = {
      id,
      name: form.name,
      description: form.description,
      category: form.category,
      custom: true,
      modificationType: form.modificationType,
      intensity: form.intensity,
    };
    setCustomCases((prev) => [...prev, newCase]);
    setModalOpen(false);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card title="Edge Case Testing">
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Run built-in or custom edge case scenarios to stress-test model
            robustness under adverse conditions.
          </p>
          <Button onClick={() => setModalOpen(true)}>
            + Create Custom Edge Case
          </Button>
        </div>
      </Card>

      {/* Edge case grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {allCases.map((ec) => (
          <EdgeCaseCard
            key={ec.id}
            edgeCase={ec}
            runState={getRunState(ec.id)}
            onRun={() => handleRun(ec)}
          />
        ))}
      </div>

      {/* Custom edge case modal */}
      <CustomEdgeCaseModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreate={handleCreateCustom}
      />
    </div>
  );
}
