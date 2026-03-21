"use client";

import { useState } from "react";
import Tabs from "@/components/ui/Tabs";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ImageUploadPreview from "@/components/vision/ImageUploadPreview";
import DualFrameUpload from "@/components/vision/DualFrameUpload";
import DetectionOverlay from "@/components/vision/DetectionOverlay";
import StatsPanel from "@/components/vision/StatsPanel";
import {
  analyzeImage,
  computeOpticalFlow,
  detectObjects,
  extractText,
  analyzeErrors,
  type VisionAnalyzeResult,
  type OpticalFlowResult,
  type DetectResult,
  type OCRResult,
  type ErrorAnalysisResult,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Preprocessing Tab
// ---------------------------------------------------------------------------

function PreprocessingTab() {
  const [file, setFile] = useState<File | null>(null);
  const [normalize, setNormalize] = useState<string>("");
  const [colorSpace, setColorSpace] = useState<string>("");
  const [edgeDetection, setEdgeDetection] = useState<string>("");
  const [resizeW, setResizeW] = useState("");
  const [resizeH, setResizeH] = useState("");
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

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const operations: Record<string, unknown> = {};
      if (normalize) operations.normalize = normalize;
      if (colorSpace) operations.color_space = colorSpace;
      if (edgeDetection) operations.edge_detection = edgeDetection;
      if (resizeW && resizeH) {
        operations.resize = { width: parseInt(resizeW), height: parseInt(resizeH) };
      }
      const res = await analyzeImage(file, operations);
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Analysis failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card title="Image Upload">
        <ImageUploadPreview label="Upload an image to preprocess" onFile={handleFile} />
      </Card>

      <Card title="Operations">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Normalize
            </label>
            <select
              value={normalize}
              onChange={(e) => setNormalize(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">None</option>
              <option value="min_max">Min-Max</option>
              <option value="z_score">Z-Score</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Color Space
            </label>
            <select
              value={colorSpace}
              onChange={(e) => setColorSpace(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">Original</option>
              <option value="rgb">RGB</option>
              <option value="hsv">HSV</option>
              <option value="lab">LAB</option>
              <option value="gray">Grayscale</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Edge Detection
            </label>
            <select
              value={edgeDetection}
              onChange={(e) => setEdgeDetection(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">None</option>
              <option value="canny">Canny</option>
              <option value="sobel">Sobel</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Resize (W x H)
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={resizeW}
                onChange={(e) => setResizeW(e.target.value)}
                placeholder="W"
                className="w-20 rounded-lg border border-gray-300 px-2 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <span className="text-gray-400">x</span>
              <input
                type="number"
                value={resizeH}
                onChange={(e) => setResizeH(e.target.value)}
                placeholder="H"
                className="w-20 rounded-lg border border-gray-300 px-2 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
        </div>

        <div className="mt-4">
          <Button onClick={handleAnalyze} loading={loading} disabled={!file}>
            Analyze
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
          <Card title="Before / After">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <p className="mb-2 text-sm font-medium text-gray-600">Original</p>
                {originalPreview && (
                  <img
                    src={originalPreview}
                    alt="Original"
                    className="max-h-72 rounded border border-gray-200 object-contain"
                  />
                )}
              </div>
              <div>
                <p className="mb-2 text-sm font-medium text-gray-600">Processed</p>
                {result.processed_image && (
                  <img
                    src={`data:image/png;base64,${result.processed_image}`}
                    alt="Processed"
                    className="max-h-72 rounded border border-gray-200 object-contain"
                  />
                )}
              </div>
            </div>
          </Card>

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

          <p className="text-xs text-gray-500">
            Processed in {result.processing_time_ms?.toFixed(1) ?? "N/A"} ms
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Optical Flow Tab
// ---------------------------------------------------------------------------

function OpticalFlowTab() {
  const [frame1, setFrame1] = useState<File | null>(null);
  const [frame2, setFrame2] = useState<File | null>(null);
  const [method, setMethod] = useState<"lucas_kanade" | "farneback">("farneback");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OpticalFlowResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview1, setPreview1] = useState<string | null>(null);
  const [preview2, setPreview2] = useState<string | null>(null);

  const handleFrame1 = (f: File) => {
    setFrame1(f);
    setPreview1(URL.createObjectURL(f));
    setResult(null);
  };
  const handleFrame2 = (f: File) => {
    setFrame2(f);
    setPreview2(URL.createObjectURL(f));
    setResult(null);
  };

  const handleCompute = async () => {
    if (!frame1 || !frame2) return;
    setLoading(true);
    setError(null);
    try {
      const res = await computeOpticalFlow(frame1, frame2, method);
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Optical flow failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card title="Upload Two Frames">
        <DualFrameUpload onFrame1={handleFrame1} onFrame2={handleFrame2} />
      </Card>

      <Card title="Method">
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="flow-method"
              checked={method === "lucas_kanade"}
              onChange={() => setMethod("lucas_kanade")}
              className="text-brand-600 focus:ring-brand-500"
            />
            Lucas-Kanade
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="flow-method"
              checked={method === "farneback"}
              onChange={() => setMethod("farneback")}
              className="text-brand-600 focus:ring-brand-500"
            />
            Farneback
          </label>
        </div>

        <div className="mt-4">
          <Button onClick={handleCompute} loading={loading} disabled={!frame1 || !frame2}>
            Compute Flow
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
          <Card title="Results">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <p className="mb-2 text-sm font-medium text-gray-600">Frame 1</p>
                {preview1 && (
                  <img
                    src={preview1}
                    alt="Frame 1"
                    className="max-h-56 rounded border border-gray-200 object-contain"
                  />
                )}
              </div>
              <div>
                <p className="mb-2 text-sm font-medium text-gray-600">Frame 2</p>
                {preview2 && (
                  <img
                    src={preview2}
                    alt="Frame 2"
                    className="max-h-56 rounded border border-gray-200 object-contain"
                  />
                )}
              </div>
              <div>
                <p className="mb-2 text-sm font-medium text-gray-600">Motion Heatmap</p>
                {result.visualization && (
                  <img
                    src={`data:image/png;base64,${result.visualization}`}
                    alt="Motion heatmap"
                    className="max-h-56 rounded border border-gray-200 object-contain"
                  />
                )}
              </div>
            </div>
          </Card>

          {result.stats && (
            <StatsPanel
              title="Flow Statistics"
              stats={[
                { label: "Mean Magnitude", value: result.stats.mean_magnitude },
                { label: "Max Magnitude", value: result.stats.max_magnitude },
                { label: "Motion Area %", value: `${result.stats.motion_area_pct.toFixed(2)}%` },
              ]}
            />
          )}

          <p className="text-xs text-gray-500">
            Processed in {result.processing_time_ms?.toFixed(1) ?? "N/A"} ms
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detection Tab
// ---------------------------------------------------------------------------

function DetectionTab() {
  const [file, setFile] = useState<File | null>(null);
  const [confidence, setConfidence] = useState(0.5);
  const [classFilter, setClassFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DetectResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDetect = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await detectObjects(
        file,
        confidence,
        classFilter.trim() || undefined,
      );
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Detection failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card title="Image Upload">
        <ImageUploadPreview
          label="Upload an image for object detection"
          onFile={(f) => {
            setFile(f);
            setResult(null);
            setError(null);
          }}
        />
      </Card>

      <Card title="Detection Settings">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Confidence Threshold: {confidence.toFixed(2)}
            </label>
            <input
              type="range"
              min={0.1}
              max={1.0}
              step={0.05}
              value={confidence}
              onChange={(e) => setConfidence(parseFloat(e.target.value))}
              className="w-full accent-brand-600"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>0.1</span>
              <span>1.0</span>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Class Filter (comma-separated IDs)
            </label>
            <input
              type="text"
              value={classFilter}
              onChange={(e) => setClassFilter(e.target.value)}
              placeholder="e.g. 0,1,2"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
        </div>

        <div className="mt-4">
          <Button onClick={handleDetect} loading={loading} disabled={!file}>
            Detect
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
          <Card title={`Detections (${result.count})`}>
            {result.visualization && (
              <img
                src={`data:image/png;base64,${result.visualization}`}
                alt="Detections"
                className="max-w-full rounded border border-gray-200"
              />
            )}
          </Card>

          {result.detections.length > 0 && (
            <Card title="Detection List">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 text-left text-xs font-medium uppercase text-gray-500">
                      <th className="px-3 py-2">Class</th>
                      <th className="px-3 py-2">Confidence</th>
                      <th className="px-3 py-2">Bounding Box (x, y, w, h)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {result.detections.map((d, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-3 py-2 font-medium text-gray-900">
                          {d.class_name ?? d.label}
                        </td>
                        <td className="px-3 py-2 text-gray-600">
                          {(d.confidence * 100).toFixed(1)}%
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-gray-500">
                          {d.bbox?.join(", ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          <p className="text-xs text-gray-500">
            Processed in {result.processing_time_ms?.toFixed(1) ?? "N/A"} ms
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// OCR Tab
// ---------------------------------------------------------------------------

function OCRTab() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OCRResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [imgSrc, setImgSrc] = useState<string | null>(null);

  const handleFile = (f: File) => {
    setFile(f);
    setImgSrc(URL.createObjectURL(f));
    setResult(null);
    setError(null);
  };

  const handleExtract = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await extractText(file);
      setResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "OCR failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card title="Image Upload">
        <ImageUploadPreview label="Upload an image for text extraction" onFile={handleFile} />
      </Card>

      <div>
        <Button onClick={handleExtract} loading={loading} disabled={!file}>
          Extract Text
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {imgSrc && result.blocks.length > 0 && (
            <Card title="Text Regions">
              <DetectionOverlay
                imageSrc={imgSrc}
                boxes={result.blocks.map((b: { text: string; confidence: number; bbox: number[] }) => ({
                  label: b.text.slice(0, 20),
                  confidence: b.confidence,
                  bbox: b.bbox,
                }))}
              />
            </Card>
          )}

          <Card title="Extracted Text">
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded bg-gray-50 p-4 text-sm text-gray-800">
              {result.full_text || "(no text found)"}
            </pre>
          </Card>

          {result.blocks.length > 0 && (
            <Card title="Text Blocks">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 text-left text-xs font-medium uppercase text-gray-500">
                      <th className="px-3 py-2">Text</th>
                      <th className="px-3 py-2">Confidence</th>
                      <th className="px-3 py-2">BBox</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {result.blocks.map((b: { text: string; confidence: number; bbox: number[] }, i: number) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-3 py-2 text-gray-900">{b.text}</td>
                        <td className="px-3 py-2 text-gray-600">
                          {(b.confidence * 100).toFixed(1)}%
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-gray-500">
                          {b.bbox.join(", ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          <p className="text-xs text-gray-500">
            Processed in {result.processing_time_ms?.toFixed(1) ?? "N/A"} ms
          </p>
        </div>
      )}
    </div>
  );
}

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
    "optical-flow": <OpticalFlowTab />,
    detection: <DetectionTab />,
    ocr: <OCRTab />,
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
