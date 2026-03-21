"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import api from "@/lib/api";
import ImageUploadPreview from "./ImageUploadPreview";
import LoadingSpinner from "@/components/ui/LoadingSpinner";

type OutputFormat = "plain" | "json" | "bboxes";

type Language = "en" | "es" | "fr" | "de" | "auto";

const LANGUAGE_OPTIONS: { value: Language; label: string }[] = [
  { value: "auto", label: "Auto-detect" },
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
];

interface OCRWord {
  text: string;
  confidence: number;
  bbox: number[]; // [x, y, w, h]
}

interface OCRResponse {
  text: string;
  words: OCRWord[];
  language?: string;
  confidence?: number;
  processing_time_ms?: number;
}

interface OCRMetrics {
  wordCount: number;
  charCount: number;
  detectedLanguage: string;
  avgConfidence: number;
}

function computeMetrics(result: OCRResponse): OCRMetrics {
  const words = result.text.trim().split(/\s+/).filter(Boolean);
  const filteredWords = result.words ?? [];
  const avgConf =
    filteredWords.length > 0
      ? filteredWords.reduce((sum, b) => sum + b.confidence, 0) / filteredWords.length
      : result.confidence ?? 0;

  return {
    wordCount: words.length,
    charCount: result.text.length,
    detectedLanguage: result.language ?? "unknown",
    avgConfidence: avgConf,
  };
}

interface OCRTabProps {
  imageSrc?: string;
  imageFile?: File;
}

