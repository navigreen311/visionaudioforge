"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";

// ── Types ──────────────────────────────────────────────────────────

export type NormalizationMode = "none" | "min-max" | "z-score" | "per-channel";
export type ColorSpace = "original" | "hsv" | "grayscale" | "lab" | "bgr";
export type EdgeDetection = "none" | "canny" | "sobel" | "laplacian";
export type BlurMode = "none" | "gaussian" | "median" | "bilateral";
export type RotationPreset = "0" | "90" | "180" | "270" | "custom";
export type FlipMode = "none" | "horizontal" | "vertical" | "both";
export type OutputFormat = "png" | "jpeg" | "numpy";

export interface VisionOperations {
  // Normalization
  normalization: NormalizationMode;
  minMaxRange: { min: number; max: number };
  zScoreParams: { mean: number; std: number };

  // Color Space
  colorSpace: ColorSpace;
  normalizeChannels: boolean;

  // Edge & Enhancement
  edgeDetection: EdgeDetection;
  cannyThreshold1: number;
  cannyThreshold2: number;
  blur: BlurMode;
  blurKernelSize: number;
  brightness: number;
  contrast: number;

  // Geometry
  resizeWidth: number;
  resizeHeight: number;
  keepAspectRatio: boolean;
  rotation: RotationPreset;
  customRotation: number;
  flip: FlipMode;

  // Output
  outputFormat: OutputFormat;
  jpegQuality: number;
  includeStats: boolean;
}

/** JSON payload sent to POST /api/vision/analyze as the operations array. */
export interface OperationParams {
  operations: Array<{ op: string; params: Record<string, unknown> }>;
  outputFormat: OutputFormat;
  jpegQuality: number;
  includeStats: boolean;
}

const DEFAULT_VALUES: VisionOperations = {
  normalization: "none",
  minMaxRange: { min: 0, max: 1 },
  zScoreParams: { mean: 0, std: 1 },
  colorSpace: "original",
  normalizeChannels: false,
  edgeDetection: "none",
  cannyThreshold1: 100,
  cannyThreshold2: 200,
  blur: "none",
  blurKernelSize: 3,
  brightness: 0,
  contrast: 1.0,
  resizeWidth: 0,
  resizeHeight: 0,
  keepAspectRatio: true,
  rotation: "0",
  customRotation: 0,
  flip: "none",
  outputFormat: "png",
  jpegQuality: 95,
  includeStats: false,
};

// ── Build pipeline steps from VisionOperations ─────────────────────

function buildOperationParams(ops: VisionOperations): OperationParams {
  const steps: Array<{ op: string; params: Record<string, unknown> }> = [];

  // Normalization
  if (ops.normalization !== "none") {
    const params: Record<string, unknown> = { method: ops.normalization.replace("-", "_") };
    if (ops.normalization === "min-max") {
      params.target_range = [ops.minMaxRange.min, ops.minMaxRange.max];
    }
    if (ops.normalization === "z-score") {
      params.global_stats = [ops.zScoreParams.mean, ops.zScoreParams.std];
    }
    steps.push({ op: "normalize", params });
  }

  // Color space
  if (ops.colorSpace !== "original") {
    const toMap: Record<string, string> = {
      hsv: "hsv",
      grayscale: "gray",
      lab: "lab",
      bgr: "bgr",
    };
    steps.push({
      op: "color_space",
      params: { from: "bgr", to: toMap[ops.colorSpace] ?? ops.colorSpace },
    });
  }

  // Blur
  if (ops.blur !== "none") {
    steps.push({
      op: "blur",
      params: { method: ops.blur, kernel_size: ops.blurKernelSize },
    });
  }

  // Brightness
  if (ops.brightness !== 0) {
    steps.push({ op: "brightness", params: { value: ops.brightness } });
  }

  // Contrast
  if (ops.contrast !== 1.0) {
    steps.push({ op: "contrast", params: { factor: ops.contrast } });
  }

  // Edge detection
  if (ops.edgeDetection !== "none") {
    const params: Record<string, unknown> = { method: ops.edgeDetection };
    if (ops.edgeDetection === "canny") {
      params.low = ops.cannyThreshold1;
      params.high = ops.cannyThreshold2;
    }
    steps.push({ op: "edge_detection", params });
  }

  // Resize (only if both dimensions are positive)
  if (ops.resizeWidth > 0 && ops.resizeHeight > 0) {
    steps.push({
      op: "resize",
      params: {
        width: ops.resizeWidth,
        height: ops.resizeHeight,
        maintain_aspect: ops.keepAspectRatio,
      },
    });
  }

  // Rotation
  const angle =
    ops.rotation === "custom"
      ? ops.customRotation
      : parseInt(ops.rotation, 10);
  if (angle !== 0) {
    steps.push({ op: "rotation", params: { angle } });
  }

  // Flip
  if (ops.flip !== "none") {
    const modeMap: Record<string, string> = {
      horizontal: "h",
      vertical: "v",
      both: "both",
    };
    steps.push({ op: "flip", params: { mode: modeMap[ops.flip] ?? ops.flip } });
  }

  return {
    operations: steps,
    outputFormat: ops.outputFormat,
    jpegQuality: ops.jpegQuality,
    includeStats: ops.includeStats,
  };
}

