"use client";

import { useCallback, useEffect, useState } from "react";
import { ButtonGroup, Dropdown, Section, Slider, Toggle } from "./shared";

interface Props {
  onParamsChange: (params: Record<string, unknown>) => void;
}

const SCALE_OPTIONS = [
  { value: "2", label: "2x" },
  { value: "4", label: "4x" },
  { value: "8", label: "8x" },
];

const MODELS = [
  { value: "esrgan", label: "ESRGAN" },
  { value: "real_esrgan", label: "Real-ESRGAN" },
  { value: "bsrgan", label: "BSRGAN" },
  { value: "swinir", label: "SwinIR" },
];

export default function SuperResolutionControls({ onParamsChange }: Props) {
  const [scaleFactor, setScaleFactor] = useState("4");
  const [model, setModel] = useState("real_esrgan");
  const [denoise, setDenoise] = useState(0.5);
  const [faceEnhancement, setFaceEnhancement] = useState(false);

  const emit = useCallback(() => {
    onParamsChange({
      scaleFactor: Number(scaleFactor),
      model,
      denoise,
      faceEnhancement,
    });
  }, [scaleFactor, model, denoise, faceEnhancement, onParamsChange]);

  useEffect(() => {
    emit();
  }, [emit]);

  return (
    <Section>
      <ButtonGroup
        label="Scale Factor"
        value={scaleFactor}
        options={SCALE_OPTIONS}
        onChange={setScaleFactor}
      />
      <Dropdown label="Model" value={model} options={MODELS} onChange={setModel} />
      <Slider
        label="Denoise"
        value={denoise}
        min={0}
        max={1}
        step={0.01}
        onChange={setDenoise}
      />
      <Toggle
        label="Face Enhancement"
        checked={faceEnhancement}
        onChange={setFaceEnhancement}
      />
    </Section>
  );
}
