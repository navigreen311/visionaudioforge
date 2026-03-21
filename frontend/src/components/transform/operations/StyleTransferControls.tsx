"use client";

import { useCallback, useEffect, useState } from "react";
import { Section, Slider, Toggle } from "./shared";

interface Props {
  onParamsChange: (params: Record<string, unknown>) => void;
}

const STYLE_PRESETS = [
  { value: "monet", label: "Monet", emoji: "🎨" },
  { value: "van_gogh", label: "Van Gogh", emoji: "🌻" },
  { value: "watercolor", label: "Watercolor", emoji: "💧" },
  { value: "sketch", label: "Sketch", emoji: "✏️" },
  { value: "oil_paint", label: "Oil Paint", emoji: "🖌️" },
  { value: "anime", label: "Anime", emoji: "⛩️" },
  { value: "neon", label: "Neon", emoji: "💡" },
  { value: "minimalist", label: "Minimalist", emoji: "◻️" },
] as const;

export default function StyleTransferControls({ onParamsChange }: Props) {
  const [styleStrength, setStyleStrength] = useState(75);
  const [selectedStyle, setSelectedStyle] = useState("monet");
  const [contentWeight, setContentWeight] = useState(50);
  const [preserveColors, setPreserveColors] = useState(false);

  const emit = useCallback(() => {
    onParamsChange({
      styleStrength,
      selectedStyle,
      contentWeight,
      preserveColors,
    });
  }, [styleStrength, selectedStyle, contentWeight, preserveColors, onParamsChange]);

  useEffect(() => {
    emit();
  }, [emit]);

  return (
    <Section>
      <Slider
        label="Style Strength"
        value={styleStrength}
        min={0}
        max={100}
        suffix="%"
        onChange={setStyleStrength}
      />

      <div className="space-y-1">
        <span className="block text-sm font-medium text-gray-700">Style Preset</span>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {STYLE_PRESETS.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setSelectedStyle(s.value)}
              className={`flex flex-col items-center gap-1 rounded-lg border-2 p-3 text-sm font-medium transition-colors ${
                selectedStyle === s.value
                  ? "border-brand-600 bg-brand-50 text-brand-700"
                  : "border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50"
              }`}
            >
              <span className="text-xl">{s.emoji}</span>
              <span>{s.label}</span>
            </button>
          ))}
        </div>
      </div>

      <Slider
        label="Content Weight"
        value={contentWeight}
        min={0}
        max={100}
        onChange={setContentWeight}
      />
      <Toggle
        label="Preserve Colors"
        checked={preserveColors}
        onChange={setPreserveColors}
      />
    </Section>
  );
}
