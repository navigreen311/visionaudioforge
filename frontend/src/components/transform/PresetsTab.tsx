"use client";

import React, { useCallback, useEffect, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface PresetConfig {
  tab: "audio" | "video";
  operation: string;
  params: Record<string, string | number>;
}

export interface Preset {
  id: string;
  name: string;
  description: string;
  gradient: string;
  operationType: string;
  config: PresetConfig;
  builtIn?: boolean;
}

export interface PresetsTabProps {
  onApplyPreset: (preset: Preset) => void;
}

/* ------------------------------------------------------------------ */
/*  Built-in presets (2 rows x 4 cards)                                */
/* ------------------------------------------------------------------ */

const BUILT_IN_PRESETS: Preset[] = [
  {
    id: "builtin-clean-bg",
    name: "Clean Background",
    description: "Remove background with threshold method",
    gradient: "from-sky-400 to-blue-600",
    operationType: "Video",
    config: { tab: "video", operation: "background-remove", params: { method: "threshold" } },
    builtIn: true,
  },
  {
    id: "builtin-cinematic-upscale",
    name: "Cinematic Upscale",
    description: "4x super resolution with cinematic color grade",
    gradient: "from-purple-500 to-indigo-700",
    operationType: "Video",
    config: { tab: "video", operation: "super-resolution", params: { scale: 4 } },
    builtIn: true,
  },
  {
    id: "builtin-social-square",
    name: "Social Square",
    description: "Auto-crop to 1:1 for social media",
    gradient: "from-pink-400 to-rose-600",
    operationType: "Video",
    config: { tab: "video", operation: "auto-crop", params: { aspect: "1:1" } },
    builtIn: true,
  },
  {
    id: "builtin-podcast-clean",
    name: "Podcast Clean",
    description: "Denoise and remove silence for podcasts",
    gradient: "from-emerald-400 to-teal-600",
    operationType: "Audio",
    config: { tab: "audio", operation: "denoise", params: {} },
    builtIn: true,
  },
  {
    id: "builtin-voice-enhance",
    name: "Voice Enhance",
    description: "Pitch correction and voice clarity boost",
    gradient: "from-amber-400 to-orange-600",
    operationType: "Audio",
    config: { tab: "audio", operation: "pitch-shift", params: {} },
    builtIn: true,
  },
  {
    id: "builtin-anime-style",
    name: "Anime Style",
    description: "Cartoon style transfer for anime look",
    gradient: "from-fuchsia-400 to-purple-600",
    operationType: "Video",
    config: { tab: "video", operation: "style", params: { style: "cartoon" } },
    builtIn: true,
  },
  {
    id: "builtin-warm-film",
    name: "Warm Film",
    description: "Vintage warm color grading",
    gradient: "from-yellow-400 to-red-500",
    operationType: "Video",
    config: { tab: "video", operation: "color-grade", params: { preset: "vintage" } },
    builtIn: true,
  },
  {
    id: "builtin-highlight-reel",
    name: "Highlight Reel",
    description: "High contrast dramatic color grade",
    gradient: "from-cyan-400 to-blue-700",
    operationType: "Video",
    config: { tab: "video", operation: "color-grade", params: { preset: "high_contrast" } },
    builtIn: true,
  },
];

const STORAGE_KEY = "vaf_transform_presets";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function uid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function loadUserPresets(): Preset[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as Preset[];
  } catch {
    return [];
  }
}

function saveUserPresets(presets: Preset[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(presets));
}

/* ------------------------------------------------------------------ */
/*  Gradient colors for random user presets                            */
/* ------------------------------------------------------------------ */

