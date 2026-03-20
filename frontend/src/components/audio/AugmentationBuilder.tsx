"use client";

import React, { useState } from "react";
import Button from "@/components/ui/Button";
import type { AugmentationStep } from "@/lib/api";

const PRESETS = [
  { id: "speech_robust", label: "Speech Robust" },
  { id: "music_robust", label: "Music Robust" },
  { id: "environmental", label: "Environmental" },
  { id: "light", label: "Light" },
  { id: "heavy", label: "Heavy" },
] as const;

const AUGMENTATION_TYPES = [
  {
    type: "noise",
    label: "Add Noise",
    params: [
      { key: "noise_type", label: "Type", default: "white" },
      { key: "snr_db", label: "SNR (dB)", default: 20 },
    ],
  },
  {
    type: "stretch",
    label: "Time Stretch",
    params: [{ key: "rate", label: "Rate", default: 1.2 }],
  },
  {
    type: "pitch",
    label: "Pitch Shift",
    params: [{ key: "semitones", label: "Semitones", default: 2 }],
  },
  {
    type: "shift",
    label: "Time Shift",
    params: [{ key: "shift_ms", label: "Shift (ms)", default: 100 }],
  },
  {
    type: "freq_mask",
    label: "Frequency Mask",
    params: [
      { key: "num_masks", label: "Num Masks", default: 1 },
      { key: "mask_size", label: "Mask Size", default: 20 },
    ],
  },
  {
    type: "time_mask",
    label: "Time Mask",
    params: [
      { key: "num_masks", label: "Num Masks", default: 1 },
      { key: "mask_size", label: "Mask Size", default: 20 },
    ],
  },
] as const;

interface AugmentationBuilderProps {
  onConfigChange: (config: {
    preset?: string;
    steps?: AugmentationStep[];
  }) => void;
}

export default function AugmentationBuilder({
  onConfigChange,
}: AugmentationBuilderProps) {
  const [mode, setMode] = useState<"preset" | "custom">("preset");
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [steps, setSteps] = useState<AugmentationStep[]>([]);
  const [addType, setAddType] = useState(AUGMENTATION_TYPES[0].type);

  const selectPreset = (id: string) => {
    setSelectedPreset(id);
    setMode("preset");
    onConfigChange({ preset: id });
  };

  const addStep = () => {
    const def = AUGMENTATION_TYPES.find((a) => a.type === addType);
    if (!def) return;
    const params: Record<string, number | string> = {};
    def.params.forEach((p) => {
      params[p.key] = p.default;
    });
    const newSteps = [...steps, { type: addType, params }];
    setSteps(newSteps);
    setMode("custom");
    setSelectedPreset(null);
    onConfigChange({ steps: newSteps });
  };

  const removeStep = (index: number) => {
    const newSteps = steps.filter((_, i) => i !== index);
    setSteps(newSteps);
    onConfigChange({ steps: newSteps });
  };

  const moveStep = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= steps.length) return;
    const newSteps = [...steps];
    [newSteps[index], newSteps[target]] = [newSteps[target], newSteps[index]];
    setSteps(newSteps);
    onConfigChange({ steps: newSteps });
  };

  const updateParam = (
    stepIndex: number,
    key: string,
    value: string | number,
  ) => {
    const newSteps = [...steps];
    newSteps[stepIndex] = {
      ...newSteps[stepIndex],
      params: { ...newSteps[stepIndex].params, [key]: value },
    };
    setSteps(newSteps);
    onConfigChange({ steps: newSteps });
  };

  return (
    <div className="space-y-6">
      {/* Preset Buttons */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Presets
        </label>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((preset) => (
            <Button
              key={preset.id}
              variant={
                mode === "preset" && selectedPreset === preset.id
                  ? "primary"
                  : "secondary"
              }
              size="sm"
              onClick={() => selectPreset(preset.id)}
            >
              {preset.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-white px-3 text-sm text-gray-500">
            OR build custom pipeline
          </span>
        </div>
      </div>

      {/* Custom Pipeline Builder */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Custom Pipeline
        </label>
        <div className="flex gap-2 mb-3">
          <select
            value={addType}
            onChange={(e) => setAddType(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          >
            {AUGMENTATION_TYPES.map((a) => (
              <option key={a.type} value={a.type}>
                {a.label}
              </option>
            ))}
          </select>
          <Button variant="secondary" size="sm" onClick={addStep}>
            + Add Step
          </Button>
        </div>

        {steps.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-4">
            No augmentation steps added yet
          </p>
        )}

        <div className="space-y-2">
          {steps.map((step, index) => {
            const def = AUGMENTATION_TYPES.find((a) => a.type === step.type);
            return (
              <div
                key={index}
                className="flex items-start gap-3 rounded-lg border border-gray-200 bg-gray-50 p-3"
              >
                <div className="flex flex-col gap-1">
                  <button
                    onClick={() => moveStep(index, -1)}
                    disabled={index === 0}
                    className="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-xs"
                    title="Move up"
                  >
                    &#9650;
                  </button>
                  <button
                    onClick={() => moveStep(index, 1)}
                    disabled={index === steps.length - 1}
                    className="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-xs"
                    title="Move down"
                  >
                    &#9660;
                  </button>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800 mb-1">
                    {index + 1}. {def?.label ?? step.type}
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {def?.params.map((p) => (
                      <label
                        key={p.key}
                        className="flex items-center gap-1.5 text-xs text-gray-600"
                      >
                        {p.label}:
                        <input
                          type={
                            typeof p.default === "number" ? "number" : "text"
                          }
                          value={step.params[p.key] ?? p.default}
                          onChange={(e) =>
                            updateParam(
                              index,
                              p.key,
                              typeof p.default === "number"
                                ? Number(e.target.value)
                                : e.target.value,
                            )
                          }
                          className="w-20 rounded border border-gray-300 px-2 py-0.5 text-xs focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                          step={typeof p.default === "number" ? "any" : undefined}
                        />
                      </label>
                    ))}
                  </div>
                </div>
                <button
                  onClick={() => removeStep(index)}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                  title="Remove step"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
