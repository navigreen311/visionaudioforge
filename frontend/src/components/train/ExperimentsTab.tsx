"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import Modal from "../ui/Modal";
import Button from "../ui/Button";
import Badge from "../ui/Badge";
import LoadingSpinner from "../ui/LoadingSpinner";
import TrainingCharts from "./TrainingCharts";
import EpochTable from "./EpochTable";
import type { Experiment, ExperimentStatus, ExperimentCreatePayload } from "./types";

/* ------------------------------------------------------------------ */
/*  Status helpers                                                    */
/* ------------------------------------------------------------------ */

const STATUS_BADGE: Record<ExperimentStatus, { variant: string; label: string }> = {
  running: { variant: "info", label: "Running" },
  completed: { variant: "success", label: "Completed" },
  failed: { variant: "error", label: "Failed" },
  cancelled: { variant: "neutral", label: "Cancelled" },
};

function StatusCell({ status }: { status: ExperimentStatus }) {
  const cfg = STATUS_BADGE[status] ?? STATUS_BADGE.cancelled;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="relative flex h-2 w-2">
        {status === "running" && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
        )}
        <span
          className={`relative inline-flex h-2 w-2 rounded-full ${
            status === "running"
              ? "bg-green-500"
              : status === "completed"
                ? "bg-green-500"
                : status === "failed"
                  ? "bg-red-500"
                  : "bg-gray-400"
          }`}
        />
      </span>
      <Badge variant={cfg.variant}>{cfg.label}</Badge>
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  New Experiment modal                                              */
/* ------------------------------------------------------------------ */

const MODEL_OPTIONS = [
  "ResNet-50",
  "ResNet-101",
  "EfficientNet-B0",
  "ViT-Base",
  "CLIP-ViT-B/32",
  "Custom",
];

interface NewExperimentModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: ExperimentCreatePayload) => void;
  submitting: boolean;
}