const USER_GRADIENTS = [
  "from-violet-400 to-purple-600",
  "from-teal-400 to-cyan-600",
  "from-rose-400 to-pink-600",
  "from-lime-400 to-green-600",
  "from-orange-400 to-red-600",
  "from-sky-400 to-indigo-600",
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function PresetsTab({ onApplyPreset }: PresetsTabProps) {
  const [userPresets, setUserPresets] = useState<Preset[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formTab, setFormTab] = useState<"audio" | "video">("video");
  const [formOperation, setFormOperation] = useState("color-grade");

  /* Load user presets from localStorage */
  useEffect(() => {
    setUserPresets(loadUserPresets());
  }, []);

  /* Persist changes */
  const persist = useCallback((next: Preset[]) => {
    setUserPresets(next);
    saveUserPresets(next);
  }, []);

  /* ---- Open save modal ---- */
  const openSaveModal = useCallback(() => {
    setEditingId(null);
    setFormName("");
    setFormDesc("");
    setFormTab("video");
    setFormOperation("color-grade");
    setShowModal(true);
  }, []);

  /* ---- Open edit modal ---- */
  const openEditModal = useCallback((preset: Preset) => {
    setEditingId(preset.id);
    setFormName(preset.name);
    setFormDesc(preset.description);
    setFormTab(preset.config.tab);
    setFormOperation(preset.config.operation);
    setShowModal(true);
  }, []);

  /* ---- Save / Update preset ---- */
  const handleSave = useCallback(() => {
    if (!formName.trim()) return;

    if (editingId) {
      const next = userPresets.map((p) =>
        p.id === editingId
          ? {
              ...p,
              name: formName.trim(),
              description: formDesc.trim(),
              config: { tab: formTab, operation: formOperation, params: {} },
              operationType: formTab === "audio" ? "Audio" : "Video",
            }
          : p,
      );
      persist(next);
    } else {
      const gradient = USER_GRADIENTS[userPresets.length % USER_GRADIENTS.length];
      const newPreset: Preset = {
        id: uid(),
        name: formName.trim(),
        description: formDesc.trim(),
        gradient,
        operationType: formTab === "audio" ? "Audio" : "Video",
        config: { tab: formTab, operation: formOperation, params: {} },
      };
      persist([...userPresets, newPreset]);
    }

    setShowModal(false);
  }, [formName, formDesc, formTab, formOperation, editingId, userPresets, persist]);

  /* ---- Delete preset ---- */
  const deletePreset = useCallback(
    (id: string) => {
      persist(userPresets.filter((p) => p.id !== id));
    },
    [userPresets, persist],
  );

  return (
    <div className="space-y-8">
      {/* ---- Built-in Presets ---- */}
      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Built-in Presets</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {BUILT_IN_PRESETS.map((preset) => (
            <PresetCard
              key={preset.id}
              preset={preset}
              onApply={() => onApplyPreset(preset)}
            />
          ))}
        </div>
      </section>

      {/* ---- User Presets ---- */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">My Presets</h3>
          <button
            onClick={openSaveModal}
            className="inline-flex items-center gap-2 rounded-lg border border-transparent bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Save Current Settings
          </button>
        </div>

        {userPresets.length === 0 ? (
          <div className="rounded-lg border-2 border-dashed border-gray-200 bg-gray-50 p-8 text-center">
            <svg className="mx-auto h-10 w-10 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <p className="mt-3 text-sm text-gray-500">
              No saved presets yet. Click &quot;Save Current Settings&quot; to create one.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {userPresets.map((preset) => (
              <PresetCard
                key={preset.id}
                preset={preset}
                onApply={() => onApplyPreset(preset)}
                onEdit={() => openEditModal(preset)}
                onDelete={() => deletePreset(preset.id)}
              />
            ))}
          </div>
        )}
      </section>

      {/* ---- Save / Edit Modal ---- */}
      {showModal && (
        <ModalOverlay onClose={() => setShowModal(false)}>
          <div className="relative z-10 w-full max-w-lg rounded-lg bg-white shadow-xl mx-4">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
              <h2 className="text-lg font-semibold text-gray-900">
                {editingId ? "Edit Preset" : "Save Preset"}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Body */}
            <div className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="My awesome preset"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  placeholder="What this preset does..."
                  rows={2}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
                />
              </div>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                  <select
                    value={formTab}
                    onChange={(e) => setFormTab(e.target.value as "audio" | "video")}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  >
                    <option value="video">Video / Image</option>
                    <option value="audio">Audio</option>
                  </select>
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Operation</label>
                  <select
                    value={formOperation}
                    onChange={(e) => setFormOperation(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  >
                    {formTab === "video" ? (
                      <>
                        <option value="background-remove">Background Remove</option>
                        <option value="super-resolution">Super Resolution</option>
                        <option value="style">Style Transfer</option>
                        <option value="auto-crop">Auto Crop</option>
                        <option value="color-grade">Color Grade</option>
                        <option value="subtitle">Subtitle</option>
                        <option value="inpaint">Inpaint</option>
                        <option value="smart-crop">Smart Crop</option>
                      </>
                    ) : (
                      <>
                        <option value="denoise">Denoise</option>
                        <option value="silence-remove">Remove Silence</option>
                        <option value="pitch-shift">Pitch Shift</option>
                        <option value="time-stretch">Time Stretch</option>
                        <option value="eq">Equalizer</option>
                        <option value="voice-convert">Voice Conversion</option>
                      </>
                    )}
                  </select>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-200 px-6 py-3 bg-gray-50 rounded-b-lg flex justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="inline-flex items-center rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!formName.trim()}
                className="inline-flex items-center rounded-lg border border-transparent bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {editingId ? "Update" : "Save"}
              </button>
            </div>
          </div>
        </ModalOverlay>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  PresetCard                                                         */
/* ------------------------------------------------------------------ */

interface PresetCardProps {
  preset: Preset;
  onApply: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

function PresetCard({ preset, onApply, onEdit, onDelete }: PresetCardProps) {
  return (
    <div className="group relative flex flex-col rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden transition-shadow hover:shadow-md">
      {/* Gradient thumbnail */}
      <div className={`h-24 w-full bg-gradient-to-br ${preset.gradient}`} />

      {/* Content */}
      <div className="flex flex-1 flex-col p-4">
        <h4 className="text-sm font-semibold text-gray-900 mb-1">{preset.name}</h4>
        <p className="text-xs text-gray-500 mb-3 line-clamp-2 flex-1">{preset.description}</p>

        {/* Operation type badge */}
        <div className="flex items-center justify-between">
          <span
            className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
            style={{
              backgroundColor: preset.operationType === "Audio" ? "#dbeafe" : "#f0fdf4",
              color: preset.operationType === "Audio" ? "#185FA5" : "#0F6E56",
            }}
          >
            {preset.operationType}
          </span>
          <button
            onClick={onApply}
            className="rounded-lg px-3 py-1 text-xs font-medium text-white transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1"
            style={{ backgroundColor: "#185FA5" }}
          >
            Apply
          </button>
        </div>
      </div>

      {/* Edit / Delete actions for user presets */}
      {(onEdit || onDelete) && (
        <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {onEdit && (
            <button
              onClick={onEdit}
              className="rounded bg-white/90 p-1 text-gray-600 hover:bg-white hover:text-gray-900 shadow-sm transition-colors"
              title="Edit"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="rounded bg-white/90 p-1 text-red-500 hover:bg-white hover:text-red-700 shadow-sm transition-colors"
              title="Delete"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ModalOverlay (lightweight inline portal-free overlay)              */
/* ------------------------------------------------------------------ */

interface ModalOverlayProps {
  onClose: () => void;
  children: React.ReactNode;
}

function ModalOverlay({ onClose, children }: ModalOverlayProps) {
  /* Close on Escape */
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handleEsc);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      {children}
    </div>
  );
}
