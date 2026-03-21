'use client';

import React, { useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import type { ModelRecord } from '@/lib/api';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ModelAction = 'promote' | 'shadow' | 'archive' | 'compare';

interface ModelDetailPanelProps {
  model: ModelRecord;
  isOpen: boolean;
  onClose: () => void;
  onAction: (action: ModelAction, modelId: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_BADGE_VARIANT: Record<string, string> = {
  production: 'success',
  shadow: 'warning',
  archived: 'neutral',
  staging: 'info',
  draft: 'neutral',
};

function statusVariant(status: string): string {
  return STATUS_BADGE_VARIANT[status.toLowerCase()] ?? 'neutral';
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatMetricValue(v: number | string): string {
  if (typeof v === 'number') {
    return Number.isInteger(v) ? v.toString() : v.toFixed(4);
  }
  return v;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MetadataSection({ model }: { model: ModelRecord }) {
  return (
    <section className="space-y-3">
      <h3 className="text-xs font-medium uppercase tracking-wider text-gray-500">
        Metadata
      </h3>
      <dl className="space-y-2 text-sm">
        {([
          ['Name', model.name],
          ['Version', model.version],
          ['Backbone', model.backbone ?? 'N/A'],
          ['Status', null],
          ['Workspace', model.workspace_id],
          ['Created', formatDate(model.created_at)],
          ['Updated', formatDate(model.updated_at)],
        ] as const).map(([label, value]) => (
          <div key={label} className="flex justify-between gap-2">
            <dt className="text-gray-500 shrink-0">{label}</dt>
            {label === 'Status' ? (
              <dd>
                <Badge variant={statusVariant(model.status)}>
                  {model.status}
                </Badge>
              </dd>
            ) : (
              <dd
                className="text-gray-900 text-right truncate max-w-[220px]"
                title={String(value)}
              >
                {value}
              </dd>
            )}
          </div>
        ))}
      </dl>
    </section>
  );
}

function MetricsTable({ metrics }: { metrics: Record<string, number | string> | null }) {
  if (!metrics || Object.keys(metrics).length === 0) {
    return (
      <section className="space-y-3">
        <h3 className="text-xs font-medium uppercase tracking-wider text-gray-500">
          Metrics
        </h3>
        <p className="text-sm text-gray-400">No metrics recorded.</p>
      </section>
    );
  }

  const entries = Object.entries(metrics).sort(([a], [b]) => a.localeCompare(b));

  return (
    <section className="space-y-3">
      <h3 className="text-xs font-medium uppercase tracking-wider text-gray-500">
        Metrics
      </h3>
      <div className="overflow-x-auto rounded border border-gray-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left">
              <th className="px-3 py-2 font-medium text-gray-600">Metric</th>
              <th className="px-3 py-2 font-medium text-gray-600 text-right">Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {entries.map(([key, val]) => (
              <tr key={key} className="hover:bg-gray-50 transition-colors">
                <td className="px-3 py-2 text-gray-700 font-mono text-xs">{key}</td>
                <td className="px-3 py-2 text-gray-900 text-right font-mono text-xs">
                  {formatMetricValue(val)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function VersionTimeline({ model }: { model: ModelRecord }) {
  // ASSUMPTION: The API currently returns a single model record without
  // version history. We render the current version as a single timeline
  // entry. When the API returns a versions array, extend this component.
  return (
    <section className="space-y-3">
      <h3 className="text-xs font-medium uppercase tracking-wider text-gray-500">
        Version History
      </h3>
      <ol className="relative border-l-2 border-gray-200 ml-2 space-y-4">
        <li className="ml-4">
          <div className="absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full border-2 border-brand-500 bg-white" />
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-900">
              v{model.version}
            </span>
            <Badge variant={statusVariant(model.status)}>{model.status}</Badge>
          </div>
          <p className="mt-0.5 text-xs text-gray-500">
            {formatDate(model.updated_at)}
          </p>
        </li>
      </ol>
    </section>
  );
}

function ActionButtons({
  model,
  onAction,
}: {
  model: ModelRecord;
  onAction: (action: ModelAction, modelId: string) => void;
}) {
  const isProduction = model.status.toLowerCase() === 'production';
  const isArchived = model.status.toLowerCase() === 'archived';

  return (
    <section className="space-y-2 pt-2 border-t border-gray-200">
      {!isProduction && !isArchived && (
        <Button
          variant="primary"
          className="w-full"
          onClick={() => onAction('promote', model.id)}
        >
          Promote to Production
        </Button>
      )}
      {!isArchived && model.status.toLowerCase() !== 'shadow' && (
        <Button
          variant="secondary"
          className="w-full"
          onClick={() => onAction('shadow', model.id)}
        >
          Set as Shadow
        </Button>
      )}
      {!isArchived && (
        <Button
          variant="danger"
          className="w-full"
          onClick={() => onAction('archive', model.id)}
        >
          Archive
        </Button>
      )}
      <Button
        variant="secondary"
        className="w-full"
        onClick={() => onAction('compare', model.id)}
      >
        Compare with another version
      </Button>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ModelDetailPanel({
  model,
  isOpen,
  onClose,
  onAction,
}: ModelDetailPanelProps) {
  const handleEsc = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose],
  );

  useEffect(() => {
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
  }, [isOpen, handleEsc]);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Slide-over panel */}
      <div className="relative z-10 w-full max-w-[400px] bg-white shadow-xl flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <h2 className="text-lg font-semibold text-gray-900 truncate">
              {model.name}
            </h2>
            <Badge variant={statusVariant(model.status)}>
              {model.status}
            </Badge>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors shrink-0"
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

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          <MetadataSection model={model} />
          <MetricsTable metrics={model.metrics} />
          <VersionTimeline model={model} />
          <ActionButtons model={model} onAction={onAction} />
        </div>
      </div>
    </div>,
    document.body,
  );
}
