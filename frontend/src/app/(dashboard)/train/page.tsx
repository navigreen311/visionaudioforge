"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import axios from "axios";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface DatasetItem {
  id: string;
  name: string;
  modality: string;
  sample_count: number;
  size_bytes: number;
  version: number;
  stats: DatasetStats | null;
  created_at: string;
}

interface DatasetStats {
  total_samples: number;
  modality_breakdown: Record<string, number>;
  total_size_bytes: number;
  label_distribution: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const MODALITY_COLORS: Record<string, string> = {
  image: "bg-blue-100 text-blue-800",
  video: "bg-purple-100 text-purple-800",
  audio: "bg-green-100 text-green-800",
  multimodal: "bg-orange-100 text-orange-800",
};

function humanSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(1)} ${units[i]}`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ModalityBadge({ modality }: { modality: string }) {
  const cls = MODALITY_COLORS[modality] || "bg-gray-100 text-gray-800";
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {modality}
    </span>
  );
}

function CreateDatasetModal({
  open,
  onClose,
  onCreated,
  workspaceId,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  workspaceId: string;
}) {
  const [name, setName] = useState("");
  const [modality, setModality] = useState("image");
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const handleCreate = async () => {
    setLoading(true);
    try {
      await axios.post("/api/datasets", { name, modality, workspace_id: workspaceId });
      onCreated();
      onClose();
      setName("");
    } catch (e) {
      console.error("Create failed", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">Create Dataset</h3>
        <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
        <input
          className="w-full border rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="my-dataset"
        />
        <label className="block text-sm font-medium text-gray-700 mb-1">Modality</label>
        <div className="flex gap-2 mb-6">
          {["image", "video", "audio", "multimodal"].map((m) => (
            <button
              key={m}
              onClick={() => setModality(m)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition ${
                modality === m ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!name || loading}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Creating..." : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Upload zone
// ---------------------------------------------------------------------------
function UploadZone({ datasetId, onDone }: { datasetId: string; onDone: () => void }) {
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = async (fileList: FileList) => {
    const formData = new FormData();
    Array.from(fileList).forEach((f) => formData.append("files", f));
    setProgress(0);
    try {
      await axios.post(`/api/datasets/${datasetId}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 100));
        },
      });
      onDone();
    } catch (e) {
      console.error("Upload failed", e);
    } finally {
      setProgress(null);
    }
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (e.dataTransfer.files.length) upload(e.dataTransfer.files);
    },
    [datasetId],
  );

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
        dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400"
      }`}
    >
      <input ref={inputRef} type="file" multiple className="hidden" onChange={(e) => e.target.files && upload(e.target.files)} />
      <p className="text-gray-500 text-sm">
        {progress !== null ? (
          <span className="font-medium text-blue-600">Uploading... {progress}%</span>
        ) : (
          "Drag & drop files here, or click to browse"
        )}
      </p>
      {progress !== null && (
        <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
          <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${progress}%` }} />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stats panel (simple pie via CSS conic-gradient)
