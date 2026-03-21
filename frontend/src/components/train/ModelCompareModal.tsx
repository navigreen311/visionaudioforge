'use client';

import React, { useState, useMemo } from 'react';
import { createPortal } from 'react-dom';
import type { ModelRecord } from '@/lib/api';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import { useEffect } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ModelCompareModalProps {
  modelA: ModelRecord;
  modelB?: ModelRecord;
  models: ModelRecord[];
  isOpen: boolean;
  onClose: () => void;
  onPromote?: (modelId: string) => void;
}

interface MetricDiff {
  key: string;
  valueA: number | string | null;
  valueB: number | string | null;
  numericDiff: number | null;
  /** positive = B is higher, negative = B is lower */
  direction: 'up' | 'down' | 'same' | 'na';
}

// ---------------------------------------------------------------------------
// Higher-is-better heuristic
// ---------------------------------------------------------------------------

/** Metrics where higher values are generally better. */
const HIGHER_IS_BETTER = new Set([
  'accuracy',
  'precision',
  'recall',
  'f1',
  'f1_score',
  'auc',
  'auc_roc',
  'map',
  'mAP',
  'iou',
  'dice',
  'top1_accuracy',
  'top5_accuracy',
  'bleu',
  'rouge',
]);

/** Metrics where lower values are generally better. */
const LOWER_IS_BETTER = new Set([
  'loss',
  'val_loss',
  'train_loss',
  'error',
  'error_rate',
  'mae',
  'mse',
  'rmse',
  'cer',
  'wer',
  'perplexity',
  'fid',
]);

