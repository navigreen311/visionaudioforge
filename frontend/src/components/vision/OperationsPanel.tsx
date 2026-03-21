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
  values: VisionOperations;
  onChange: (ops: VisionOperations) => void;
}

export default function OperationsPanel({ values, onChange }: OperationsPanelProps) {
  const [livePreview, setLivePreview] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingRef = useRef<VisionOperations>(values);

  // Keep pendingRef in sync when values prop changes
  useEffect(() => {
    pendingRef.current = values;
  }, [values]);

  const emit = useCallback(
    (next: VisionOperations) => {
      if (livePreview) {
        pendingRef.current = next;
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
          onChange(pendingRef.current);
        }, 500);
      } else {
        onChange(next);
      }
    },
    [livePreview, onChange],
  );

  const update = useCallback(
    <K extends keyof VisionOperations>(key: K, val: VisionOperations[K]) => {
      const next = { ...values, [key]: val };
      emit(next);
    },
    [values, emit],
  );

  const resetAll = useCallback(() => {
    onChange({ ...DEFAULT_VALUES });
  }, [onChange]);

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
              onChange={(v) => update("minMaxRange", { ...values.minMaxRange, min: v })}
              step={0.1}
            />
            <NumberInput
              label="Target Max"
              value={values.minMaxRange.max}
              onChange={(v) => update("minMaxRange", { ...values.minMaxRange, max: v })}
              step={0.1}
            />
          </div>
        )}
        {values.normalization === "z-score" && (
          <div className="grid grid-cols-2 gap-2">
            <NumberInput
              label="Mean"
              value={values.zScoreParams.mean}
              onChange={(v) => update("zScoreParams", { ...values.zScoreParams, mean: v })}
              step={0.01}
            />
            <NumberInput
              label="Std"
              value={values.zScoreParams.std}
              onChange={(v) => update("zScoreParams", { ...values.zScoreParams, std: v })}
              step={0.01}
              min={0.01}
            />
          </div>
        )}
      </Section>

      {/* ── Color Space ────────────────────────────────────── */}
      <Section title="Color Space">
        <Select
          label="Color Space"
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
      <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3">
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
    </div>
  );
}