function NewExperimentModal({ open, onClose, onSubmit, submitting }: NewExperimentModalProps) {
  const [name, setName] = useState("");
  const [model, setModel] = useState(MODEL_OPTIONS[0]);
  const [epochs, setEpochs] = useState(50);
  const [lr, setLr] = useState(0.001);
  const [batchSize, setBatchSize] = useState(32);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSubmit({ name: name.trim(), model, epochs, learning_rate: lr, batch_size: batchSize });
  };

  return (
    <Modal
      isOpen={open}
      onClose={onClose}
      title="New Experiment"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button type="submit" form="new-experiment-form" loading={submitting}>
            Create
          </Button>
        </>
      }
    >
      <form id="new-experiment-form" onSubmit={handleSubmit} className="space-y-4">
        {/* Name */}
        <div>
          <label htmlFor="exp-name" className="block text-sm font-medium text-gray-700">
            Name
          </label>
          <input
            id="exp-name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. baseline-resnet50"
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
          />
        </div>

        {/* Model */}
        <div>
          <label htmlFor="exp-model" className="block text-sm font-medium text-gray-700">
            Model
          </label>
          <select
            id="exp-model"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
          >
            {MODEL_OPTIONS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        {/* Epochs */}
        <div>
          <label htmlFor="exp-epochs" className="block text-sm font-medium text-gray-700">
            Epochs
          </label>
          <input
            id="exp-epochs"
            type="number"
            min={1}
            max={1000}
            value={epochs}
            onChange={(e) => setEpochs(Number(e.target.value))}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
          />
        </div>

        {/* Learning Rate */}
        <div>
          <label htmlFor="exp-lr" className="block text-sm font-medium text-gray-700">
            Learning Rate
          </label>
          <input
            id="exp-lr"
            type="number"
            step={0.0001}
            min={0.000001}
            max={1}
            value={lr}
            onChange={(e) => setLr(Number(e.target.value))}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
          />
        </div>

        {/* Batch Size */}
        <div>
          <label htmlFor="exp-bs" className="block text-sm font-medium text-gray-700">
            Batch Size
          </label>
          <input
            id="exp-bs"
            type="number"
            min={1}
            max={512}
            value={batchSize}
            onChange={(e) => setBatchSize(Number(e.target.value))}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
          />
        </div>
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------ */
/*  Detail / inline expand                                            */
/* ------------------------------------------------------------------ */

function ExperimentDetail({ experiment }: { experiment: Experiment }) {
  return (
    <div className="space-y-6 px-2 py-4">
      {/* Config summary */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-500">
        <span>
          <strong>Epochs:</strong> {experiment.config.epochs}
        </span>
        <span>
          <strong>LR:</strong> {experiment.config.learning_rate}
        </span>
        <span>
          <strong>Batch:</strong> {experiment.config.batch_size}
        </span>
      </div>

      {experiment.error_message && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700">
          {experiment.error_message}
        </div>
      )}

      <TrainingCharts
        epochs={experiment.epochs}
        bestEpoch={experiment.best_epoch ?? undefined}
      />

      <EpochTable
        epochs={experiment.epochs}
        bestEpoch={experiment.best_epoch ?? undefined}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main tab                                                          */
/* ------------------------------------------------------------------ */

const POLL_INTERVAL = 5_000;

export default function ExperimentsTab() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* ---------- Fetch ---------- */

  const fetchExperiments = useCallback(async () => {
    try {
      const res = await fetch("/api/experiments");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: { items: Experiment[] } | Experiment[] = await res.json();
      const items = Array.isArray(data) ? data : data.items;
      setExperiments(items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch experiments");
    } finally {
      setLoading(false);
    }
  }, []);

  /* ---------- Polling ---------- */

  useEffect(() => {
    fetchExperiments();
  }, [fetchExperiments]);

  useEffect(() => {
    const hasRunning = experiments.some((e) => e.status === "running");

    if (hasRunning) {
      if (!pollingRef.current) {
        pollingRef.current = setInterval(fetchExperiments, POLL_INTERVAL);
      }
    } else if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [experiments, fetchExperiments]);

  /* ---------- Actions ---------- */

  const handleCreate = useCallback(
    async (payload: ExperimentCreatePayload) => {
      setSubmitting(true);
      try {
        const res = await fetch("/api/experiments", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setModalOpen(false);
        await fetchExperiments();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create experiment");
      } finally {
        setSubmitting(false);
      }
    },
    [fetchExperiments],
  );

  const handleCancel = useCallback(
    async (id: string) => {
      try {
        const res = await fetch(`/api/experiments/${id}/cancel`, { method: "POST" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await fetchExperiments();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to cancel experiment");
      }
    },
    [fetchExperiments],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      if (!window.confirm("Delete this experiment? This cannot be undone.")) return;
      try {
        const res = await fetch(`/api/experiments/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (expandedId === id) setExpandedId(null);
        await fetchExperiments();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to delete experiment");
      }
    },
    [fetchExperiments, expandedId],
  );

  /* ---------- Render ---------- */

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Experiments</h3>
        <Button onClick={() => setModalOpen(true)}>+ New Experiment</Button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 font-medium underline hover:text-red-800"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Table */}
      {experiments.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 px-6 py-12 text-center text-sm text-gray-500">
          No experiments yet. Click &ldquo;New Experiment&rdquo; to get started.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["Name", "Model", "Status", "Best Val Loss", "Best Epoch", "Duration", "Actions"].map(
                  (h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {experiments.map((exp) => (
                <React.Fragment key={exp.id}>
                  <tr
                    className="cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => setExpandedId(expandedId === exp.id ? null : exp.id)}
                  >
                    <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">
                      {exp.name}
                    </td>
                    <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{exp.model}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <StatusCell status={exp.status} />
                    </td>
                    <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                      {exp.best_val_loss !== null ? exp.best_val_loss.toFixed(4) : "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                      {exp.best_epoch !== null ? exp.best_epoch : "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                      {exp.duration ?? "-"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setExpandedId(expandedId === exp.id ? null : exp.id)
                          }
                        >
                          {expandedId === exp.id ? "Hide" : "View"}
                        </Button>
                        {exp.status === "running" && (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleCancel(exp.id)}
                          >
                            Cancel
                          </Button>
                        )}
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => handleDelete(exp.id)}
                        >
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                  {expandedId === exp.id && (
                    <tr>
                      <td colSpan={7} className="bg-gray-50 px-4 py-0">
                        <ExperimentDetail experiment={exp} />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* New experiment modal */}
      <NewExperimentModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleCreate}
        submitting={submitting}
      />
    </div>
  );
}
