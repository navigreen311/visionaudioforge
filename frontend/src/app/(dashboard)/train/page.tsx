"use client";

import { useState, useEffect, useMemo } from "react";
import api from "@/lib/api";

// ---------- Types ----------

interface EpochData {
  epoch_number: number;
  train_loss: number | null;
  val_loss: number | null;
  accuracy: number | null;
  val_accuracy: number | null;
}

interface Experiment {
  id: string;
  name: string;
  status: string;
  config: Record<string, unknown>;
  workspace_id: string;
  model_id: string | null;
  best_epoch: number | null;
  error_message: string | null;
  epochs: EpochData[];
}

// ---------- Status Badge ----------

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    created: "bg-gray-100 text-gray-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || "bg-gray-100 text-gray-600"}`}
    >
      {status}
    </span>
  );
}

// ---------- Simple SVG Line Chart ----------

interface ChartLine {
  label: string;
  color: string;
  data: { x: number; y: number }[];
}

function LineChart({
  lines,
  width = 560,
  height = 280,
}: {
  lines: ChartLine[];
  width?: number;
  height?: number;
}) {
  const padding = { top: 20, right: 80, bottom: 40, left: 60 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const allPoints = lines.flatMap((l) => l.data);
  if (allPoints.length === 0) return <div className="text-gray-400 text-sm">No data</div>;

  const xMin = Math.min(...allPoints.map((p) => p.x));
  const xMax = Math.max(...allPoints.map((p) => p.x));
  const yMin = Math.min(...allPoints.map((p) => p.y));
  const yMax = Math.max(...allPoints.map((p) => p.y));
  const yRange = yMax - yMin || 1;
  const xRange = xMax - xMin || 1;

  const toX = (v: number) => padding.left + ((v - xMin) / xRange) * chartW;
  const toY = (v: number) => padding.top + chartH - ((v - yMin) / yRange) * chartH;

  return (
    <svg width={width} height={height} className="bg-white rounded border border-gray-200">
      {/* Y axis labels */}
      {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
        const val = yMin + frac * yRange;
        const y = toY(val);
        return (
          <g key={frac}>
            <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#e5e7eb" />
            <text x={padding.left - 8} y={y + 4} textAnchor="end" className="text-[10px] fill-gray-500">
              {val.toFixed(3)}
            </text>
          </g>
        );
      })}
      {/* X axis label */}
      <text x={padding.left + chartW / 2} y={height - 6} textAnchor="middle" className="text-[11px] fill-gray-500">
        Epoch
      </text>
      {/* Lines */}
      {lines.map((line) => {
        if (line.data.length < 2) return null;
        const d = line.data.map((p, i) => `${i === 0 ? "M" : "L"}${toX(p.x)},${toY(p.y)}`).join(" ");
        return <path key={line.label} d={d} fill="none" stroke={line.color} strokeWidth={2} />;
      })}
      {/* Legend */}
      {lines.map((line, i) => (
        <g key={line.label}>
          <line
            x1={width - padding.right + 8}
            y1={padding.top + i * 18 + 4}
            x2={width - padding.right + 22}
            y2={padding.top + i * 18 + 4}
            stroke={line.color}
            strokeWidth={2}
          />
          <text
            x={width - padding.right + 26}
            y={padding.top + i * 18 + 8}
            className="text-[10px] fill-gray-700"
          >
            {line.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

// ---------- Training Curves ----------

function TrainingCurves({ experiment }: { experiment: Experiment }) {
  const lines: ChartLine[] = useMemo(() => {
    const epochs = experiment.epochs || [];
    return [
      {
        label: "loss",
        color: "#ef4444",
        data: epochs.filter((e) => e.train_loss != null).map((e) => ({ x: e.epoch_number, y: e.train_loss! })),
      },
      {
        label: "val_loss",
        color: "#3b82f6",
        data: epochs.filter((e) => e.val_loss != null).map((e) => ({ x: e.epoch_number, y: e.val_loss! })),
      },
      {
        label: "accuracy",
        color: "#22c55e",
        data: epochs.filter((e) => e.accuracy != null).map((e) => ({ x: e.epoch_number, y: e.accuracy! })),
      },
    ];
  }, [experiment]);

  return <LineChart lines={lines} />;
}

// ---------- Compare Chart ----------

function CompareChart({ experiments }: { experiments: Experiment[] }) {
  const colors = ["#ef4444", "#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6"];
  const lines: ChartLine[] = experiments.flatMap((exp, i) => [
    {
      label: `${exp.name} loss`,
      color: colors[i % colors.length],
      data: (exp.epochs || []).filter((e) => e.val_loss != null).map((e) => ({ x: e.epoch_number, y: e.val_loss! })),
    },
  ]);
  return <LineChart lines={lines} width={700} height={320} />;
}

// ---------- Start Training Modal ----------

function StartTrainingModal({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (data: Record<string, unknown>) => void;
}) {
  const [form, setForm] = useState({
    experiment_name: "finetune-experiment",
    backbone: "resnet18",
    num_epochs: 10,
    learning_rate: 0.001,
    batch_size: 32,
    freeze_layers: true,
    gradient_clip_value: "",
    early_stopping_patience: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      experiment_name: form.experiment_name,
      backbone: form.backbone,
      num_epochs: form.num_epochs,
      learning_rate: form.learning_rate,
      batch_size: form.batch_size,
      freeze_layers: form.freeze_layers,
      gradient_clip_value: form.gradient_clip_value ? parseFloat(form.gradient_clip_value) : null,
      early_stopping_patience: form.early_stopping_patience ? parseInt(form.early_stopping_patience) : null,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">Start Training</h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Experiment Name</label>
            <input
              type="text"
              value={form.experiment_name}
              onChange={(e) => setForm({ ...form, experiment_name: e.target.value })}
              className="w-full border rounded px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Backbone</label>
            <select
              value={form.backbone}
              onChange={(e) => setForm({ ...form, backbone: e.target.value })}
              className="w-full border rounded px-3 py-1.5 text-sm"
            >
              <option value="resnet18">ResNet-18</option>
              <option value="resnet50">ResNet-50</option>
              <option value="clip">CLIP</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Epochs</label>
              <input
                type="number"
                value={form.num_epochs}
                onChange={(e) => setForm({ ...form, num_epochs: parseInt(e.target.value) || 1 })}
                className="w-full border rounded px-3 py-1.5 text-sm"
                min={1}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Learning Rate</label>
              <input
                type="number"
                step="0.0001"
                value={form.learning_rate}
                onChange={(e) => setForm({ ...form, learning_rate: parseFloat(e.target.value) || 0.001 })}
                className="w-full border rounded px-3 py-1.5 text-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Batch Size</label>
              <input
                type="number"
                value={form.batch_size}
                onChange={(e) => setForm({ ...form, batch_size: parseInt(e.target.value) || 1 })}
                className="w-full border rounded px-3 py-1.5 text-sm"
                min={1}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Gradient Clip</label>
              <input
                type="text"
                placeholder="e.g. 1.0"
                value={form.gradient_clip_value}
                onChange={(e) => setForm({ ...form, gradient_clip_value: e.target.value })}
                className="w-full border rounded px-3 py-1.5 text-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Early Stop Patience</label>
              <input
                type="text"
                placeholder="e.g. 5"
                value={form.early_stopping_patience}
                onChange={(e) => setForm({ ...form, early_stopping_patience: e.target.value })}
                className="w-full border rounded px-3 py-1.5 text-sm"
              />
            </div>
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.freeze_layers}
                  onChange={(e) => setForm({ ...form, freeze_layers: e.target.checked })}
                />
                Freeze Layers
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Start
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------- Main Page ----------

export default function TrainPage() {
  const [tab, setTab] = useState<"experiments" | "compare">("experiments");
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selected, setSelected] = useState<Experiment | null>(null);
  const [compareIds, setCompareIds] = useState<Set<string>>(new Set());
  const [compareData, setCompareData] = useState<Experiment[] | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // For demo purposes, use a fixed workspace_id
  const workspaceId = "00000000-0000-0000-0000-000000000001";

  const fetchExperiments = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/api/experiments?workspace_id=${workspaceId}`);
      setExperiments(res.data.items || []);
    } catch (err: unknown) {
      setError("Failed to load experiments. Backend may be unavailable.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExperiments();
  }, []);

  const handleSelectExperiment = async (exp: Experiment) => {
    try {
      const res = await api.get(`/api/experiments/${exp.id}`);
      setSelected(res.data);
    } catch {
      setSelected(exp);
    }
  };

  const toggleCompare = (id: string) => {
    setCompareIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCompare = async () => {
    if (compareIds.size < 2) return;
    try {
      const res = await api.post("/api/experiments/compare", {
        experiment_ids: Array.from(compareIds),
      });
      setCompareData(res.data);
      setTab("compare");
    } catch {
      setError("Failed to compare experiments.");
    }
  };

  const handleStartTraining = async (data: Record<string, unknown>) => {
    try {
      await api.post("/api/transfer/start", {
        ...data,
        workspace_id: workspaceId,
        dataset_path: "",
      });
      setShowModal(false);
      fetchExperiments();
    } catch {
      setError("Failed to start training.");
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Training & Experiments</h1>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          Start Training
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b">
        <button
          onClick={() => { setTab("experiments"); setCompareData(null); }}
          className={`px-4 py-2 text-sm font-medium border-b-2 ${tab === "experiments" ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          Experiments
        </button>
        <button
          onClick={() => setTab("compare")}
          className={`px-4 py-2 text-sm font-medium border-b-2 ${tab === "compare" ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          Compare
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded-lg border border-red-200">
          {error}
        </div>
      )}

      {/* Experiments Tab */}
      {tab === "experiments" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: experiment list */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-gray-700">Experiment List</h2>
              {compareIds.size >= 2 && (
                <button
                  onClick={handleCompare}
                  className="px-3 py-1 text-xs bg-purple-600 text-white rounded hover:bg-purple-700"
                >
                  Compare ({compareIds.size})
                </button>
              )}
            </div>

            {loading ? (
              <div className="text-gray-400 text-sm py-8 text-center">Loading...</div>
            ) : experiments.length === 0 ? (
              <div className="text-gray-400 text-sm py-8 text-center">
                No experiments yet. Click &quot;Start Training&quot; to begin.
              </div>
            ) : (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-600">
                    <tr>
                      <th className="text-left px-3 py-2 w-8"></th>
                      <th className="text-left px-3 py-2">Name</th>
                      <th className="text-left px-3 py-2">Status</th>
                      <th className="text-left px-3 py-2">Best</th>
                      <th className="text-left px-3 py-2">Epochs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {experiments.map((exp) => (
                      <tr
                        key={exp.id}
                        className={`border-t hover:bg-gray-50 cursor-pointer ${selected?.id === exp.id ? "bg-blue-50" : ""}`}
                        onClick={() => handleSelectExperiment(exp)}
                      >
                        <td className="px-3 py-2">
                          <input
                            type="checkbox"
                            checked={compareIds.has(exp.id)}
                            onClick={(e) => e.stopPropagation()}
                            onChange={() => toggleCompare(exp.id)}
                          />
                        </td>
                        <td className="px-3 py-2 font-medium text-gray-900">{exp.name}</td>
                        <td className="px-3 py-2">
                          <StatusBadge status={exp.status} />
                        </td>
                        <td className="px-3 py-2 text-gray-600">
                          {exp.best_epoch != null ? `Epoch ${exp.best_epoch}` : "-"}
                        </td>
                        <td className="px-3 py-2 text-gray-600">
                          {exp.epochs?.length || 0}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Right: detail view */}
          <div>
            {selected ? (
              <div className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-gray-900">{selected.name}</h3>
                  <StatusBadge status={selected.status} />
                </div>
                {selected.config && (
                  <div className="text-xs text-gray-500 mb-3">
                    Config: {JSON.stringify(selected.config)}
                  </div>
                )}
                {selected.best_epoch != null && (
                  <div className="text-sm text-green-700 mb-3">
                    Best epoch: {selected.best_epoch}
                  </div>
                )}
                {selected.error_message && (
                  <div className="text-sm text-red-600 mb-3">
                    Error: {selected.error_message}
                  </div>
                )}
                <h4 className="text-sm font-medium text-gray-700 mb-2">Training Curves</h4>
                <TrainingCurves experiment={selected} />
              </div>
            ) : (
              <div className="text-gray-400 text-sm py-8 text-center border rounded-lg">
                Select an experiment to view details and training curves.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Compare Tab */}
      {tab === "compare" && (
        <div>
          {compareData && compareData.length >= 2 ? (
            <div>
              <h2 className="text-sm font-semibold text-gray-700 mb-3">
                Comparing {compareData.length} Experiments
              </h2>
              <div className="border rounded-lg p-4 mb-4">
                <CompareChart experiments={compareData} />
              </div>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-600">
                    <tr>
                      <th className="text-left px-3 py-2">Name</th>
                      <th className="text-left px-3 py-2">Status</th>
                      <th className="text-left px-3 py-2">Total Epochs</th>
                      <th className="text-left px-3 py-2">Best Val Loss</th>
                      <th className="text-left px-3 py-2">Best Accuracy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compareData.map((exp: Record<string, unknown>) => (
                      <tr key={exp.id as string} className="border-t">
                        <td className="px-3 py-2 font-medium">{exp.name as string}</td>
                        <td className="px-3 py-2">
                          <StatusBadge status={exp.status as string} />
                        </td>
                        <td className="px-3 py-2">{exp.total_epochs as number}</td>
                        <td className="px-3 py-2">
                          {exp.best_val_loss != null ? (exp.best_val_loss as number).toFixed(4) : "-"}
                        </td>
                        <td className="px-3 py-2">
                          {exp.best_accuracy != null ? (exp.best_accuracy as number).toFixed(4) : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="text-gray-400 text-sm py-8 text-center">
              Select 2 or more experiments from the Experiments tab and click Compare.
            </div>
          )}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <StartTrainingModal onClose={() => setShowModal(false)} onSubmit={handleStartTraining} />
      )}
    </div>
  );
}