export default function OCRTab({ imageSrc: externalSrc, imageFile: externalFile }: OCRTabProps) {
  const [file, setFile] = useState<File | null>(externalFile ?? null);
  const [imageSrc, setImageSrc] = useState<string | null>(externalSrc ?? null);
  const [language, setLanguage] = useState<Language>("auto");
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("plain");
  const [confidenceFilter, setConfidenceFilter] = useState(60);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OCRResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  // Sync external props
  useEffect(() => {
    if (externalFile) {
      setFile(externalFile);
      setImageSrc(URL.createObjectURL(externalFile));
      setResult(null);
    }
  }, [externalFile]);

  useEffect(() => {
    if (externalSrc) {
      setImageSrc(externalSrc);
      setResult(null);
    }
  }, [externalSrc]);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    const url = URL.createObjectURL(f);
    setImageSrc(url);
    setResult(null);
  }, []);

  const handleExtract = async () => {
    if (!file) {
      setError("Please upload an image first.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      // Backend uses Query parameters
      const params = new URLSearchParams();
      params.set("language", language === "auto" ? "auto" : language);
      params.set("output_format", outputFormat === "plain" ? "text" : "json");
      params.set("confidence_filter", String(confidenceFilter / 100));

      const { data } = await api.post<OCRResponse>(
        `/api/vision/ocr?${params.toString()}`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );

      // Normalize response: backend returns { text, words, language, confidence }
      const normalized: OCRResponse = {
        text: data.text ?? "",
        words: (data.words ?? []).map((w) => ({
          text: w.text,
          confidence: w.confidence,
          bbox: w.bbox,
        })),
        language: data.language,
        confidence: data.confidence,
        processing_time_ms: data.processing_time_ms,
      };

      setResult(normalized);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "OCR extraction failed.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  // Draw bounding boxes on canvas when in bboxes mode
  useEffect(() => {
    if (outputFormat !== "bboxes" || !result || !imageSrc) return;
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;

    const draw = () => {
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);

      const filtered = (result.words ?? []).filter(
        (b) => b.confidence >= confidenceFilter / 100,
      );

      filtered.forEach((word) => {
        const [x, y, w, h] = word.bbox;

        ctx.strokeStyle = "#3b82f6";
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);

        const confLabel = `${(word.confidence * 100).toFixed(0)}%`;
        ctx.font = "12px sans-serif";
        const textW = ctx.measureText(confLabel).width;
        ctx.fillStyle = "rgba(59, 130, 246, 0.85)";
        ctx.fillRect(x, y - 16, textW + 6, 16);
        ctx.fillStyle = "#ffffff";
        ctx.fillText(confLabel, x + 3, y - 3);
      });
    };

    if (img.complete) {
      draw();
    } else {
      img.onload = draw;
    }
  }, [result, imageSrc, outputFormat, confidenceFilter]);

  const handleCopyText = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-secure contexts
      const textarea = document.createElement("textarea");
      textarea.value = result.text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const metrics = result ? computeMetrics(result) : null;
  const filteredWords = result
    ? (result.words ?? []).filter((b) => b.confidence >= confidenceFilter / 100)
    : [];

  return (
    <div className="space-y-6">
      {/* Image upload */}
      <ImageUploadPreview label="Upload Image" onFile={handleFile} accept="image/*" />

      {/* Controls */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs text-gray-500">Language</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          >
            {LANGUAGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-2 block text-xs text-gray-500">Output Format</label>
          <div className="flex gap-4">
            {(
              [
                { value: "plain", label: "Plain Text" },
                { value: "json", label: "Structured JSON" },
                { value: "bboxes", label: "Bounding Boxes" },
              ] as const
            ).map((opt) => (
              <label
                key={opt.value}
                className="flex items-center gap-1.5 text-sm text-gray-700"
              >
                <input
                  type="radio"
                  name="ocr-format"
                  value={opt.value}
                  checked={outputFormat === opt.value}
                  onChange={() => setOutputFormat(opt.value)}
                  className="text-brand-600 focus:ring-brand-500"
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="text-xs text-gray-500">Confidence Filter</label>
            <span className="inline-flex items-center rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700">
              {confidenceFilter}%
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            value={confidenceFilter}
            onChange={(e) => setConfidenceFilter(Number(e.target.value))}
            className="w-full"
          />
        </div>
      </div>

      {/* Extract button */}
      <button
        onClick={handleExtract}
        disabled={loading || !file}
        className="rounded-lg bg-brand-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Extracting..." : "Extract Text"}
      </button>

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-3 text-sm text-gray-500">
          <LoadingSpinner size="sm" />
          Running OCR extraction...
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">Results</h3>
            <button
              onClick={handleCopyText}
              className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
            >
              {copied ? "Copied!" : "Copy Text"}
            </button>
          </div>

          {/* Metrics row */}
          {metrics && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
                <p className="text-xs text-gray-500">Word Count</p>
                <p className="text-sm font-medium text-gray-900">{metrics.wordCount}</p>
              </div>
              <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
                <p className="text-xs text-gray-500">Char Count</p>
                <p className="text-sm font-medium text-gray-900">{metrics.charCount}</p>
              </div>
              <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
                <p className="text-xs text-gray-500">Detected Language</p>
                <p className="text-sm font-medium text-gray-900">{metrics.detectedLanguage}</p>
              </div>
              <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
                <p className="text-xs text-gray-500">Avg Confidence</p>
                <p className="text-sm font-medium text-gray-900">
                  {(metrics.avgConfidence * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          )}

          {/* Output display */}
          {outputFormat === "plain" && (
            <textarea
              readOnly
              value={result.text}
              rows={10}
              className="w-full rounded-lg border border-gray-300 bg-white p-3 text-sm text-gray-800 focus:outline-none"
            />
          )}

          {outputFormat === "json" && (
            <pre className="max-h-96 overflow-auto rounded-lg border border-gray-300 bg-gray-900 p-4 text-sm text-green-400">
              <code>{JSON.stringify(filteredWords, null, 2)}</code>
            </pre>
          )}

          {outputFormat === "bboxes" && imageSrc && (
            <div className="relative">
              <img
                ref={imgRef}
                src={imageSrc}
                alt="OCR source"
                className="hidden"
                crossOrigin="anonymous"
              />
              <canvas
                ref={canvasRef}
                className="max-w-full rounded border border-gray-200"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
