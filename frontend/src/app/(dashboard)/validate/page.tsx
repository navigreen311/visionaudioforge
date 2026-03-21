"use client";

import React, { useState } from "react";
import Tabs from "@/components/ui/Tabs";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import FileUpload from "@/components/ui/FileUpload";
import DriftDetectionTab from "@/components/validate/DriftDetectionTab";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface CalibrationBin {
  bin_start: number;
  bin_end: number;
  avg_confidence: number;
  accuracy: number;
  count: number;
}

interface CalibrationResult {
  bins: CalibrationBin[];
  ece: number;
  mce: number;
  is_calibrated: boolean;
}

interface FeatureAttribution {
  feature: string;
  importance: number;
}

interface ModelCard {
  model_name: string;
  version: string;
  description: string;
  metrics: Record<string, number>;
  intended_use: string;
  limitations: string;
  training_data: string;
  evaluation_results: Record<string, number>;
  ethical_considerations: string;
}

/* ------------------------------------------------------------------ */
/*  Calibration Tab                                                    */
/* ------------------------------------------------------------------ */

function CalibrationTab() {
  const [result, setResult] = useState<CalibrationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [predictionsText, setPredictionsText] = useState("");
  const [groundTruthText, setGroundTruthText] = useState("");

  const handleAnalyze = async () => {
    setError(null);
    try {
      const predictions = predictionsText.split(",").map((s) => parseFloat(s.trim()));
      const ground_truth = groundTruthText.split(",").map((s) => parseInt(s.trim(), 10));

      if (predictions.some(isNaN) || ground_truth.some(isNaN)) {
        setError("Invalid input. Provide comma-separated numbers.");
        return;
      }

      setLoading(true);
      const resp = await fetch(`${API_BASE}/api/validate/calibration`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ predictions, ground_truth, n_bins: 10 }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      setResult(await resp.json());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (files: File[]) => {
    const file = files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const lines = text.trim().split("\n");
      if (lines.length >= 2) {
        setPredictionsText(lines[0]);
        setGroundTruthText(lines[1]);
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="space-y-6">
      <Card title="Upload Predictions">
        <p className="mb-3 text-sm text-gray-500">
          Upload a CSV with two rows: predictions (float) and ground truth (0/1), or enter them manually below.
        </p>
        <FileUpload accept=".csv,.txt" onFiles={handleFileUpload} />
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Predictions (comma-separated)
            </label>
            <textarea
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              rows={3}
              value={predictionsText}
              onChange={(e) => setPredictionsText(e.target.value)}
              placeholder="0.1, 0.4, 0.6, 0.9"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ground Truth (comma-separated)
            </label>
            <textarea
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              rows={3}
              value={groundTruthText}
              onChange={(e) => setGroundTruthText(e.target.value)}
              placeholder="0, 0, 1, 1"
            />
          </div>
        </div>
        <div className="mt-4">
          <Button onClick={handleAnalyze} disabled={loading}>
            {loading ? "Analyzing..." : "Run Calibration Analysis"}
          </Button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </Card>

      {result && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Card title="ECE">
              <p className="text-3xl font-bold text-gray-900">{result.ece.toFixed(4)}</p>
              <p className="text-sm text-gray-500">Expected Calibration Error</p>
            </Card>
            <Card title="MCE">
              <p className="text-3xl font-bold text-gray-900">{result.mce.toFixed(4)}</p>
              <p className="text-sm text-gray-500">Max Calibration Error</p>
            </Card>
            <Card title="Status">
              <Badge variant={result.is_calibrated ? "success" : "warning"}>
                {result.is_calibrated ? "Well Calibrated" : "Needs Calibration"}
              </Badge>
            </Card>
          </div>

          <Card title="Reliability Diagram">
            <div className="flex items-end gap-1" style={{ height: 220 }}>
              {result.bins.map((bin, i) => {
                const maxH = 200;
                const confH = bin.avg_confidence * maxH;
                const accH = bin.accuracy * maxH;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                    <div className="w-full flex items-end gap-px" style={{ height: maxH }}>
                      <div
                        className="flex-1 bg-blue-300 rounded-t"
                        style={{ height: confH }}
                        title={`Confidence: ${bin.avg_confidence.toFixed(2)}`}
                      />
                      <div
                        className="flex-1 bg-green-500 rounded-t"
                        style={{ height: accH }}
                        title={`Accuracy: ${bin.accuracy.toFixed(2)}`}
                      />
                    </div>
                    <span className="text-[10px] text-gray-400">
                      {bin.bin_start.toFixed(1)}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="mt-2 flex gap-4 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-blue-300" /> Confidence
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-green-500" /> Accuracy
              </span>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Explainability Tab                                                 */
/* ------------------------------------------------------------------ */

function ExplainabilityTab() {
  const [saliencyB64, setSaliencyB64] = useState<string | null>(null);
  const [attributions, setAttributions] = useState<FeatureAttribution[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modelOutput, setModelOutput] = useState('{"class": "cat", "confidence": 0.92}');
  const [imageFile, setImageFile] = useState<File | null>(null);

  const handleExplain = async () => {
    if (!imageFile) {
      setError("Please upload an image first.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", imageFile);
      formData.append("model_output", modelOutput);
      const resp = await fetch(`${API_BASE}/api/validate/explain`, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      setSaliencyB64(data.saliency_map_base64);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleAttribution = async () => {
    setError(null);
    try {
      // Demo feature attribution with sample data
      const resp = await fetch(`${API_BASE}/api/validate/calibration`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          predictions: [0.1, 0.5, 0.9],
          ground_truth: [0, 1, 1],
          n_bins: 10,
        }),
      });
      if (resp.ok) {
        // Show mock attribution for demo
        setAttributions([
          { feature: "edge_density", importance: 0.87 },
          { feature: "color_histogram", importance: 0.65 },
          { feature: "texture_score", importance: 0.43 },
          { feature: "brightness", importance: 0.21 },
          { feature: "noise_level", importance: -0.12 },
        ]);
      }
    } catch {
      setError("Attribution request failed");
    }
  };

  return (
    <div className="space-y-6">
      <Card title="Saliency Map">
        <p className="mb-3 text-sm text-gray-500">
          Upload an image and provide model output to generate a saliency heatmap.
        </p>
        <FileUpload
          accept="image/*"
          onFiles={(files) => setImageFile(files[0] ?? null)}
        />
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Model Output (JSON)
          </label>
          <textarea
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
            rows={3}
            value={modelOutput}
            onChange={(e) => setModelOutput(e.target.value)}
          />
        </div>
        <div className="mt-4 flex gap-3">
          <Button onClick={handleExplain} disabled={loading}>
            {loading ? "Generating..." : "Generate Saliency Map"}
          </Button>
          <Button onClick={handleAttribution} disabled={loading}>
            Feature Attribution
          </Button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </Card>

      {saliencyB64 && (
        <Card title="Saliency Heatmap">
          <div className="flex justify-center rounded bg-gray-900 p-4">
            <img
              src={`data:image/x-portable-graymap;base64,${saliencyB64}`}
              alt="Saliency heatmap"
              className="max-h-96 object-contain"
            />
          </div>
          <p className="mt-2 text-xs text-gray-500">
            V1: Sobel gradient magnitude. Full Grad-CAM requires model access (V2).
          </p>
        </Card>
      )}

      {attributions && (
        <Card title="Feature Importance">
          <div className="space-y-2">
            {attributions.map((attr) => {
              const absImp = Math.abs(attr.importance);
              const isNegative = attr.importance < 0;
              return (
                <div key={attr.feature} className="flex items-center gap-3">
                  <span className="w-36 text-sm font-medium text-gray-700 truncate">
                    {attr.feature}
                  </span>
                  <div className="flex-1 h-5 bg-gray-100 rounded overflow-hidden">
                    <div
                      className={`h-full rounded ${isNegative ? "bg-red-400" : "bg-blue-500"}`}
                      style={{ width: `${absImp * 100}%` }}
                    />
                  </div>
                  <span className="w-14 text-right text-sm text-gray-600">
                    {attr.importance.toFixed(2)}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Model Cards Tab                                                    */
/* ------------------------------------------------------------------ */

function ModelCardsTab() {
  const [modelId, setModelId] = useState("");
  const [card, setCard] = useState<ModelCard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Demo model card for display
  const demoCard: ModelCard = {
    model_name: "resnet50-detector",
    version: "2.1.0",
    description: "ResNet50-based object detector for industrial inspection.",
    metrics: { accuracy: 0.94, f1: 0.91, precision: 0.93, recall: 0.89 },
    intended_use: "Production inference on vision/audio data within the VisionAudioForge platform.",
    limitations:
      "Performance may degrade on out-of-distribution data. Evaluate calibration and drift before deploying to new domains.",
    training_data: "Industrial inspection dataset v3 (50k images, 12 defect classes).",
    evaluation_results: { accuracy: 0.94, f1: 0.91, precision: 0.93, recall: 0.89 },
    ethical_considerations:
      "Ensure representative evaluation across demographic groups. Monitor for fairness and bias before production deployment.",
  };

  const handleFetch = async () => {
    if (!modelId.trim()) {
      setCard(demoCard);
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/validate/model-card/${modelId}`);
      if (resp.status === 501) {
        // Stub endpoint — show demo card
        setCard(demoCard);
        setError("Model card endpoint returns stub (V2). Showing demo card.");
        return;
      }
      if (!resp.ok) throw new Error(await resp.text());
      setCard(await resp.json());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Request failed");
      setCard(demoCard);
    } finally {
      setLoading(false);
    }
  };

  const displayCard = card ?? null;

  return (
    <div className="space-y-6">
      <Card title="Select Model">
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Model ID (UUID) — leave blank for demo
            </label>
            <input
              type="text"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              placeholder="00000000-0000-0000-0000-000000000001"
            />
          </div>
          <Button onClick={handleFetch} disabled={loading}>
            {loading ? "Loading..." : "Load Model Card"}
          </Button>
        </div>
        {error && <p className="mt-2 text-sm text-yellow-600">{error}</p>}
      </Card>

      {displayCard && (
        <div className="space-y-4">
          <Card title={`${displayCard.model_name} v${displayCard.version}`}>
            <p className="text-sm text-gray-600">{displayCard.description}</p>
          </Card>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card title="Metrics">
              <dl className="space-y-2">
                {Object.entries(displayCard.metrics).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-600 capitalize">{k}</dt>
                    <dd className="text-sm font-semibold text-gray-900">
                      {typeof v === "number" ? v.toFixed(4) : String(v)}
                    </dd>
                  </div>
                ))}
              </dl>
            </Card>

            <Card title="Evaluation Results">
              <dl className="space-y-2">
                {Object.entries(displayCard.evaluation_results).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-600 capitalize">{k}</dt>
                    <dd className="text-sm font-semibold text-gray-900">
                      {typeof v === "number" ? v.toFixed(4) : String(v)}
                    </dd>
                  </div>
                ))}
              </dl>
            </Card>
          </div>

          <Card title="Intended Use">
            <p className="text-sm text-gray-600">{displayCard.intended_use}</p>
          </Card>

          <Card title="Limitations">
            <p className="text-sm text-gray-600">{displayCard.limitations}</p>
          </Card>

          <Card title="Training Data">
            <p className="text-sm text-gray-600">{displayCard.training_data}</p>
          </Card>

          <Card title="Ethical Considerations">
            <p className="text-sm text-gray-600">{displayCard.ethical_considerations}</p>
          </Card>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

export default function ValidatePage() {
  const [activeTab, setActiveTab] = useState("calibration");

  const tabs = [
    { id: "calibration", label: "Calibration", content: <CalibrationTab /> },
    { id: "drift", label: "Drift Detection", content: <DriftDetectionTab /> },
    { id: "explainability", label: "Explainability", content: <ExplainabilityTab /> },
    { id: "model-cards", label: "Model Cards", content: <ModelCardsTab /> },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Validate &amp; Trust</h1>
        <p className="mt-1 text-sm text-gray-500">
          Confidence calibration, drift detection, explainability, and model cards.
        </p>
      </div>
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}
