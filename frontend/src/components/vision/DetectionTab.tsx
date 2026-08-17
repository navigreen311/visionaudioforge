"use client";

import React, { useState, useCallback, useRef, useEffect, useMemo } from "react";
import api from "@/lib/api";
import ImageUploadPreview from "./ImageUploadPreview";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

const COCO_CLASSES = [
  "person", "bicycle", "car", "motorcycle", "airplane",
  "bus", "train", "truck", "boat", "traffic light",
  "fire hydrant", "stop sign", "parking meter", "bench",
  "bird", "cat", "dog", "horse", "sheep", "cow",
  "elephant", "bear", "zebra", "giraffe", "backpack",
  "umbrella", "handbag", "suitcase", "frisbee", "skis",
] as const;

const PALETTE = [
  "#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4",
  "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6", "#f43f5e",
  "#a855f7", "#0ea5e9", "#84cc16", "#d946ef", "#f59e0b",
  "#10b981", "#6366f1", "#f472b6", "#34d399", "#fb923c",
];

const BBOX_COLORS: Record<string, string> = {};

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

/**
 * A detection exactly as /api/vision/detect returns it: the YOLO detector emits
 * `class_name` with an xyxy `bbox` (backend/app/services/vision/detection.py).
 * `label` is not sent today — the normaliser below still prefers it if present.
 */
interface RawDetection {
  bbox?: number[];
  class_id?: number;
  class_name?: string;
  confidence: number;
  label?: string;
}

interface DetectResponse {
  detections: RawDetection[];
  count: number;
  image_b64?: string;
  processing_time_ms?: number;
}

type SortField = "label" | "confidence" | "area";
type SortDir = "asc" | "desc";

interface DetectionTabProps {
  imageSrc?: string;
  imageFile?: File;
}

