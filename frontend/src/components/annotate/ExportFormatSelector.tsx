"use client";

import { useCallback, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ExportFormat = "coco_json" | "yolo_txt" | "pascal_voc_xml" | "csv";

interface ExportFormatSelectorProps {
  datasetId: string;
  assetIds: string[];
  onExport: (result: ExportResult) => void;
}

export interface ExportResult {
  format: ExportFormat;
  downloadUrl?: string;
  message: string;
  success: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const FORMAT_OPTIONS: { value: ExportFormat; label: string; description: string }[] = [
  { value: "coco_json", label: "COCO JSON", description: "Microsoft COCO format (.json)" },
  { value: "yolo_txt", label: "YOLO TXT", description: "Darknet / Ultralytics format (.txt)" },
  { value: "pascal_voc_xml", label: "Pascal VOC XML", description: "Pascal VOC format (.xml)" },
  { value: "csv", label: "CSV", description: "Flat CSV table (.csv)" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ExportFormatSelector({
  datasetId,
  assetIds,
  onExport,
}: ExportFormatSelectorProps) {
  const [format, setFormat] = useState<ExportFormat>("coco_json");
  const [currentOnly, setCurrentOnly] = useState(false);
  const [exporting, setExporting] = useState(false);

  const handleExport = useCallback(async () => {
    setExporting(true);
    try {
      const response = await fetch("/api/annotate/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_id: datasetId,
          format,
          asset_ids: currentOnly ? assetIds.slice(0, 1) : assetIds,
          current_only: currentOnly,
        }),
      });

      const data: Record<string, unknown> = await response.json();

      onExport({
        format,
        downloadUrl: data.download_url as string | undefined,
        message: (data.message as string) ?? "Export complete",
        success: response.ok,
      });
    } catch {
      onExport({
        format,
        message: "Export failed. Please try again.",
        success: false,
      });
    } finally {
      setExporting(false);
    }
  }, [format, currentOnly, datasetId, assetIds, onExport]);

  return (
    <div className="flex flex-col gap-3 p-4 bg-white rounded-lg border border-gray-200">
      <h4 className="text-sm font-semibold text-gray-900">Export Annotations</h4>

      {/* Format dropdown */}
      <div className="flex flex-col gap-1">
        <label htmlFor="export-format" className="text-xs font-medium text-gray-500 uppercase tracking-wider">
          Format
        </label>
        <select
          id="export-format"
          value={format}
          onChange={(e) => setFormat(e.target.value as ExportFormat)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        >
          {FORMAT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-400">
          {FORMAT_OPTIONS.find((o) => o.value === format)?.description}
        </span>
      </div>

      {/* Current image only */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={currentOnly}
          onChange={(e) => setCurrentOnly(e.target.checked)}
          className="rounded border-gray-300 text-brand-600 focus:ring-brand-500 h-4 w-4"
        />
        <span className="text-sm text-gray-700">Export Current Image Only</span>
      </label>

      {/* Export button */}
      <button
        onClick={() => void handleExport()}
        disabled={exporting || assetIds.length === 0}
        className={`w-full rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
          exporting || assetIds.length === 0
            ? "bg-gray-200 text-gray-500 cursor-not-allowed"
            : "bg-brand-600 text-white hover:bg-brand-700 shadow-sm"
        }`}
      >
        {exporting ? "Exporting..." : "Export"}
      </button>
    </div>
  );
}
