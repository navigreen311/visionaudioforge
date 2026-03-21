"use client";

import { useCallback, useEffect, useState } from "react";
import { Dropdown, NumberInput, Section } from "./shared";

interface Props {
  onParamsChange: (params: Record<string, unknown>) => void;
}

const TARGET_FPS_OPTIONS = [
  { value: "30", label: "30 FPS" },
  { value: "60", label: "60 FPS" },
  { value: "120", label: "120 FPS" },
  { value: "240", label: "240 FPS" },
];

const METHODS = [
  { value: "rife", label: "RIFE" },
  { value: "film", label: "FILM" },
  { value: "dain", label: "DAIN" },
];

export default function FrameInterpolateControls({ onParamsChange }: Props) {
  const [targetFps, setTargetFps] = useState("60");
  const [inputFps, setInputFps] = useState(24);
  const [method, setMethod] = useState("rife");

  const emit = useCallback(() => {
    onParamsChange({
      targetFps: Number(targetFps),
      inputFps,
      method,
    });
  }, [targetFps, inputFps, method, onParamsChange]);

  useEffect(() => {
    emit();
  }, [emit]);

  return (
    <Section>
      <Dropdown
        label="Target FPS"
        value={targetFps}
        options={TARGET_FPS_OPTIONS}
        onChange={setTargetFps}
      />
      <NumberInput
        label="Input FPS"
        value={inputFps}
        min={1}
        max={240}
        onChange={setInputFps}
      />
      <Dropdown label="Method" value={method} options={METHODS} onChange={setMethod} />
    </Section>
  );
}
