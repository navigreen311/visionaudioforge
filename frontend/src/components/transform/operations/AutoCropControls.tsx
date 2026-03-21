"use client";

import { useCallback, useEffect, useState } from "react";
import { ButtonGroup, Dropdown, NumberInput, Section, Slider } from "./shared";

interface Props {
  onParamsChange: (params: Record<string, unknown>) => void;
}

const ASPECT_RATIOS = [
  { value: "free", label: "Free" },
  { value: "1:1", label: "1:1" },
  { value: "4:3", label: "4:3" },
  { value: "16:9", label: "16:9" },
  { value: "9:16", label: "9:16" },
  { value: "3:2", label: "3:2" },
];

const SUBJECT_FOCUS = [
  { value: "auto", label: "Auto" },
  { value: "face", label: "Face" },
  { value: "object", label: "Object" },
  { value: "text", label: "Text" },
];

export default function AutoCropControls({ onParamsChange }: Props) {
  const [aspectRatio, setAspectRatio] = useState("free");
  const [subjectFocus, setSubjectFocus] = useState("auto");
  const [padding, setPadding] = useState(5);
  const [minWidth, setMinWidth] = useState(100);
  const [minHeight, setMinHeight] = useState(100);

  const emit = useCallback(() => {
    onParamsChange({
      aspectRatio,
      subjectFocus,
      padding,
      minWidth,
      minHeight,
    });
  }, [aspectRatio, subjectFocus, padding, minWidth, minHeight, onParamsChange]);

  useEffect(() => {
    emit();
  }, [emit]);

  return (
    <Section>
      <ButtonGroup
        label="Aspect Ratio"
        value={aspectRatio}
        options={ASPECT_RATIOS}
        onChange={setAspectRatio}
      />
      <Dropdown
        label="Subject Focus"
        value={subjectFocus}
        options={SUBJECT_FOCUS}
        onChange={setSubjectFocus}
      />
      <Slider
        label="Padding"
        value={padding}
        min={0}
        max={20}
        suffix="%"
        onChange={setPadding}
      />
      <div className="grid grid-cols-2 gap-3">
        <NumberInput
          label="Min Width (px)"
          value={minWidth}
          min={1}
          onChange={setMinWidth}
        />
        <NumberInput
          label="Min Height (px)"
          value={minHeight}
          min={1}
          onChange={setMinHeight}
        />
      </div>
    </Section>
  );
}
