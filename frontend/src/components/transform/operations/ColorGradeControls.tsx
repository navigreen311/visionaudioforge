"use client";

import { useCallback, useEffect, useState } from "react";
import { Dropdown, Section, Slider } from "./shared";

interface Props {
  onParamsChange: (params: Record<string, unknown>) => void;
}

const LUT_PRESETS = [
  { value: "none", label: "None" },
  { value: "cinematic", label: "Cinematic" },
  { value: "warm", label: "Warm" },
  { value: "cool", label: "Cool" },
  { value: "vintage", label: "Vintage" },
  { value: "faded", label: "Faded" },
  { value: "high_contrast", label: "High Contrast" },
  { value: "matte", label: "Matte" },
];

interface ColorState {
  lutPreset: string;
  brightness: number;
  contrast: number;
  saturation: number;
  hueShift: number;
}

const DEFAULTS: ColorState = {
  lutPreset: "none",
  brightness: 0,
  contrast: 1.0,
  saturation: 1.0,
  hueShift: 0,
};

export default function ColorGradeControls({ onParamsChange }: Props) {
  const [state, setState] = useState<ColorState>(DEFAULTS);

  const update = useCallback(
    <K extends keyof ColorState>(key: K, value: ColorState[K]) => {
      setState((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const resetAll = useCallback(() => {
    setState(DEFAULTS);
  }, []);

  const emit = useCallback(() => {
    onParamsChange({ ...state });
  }, [state, onParamsChange]);

  useEffect(() => {
    emit();
  }, [emit]);

  return (
    <Section>
      <Dropdown
        label="LUT Preset"
        value={state.lutPreset}
        options={LUT_PRESETS}
        onChange={(v) => update("lutPreset", v)}
      />
      <Slider
        label="Brightness"
        value={state.brightness}
        min={-100}
        max={100}
        onChange={(v) => update("brightness", v)}
      />
      <Slider
        label="Contrast"
        value={state.contrast}
        min={0.1}
        max={3.0}
        step={0.01}
        onChange={(v) => update("contrast", v)}
      />
      <Slider
        label="Saturation"
        value={state.saturation}
        min={0}
        max={2.0}
        step={0.01}
        onChange={(v) => update("saturation", v)}
      />
      <Slider
        label="Hue Shift"
        value={state.hueShift}
        min={-180}
        max={180}
        suffix={"\u00B0"}
        onChange={(v) => update("hueShift", v)}
      />
      <button
        type="button"
        onClick={resetAll}
        className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-100"
      >
        Reset All
      </button>
    </Section>
  );
}