// ---------------------------------------------------------------------------
function StatsPanel({ stats }: { stats: DatasetStats | null }) {
  if (!stats) return <p className="text-sm text-gray-400">No stats computed yet.</p>;

  const labels = Object.entries(stats.label_distribution);
  const total = labels.reduce((s, [, v]) => s + v, 0);

  // Build conic-gradient segments
  const colors = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#6366f1", "#ec4899"];
  let cumPct = 0;
  const segments = labels.map(([, count], i) => {
    const pct = total ? (count / total) * 100 : 0;
    const seg = `${colors[i % colors.length]} ${cumPct}% ${cumPct + pct}%`;
    cumPct += pct;
    return seg;
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-6">
        {total > 0 && (
          <div
            className="w-24 h-24 rounded-full flex-shrink-0"
            style={{ background: `conic-gradient(${segments.join(", ")})` }}
          />
        )}
        <div className="text-sm space-y-1">
          <p><span className="font-medium">{stats.total_samples}</span> samples</p>
          <p><span className="font-medium">{humanSize(stats.total_size_bytes)}</span> total</p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {labels.map(([label, count], i) => (
          <span key={label} className="flex items-center gap-1 text-xs">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: colors[i % colors.length] }} />
            {label}: {count}
          </span>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Split controls
// ---------------------------------------------------------------------------
function SplitControls({ datasetId, onDone }: { datasetId: string; onDone: () => void }) {
  const [train, setTrain] = useState(70);
  const [val, setVal] = useState(15);
  const test = 100 - train - val;
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ train: number; val: number; test: number } | null>(null);

  const handleSplit = async () => {
    setLoading(true);
    try {
      const resp = await axios.post(`/api/datasets/${datasetId}/split`, {
        train: train / 100,
        val: val / 100,
        test: test / 100,
        stratified: true,
      });
      setResult(resp.data);
      onDone();
    } catch (e) {
      console.error("Split failed", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <label className="flex justify-between text-sm"><span>Train</span><span>{train}%</span></label>
        <input type="range" min={0} max={100} value={train} onChange={(e) => { const v = +e.target.value; setTrain(v); if (v + val > 100) setVal(100 - v); }} className="w-full" />
        <label className="flex justify-between text-sm"><span>Validation</span><span>{val}%</span></label>
        <input type="range" min={0} max={100 - train} value={val} onChange={(e) => setVal(+e.target.value)} className="w-full" />
        <label className="flex justify-between text-sm text-gray-500"><span>Test</span><span>{test}%</span></label>
      </div>
      <button onClick={handleSplit} disabled={loading || test < 0} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
        {loading ? "Splitting..." : "Split Dataset"}
      </button>
      {result && (
        <p className="text-xs text-green-600">
          Split complete: {result.train} train / {result.val} val / {result.test} test
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dataset detail view
// ---------------------------------------------------------------------------
function DatasetDetail({ dataset, onBack }: { dataset: DatasetItem; onBack: () => void }) {
  const [stats, setStats] = useState<DatasetStats | null>(dataset.stats);

  const recomputeStats = async () => {
    try {
      const resp = await axios.post(`/api/datasets/${dataset.id}/stats`);
      setStats(resp.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleExport = () => {
    window.open(`/api/datasets/${dataset.id}/export?format=json`, "_blank");
  };

  return (
    <div className="space-y-6">
      <button onClick={onBack} className="text-sm text-blue-600 hover:underline">&larr; Back to datasets</button>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">{dataset.name}</h2>
          <div className="flex items-center gap-2 mt-1">
            <ModalityBadge modality={dataset.modality} />
            <span className="text-sm text-gray-500">{dataset.sample_count} samples</span>
            <span className="text-sm text-gray-500">{humanSize(dataset.size_bytes)}</span>
          </div>
        </div>
        <button onClick={handleExport} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Export JSON</button>
      </div>

      {/* Upload zone */}
      <section>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Upload Samples</h3>
        <UploadZone datasetId={dataset.id} onDone={recomputeStats} />
      </section>

      {/* Sample preview grid (placeholder thumbnails) */}
      <section>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Sample Preview</h3>
        <div className="grid grid-cols-5 sm:grid-cols-10 gap-2">
          {Array.from({ length: Math.min(dataset.sample_count, 20) }).map((_, i) => (
            <div key={i} className="aspect-square bg-gray-100 rounded-lg flex items-center justify-center text-xs text-gray-400">
              {i + 1}
            </div>
          ))}
          {dataset.sample_count === 0 && <p className="col-span-full text-sm text-gray-400">No samples yet.</p>}
        </div>
      </section>

      {/* Stats */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-gray-700">Statistics</h3>
          <button onClick={recomputeStats} className="text-xs text-blue-600 hover:underline">Recompute</button>
        </div>
        <StatsPanel stats={stats} />
      </section>

      {/* Split */}
      <section>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Train / Val / Test Split</h3>
        <SplitControls datasetId={dataset.id} onDone={recomputeStats} />
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function TrainPage() {
  const [tab, setTab] = useState<"models" | "experiments" | "datasets">("models");
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<DatasetItem | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(false);

  // ASSUMPTION: workspace_id comes from context/auth in real app. Placeholder for now.
  const workspaceId = "00000000-0000-0000-0000-000000000001";

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await axios.get(`/api/datasets?workspace_id=${workspaceId}`);
      setDatasets(resp.data.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    if (tab === "datasets") fetchDatasets();
  }, [tab]);

  const TAB_LABELS: Record<string, string> = {
    models: "Models",
    experiments: "Experiments",
    datasets: "Datasets",
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Tab bar */}
      <div className="flex gap-4 border-b mb-6">
        {(["models", "experiments", "datasets"] as const).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setSelectedDataset(null); }}
            className={`pb-2 px-1 text-sm font-medium border-b-2 transition ${
              tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {/* Models tab */}
      {tab === "models" && (
        <div className="flex items-center justify-center min-h-[40vh]">
          <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full text-center border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Models</h2>
            <p className="text-gray-500">Model registry, versioning, and lifecycle management.</p>
            <div className="mt-4 inline-block px-3 py-1 bg-yellow-50 text-yellow-700 text-sm rounded-full border border-yellow-200">
              Not Implemented
            </div>
          </div>
        </div>
      )}

      {/* Experiments tab */}
      {tab === "experiments" && (
        <div className="flex items-center justify-center min-h-[40vh]">
          <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full text-center border border-gray-100">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Experiments</h2>
            <p className="text-gray-500">Experiment tracking, training curves, and hyperparameter comparison.</p>
            <div className="mt-4 inline-block px-3 py-1 bg-yellow-50 text-yellow-700 text-sm rounded-full border border-yellow-200">
              Not Implemented
            </div>
          </div>
        </div>
      )}

      {/* Datasets tab */}
      {tab === "datasets" && !selectedDataset && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Datasets</h2>
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
            >
              Create Dataset
            </button>
          </div>
          {loading ? (
            <p className="text-sm text-gray-400">Loading...</p>
          ) : datasets.length === 0 ? (
            <p className="text-sm text-gray-400">No datasets yet. Create one to get started.</p>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                  <tr>
                    <th className="text-left px-4 py-3">Name</th>
                    <th className="text-left px-4 py-3">Modality</th>
                    <th className="text-right px-4 py-3">Samples</th>
                    <th className="text-right px-4 py-3">Size</th>
                    <th className="text-right px-4 py-3">Version</th>
                    <th className="text-left px-4 py-3">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((ds) => (
                    <tr
                      key={ds.id}
                      onClick={() => setSelectedDataset(ds)}
                      className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                    >
                      <td className="px-4 py-3 font-medium">{ds.name}</td>
                      <td className="px-4 py-3"><ModalityBadge modality={ds.modality} /></td>
                      <td className="px-4 py-3 text-right">{ds.sample_count}</td>
                      <td className="px-4 py-3 text-right">{humanSize(ds.size_bytes)}</td>
                      <td className="px-4 py-3 text-right">v{ds.version}</td>
                      <td className="px-4 py-3 text-gray-500">{new Date(ds.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <CreateDatasetModal
            open={showCreate}
            onClose={() => setShowCreate(false)}
            onCreated={fetchDatasets}
            workspaceId={workspaceId}
          />
        </div>
      )}

      {/* Dataset detail */}
      {tab === "datasets" && selectedDataset && (
        <DatasetDetail dataset={selectedDataset} onBack={() => { setSelectedDataset(null); fetchDatasets(); }} />
      )}
    </div>
  );
}
