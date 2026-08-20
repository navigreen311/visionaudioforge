"use client";

import { API_BASE_URL } from "@/lib/api";
import { readWorkspaceId } from "@/lib/session";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import HeatmapViewer from "./HeatmapViewer";
import SHAPChart from "./SHAPChart";

const API_BASE = API_BASE_URL;

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type ExplanationMethod =
  | "grad-cam"
  | "grad-cam++"
  | "saliency-map"
  | "shap";

interface RegistryModel {
  id: string;
  name: string;
  version: string;
  backbone: string;
}

interface SHAPValue {
  feature: string;
  value: number;
}

interface Prediction {
  className: string;
  confidence: number;
}

interface ExplainResponse {
  heatmap_b64: string | null;
  predictions: Prediction[];
  shap_values: SHAPValue[];
  method: string;
  target_class: string | null;
}

const METHODS: { id: ExplanationMethod; label: string }[] = [
  { id: "grad-cam", label: "Grad-CAM" },
  { id: "grad-cam++", label: "Grad-CAM++" },
  { id: "saliency-map", label: "Saliency Map" },
  { id: "shap", label: "SHAP" },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function ExplainabilityTab() {
  /* --- state ---------------------------------------------------- */
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const [models, setModels] = useState<RegistryModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [modelsLoading, setModelsLoading] = useState(false);

  const [method, setMethod] = useState<ExplanationMethod>("grad-cam");
  const [targetClass, setTargetClass] = useState("");
  const [autoTarget, setAutoTarget] = useState(true);

  const [result, setResult] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  /* --- fetch models from registry ------------------------------- */
  useEffect(() => {
    let cancelled = false;
    const fetchModels = async () => {
      setModelsLoading(true);
      try {
        const resp = await fetch(
          `${API_BASE}/api/registry/models?workspace_id=${readWorkspaceId() ?? ""}&limit=50`,
        );
        if (!resp.ok) throw new Error("Failed to fetch models");
        const data: { items: RegistryModel[] } = await resp.json();
        if (!cancelled) {
          setModels(data.items ?? []);
          if (data.items?.length > 0) {
            setSelectedModel(data.items[0].id);
          }
        }
      } catch {
        // If registry unavailable, provide fallback demo models
        if (!cancelled) {
          setModels([
            {
              id: "demo-resnet50",
              name: "ResNet-50",
              version: "1.0.0",
              backbone: "resnet50",
            },
            {
              id: "demo-vgg16",
              name: "VGG-16",
              version: "1.0.0",
              backbone: "vgg16",
            },
            {
              id: "demo-efficientnet",
              name: "EfficientNet-B0",
              version: "1.0.0",
              backbone: "efficientnet_b0",
            },
          ]);
          setSelectedModel("demo-resnet50");
        }
      } finally {
        if (!cancelled) setModelsLoading(false);
      }
    };
    fetchModels();
    return () => {
      cancelled = true;
    };
  }, []);

  /* --- image handling ------------------------------------------- */
  const handleFile = useCallback((file: File) => {
    setImageFile(file);
    setResult(null);
    setError(null);
    const url = URL.createObjectURL(file);
    setImagePreview((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return url;
    });
  }, []);

  const processFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      handleFile(files[0]);
    },
    [handleFile],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      processFiles(e.dataTransfer.files);
    },
    [processFiles],
  );

  /* --- generate explanation ------------------------------------- */
  const handleGenerate = async () => {
    if (!imageFile) {
      setError("Please upload an image first.");
      return;
    }
    if (!selectedModel) {
      setError("Please select a model.");
      return;
    }

    setError(null);
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", imageFile);
      formData.append("model_id", selectedModel);
      formData.append("method", method);
      if (!autoTarget && targetClass.trim()) {
        formData.append("target_class", targetClass.trim());
      }

      const resp = await fetch(`${API_BASE}/api/validate/explain`, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `HTTP ${resp.status}`);
      }
      const data: ExplainResponse = await resp.json();
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  /* --- render --------------------------------------------------- */
  return (
    <div className="space-y-6">
      {/* Image dropzone */}
      <Card title="Input Image">
        <div
          className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors cursor-pointer ${
            dragOver
              ? "border-brand-500 bg-brand-50"
              : "border-gray-300 bg-gray-50 hover:border-gray-400"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          {imagePreview ? (
            <img
              src={imagePreview}
              alt="Uploaded preview"
              className="max-h-48 object-contain rounded"
            />
          ) : (
            <>
              <svg
                className="mb-3 h-10 w-10 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <p className="text-sm text-gray-600">
                <span className="font-medium text-brand-600">
                  Click to upload
                </span>{" "}
                or drag and drop an image
              </p>
              <p className="mt-1 text-xs text-gray-500">
                PNG, JPG, WEBP up to 10 MB
              </p>
            </>
          )}
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            onChange={(e) => processFiles(e.target.files)}
            className="hidden"
          />
        </div>
        {imageFile && (
          <p className="mt-2 text-sm text-gray-500">
            {imageFile.name} ({(imageFile.size / 1024).toFixed(1)} KB)
          </p>
        )}
      </Card>

      {/* Controls: Model selector + Method + Target class */}
      <Card title="Explanation Settings">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {/* Model selector */}
          <div>
            <label
              htmlFor="model-select"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Model
            </label>
            <select
              id="model-select"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={modelsLoading}
            >
              {modelsLoading && <option value="">Loading models...</option>}
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} v{m.version} ({m.backbone})
                </option>
              ))}
            </select>
          </div>

          {/* Explanation method */}
          <div>
            <p className="block text-sm font-medium text-gray-700 mb-1">
              Explanation Method
            </p>
            <div className="flex flex-wrap gap-2">
              {METHODS.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setMethod(m.id)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors border ${
                    method === m.id
                      ? "border-brand-600 bg-brand-50 text-brand-700"
                      : "border-gray-300 bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          {/* Target class */}
          <div>
            <label
              htmlFor="target-class"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Target Class
            </label>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoTarget}
                  onChange={(e) => setAutoTarget(e.target.checked)}
                  className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                />
                Auto
              </label>
              <input
                id="target-class"
                type="text"
                className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400"
                placeholder="e.g. cat"
                value={targetClass}
                onChange={(e) => setTargetClass(e.target.value)}
                disabled={autoTarget}
              />
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <Button onClick={handleGenerate} loading={loading} disabled={loading}>
            Generate Explanation
          </Button>
          {result && (
            <Badge variant="success">
              {result.method} {result.target_class ? `(${result.target_class})` : ""}
            </Badge>
          )}
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </Card>

      {/* Results */}
      {result && imagePreview && (
        <>
          <Card title="Visualization">
            <HeatmapViewer
              originalSrc={imagePreview}
              heatmapB64={result.heatmap_b64}
            />
          </Card>

          <Card title="Predictions &amp; SHAP Values">
            <SHAPChart
              shapValues={result.shap_values}
              predictions={result.predictions}
            />
          </Card>
        </>
      )}
    </div>
  );
}
