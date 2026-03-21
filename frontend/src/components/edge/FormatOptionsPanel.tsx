"use client";

import { useState } from "react";

// ---- Per-format option types ----

interface OnnxOptions {
  opset: number;
  dynamicAxes: boolean;
  simplify: boolean;
}

interface TensorRTOptions {
  precision: "fp32" | "fp16" | "int8";
  workspaceMb: number;
  device: number;
}

interface CoreMLOptions {
  iosVersion: number;
  computeUnits: "all" | "cpu_only" | "cpu_and_gpu" | "cpu_and_ne";
  quantize: boolean;
}

interface TFLiteOptions {
  quantization: "none" | "dynamic" | "float16" | "int8";
  selectOps: boolean;
}

interface OpenVINOOptions {
  device: "CPU" | "GPU" | "MYRIAD" | "AUTO";
  precision: "FP32" | "FP16" | "INT8";
}

interface WebGPUOptions {
  shaderType: "wgsl" | "spirv";
  precision: "f32" | "f16";
}

export type FormatOptionValues =
  | OnnxOptions
  | TensorRTOptions
  | CoreMLOptions
  | TFLiteOptions
  | OpenVINOOptions
  | WebGPUOptions;

export interface FormatOptionsPanelProps {
  format: string;
  options: Record<string, string | number | boolean>;
  onChange: (options: Record<string, string | number | boolean>) => void;
}

// ---- Default option values per format ----

export const FORMAT_DEFAULTS: Record<string, Record<string, string | number | boolean>> = {
  onnx: { opset: 17, dynamicAxes: true, simplify: true },
  tensorrt: { precision: "fp16", workspaceMb: 1024, device: 0 },
  coreml: { iosVersion: 16, computeUnits: "all", quantize: false },
  tflite: { quantization: "none", selectOps: false },
  openvino: { device: "CPU", precision: "FP32" },
  webgpu: { shaderType: "wgsl", precision: "f32" },
};

export default function FormatOptionsPanel({
  format,
  options,
  onChange,
}: FormatOptionsPanelProps) {
  const [open, setOpen] = useState(false);

  const update = (key: string, value: string | number | boolean) => {
    onChange({ ...options, [key]: value });
  };

  const labelClass = "block text-xs font-medium text-gray-600 mb-0.5";
  const inputClass =
    "w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none";
  const selectClass = inputClass;

  const renderFields = () => {
    switch (format) {
      case "onnx":
        return (
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={labelClass}>Opset Version</label>
              <input
                type="number"
                min={7}
                max={21}
                value={Number(options.opset ?? 17)}
                onChange={(e) => update("opset", Number(e.target.value))}
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Dynamic Axes</label>
              <input
                type="checkbox"
                checked={Boolean(options.dynamicAxes ?? true)}
                onChange={(e) => update("dynamicAxes", e.target.checked)}
                className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className={labelClass}>Simplify</label>
              <input
                type="checkbox"
                checked={Boolean(options.simplify ?? true)}
                onChange={(e) => update("simplify", e.target.checked)}
                className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
            </div>
          </div>
        );

      case "tensorrt":
        return (
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={labelClass}>Precision</label>
              <select
                value={String(options.precision ?? "fp16")}
                onChange={(e) => update("precision", e.target.value)}
                className={selectClass}
              >
                <option value="fp32">FP32</option>
                <option value="fp16">FP16</option>
                <option value="int8">INT8</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Workspace (MB)</label>
              <input
                type="number"
                min={128}
                max={16384}
                step={128}
                value={Number(options.workspaceMb ?? 1024)}
                onChange={(e) => update("workspaceMb", Number(e.target.value))}
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Device ID</label>
              <input
                type="number"
                min={0}
                max={7}
                value={Number(options.device ?? 0)}
                onChange={(e) => update("device", Number(e.target.value))}
                className={inputClass}
              />
            </div>
          </div>
        );

      case "coreml":
        return (
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={labelClass}>iOS Version</label>
              <input
                type="number"
                min={13}
                max={18}
                value={Number(options.iosVersion ?? 16)}
                onChange={(e) => update("iosVersion", Number(e.target.value))}
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Compute Units</label>
              <select
                value={String(options.computeUnits ?? "all")}
                onChange={(e) => update("computeUnits", e.target.value)}
                className={selectClass}
              >
                <option value="all">All</option>
                <option value="cpu_only">CPU Only</option>
                <option value="cpu_and_gpu">CPU + GPU</option>
                <option value="cpu_and_ne">CPU + Neural Engine</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Quantize</label>
              <input
                type="checkbox"
                checked={Boolean(options.quantize ?? false)}
                onChange={(e) => update("quantize", e.target.checked)}
                className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
            </div>
          </div>
        );

      case "tflite":
        return (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Quantization</label>
              <select
                value={String(options.quantization ?? "none")}
                onChange={(e) => update("quantization", e.target.value)}
                className={selectClass}
              >
                <option value="none">None</option>
                <option value="dynamic">Dynamic Range</option>
                <option value="float16">Float16</option>
                <option value="int8">Full Integer (INT8)</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Select TF Ops</label>
              <input
                type="checkbox"
                checked={Boolean(options.selectOps ?? false)}
                onChange={(e) => update("selectOps", e.target.checked)}
                className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
            </div>
          </div>
        );

      case "openvino":
        return (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Target Device</label>
              <select
                value={String(options.device ?? "CPU")}
                onChange={(e) => update("device", e.target.value)}
                className={selectClass}
              >
                <option value="CPU">CPU</option>
                <option value="GPU">GPU</option>
                <option value="MYRIAD">Myriad (VPU)</option>
                <option value="AUTO">Auto</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Precision</label>
              <select
                value={String(options.precision ?? "FP32")}
                onChange={(e) => update("precision", e.target.value)}
                className={selectClass}
              >
                <option value="FP32">FP32</option>
                <option value="FP16">FP16</option>
                <option value="INT8">INT8</option>
              </select>
            </div>
          </div>
        );

      case "webgpu":
        return (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Shader Type</label>
              <select
                value={String(options.shaderType ?? "wgsl")}
                onChange={(e) => update("shaderType", e.target.value)}
                className={selectClass}
              >
                <option value="wgsl">WGSL</option>
                <option value="spirv">SPIR-V</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Precision</label>
              <select
                value={String(options.precision ?? "f32")}
                onChange={(e) => update("precision", e.target.value)}
                className={selectClass}
              >
                <option value="f32">F32</option>
                <option value="f16">F16</option>
              </select>
            </div>
          </div>
        );

      default:
        return (
          <p className="text-xs text-gray-400">
            No configurable options for this format.
          </p>
        );
    }
  };

  const formatLabel: Record<string, string> = {
    onnx: "ONNX",
    tensorrt: "TensorRT",
    coreml: "CoreML",
    tflite: "TFLite",
    openvino: "OpenVINO",
    webgpu: "WebGPU",
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        <span>{formatLabel[format] ?? format} Options</span>
        <svg
          className={`h-4 w-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-gray-200 px-4 py-3">{renderFields()}</div>
      )}
    </div>
  );
}
