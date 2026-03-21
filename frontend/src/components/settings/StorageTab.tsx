"use client";

import React, { useState, useCallback } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import DataTable from "@/components/ui/DataTable";
import Modal from "@/components/ui/Modal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CategoryUsage {
  category: string;
  size_gb: number;
  percentage: number;
  color: string;
}

interface LargestAsset {
  id: string;
  filename: string;
  type: string;
  size_mb: number;
  last_accessed: string;
}

interface RetentionPolicy {
  category: string;
  retention: string;
  auto_delete_gb: number | null;
}

interface StorageData {
  used_gb: number;
  total_gb: number;
  categories: CategoryUsage[];
  largest_assets: LargestAsset[];
  retention_policies: RetentionPolicy[];
}

// ---------------------------------------------------------------------------
// Mock data (mirrors backend GET /api/settings/storage)
// ---------------------------------------------------------------------------

const MOCK_STORAGE: StorageData = {
  used_gb: 2.4,
  total_gb: 10.0,
  categories: [
    { category: "Images", size_gb: 1.2, percentage: 50.0, color: "#3B82F6" },
    { category: "Audio", size_gb: 0.792, percentage: 33.0, color: "#8B5CF6" },
    { category: "Video", size_gb: 0.3, percentage: 12.5, color: "#14B8A6" },
    { category: "Other", size_gb: 0.108, percentage: 4.5, color: "#6B7280" },
  ],
  largest_assets: [
    { id: "ast_001", filename: "warehouse_cam_01.mp4", type: "Video", size_mb: 185.4, last_accessed: "2026-03-18" },
    { id: "ast_002", filename: "training_batch_v3.zip", type: "Other", size_mb: 142.7, last_accessed: "2026-03-10" },
    { id: "ast_003", filename: "defect_dataset.tar.gz", type: "Other", size_mb: 98.3, last_accessed: "2026-03-15" },
    { id: "ast_004", filename: "audio_samples_q1.wav", type: "Audio", size_mb: 87.6, last_accessed: "2026-03-19" },
    { id: "ast_005", filename: "floor_plan_hires.png", type: "Images", size_mb: 76.2, last_accessed: "2026-03-20" },
    { id: "ast_006", filename: "inspection_feed.mp4", type: "Video", size_mb: 64.8, last_accessed: "2026-03-12" },
    { id: "ast_007", filename: "env_noise_baseline.wav", type: "Audio", size_mb: 54.1, last_accessed: "2026-03-14" },
    { id: "ast_008", filename: "annotated_frames.zip", type: "Other", size_mb: 48.9, last_accessed: "2026-03-17" },
    { id: "ast_009", filename: "product_catalog.jpg", type: "Images", size_mb: 32.5, last_accessed: "2026-03-20" },
    { id: "ast_010", filename: "shift_summary.png", type: "Images", size_mb: 28.1, last_accessed: "2026-03-19" },
  ],
  retention_policies: [
    { category: "Images", retention: "forever", auto_delete_gb: null },
    { category: "Audio", retention: "90d", auto_delete_gb: 2.0 },
    { category: "Video", retention: "30d", auto_delete_gb: 1.0 },
    { category: "Other", retention: "1yr", auto_delete_gb: null },
  ],
};

const RETENTION_OPTIONS = [
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "1yr", label: "1 year" },
  { value: "forever", label: "Forever" },
];

// ---------------------------------------------------------------------------
// Donut Chart (SVG, 200x200)
// ---------------------------------------------------------------------------