// ── Collapsible Section ────────────────────────────────────────────

interface SectionProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function Section({ title, children, defaultOpen = false }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-gray-200 last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-gray-700 hover:bg-gray-50"
      >
        {title}
        <span className="text-gray-400">{open ? "\u25B2" : "\u25BC"}</span>
      </button>
      {open && <div className="space-y-3 px-4 pb-4">{children}</div>}
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────

interface SelectProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}

function Select({ label, value, options, onChange }: SelectProps) {
  return (
    <label className="block text-xs text-gray-600">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 block w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
}

function Slider({ label, value, min, max, step = 1, onChange }: SliderProps) {
  return (
    <label className="block text-xs text-gray-600">
      <span className="flex items-center justify-between">
        {label}
        <span className="font-medium text-gray-800">{value}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full"
      />
    </label>
  );
}

interface NumberInputProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}

function NumberInput({ label, value, onChange, min, max, step }: NumberInputProps) {
  return (
    <label className="block text-xs text-gray-600">
      {label}
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
      />
    </label>
  );
}

// ── Main Component ─────────────────────────────────────────────────

interface OperationsPanelProps {
  onAnalyze: (params: OperationParams) => void;
  isAnalyzing: boolean;
}

export default function OperationsPanel({
  onAnalyze,
  isAnalyzing,
}: OperationsPanelProps) {
  const [values, setValues] = useState<VisionOperations>({ ...DEFAULT_VALUES });
  const [livePreview, setLivePreview] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const valuesRef = useRef<VisionOperations>(values);

  // Keep ref in sync
  useEffect(() => {
    valuesRef.current = values;
  }, [values]);

  // Debounced live-preview trigger
  const triggerLivePreview = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onAnalyze(buildOperationParams(valuesRef.current));
    }, 500);
  }, [onAnalyze]);

  // Clean up debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const update = useCallback(
    <K extends keyof VisionOperations>(key: K, val: VisionOperations[K]) => {
      setValues((prev) => {
        const next = { ...prev, [key]: val };
        return next;
      });
    },
    [],
  );

  // Fire live preview whenever values change AND livePreview is on
  useEffect(() => {
    if (livePreview && !isAnalyzing) {
      triggerLivePreview();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values, livePreview]);

  const resetAll = useCallback(() => {
    setValues({ ...DEFAULT_VALUES });
  }, []);

  const handleAnalyze = useCallback(() => {
    onAnalyze(buildOperationParams(values));
  }, [onAnalyze, values]);

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {/* ── Normalization ──────────────────────────────────── */}
      <Section title="Normalization" defaultOpen>
        <Select
          label="Mode"
          value={values.normalization}
          options={[
            { value: "none", label: "None" },
            { value: "min-max", label: "Min-Max" },
            { value: "z-score", label: "Z-Score" },
            { value: "per-channel", label: "Per-Channel" },
          ]}
          onChange={(v) => update("normalization", v as NormalizationMode)}
        />
        {values.normalization === "min-max" && (
          <div className="grid grid-cols-2 gap-2">
            <NumberInput
              label="Target Min"
              value={values.minMaxRange.min}
              onChange={(v) =>
                update("minMaxRange", { ...values.minMaxRange, min: v })
              }
              step={0.1}
            />
            <NumberInput
              label="Target Max"
              value={values.minMaxRange.max}
              onChange={(v) =>
                update("minMaxRange", { ...values.minMaxRange, max: v })
              }
              step={0.1}
            />
          </div>
        )}
        {values.normalization === "z-score" && (
          <div className="grid grid-cols-2 gap-2">
            <NumberInput
              label="Mean"
              value={values.zScoreParams.mean}
              onChange={(v) =>
                update("zScoreParams", { ...values.zScoreParams, mean: v })
              }
              step={0.01}
            />
            <NumberInput
              label="Std"
              value={values.zScoreParams.std}
              onChange={(v) =>
                update("zScoreParams", { ...values.zScoreParams, std: v })
              }
              step={0.01}
              min={0.01}
            />
          </div>
        )}
      </Section>

      {/* ── Color Space ────────────────────────────────────── */}
      <Section title="Color Space">
        <Select
          label="Convert To"
          value={values.colorSpace}
          options={[
            { value: "original", label: "Original" },
            { value: "hsv", label: "HSV" },
            { value: "grayscale", label: "Grayscale" },
            { value: "lab", label: "LAB" },
            { value: "bgr", label: "BGR" },
          ]}
          onChange={(v) => update("colorSpace", v as ColorSpace)}
        />
        <label className="flex items-center gap-2 text-xs text-gray-600">
          <input
            type="checkbox"
            checked={values.normalizeChannels}
            onChange={(e) => update("normalizeChannels", e.target.checked)}
            className="rounded border-gray-300"
          />
          Normalize Channels
        </label>
      </Section>

      {/* ── Edge & Enhancement ─────────────────────────────── */}
      <Section title="Edge & Enhancement">
        <Select
          label="Edge Detection"
          value={values.edgeDetection}
          options={[
            { value: "none", label: "None" },
            { value: "canny", label: "Canny" },
            { value: "sobel", label: "Sobel" },
            { value: "laplacian", label: "Laplacian" },
          ]}
          onChange={(v) => update("edgeDetection", v as EdgeDetection)}
        />
        {values.edgeDetection === "canny" && (
          <>
            <Slider
              label="Threshold 1"
              value={values.cannyThreshold1}
              min={0}
              max={500}
              onChange={(v) => update("cannyThreshold1", v)}
            />
            <Slider
              label="Threshold 2"
              value={values.cannyThreshold2}
              min={0}
              max={500}
              onChange={(v) => update("cannyThreshold2", v)}
            />
          </>
        )}

        <Select
          label="Blur"
          value={values.blur}
          options={[
            { value: "none", label: "None" },
            { value: "gaussian", label: "Gaussian" },
            { value: "median", label: "Median" },
            { value: "bilateral", label: "Bilateral" },
          ]}
          onChange={(v) => update("blur", v as BlurMode)}
        />
        {values.blur !== "none" && (
          <NumberInput
            label="Kernel Size"
            value={values.blurKernelSize}
            onChange={(v) => update("blurKernelSize", v)}
            min={1}
            step={2}
          />
        )}

        <Slider
          label="Brightness"
          value={values.brightness}
          min={-100}
          max={100}
          onChange={(v) => update("brightness", v)}
        />
        <Slider
          label="Contrast"
          value={values.contrast}
          min={0.1}
          max={3.0}
          step={0.1}
          onChange={(v) => update("contrast", v)}
        />
      </Section>

      {/* ── Geometry ───────────────────────────────────────── */}
      <Section title="Geometry">
        <div className="grid grid-cols-2 gap-2">
          <NumberInput
            label="Width"
            value={values.resizeWidth}
            onChange={(v) => update("resizeWidth", v)}
            min={0}
          />
          <NumberInput
            label="Height"
            value={values.resizeHeight}
            onChange={(v) => update("resizeHeight", v)}
            min={0}
          />
        </div>
        <label className="flex items-center gap-2 text-xs text-gray-600">
          <input
            type="checkbox"
            checked={values.keepAspectRatio}
            onChange={(e) => update("keepAspectRatio", e.target.checked)}
            className="rounded border-gray-300"
          />
          Keep Aspect Ratio
        </label>

        <Select
          label="Rotation"
          value={values.rotation}
          options={[
            { value: "0", label: "0\u00B0" },
            { value: "90", label: "90\u00B0" },
            { value: "180", label: "180\u00B0" },
            { value: "270", label: "270\u00B0" },
            { value: "custom", label: "Custom" },
          ]}
          onChange={(v) => update("rotation", v as RotationPreset)}
        />
        {values.rotation === "custom" && (
          <NumberInput
            label="Degrees"
            value={values.customRotation}
            onChange={(v) => update("customRotation", v)}
            min={-360}
            max={360}
          />
        )}

        <Select
          label="Flip"
          value={values.flip}
          options={[
            { value: "none", label: "None" },
            { value: "horizontal", label: "Horizontal" },
            { value: "vertical", label: "Vertical" },
            { value: "both", label: "Both" },
          ]}
          onChange={(v) => update("flip", v as FlipMode)}
        />
      </Section>

      {/* ── Output ─────────────────────────────────────────── */}
      <Section title="Output">
        <Select
          label="Format"
          value={values.outputFormat}
          options={[
            { value: "png", label: "PNG" },
            { value: "jpeg", label: "JPEG" },
            { value: "numpy", label: "NumPy" },
          ]}
          onChange={(v) => update("outputFormat", v as OutputFormat)}
        />
        {values.outputFormat === "jpeg" && (
          <Slider
            label="JPEG Quality"
            value={values.jpegQuality}
            min={1}
            max={100}
            onChange={(v) => update("jpegQuality", v)}
          />
        )}
        <label className="flex items-center gap-2 text-xs text-gray-600">
          <input
            type="checkbox"
            checked={values.includeStats}
            onChange={(e) => update("includeStats", e.target.checked)}
            className="rounded border-gray-300"
          />
          Include Stats
        </label>
      </Section>

      {/* ── Action Bar ─────────────────────────────────────── */}
      <div className="flex flex-col gap-3 border-t border-gray-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={resetAll}
            className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
          >
            Reset All
          </button>
          <label className="flex items-center gap-2 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={livePreview}
              onChange={(e) => setLivePreview(e.target.checked)}
              className="rounded border-gray-300"
            />
            Live Preview
          </label>
        </div>
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={isAnalyzing}
          className="inline-flex items-center justify-center rounded bg-blue-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isAnalyzing ? (
            <>
              <svg
                className="-ml-0.5 mr-1.5 h-3 w-3 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Analyzing...
            </>
          ) : (
            "Analyze"
          )}
        </button>
      </div>
    </div>
  );
}
