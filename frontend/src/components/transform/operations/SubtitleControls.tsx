"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ButtonGroup,
  ColorPicker,
  Dropdown,
  Section,
  Slider,
  TextInput,
  Toggle,
} from "./shared";

interface Props {
  onParamsChange: (params: Record<string, unknown>) => void;
}

const FONTS = [
  { value: "arial", label: "Arial" },
  { value: "helvetica", label: "Helvetica" },
  { value: "times_new_roman", label: "Times New Roman" },
  { value: "courier", label: "Courier" },
  { value: "georgia", label: "Georgia" },
  { value: "verdana", label: "Verdana" },
  { value: "impact", label: "Impact" },
  { value: "comic_sans", label: "Comic Sans" },
];

const POSITIONS = [
  { value: "top", label: "Top" },
  { value: "center", label: "Center" },
  { value: "bottom", label: "Bottom" },
];

export default function SubtitleControls({ onParamsChange }: Props) {
  const [text, setText] = useState("");
  const [font, setFont] = useState("arial");
  const [fontSize, setFontSize] = useState(24);
  const [color, setColor] = useState("#ffffff");
  const [position, setPosition] = useState("bottom");
  const [outline, setOutline] = useState(true);
  const [outlineColor, setOutlineColor] = useState("#000000");

  const emit = useCallback(() => {
    onParamsChange({
      text,
      font,
      fontSize,
      color,
      position,
      outline,
      ...(outline ? { outlineColor } : {}),
    });
  }, [text, font, fontSize, color, position, outline, outlineColor, onParamsChange]);

  useEffect(() => {
    emit();
  }, [emit]);

  return (
    <Section>
      <TextInput
        label="Subtitle Text"
        value={text}
        placeholder="Enter subtitle text..."
        onChange={setText}
      />
      <Dropdown label="Font" value={font} options={FONTS} onChange={setFont} />
      <Slider
        label="Font Size"
        value={fontSize}
        min={12}
        max={72}
        suffix="px"
        onChange={setFontSize}
      />
      <ColorPicker label="Text Color" value={color} onChange={setColor} />
      <ButtonGroup
        label="Position"
        value={position}
        options={POSITIONS}
        onChange={setPosition}
      />
      <Toggle label="Outline" checked={outline} onChange={setOutline} />
      {outline && (
        <ColorPicker
          label="Outline Color"
          value={outlineColor}
          onChange={setOutlineColor}
        />
      )}
    </Section>
  );
}