function DonutChart({ categories }: { categories: CategoryUsage[] }) {
  const size = 200;
  const cx = size / 2;
  const cy = size / 2;
  const outerR = 85;
  const innerR = 55;

  // Build arc paths for each slice
  let cumulativeAngle = -90; // start from top

  const slices = categories.map((cat) => {
    const angleDeg = (cat.percentage / 100) * 360;
    const startAngle = cumulativeAngle;
    const endAngle = cumulativeAngle + angleDeg;
    cumulativeAngle = endAngle;

    const toRad = (deg: number) => (deg * Math.PI) / 180;

    const x1Outer = cx + outerR * Math.cos(toRad(startAngle));
    const y1Outer = cy + outerR * Math.sin(toRad(startAngle));
    const x2Outer = cx + outerR * Math.cos(toRad(endAngle));
    const y2Outer = cy + outerR * Math.sin(toRad(endAngle));

    const x1Inner = cx + innerR * Math.cos(toRad(endAngle));
    const y1Inner = cy + innerR * Math.sin(toRad(endAngle));
    const x2Inner = cx + innerR * Math.cos(toRad(startAngle));
    const y2Inner = cy + innerR * Math.sin(toRad(startAngle));

    const largeArc = angleDeg > 180 ? 1 : 0;

    const d = [
      `M ${x1Outer} ${y1Outer}`,
      `A ${outerR} ${outerR} 0 ${largeArc} 1 ${x2Outer} ${y2Outer}`,
      `L ${x1Inner} ${y1Inner}`,
      `A ${innerR} ${innerR} 0 ${largeArc} 0 ${x2Inner} ${y2Inner}`,
      "Z",
    ].join(" ");

    return { d, color: cat.color, category: cat.category, percentage: cat.percentage };
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mx-auto">
      {slices.map((slice) => (
        <path
          key={slice.category}
          d={slice.d}
          fill={slice.color}
          className="transition-opacity hover:opacity-80"
        >
          <title>{slice.category}: {slice.percentage}%</title>
        </path>
      ))}
      {/* Center label */}
      <text x={cx} y={cy - 6} textAnchor="middle" className="fill-gray-900 text-lg font-bold" fontSize="18">
        {MOCK_STORAGE.used_gb} GB
      </text>
      <text x={cx} y={cy + 14} textAnchor="middle" className="fill-gray-500 text-xs" fontSize="12">
        of {MOCK_STORAGE.total_gb} GB
      </text>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Legend
// ---------------------------------------------------------------------------

function ChartLegend({ categories }: { categories: CategoryUsage[] }) {
  return (
    <div className="space-y-2">
      {categories.map((cat) => (
        <div key={cat.category} className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ backgroundColor: cat.color }}
            />
            <span className="text-gray-700">{cat.category}</span>
          </div>
          <span className="text-gray-500">
            {cat.size_gb.toFixed(2)} GB ({cat.percentage}%)
          </span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Total Usage Bar
// ---------------------------------------------------------------------------

function UsageBar({ usedGb, totalGb }: { usedGb: number; totalGb: number }) {
  const pct = Math.min((usedGb / totalGb) * 100, 100);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">Total Storage</span>
        <span className="text-sm text-gray-500">
          {usedGb} GB / {totalGb} GB
        </span>
      </div>
      <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-brand-600 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-gray-400 mt-1">{(totalGb - usedGb).toFixed(1)} GB remaining</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Danger Action (with confirm modal)
// ---------------------------------------------------------------------------

interface DangerActionProps {
  label: string;
  description: string;
  confirmText: string;
  onConfirm: () => void;
}

function DangerAction({ label, description, confirmText, onConfirm }: DangerActionProps) {
  const [open, setOpen] = useState(false);

  const handleConfirm = useCallback(() => {
    onConfirm();
    setOpen(false);
  }, [onConfirm]);

  return (
    <>
      <div className="flex items-center justify-between py-3">
        <div>
          <p className="text-sm font-medium text-gray-900">{label}</p>
          <p className="text-xs text-gray-500">{description}</p>
        </div>
        <Button variant="danger" size="sm" onClick={() => setOpen(true)}>
          {label}
        </Button>
      </div>

      <Modal
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Confirm Destructive Action"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleConfirm}>
              {confirmText}
            </Button>
          </>
        }
      >
        <p className="text-sm text-gray-700">
          Are you sure you want to <strong>{label.toLowerCase()}</strong>? This action cannot be
          undone.
        </p>
      </Modal>
    </>
  );
}

// ---------------------------------------------------------------------------
// StorageTab (main export)
// ---------------------------------------------------------------------------

export default function StorageTab() {
  const [data] = useState<StorageData>(MOCK_STORAGE);
  const [assets, setAssets] = useState<LargestAsset[]>(MOCK_STORAGE.largest_assets);
  const [policies, setPolicies] = useState<RetentionPolicy[]>(MOCK_STORAGE.retention_policies);

  // --- Retention helpers ---
  const updateRetention = useCallback(
    (category: string, retention: string) => {
      setPolicies((prev) =>
        prev.map((p) => (p.category === category ? { ...p, retention } : p)),
      );
    },
    [],
  );

  const updateAutoDeleteGb = useCallback(
    (category: string, value: string) => {
      const parsed = value === "" ? null : parseFloat(value);
      setPolicies((prev) =>
        prev.map((p) =>
          p.category === category
            ? { ...p, auto_delete_gb: parsed !== null && !isNaN(parsed) ? parsed : null }
            : p,
        ),
      );
    },
    [],
  );

  // --- Asset delete handler ---
  const handleDeleteAsset = useCallback((id: string) => {
    setAssets((prev) => prev.filter((a) => a.id !== id));
  }, []);

  // --- Danger action handlers (stubs — would call API) ---
  const handleDeleteOldAssets = useCallback(() => {
    setAssets((prev) => prev.filter((a) => {
      const accessed = new Date(a.last_accessed);
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - 90);
      return accessed >= cutoff;
    }));
  }, []);

  const handlePurgeExports = useCallback(() => {
    // stub — would POST /api/settings/storage/purge-exports
  }, []);

  const handleClearAnnotations = useCallback(() => {
    // stub — would POST /api/settings/storage/clear-annotations
  }, []);

  // --- Table columns ---
  const assetColumns = [
    { key: "filename", label: "Filename", sortable: true },
    {
      key: "type",
      label: "Type",
      sortable: true,
      render: (v: unknown) => {
        const t = String(v);
        const variantMap: Record<string, "info" | "success" | "warning" | "neutral"> = {
          Images: "info",
          Audio: "success",
          Video: "warning",
          Other: "neutral",
        };
        return <Badge variant={variantMap[t] ?? "neutral"}>{t}</Badge>;
      },
    },
    {
      key: "size_mb",
      label: "Size",
      sortable: true,
      render: (v: unknown) => `${Number(v).toFixed(1)} MB`,
    },
    { key: "last_accessed", label: "Last Accessed", sortable: true },
    {
      key: "id",
      label: "Actions",
      render: (_v: unknown, row: Record<string, unknown>) => (
        <Button
          variant="danger"
          size="sm"
          onClick={() => handleDeleteAsset(String(row.id))}
        >
          Delete
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* --- Total Usage Bar --- */}
      <Card title="Storage Overview">
        <UsageBar usedGb={data.used_gb} totalGb={data.total_gb} />
      </Card>

      {/* --- Donut Chart + Legend --- */}
      <Card title="Usage Breakdown">
        <div className="flex flex-col sm:flex-row items-center gap-8">
          <DonutChart categories={data.categories} />
          <div className="flex-1 w-full">
            <ChartLegend categories={data.categories} />
          </div>
        </div>
      </Card>

      {/* --- Largest Assets Table --- */}
      <Card title="Largest Assets (Top 10)">
        <DataTable columns={assetColumns} data={assets as unknown as Record<string, unknown>[]} />
      </Card>

      {/* --- Retention Policies --- */}
      <Card title="Retention Policies">
        <div className="space-y-4">
          {policies.map((policy) => (
            <div
              key={policy.category}
              className="flex flex-col sm:flex-row sm:items-center gap-3 border-b border-gray-100 pb-4 last:border-0 last:pb-0"
            >
              <div className="w-24">
                <span className="text-sm font-medium text-gray-900">{policy.category}</span>
              </div>

              <div className="flex-1 flex flex-col sm:flex-row sm:items-center gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Retention Period</label>
                  <select
                    value={policy.retention}
                    onChange={(e) => updateRetention(policy.category, e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  >
                    {RETENTION_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-gray-500 mb-1">Auto-delete above (GB)</label>
                  <input
                    type="number"
                    min={0}
                    step={0.5}
                    placeholder="No limit"
                    value={policy.auto_delete_gb ?? ""}
                    onChange={(e) => updateAutoDeleteGb(policy.category, e.target.value)}
                    className="w-28 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
              </div>
            </div>
          ))}

          <div className="pt-2">
            <Button variant="primary" size="md">
              Save Policies
            </Button>
          </div>
        </div>
      </Card>

      {/* --- Danger Zone --- */}
      <Card title="Danger Zone" className="border-red-200">
        <div className="divide-y divide-gray-100">
          <DangerAction
            label="Delete assets older than 90 days"
            description="Permanently remove all assets that haven't been accessed in the last 90 days."
            confirmText="Delete Old Assets"
            onConfirm={handleDeleteOldAssets}
          />
          <DangerAction
            label="Purge all exports"
            description="Remove all generated export files (CSV, JSON, ZIP archives)."
            confirmText="Purge Exports"
            onConfirm={handlePurgeExports}
          />
          <DangerAction
            label="Clear all annotations"
            description="Delete every annotation across all assets. Model references will be unaffected."
            confirmText="Clear Annotations"
            onConfirm={handleClearAnnotations}
          />
        </div>
      </Card>
    </div>
  );
}
