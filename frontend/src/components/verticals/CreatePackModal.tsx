"use client";

import React, { useState, useEffect, useCallback } from "react";
import Modal from "../ui/Modal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PipelineItem {
  id: string;
  name: string;
  status?: string;
}

interface AlertRule {
  id: string;
  name: string;
  severity?: string;
}

interface CustomPack {
  slug: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  pipelineIds: string[];
  pipelineNames: string[];
  alertRuleIds: string[];
  alertRuleNames: string[];
  createdAt: string;
  isCustom: true;
}

interface CreatePackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (pack: CustomPack) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STORAGE_KEY = "vaf_custom_packs";

const CATEGORIES = [
  "Public Safety",
  "Healthcare",
  "Customer Service",
  "Retail",
  "Manufacturing",
  "Media & Entertainment",
  "Education",
  "Transportation",
  "Agriculture",
  "Custom",
] as const;

const PRESET_ICONS: { label: string; svg: React.ReactNode }[] = [
  {
    label: "Shield",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
  {
    label: "Eye",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
      </svg>
    ),
  },
  {
    label: "Cog",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.573-1.066z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
  {
    label: "Chart",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    label: "Bell",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ),
  },
  {
    label: "Camera",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
  {
    label: "Mic",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
      </svg>
    ),
  },
  {
    label: "Cube",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-6 w-6">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
      </svg>
    ),
  },
];

// Map icon label to a simple emoji-like identifier for storage
const ICON_MAP: Record<string, string> = {
  Shield: "shield",
  Eye: "eye",
  Cog: "cog",
  Chart: "chart",
  Bell: "bell",
  Camera: "camera",
  Mic: "mic",
  Cube: "cube",
};

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

function loadCustomPacks(): CustomPack[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as CustomPack[];
  } catch {
    return [];
  }
}

function saveCustomPacks(packs: CustomPack[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(packs));
  } catch {
    // Storage full or unavailable - fail silently
  }
}

