"use client";

import { useState, useCallback } from "react";
import Tabs from "@/components/ui/Tabs";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import ImageUploadPreview from "@/components/vision/ImageUploadPreview";
import StatsPanel from "@/components/vision/StatsPanel";
import VisionSplitPane from "@/components/vision/VisionSplitPane";
import BeforeAfterViewer from "@/components/vision/BeforeAfterViewer";
import OperationsPanel, { type OperationParams } from "@/components/vision/OperationsPanel";
import RGBHistogram from "@/components/vision/RGBHistogram";
import ProcessingHistory, { type HistoryEntry, saveToHistory } from "@/components/vision/ProcessingHistory";
import ExportPanel from "@/components/vision/ExportPanel";
import OpticalFlowTabComponent from "@/components/vision/OpticalFlowTab";
import DetectionTabComponent from "@/components/vision/DetectionTab";
import OCRTabComponent from "@/components/vision/OCRTab";
import {
  analyzeImage,
  analyzeErrors,
  type VisionAnalyzeResult,
  type ErrorAnalysisResult,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Preprocessing Tab
// ---------------------------------------------------------------------------

function PreprocessingTab() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VisionAnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [originalPreview, setOriginalPreview] = useState<string | null>(null);

  const handleFile = (f: File) => {
    setFile(f);
    setOriginalPreview(URL.createObjectURL(f));
    setResult(null);
    setError(null);
  };

  const handleAnalyze = useCallback(
    async (params: OperationParams) => {
      if (!file) return;
      setLoading(true);
      setError(null);
      try {
        // POST /api/vision/analyze takes a JSON *array* of {op, params} steps -
        // its own docstring says so, and it 400s on anything else. This used to
        // flatten the steps into an object keyed by op name, under a comment
        // claiming that was "the flat Record the API expects", so every analysis
        // from the console came back
        // `{"error": "operations must be a JSON array"}`. Found by the browser
        // e2e suite; nothing else exercised this path.
        const res = await analyzeImage(file, params.operations);
        setResult(res);

        // Save to processing history
        const thumbnail =
          // The endpoint returns the base64 under `image`. The console read
          // `processed_image`, which is never present, so a successful analysis
          // rendered no picture at all.
          res.image ?? res.processed_image
            ? `data:image/png;base64,${res.image ?? res.processed_image}`
            : originalPreview ?? "";
        saveToHistory({
          id: `preprocess-${Date.now()}`,
          thumbnail,
          operationType: params.operations.map((o) => o.op).join(", ") || "Preprocessing",
          timestamp: new Date().toISOString(),
          inputImage: originalPreview ?? undefined,
          results: res as unknown as Record<string, unknown>,
        });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Analysis failed";
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [file, originalPreview],
  );

  const handleRestore = useCallback((entry: HistoryEntry) => {
    if (entry.results) {
      setResult(entry.results as unknown as VisionAnalyzeResult);
    }
    if (entry.inputImage) {
      setOriginalPreview(entry.inputImage);
    }
  }, []);

  const processedSrc = result?.processed_image
    ? `data:image/png;base64,${result.processed_image}`
    : undefined;

  return (
    <VisionSplitPane
      left={
        <div className="space-y-6">
          <Card title="Image Upload">
            <ImageUploadPreview label="Upload an image to preprocess" onFile={handleFile} />
          </Card>

          <OperationsPanel onAnalyze={handleAnalyze} isAnalyzing={loading} />

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <ProcessingHistory onRestore={handleRestore} />
        </div>
      }
      right={
        result ? (
          <div className="space-y-4">
            <BeforeAfterViewer
              originalSrc={originalPreview ?? undefined}
              processedSrc={processedSrc}
              stats={
                result.stats
                  ? {
                      min: result.stats.mean?.[0] != null ? Math.min(...result.stats.mean) : 0,
                      max: result.stats.mean?.[0] != null ? Math.max(...result.stats.mean) : 0,
                      mean:
                        result.stats.mean?.length > 0
                          ? result.stats.mean.reduce((a: number, b: number) => a + b, 0) /
                            result.stats.mean.length
                          : 0,
                      std:
                        result.stats.std?.length > 0
                          ? result.stats.std.reduce((a: number, b: number) => a + b, 0) /
                            result.stats.std.length
                          : 0,
                    }
                  : undefined
              }
            />

            {result.stats && (
              <StatsPanel
                title="Image Statistics"
                stats={[
                  { label: "Shape", value: result.stats.shape.join(" x ") },
                  { label: "Dtype", value: result.stats.dtype },
                  ...result.stats.mean.map((m: number, i: number) => ({
                    label: `Mean Ch${i}`,
                    value: m,
                  })),
                  ...result.stats.std.map((s: number, i: number) => ({
                    label: `Std Ch${i}`,
                    value: s,
                  })),
                ]}
              />
            )}

            {result.histogram && (
              <RGBHistogram
                histogram={result.histogram as { r: number[]; g: number[]; b: number[] }}
              />
            )}

            <ExportPanel
              isVisible={true}
              processedImageB64={result.processed_image}
              results={result as unknown as Record<string, unknown>}
            />

            <p className="text-xs text-gray-500">
              Processed in {result.processing_time_ms?.toFixed(1) ?? "N/A"} ms
            </p>
          </div>
        ) : null
      }
    />
  );
}

// ---------------------------------------------------------------------------
// Optical Flow, Detection, OCR — use dedicated component implementations
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Error Analysis Tab
// ---------------------------------------------------------------------------

function ErrorAnalysisTab() {
  const [predictions, setPredictions] = useState("");
  const [groundTruth, setGroundTruth] = useState("");
  const [classes, setClasses] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ErrorAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    const preds = predictions
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    const gt = groundTruth
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    const cls = classes
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);

    if (preds.length === 0 || gt.length === 0 || cls.length === 0) {
      setError("All fields are required.");
      return;
    }
    if (preds.length !== gt.length) {
      setError("Predictions and ground truth must have the same number of lines.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await analyzeErrors(preds, gt, cls);
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error analysis failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const cellColor = (value: number, maxVal: number) => {
    if (maxVal === 0) return "bg-gray-50";
    const ratio = value / maxVal;
    if (ratio > 0.8) return "bg-red-200 text-red-900";
    if (ratio > 0.5) return "bg-orange-100 text-orange-900";
    if (ratio > 0.2) return "bg-yellow-50 text-yellow-900";
    if (value > 0) return "bg-blue-50 text-blue-900";
    return "bg-gray-50 text-gray-400";
  };

  return (
    <div className="space-y-6">
      <Card title="Input Data">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Predictions (one per line)
            </label>
            <textarea
              value={predictions}
              onChange={(e) => setPredictions(e.target.value)}
              rows={8}
              placeholder={"cat\ndog\ncat\nbird"}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Ground Truth (one per line)
            </label>
            <textarea
              value={groundTruth}
              onChange={(e) => setGroundTruth(e.target.value)}
              rows={8}
              placeholder={"cat\ncat\ndog\nbird"}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
        </div>

        <div className="mt-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Classes (comma-separated)
          </label>
          <input
            type="text"
            value={classes}
            onChange={(e) => setClasses(e.target.value)}
            placeholder="cat, dog, bird"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <div className="mt-4">
          <Button onClick={handleAnalyze} loading={loading}>
            Analyze Errors
          </Button>
        </div>
      </Card>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <StatsPanel
            title="Overall"
            stats={[
              { label: "Accuracy", value: `${(result.overall_accuracy * 100).toFixed(2)}%` },
            ]}
          />

          <Card title="Confusion Matrix">
            <div className="overflow-x-auto">
              <table className="text-sm">
                <thead>
                  <tr>
                    <th className="px-3 py-2 text-xs text-gray-500">True \ Pred</th>
                    {result.classes.map((c: string) => (
                      <th key={c} className="px-3 py-2 text-xs font-medium text-gray-700">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.confusion_matrix.map((row: number[], ri: number) => {
                    const maxVal = Math.max(...result.confusion_matrix.flat(), 1);
                    return (
                      <tr key={ri}>
                        <td className="px-3 py-2 text-xs font-medium text-gray-700">
                          {result.classes[ri]}
                        </td>
                        {row.map((val: number, ci: number) => (
                          <td
                            key={ci}
                            className={`px-3 py-2 text-center font-mono text-sm ${cellColor(val, maxVal)}`}
                          >
                            {val}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="Per-Class Metrics">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs font-medium uppercase text-gray-500">
                    <th className="px-3 py-2">Class</th>
                    <th className="px-3 py-2">Precision</th>
                    <th className="px-3 py-2">Recall</th>
                    <th className="px-3 py-2">F1</th>
                    <th className="px-3 py-2">Support</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {result.per_class_metrics.map((m: { class_name: string; precision: number; recall: number; f1: number; support: number }) => (
                    <tr key={m.class_name} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-medium text-gray-900">{m.class_name}</td>
                      <td className="px-3 py-2 text-gray-600">{(m.precision * 100).toFixed(1)}%</td>
                      <td className="px-3 py-2 text-gray-600">{(m.recall * 100).toFixed(1)}%</td>
                      <td className="px-3 py-2 text-gray-600">{(m.f1 * 100).toFixed(1)}%</td>
                      <td className="px-3 py-2 text-gray-500">{m.support}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {result.top_confusions.length > 0 && (
            <Card title="Top Confusions">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 text-left text-xs font-medium uppercase text-gray-500">
                      <th className="px-3 py-2">True Label</th>
                      <th className="px-3 py-2">Predicted</th>
                      <th className="px-3 py-2">Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {result.top_confusions.map((c: { true_label: string; predicted_label: string; count: number }, i: number) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-3 py-2 text-gray-900">{c.true_label}</td>
                        <td className="px-3 py-2 text-gray-600">{c.predicted_label}</td>
                        <td className="px-3 py-2 font-mono text-gray-500">{c.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

const TABS = [
  { id: "preprocessing", label: "Preprocessing" },
  { id: "optical-flow", label: "Optical Flow" },
  { id: "detection", label: "Detection" },
  { id: "ocr", label: "OCR" },
  { id: "error-analysis", label: "Error Analysis" },
];

export default function VisionPage() {
  const [activeTab, setActiveTab] = useState("preprocessing");

  const tabContent: Record<string, React.ReactNode> = {
    preprocessing: <PreprocessingTab />,
    "optical-flow": <OpticalFlowTabComponent />,
    detection: <DetectionTabComponent />,
    ocr: <OCRTabComponent />,
    "error-analysis": <ErrorAnalysisTab />,
  };

  const tabs = TABS.map((t) => ({ ...t, content: tabContent[t.id] }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Vision Analysis</h1>
        <p className="mt-1 text-sm text-gray-500">
          Computer vision analysis including preprocessing, optical flow, object
          detection, OCR, and error analysis.
        </p>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}