function isImprovement(key: string, diff: number): boolean {
  const k = key.toLowerCase();
  if (HIGHER_IS_BETTER.has(k)) return diff > 0;
  if (LOWER_IS_BETTER.has(k)) return diff < 0;
  // Default: treat higher as better
  return diff > 0;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMetricValue(v: number | string | null): string {
  if (v === null || v === undefined) return '--';
  if (typeof v === 'number') {
    return Number.isInteger(v) ? v.toString() : v.toFixed(4);
  }
  return v;
}

function formatDiff(diff: number): string {
  const sign = diff >= 0 ? '+' : '';
  return `${sign}${diff.toFixed(4)}`;
}

function computeDiffs(
  metricsA: Record<string, number | string> | null,
  metricsB: Record<string, number | string> | null,
): MetricDiff[] {
  const keysA = new Set(metricsA ? Object.keys(metricsA) : []);
  const keysB = new Set(metricsB ? Object.keys(metricsB) : []);
  const allKeys = Array.from(new Set([...keysA, ...keysB])).sort();

  return allKeys.map((key) => {
    const rawA = metricsA?.[key] ?? null;
    const rawB = metricsB?.[key] ?? null;
    const numA = typeof rawA === 'number' ? rawA : null;
    const numB = typeof rawB === 'number' ? rawB : null;

    let numericDiff: number | null = null;
    let direction: MetricDiff['direction'] = 'na';

    if (numA !== null && numB !== null) {
      numericDiff = numB - numA;
      if (numericDiff === 0) direction = 'same';
      else direction = numericDiff > 0 ? 'up' : 'down';
    }

    return { key, valueA: rawA, valueB: rawB, numericDiff, direction };
  });
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ModelHeader({ model, label }: { model: ModelRecord; label: string }) {
  return (
    <div className="space-y-1">
      <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
        {label}
      </span>
      <h3 className="text-sm font-semibold text-gray-900 truncate" title={model.name}>
        {model.name}
      </h3>
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span>v{model.version}</span>
        <Badge variant={model.status === 'production' ? 'success' : 'neutral'}>
          {model.status}
        </Badge>
      </div>
      {model.backbone && (
        <p className="text-xs text-gray-400">Backbone: {model.backbone}</p>
      )}
    </div>
  );
}

function DiffArrow({
  diff,
  metricKey,
}: {
  diff: MetricDiff;
  metricKey: string;
}) {
  if (diff.direction === 'na' || diff.direction === 'same') {
    return <span className="text-gray-400 text-xs">=</span>;
  }

  const improved =
    diff.numericDiff !== null && isImprovement(metricKey, diff.numericDiff);

  const colorClass = improved ? 'text-green-600' : 'text-red-600';
  const arrow = diff.direction === 'up' ? '\u2191' : '\u2193';

  return (
    <span className={`font-semibold text-xs ${colorClass}`} title={diff.numericDiff !== null ? formatDiff(diff.numericDiff) : ''}>
      {arrow} {diff.numericDiff !== null ? formatDiff(diff.numericDiff) : ''}
    </span>
  );
}

function ModelSelector({
  models,
  selectedId,
  excludeId,
  onChange,
}: {
  models: ModelRecord[];
  selectedId: string | undefined;
  excludeId: string;
  onChange: (id: string) => void;
}) {
  const options = models.filter((m) => m.id !== excludeId);

  return (
    <select
      value={selectedId ?? ''}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
    >
      <option value="" disabled>
        Select a model to compare...
      </option>
      {options.map((m) => (
        <option key={m.id} value={m.id}>
          {m.name} v{m.version} ({m.status})
        </option>
      ))}
    </select>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ModelCompareModal({
  modelA,
  modelB: initialModelB,
  models,
  isOpen,
  onClose,
  onPromote,
}: ModelCompareModalProps) {
  const [selectedModelBId, setSelectedModelBId] = useState<string | undefined>(
    initialModelB?.id,
  );

  // Sync when prop changes
  useEffect(() => {
    setSelectedModelBId(initialModelB?.id);
  }, [initialModelB?.id]);

  // Escape to close
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleEsc);
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleEsc);
    };
  }, [isOpen, onClose]);

  const resolvedModelB = useMemo(
    () => models.find((m) => m.id === selectedModelBId),
    [models, selectedModelBId],
  );

  const diffs = useMemo(
    () => computeDiffs(modelA.metrics, resolvedModelB?.metrics ?? null),
    [modelA.metrics, resolvedModelB?.metrics],
  );

  const bOutperforms = useMemo(() => {
    if (!resolvedModelB) return false;
    let improvements = 0;
    let regressions = 0;
    for (const d of diffs) {
      if (d.numericDiff !== null && d.direction !== 'same') {
        if (isImprovement(d.key, d.numericDiff)) improvements++;
        else regressions++;
      }
    }
    return improvements > regressions && improvements > 0;
  }, [diffs, resolvedModelB]);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative z-10 w-full max-w-4xl max-h-[90vh] rounded-lg bg-white shadow-xl mx-4 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 shrink-0">
          <h2 className="text-lg font-semibold text-gray-900">
            Compare Models
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Two-column model headers */}
          <div className="grid grid-cols-2 gap-6">
            <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
              <ModelHeader model={modelA} label="Model A (Baseline)" />
            </div>
            <div className="p-4 rounded-lg bg-gray-50 border border-gray-200 space-y-3">
              {resolvedModelB ? (
                <ModelHeader model={resolvedModelB} label="Model B (Candidate)" />
              ) : (
                <div className="space-y-1">
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
                    Model B (Candidate)
                  </span>
                  <p className="text-sm text-gray-400">
                    Select a model below
                  </p>
                </div>
              )}
              <ModelSelector
                models={models}
                selectedId={selectedModelBId}
                excludeId={modelA.id}
                onChange={setSelectedModelBId}
              />
            </div>
          </div>

          {/* Metrics comparison table */}
          {diffs.length > 0 ? (
            <div className="overflow-x-auto rounded border border-gray-200">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left">
                    <th className="px-4 py-2 font-medium text-gray-600">
                      Metric
                    </th>
                    <th className="px-4 py-2 font-medium text-gray-600 text-right">
                      Model A
                    </th>
                    <th className="px-4 py-2 font-medium text-gray-600 text-center">
                      Diff
                    </th>
                    <th className="px-4 py-2 font-medium text-gray-600 text-right">
                      Model B
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {diffs.map((d) => (
                    <tr
                      key={d.key}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-4 py-2 text-gray-700 font-mono text-xs">
                        {d.key}
                      </td>
                      <td className="px-4 py-2 text-gray-900 text-right font-mono text-xs">
                        {formatMetricValue(d.valueA)}
                      </td>
                      <td className="px-4 py-2 text-center">
                        <DiffArrow diff={d} metricKey={d.key} />
                      </td>
                      <td className="px-4 py-2 text-gray-900 text-right font-mono text-xs">
                        {formatMetricValue(d.valueB)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">
              {resolvedModelB
                ? 'No metrics available for comparison.'
                : 'Select Model B to compare metrics.'}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-6 py-3 bg-gray-50 rounded-b-lg flex items-center justify-between shrink-0">
          <div className="text-xs text-gray-500">
            {bOutperforms && resolvedModelB && (
              <span className="text-green-600 font-medium">
                Model B outperforms Model A on the majority of metrics
              </span>
            )}
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
            {bOutperforms && resolvedModelB && onPromote && (
              <Button
                variant="primary"
                onClick={() => onPromote(resolvedModelB.id)}
              >
                Promote Model B
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
