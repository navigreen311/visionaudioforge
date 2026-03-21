"use client";

import { useCallback, useEffect, useState } from "react";
import { ColorPicker, Dropdown, Section, Slider } from "./shared";

interface Props {
  onParamsChange: (params: Record<string, unknown>) => void;
}

const METHODS = [
  { value: "threshold", label: "Threshold" },
  { value: "u2net", label: "U2Net" },
  { value: "grabcut", label: "GrabCut" },
  { value: "sam", label: "SAM" },
];

const OUTPUT_FORMATS = [
  { value: "png_transparent", label: "PNG (Transparent)" },
  { value: "jpeg_white", label: "JPEG (White)" },
  { value: "jpeg_custom", label: "JPEG (Custom Color)" },
];

export default function BackgroundRemoveControls({ onParamsChange }: Props) {
  const [method, setMethod] = useState("u2net");
  const [edgeRefinement, setEdgeRefinement] = useState(3);
  const [outputFormat, setOutputFormat] = useState("png_transparent");
  const [customColor, setCustomColor] = useState("#ffffff");

  const emit = useCallback(() => {
    onParamsChange({
      method,
      edgeRefinement,
      outputFormat,
      ...(outputFormat === "jpeg_custom" ? { customColor } : {}),
    });
  }, [method, edgeRefinement, outputFormat, customColor, onParamsChange]);

  useEffect(() => {
    emit();
  }, [emit]);

  return (
    <Section>
      <Dropdown label="Method" value={method} options={METHODS} onChange={setMethod} />
      <Slider
        label="Edge Refinement"
        value={edgeRefinement}
        min={0}
        max={10}
        onChange={setEdgeRefinement}
      />
      <Dropdown
        label="Output Format"
        value={outputFormat}
        options={OUTPUT_FORMATS}
        onChange={setOutputFormat}
      />
      {outputFormat === "jpeg_custom" && (
        <ColorPicker
          label="Background Color"
          value={customColor}
          onChange={setCustomColor}
        />
      )}
    </Section>
  );
}
