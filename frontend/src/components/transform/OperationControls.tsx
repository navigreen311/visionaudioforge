"use client";

import React from "react";
import {
  AutoCropControls,
  BackgroundRemoveControls,
  ColorGradeControls,
  FrameInterpolateControls,
  HighlightClipControls,
  InpaintControls,
  SmartCropControls,
  StyleTransferControls,
  SubtitleControls,
  SuperResolutionControls,
} from "./operations";

/* ------------------------------------------------------------------ */
/*  Operation display metadata                                         */
/* ------------------------------------------------------------------ */

const OPERATION_LABELS: Record<string, string> = {
  background_remove: "Background Removal",
  super_resolution: "Super Resolution",
  style_transfer: "Style Transfer",
  auto_crop: "Auto Crop",
  color_grade: "Color Grading",
  subtitle: "Subtitle",
  inpaint: "Inpaint",
  smart_crop: "Smart Crop",
  frame_interpolate: "Frame Interpolation",
  highlight_clip: "Highlight Clip",
};

/* ------------------------------------------------------------------ */
/*  Component map — maps operation key to its control panel            */
/* ------------------------------------------------------------------ */

const CONTROL_MAP: Record<
  string,
  React.ComponentType<{ onParamsChange: (params: Record<string, unknown>) => void }>
> = {
  background_remove: BackgroundRemoveControls,
  super_resolution: SuperResolutionControls,
  style_transfer: StyleTransferControls,
  auto_crop: AutoCropControls,
  color_grade: ColorGradeControls,
  subtitle: SubtitleControls,
  inpaint: InpaintControls,
  smart_crop: SmartCropControls,
  frame_interpolate: FrameInterpolateControls,
  highlight_clip: HighlightClipControls,
};

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface OperationControlsProps {
  operation: string;
  onParamsChange: (params: Record<string, unknown>) => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function OperationControls({
  operation,
  onParamsChange,
}: OperationControlsProps) {
  const ControlPanel = CONTROL_MAP[operation];

  if (!ControlPanel) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        No controls available for operation{" "}
        <code className="rounded bg-amber-100 px-1 py-0.5 font-mono text-xs">
          {operation}
        </code>
      </div>
    );
  }

  const label = OPERATION_LABELS[operation] ?? operation;

  return (
    <div className="space-y-4">
      <h3 className="text-base font-semibold text-gray-900">{label}</h3>
      <ControlPanel onParamsChange={onParamsChange} />
    </div>
  );
}
