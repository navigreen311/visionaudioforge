"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import api from "@/lib/api";
import ImageUploadPreview from "./ImageUploadPreview";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

const COCO_CLASSES = [
  "person", "bicycle", "car", "motorcycle", "airplane",
  "bus", "train", "truck", "boat", "traffic light",
  "fire hydrant", "stop sign", "bench", "bird", "cat",
  "dog", "horse", "cow", "elephant", "bear",
] as const;

const BBOX_COLORS: Record<string, string> = {};
const PALETTE = [
  "#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4",
  "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6", "#f43f5e",
  "#a855f7", "#0ea5e9", "#84cc16", "#d946ef", "#f59e0b",
];

function getClassColor(label: string): string {
  if (!BBOX_COLORS[label]) {
    const idx = Object.keys(BBOX_COLORS).length % PALETTE.length;
    BBOX_COLORS[label] = PALETTE[idx];
  }
  return BBOX_COLORS[label];
}

interface Detection {
  label: string;
  confidence: number;
  bbox: [number, number, number, number]; // [x, y, w, h]
}

interface DetectResponse {
  detections: Detection[];
  [key: string]: unknown;
}

export default function DetectionTab() {
  const [file, setFile] = useState<File | null>(null);
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [confidence, setConfidence] = useState(50);
  const [iou, setIou] = useState(45);
  const [classFilter, setClassFilter] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [maxDetections, setMaxDetections] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const filteredSuggestions = COCO_CLASSES.filter(
    (c) => c.includes(classFilter.toLowerCase()) && c !== classFilter.toLowerCase(),
  );

  const handleFile = useCallback((f: File) => {
    setFile(f);
    const url = URL.createObjectURL(f);
    setImageSrc(url);
    setDetections([]);
  }, []);

  const handleDetect = async () => {
    if (!file) {
      setError("Please upload an image first.");
      return;
    }

    setLoading(true);
    setError(null);
    setDetections([]);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("confidence", String(confidence / 100));
      formData.append("iou", String(iou / 100));
      formData.append("max_detections", String(maxDetections));
      if (classFilter.trim()) {
        formData.append("class_filter", classFilter.trim());
      }

      const { data } = await api.post<DetectResponse>("/api/vision/detect", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setDetections(data.detections);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Detection failed.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  // Draw bounding boxes on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img || !imageSrc || detections.length === 0) return;

    const draw = () => {
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);

      detections.forEach((det) => {
        const color = getClassColor(det.label);
        const [x, y, w, h] = det.bbox;

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);

        const label = `${det.label} ${(det.confidence * 100).toFixed(0)}%`;
        ctx.font = "14px sans-serif";
        const textW = ctx.measureText(label).width;
        ctx.fillStyle = color;
        ctx.fillRect(x, y - 20, textW + 8, 20);
        ctx.fillStyle = "#ffffff";
        ctx.fillText(label, x + 4, y - 5);
      });
    };

    if (img.complete) {
      draw();
    } else {
      img.onload = draw;
    }
  }, [imageSrc, detections]);

  const exportCSV = () => {
    const header = "Class,Confidence,X,Y,Width,Height,Area\n";
    const rows = detections
      .map((d) => {
        const [x, y, w, h] = d.bbox;
        return `${d.label},${d.confidence.toFixed(4)},${x},${y},${w},${h},${w * h}`;
      })
      .join("\n");
    downloadFile(header + rows, "detections.csv", "text/csv");
  };

  const exportJSON = () => {
    const json = JSON.stringify(detections, null, 2);
    downloadFile(json, "detections.json", "application/json");
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Image upload */}
      <ImageUploadPreview label="Upload Image" onFile={handleFile} accept="image/*" />

      {/* Controls */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs text-gray-500">
            Confidence: {confidence}%
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
            className="w-full"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">
            IoU Threshold: {iou}%
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={iou}
            onChange={(e) => setIou(Number(e.target.value))}
            className="w-full"
          />
        </div>
        <div className="relative">
          <label className="mb-1 block text-xs text-gray-500">Class Filter</label>
          <input
            type="text"
            value={classFilter}
            onChange={(e) => {
              setClassFilter(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="e.g. person, car"
            className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          />
          {showSuggestions && filteredSuggestions.length > 0 && (
            <ul className="absolute z-10 mt-1 max-h-40 w-full overflow-y-auto rounded border border-gray-200 bg-white shadow-lg">
              {filteredSuggestions.map((cls) => (
                <li
                  key={cls}
                  onMouseDown={() => {
                    setClassFilter(cls);
                    setShowSuggestions(false);
                  }}
                  className="cursor-pointer px-3 py-1.5 text-sm text-gray-700 hover:bg-brand-50"
                >
                  {cls}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">Max Detections</label>
          <input
            type="number"
            min={1}
            max={1000}
            value={maxDetections}
            onChange={(e) => setMaxDetections(Number(e.target.value))}
            className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          />
        </div>
      </div>

      {/* Detect button */}
      <button
        onClick={handleDetect}
        disabled={loading || !file}
        className="rounded-lg bg-brand-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Detecting..." : "Detect Objects"}
      </button>

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <LoadingSpinner size="sm" />
          Running object detection...
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      {detections.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">
              Results ({detections.length} detections)
            </h3>
            <div className="flex gap-2">
              <button
                onClick={exportCSV}
                className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                Export CSV
              </button>
              <button
                onClick={exportJSON}
                className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                Export JSON
              </button>
            </div>
          </div>

          {/* Canvas with bounding boxes */}
          <div className="relative">
            {imageSrc && (
              <img
                ref={imgRef}
                src={imageSrc}
                alt="Detection source"
                className="hidden"
                crossOrigin="anonymous"
              />
            )}
            <canvas
              ref={canvasRef}
              className="max-w-full rounded border border-gray-200"
            />
          </div>

          {/* Detection table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-xs font-medium uppercase text-gray-500">
                  <th className="px-3 py-2">Class</th>
                  <th className="px-3 py-2">Confidence</th>
                  <th className="px-3 py-2">BBox</th>
                  <th className="px-3 py-2">Area</th>
                </tr>
              </thead>
              <tbody>
                {detections.map((det, i) => {
                  const [x, y, w, h] = det.bbox;
                  const area = w * h;
                  const pct = det.confidence * 100;
                  return (
                    <tr key={i} className="border-b border-gray-100">
                      <td className="px-3 py-2">
                        <span className="flex items-center gap-2">
                          <span
                            className="inline-block h-3 w-3 rounded-sm"
                            style={{ backgroundColor: getClassColor(det.label) }}
                          />
                          {det.label}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-200">
                            <div
                              className="h-full rounded-full bg-brand-500"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500">{pct.toFixed(1)}%</span>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-500">
                        [{x}, {y}, {w}, {h}]
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-500">
                        {area.toLocaleString()} px
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