export function getCustomPacks(): CustomPack[] {
  return loadCustomPacks();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CreatePackModal({
  isOpen,
  onClose,
  onCreated,
}: CreatePackModalProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Step 1 state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<string>(CATEGORIES[0]);
  const [selectedIcon, setSelectedIcon] = useState("Shield");

  // Step 2 state
  const [pipelines, setPipelines] = useState<PipelineItem[]>([]);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [selectedPipelines, setSelectedPipelines] = useState<Set<string>>(new Set());
  const [selectedAlertRules, setSelectedAlertRules] = useState<Set<string>>(new Set());
  const [loadingData, setLoadingData] = useState(false);

  // General state
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Fetch pipelines and alert rules when entering step 2
  useEffect(() => {
    if (step !== 2 || pipelines.length > 0) return;

    const fetchData = async () => {
      setLoadingData(true);
      try {
        const [pipelineRes, alertRes] = await Promise.allSettled([
          fetch("/api/pipeline/list"),
          fetch("/api/alerts/rules"),
        ]);

        if (pipelineRes.status === "fulfilled" && pipelineRes.value.ok) {
          const data: PipelineItem[] = await pipelineRes.value.json();
          setPipelines(data);
        } else {
          // Fallback mock data when API unavailable
          setPipelines([
            { id: "pipe-1", name: "Object Detection" },
            { id: "pipe-2", name: "Audio Transcription" },
            { id: "pipe-3", name: "Motion Analysis" },
            { id: "pipe-4", name: "Face Recognition" },
            { id: "pipe-5", name: "Anomaly Detection" },
          ]);
        }

        if (alertRes.status === "fulfilled" && alertRes.value.ok) {
          const data: AlertRule[] = await alertRes.value.json();
          setAlertRules(data);
        } else {
          // Fallback mock data when API unavailable
          setAlertRules([
            { id: "rule-1", name: "High Priority Alert", severity: "critical" },
            { id: "rule-2", name: "Motion Detected", severity: "warning" },
            { id: "rule-3", name: "Audio Threshold Exceeded", severity: "warning" },
            { id: "rule-4", name: "System Health Check", severity: "info" },
          ]);
        }
      } catch {
        // Use fallback data on network error
        setPipelines([
          { id: "pipe-1", name: "Object Detection" },
          { id: "pipe-2", name: "Audio Transcription" },
          { id: "pipe-3", name: "Motion Analysis" },
        ]);
        setAlertRules([
          { id: "rule-1", name: "High Priority Alert", severity: "critical" },
          { id: "rule-2", name: "Motion Detected", severity: "warning" },
        ]);
      } finally {
        setLoadingData(false);
      }
    };

    fetchData();
  }, [step, pipelines.length]);

  const resetForm = useCallback(() => {
    setStep(1);
    setName("");
    setDescription("");
    setCategory(CATEGORIES[0]);
    setSelectedIcon("Shield");
    setPipelines([]);
    setAlertRules([]);
    setSelectedPipelines(new Set());
    setSelectedAlertRules(new Set());
    setError(null);
    setSaving(false);
  }, []);

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const togglePipeline = (id: string) => {
    setSelectedPipelines((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAlertRule = (id: string) => {
    setSelectedAlertRules((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleNext = () => {
    if (step === 1) {
      if (!name.trim()) {
        setError("Pack name is required.");
        return;
      }
      setError(null);
      setStep(2);
    } else if (step === 2) {
      setError(null);
      setStep(3);
    }
  };

  const handleBack = () => {
    setError(null);
    if (step === 2) setStep(1);
    else if (step === 3) setStep(2);
  };

  const handleSave = () => {
    setSaving(true);
    setError(null);

    const slug = `custom-${name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "")}`;

    const selectedPipelineNames = pipelines
      .filter((p) => selectedPipelines.has(p.id))
      .map((p) => p.name);
    const selectedAlertRuleNames = alertRules
      .filter((r) => selectedAlertRules.has(r.id))
      .map((r) => r.name);

    const newPack: CustomPack = {
      slug,
      name: name.trim(),
      description: description.trim(),
      category,
      icon: ICON_MAP[selectedIcon] ?? "cube",
      pipelineIds: Array.from(selectedPipelines),
      pipelineNames: selectedPipelineNames,
      alertRuleIds: Array.from(selectedAlertRules),
      alertRuleNames: selectedAlertRuleNames,
      createdAt: new Date().toISOString(),
      isCustom: true,
    };

    const existing = loadCustomPacks();
    // Prevent duplicate slug
    if (existing.some((p) => p.slug === slug)) {
      setError("A custom pack with this name already exists.");
      setSaving(false);
      return;
    }

    saveCustomPacks([...existing, newPack]);
    setSaving(false);
    resetForm();
    onCreated(newPack);
  };

  // ---------------------------------------------------------------------------
  // Step icon indicator
  // ---------------------------------------------------------------------------

  const iconForStep = (s: number) =>
    PRESET_ICONS.find((i) => i.label === selectedIcon)?.svg ?? PRESET_ICONS[0].svg;

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  const stepIndicator = (
    <div className="flex items-center justify-center gap-2 mb-6">
      {[1, 2, 3].map((s) => (
        <React.Fragment key={s}>
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
              s === step
                ? "bg-brand-600 text-white"
                : s < step
                  ? "bg-brand-100 text-brand-700"
                  : "bg-gray-100 text-gray-400"
            }`}
          >
            {s}
          </div>
          {s < 3 && (
            <div
              className={`h-0.5 w-8 ${
                s < step ? "bg-brand-400" : "bg-gray-200"
              }`}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );

  const renderStep1 = () => (
    <div className="space-y-4">
      {/* Name */}
      <div>
        <label htmlFor="pack-name" className="block text-sm font-medium text-gray-700 mb-1">
          Pack Name
        </label>
        <input
          id="pack-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Warehouse Safety"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
        />
      </div>

      {/* Description */}
      <div>
        <label htmlFor="pack-description" className="block text-sm font-medium text-gray-700 mb-1">
          Description
        </label>
        <textarea
          id="pack-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          placeholder="What does this pack cover?"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
        />
      </div>

      {/* Category */}
      <div>
        <label htmlFor="pack-category" className="block text-sm font-medium text-gray-700 mb-1">
          Category
        </label>
        <select
          id="pack-category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent bg-white"
        >
          {CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
      </div>

      {/* Icon Selector */}
      <div>
        <span className="block text-sm font-medium text-gray-700 mb-2">Icon</span>
        <div className="grid grid-cols-4 gap-2">
          {PRESET_ICONS.map((icon) => (
            <button
              key={icon.label}
              type="button"
              onClick={() => setSelectedIcon(icon.label)}
              className={`flex flex-col items-center gap-1 rounded-lg border p-3 transition-colors ${
                selectedIcon === icon.label
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-gray-200 bg-white text-gray-500 hover:bg-gray-50"
              }`}
            >
              {icon.svg}
              <span className="text-[10px] font-medium">{icon.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-5">
      {loadingData ? (
        <div className="flex items-center justify-center py-8 text-sm text-gray-500">
          Loading pipelines and alert rules...
        </div>
      ) : (
        <>
          {/* Pipelines */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Pipelines ({selectedPipelines.size} selected)
            </h4>
            <div className="max-h-40 overflow-y-auto rounded-lg border border-gray-200 divide-y divide-gray-100">
              {pipelines.map((pipeline) => (
                <label
                  key={pipeline.id}
                  className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedPipelines.has(pipeline.id)}
                    onChange={() => togglePipeline(pipeline.id)}
                    className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                  />
                  <span className="text-sm text-gray-700">{pipeline.name}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Alert Rules */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Alert Rules ({selectedAlertRules.size} selected)
            </h4>
            <div className="max-h-40 overflow-y-auto rounded-lg border border-gray-200 divide-y divide-gray-100">
              {alertRules.map((rule) => (
                <label
                  key={rule.id}
                  className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedAlertRules.has(rule.id)}
                    onChange={() => toggleAlertRule(rule.id)}
                    className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                  />
                  <span className="text-sm text-gray-700">{rule.name}</span>
                  {rule.severity && (
                    <span className={`ml-auto text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                      rule.severity === "critical"
                        ? "bg-red-100 text-red-700"
                        : rule.severity === "warning"
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-blue-100 text-blue-700"
                    }`}>
                      {rule.severity}
                    </span>
                  )}
                </label>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );

  const renderStep3 = () => {
    const selectedPipelineNames = pipelines
      .filter((p) => selectedPipelines.has(p.id))
      .map((p) => p.name);
    const selectedAlertRuleNames = alertRules
      .filter((r) => selectedAlertRules.has(r.id))
      .map((r) => r.name);

    return (
      <div className="space-y-4">
        <h4 className="text-sm font-semibold text-gray-900">Review Your Pack</h4>

        {/* Pack Info */}
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-2">
          <div className="flex items-center gap-3">
            <div className="text-brand-600">{iconForStep(step)}</div>
            <div>
              <p className="font-semibold text-gray-900">{name.trim()}</p>
              <p className="text-xs text-gray-500">{category}</p>
            </div>
          </div>
          {description.trim() && (
            <p className="text-sm text-gray-600">{description.trim()}</p>
          )}
        </div>

        {/* Selected Pipelines */}
        <div>
          <h5 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
            Pipelines ({selectedPipelineNames.length})
          </h5>
          {selectedPipelineNames.length === 0 ? (
            <p className="text-sm text-gray-400 italic">None selected</p>
          ) : (
            <ul className="space-y-1">
              {selectedPipelineNames.map((n) => (
                <li key={n} className="text-sm text-gray-700 flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-brand-500" />
                  {n}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Selected Alert Rules */}
        <div>
          <h5 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
            Alert Rules ({selectedAlertRuleNames.length})
          </h5>
          {selectedAlertRuleNames.length === 0 ? (
            <p className="text-sm text-gray-400 italic">None selected</p>
          ) : (
            <ul className="space-y-1">
              {selectedAlertRuleNames.map((n) => (
                <li key={n} className="text-sm text-gray-700 flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                  {n}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    );
  };

  // ---------------------------------------------------------------------------
  // Footer buttons
  // ---------------------------------------------------------------------------

  const footer = (
    <>
      {step > 1 && (
        <button
          onClick={handleBack}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
      )}
      <button
        onClick={handleClose}
        className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        Cancel
      </button>
      {step < 3 ? (
        <button
          onClick={handleNext}
          disabled={step === 1 && !name.trim()}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Next
        </button>
      ) : (
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? "Saving..." : "Save as Pack"}
        </button>
      )}
    </>
  );

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const stepTitles: Record<number, string> = {
    1: "Create Custom Pack - Details",
    2: "Create Custom Pack - Select Resources",
    3: "Create Custom Pack - Review",
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={stepTitles[step] ?? "Create Custom Pack"}
      footer={footer}
    >
      <div>
        {stepIndicator}

        {/* Error banner */}
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700 mb-4">
            {error}
          </div>
        )}

        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
      </div>
    </Modal>
  );
}
