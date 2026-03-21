"use client";

import { useCallback, useEffect, useState } from "react";
import { ButtonGroup, MultiSelect, Section, Slider } from "./shared";

interface Props {
  onParamsChange: (params: Record<string, unknown>) => void;
}

const DETECTION_OPTIONS = [
  { value: "motion", label: "Motion" },
  { value: "faces", label: "Faces" },
  { value: "objects", label: "Objects" },
  { value: "audio_peaks", label: "Audio Peaks" },
];

const OUTPUT_FORMATS = [
  { value: "mp4", label: "MP4" },
  { value: "gif", label: "GIF" },
  { value: "webm", label: "WebM" },
];

export default function HighlightClipControls({ onParamsChange }: Props) {
  const [duration, setDuration] = useState(30);
  const [detection, setDetection] = useState<string[]>(["motion"]);
  const [outputFormat, setOutputFormat] = useState("mp4");

  const emit = useCallback(() => {
    onParamsChange({
      duration,
      detection,
      outputFormat,
    });
  }, [duration, detection, outputFormat, onParamsChange]);

  useEffect(() => {
    emit();
  }, [emit]);

  return (
    <Section>
      <Slider
        label="Duration"
        value={duration}
        min={5}
        max={120}
        suffix="s"
        onChange={setDuration}
      />
      <MultiSelect
        label="Detection"
        options={DETECTION_OPTIONS}
        selected={detection}
        onChange={setDetection}
      />
      <ButtonGroup
        label="Output Format"
        value={outputFormat}
        options={OUTPUT_FORMATS}
        onChange={setOutputFormat}
      />
    </Section>
  );
}
