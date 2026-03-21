"use client";

import React, { useState, useRef, useCallback } from "react";
import Tabs from "@/components/ui/Tabs";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import FileUpload from "@/components/ui/FileUpload";
import DriftDetectionTab from "@/components/validate/DriftDetectionTab";
import ExplainabilityTab from "@/components/validate/ExplainabilityTab";
import ModelCardsTab from "@/components/validate/ModelCardsTab";
import CalibrationResults from "@/components/validate/CalibrationResults";
import ReliabilityDiagram from "@/components/validate/ReliabilityDiagram";
import ConfidenceHistogram from "@/components/validate/ConfidenceHistogram";

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
  /* Extended metrics (populated by enhanced endpoint) */
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1?: number;
  auc_roc?: number;
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
          {/* VA1 — 6 stat cards row */}
          <CalibrationResults
            results={{
              bins: result.bins,
              ece: result.ece,
              mce: result.mce,
              is_calibrated: result.is_calibrated,
              accuracy: result.accuracy,
              precision: result.precision,
              recall: result.recall,
              f1: result.f1,
              auc_roc: result.auc_roc,
            }}
          />

          {/* Reliability Diagram (SVG 300x300) */}
          <Card title="Reliability Diagram">
            <ReliabilityDiagram bins={result.bins} />
          </Card>

          {/* Confidence Histogram (SVG 400x200) */}
          <Card title="Confidence Distribution">
            <ConfidenceHistogram bins={result.bins} />
          </Card>
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Export Report Floating Button (VA5)                                 */
/* ------------------------------------------------------------------ */

interface ExportMenuProps {
  onExportPdf: () => void;
  onExportJson: () => void;
  onCopySummary: () => void;
}

function ExportReportButton({ onExportPdf, onExportJson, onCopySummary }: ExportMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const toggle = useCallback(() => setOpen((prev) => !prev), []);

  return (
    <div ref={menuRef} className="fixed bottom-6 right-6 z-50">
      {open && (
        <div className="mb-2 flex flex-col gap-1 rounded-lg border border-gray-200 bg-white p-2 shadow-lg">
          <button
            onClick={() => { onExportPdf(); setOpen(false); }}
            className="flex items-center gap-2 rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            Download PDF
          </button>
          <button
            onClick={() => { onExportJson(); setOpen(false); }}
            className="flex items-center gap-2 rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            Download JSON
          </button>
          <button
            onClick={() => { onCopySummary(); setOpen(false); }}
            className="flex items-center gap-2 rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            Copy Summary
          </button>
        </div>
      )}
      <button
        onClick={toggle}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg transition-transform hover:scale-105 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        aria-label="Export Report"
        title="Export Report"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"
          />
        </svg>
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

export default function ValidatePage() {
  const [activeTab, setActiveTab] = useState("calibration");

  /* ---- Export handlers (VA5) ---- */
  const handleExportPdf = useCallback(() => {
    window.print();
  }, []);

  const handleExportJson = useCallback(() => {
    const payload = {
      exported_at: new Date().toISOString(),
      active_tab: activeTab,
      note: "Full export requires backend report generation (V2).",
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `validate-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [activeTab]);

  const handleCopySummary = useCallback(async () => {
    const summary = `Validate & Trust Report\nTab: ${activeTab}\nExported: ${new Date().toISOString()}`;
    try {
      await navigator.clipboard.writeText(summary);
    } catch {
      const textArea = document.createElement("textarea");
      textArea.value = summary;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
    }
  }, [activeTab]);

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

      {/* VA5 — Floating Export Report button */}
      <ExportReportButton
        onExportPdf={handleExportPdf}
        onExportJson={handleExportJson}
        onCopySummary={handleCopySummary}
      />
    </div>
  );
}