export default function DetectionTab({ imageSrc: externalSrc, imageFile: externalFile }: DetectionTabProps) {
  const [file, setFile] = useState<File | null>(externalFile ?? null);
  const [imageSrc, setImageSrc] = useState<string | null>(externalSrc ?? null);
  const [confidence, setConfidence] = useState(50);
  const [iou, setIou] = useState(45);
  const [selectedClasses, setSelectedClasses] = useState<string[]>([]);
  const [classSearch, setClassSearch] = useState("");
  const [showClassDropdown, setShowClassDropdown] = useState(false);
  const [maxDetections, setMaxDetections] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [sortField, setSortField] = useState<SortField>("confidence");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Sync external props
  useEffect(() => {
    if (externalFile) {
      setFile(externalFile);
      setImageSrc(URL.createObjectURL(externalFile));
      setDetections([]);
    }
  }, [externalFile]);

  useEffect(() => {
    if (externalSrc) {
      setImageSrc(externalSrc);
      setDetections([]);
    }
  }, [externalSrc]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowClassDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredClassOptions = COCO_CLASSES.filter(
    (c) =>
      c.toLowerCase().includes(classSearch.toLowerCase()) &&
      !selectedClasses.includes(c),
  );

  const toggleClass = (cls: string) => {
    setSelectedClasses((prev) =>
      prev.includes(cls) ? prev.filter((c) => c !== cls) : [...prev, cls],
    );
    setClassSearch("");
  };

  const removeSelectedClass = (cls: string) => {
    setSelectedClasses((prev) => prev.filter((c) => c !== cls));
  };

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

      // Build query params (backend uses Query parameters, not Form fields)
      const params = new URLSearchParams();
      params.set("confidence", String(confidence / 100));
      params.set("iou_threshold", String(iou / 100));
      params.set("max_detections", String(maxDetections));
      if (selectedClasses.length > 0) {
        params.set("classes", selectedClasses.join(","));
      }

      const { data } = await api.post<DetectResponse>(
        `/api/vision/detect?${params.toString()}`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );

      // Normalize: backend returns class_name + xyxy bbox; convert to label + [x,y,w,h]
      const normalized: Detection[] = (data.detections ?? []).map((raw) => {
        const label = raw.label ?? raw.class_name ?? "unknown";
        const rawBbox = raw.bbox ?? [0, 0, 0, 0];
        // If bbox looks like xyxy (x2 > x1 and y2 > y1 and values are large), convert to xywh
        let bbox: [number, number, number, number];
        if (rawBbox.length === 4 && rawBbox[2] > rawBbox[0] && rawBbox[3] > rawBbox[1]) {
          // xyxy -> xywh
          bbox = [
            Math.round(rawBbox[0]),
            Math.round(rawBbox[1]),
            Math.round(rawBbox[2] - rawBbox[0]),
            Math.round(rawBbox[3] - rawBbox[1]),
          ];
        } else {
          bbox = [rawBbox[0], rawBbox[1], rawBbox[2], rawBbox[3]];
        }
        return {
          label,
          confidence: raw.confidence,
          bbox,
        };
      });

      setDetections(normalized);
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

  // Sortable detections
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir(field === "label" ? "asc" : "desc");
    }
  };

  const sortedDetections = useMemo(() => {
    const sorted = [...detections];
    sorted.sort((a, b) => {
      let cmp = 0;
      if (sortField === "label") {
        cmp = a.label.localeCompare(b.label);
      } else if (sortField === "confidence") {
        cmp = a.confidence - b.confidence;
      } else if (sortField === "area") {
        cmp = a.bbox[2] * a.bbox[3] - b.bbox[2] * b.bbox[3];
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [detections, sortField, sortDir]);

  const sortIndicator = (field: SortField) => {
    if (sortField !== field) return "";
    return sortDir === "asc" ? " \u25B2" : " \u25BC";
  };

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
        {/* Confidence Threshold */}
        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="text-xs text-gray-500">Confidence Threshold</label>
            <span className="inline-flex items-center rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700">
              {confidence}%
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
            className="w-full"
          />
        </div>

        {/* IoU Threshold */}
        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="text-xs text-gray-500">IoU Threshold</label>
            <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
              {iou}%
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={iou}
            onChange={(e) => setIou(Number(e.target.value))}
            className="w-full"
          />
        </div>

        {/* Multi-select Class Filter */}
        <div className="relative" ref={dropdownRef}>
          <label className="mb-1 block text-xs text-gray-500">Class Filter</label>
          <div
            className="flex min-h-[38px] cursor-text flex-wrap gap-1 rounded border border-gray-300 px-2 py-1.5 text-sm focus-within:border-brand-500 focus-within:ring-1 focus-within:ring-brand-500"
            onClick={() => setShowClassDropdown(true)}
          >
            {selectedClasses.map((cls) => (
              <span
                key={cls}
                className="inline-flex items-center gap-1 rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700"
              >
                {cls}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeSelectedClass(cls);
                  }}
                  className="ml-0.5 text-brand-500 hover:text-brand-800"
                >
                  x
                </button>
              </span>
            ))}
            <input
              type="text"
              value={classSearch}
              onChange={(e) => {
                setClassSearch(e.target.value);
                setShowClassDropdown(true);
              }}
              onFocus={() => setShowClassDropdown(true)}
              placeholder={selectedClasses.length === 0 ? "All classes" : ""}
              className="min-w-[60px] flex-1 border-0 bg-transparent p-0 text-sm focus:outline-none focus:ring-0"
            />
          </div>
          {showClassDropdown && filteredClassOptions.length > 0 && (
            <ul className="absolute z-10 mt-1 max-h-40 w-full overflow-y-auto rounded border border-gray-200 bg-white shadow-lg">
              {filteredClassOptions.map((cls) => (
                <li
                  key={cls}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    toggleClass(cls);
                  }}
                  className="cursor-pointer px-3 py-1.5 text-sm text-gray-700 hover:bg-brand-50"
                >
                  {cls}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Max Detections */}
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

          {/* Detection table — sortable */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-xs font-medium uppercase text-gray-500">
                  <th
                    className="cursor-pointer select-none px-3 py-2 hover:text-gray-800"
                    onClick={() => handleSort("label")}
                  >
                    Class{sortIndicator("label")}
                  </th>
                  <th
                    className="cursor-pointer select-none px-3 py-2 hover:text-gray-800"
                    onClick={() => handleSort("confidence")}
                  >
                    Confidence{sortIndicator("confidence")}
                  </th>
                  <th className="px-3 py-2">BBox (x, y, w, h)</th>
                  <th
                    className="cursor-pointer select-none px-3 py-2 hover:text-gray-800"
                    onClick={() => handleSort("area")}
                  >
                    Area{sortIndicator("area")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedDetections.map((det, i) => {
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
