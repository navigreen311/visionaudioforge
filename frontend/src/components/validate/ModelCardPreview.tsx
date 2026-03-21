"use client";

import React from "react";
import { createPortal } from "react-dom";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface PerformanceMetric {
  name: string;
  value: string;
  dataset: string;
  notes: string;
}

export interface ModelCardData {
  /* Model Details */
  modelName: string;
  version: string;
  modelType: string;
  architecture: string;
  trainingDate: string;
  framework: string;
  license: string;

  /* Intended Use */
  primaryUseCases: string;
  outOfScope: string;
  targetUsers: string;

  /* Performance */
  metrics: PerformanceMetric[];

  /* Limitations & Risks */
  knownLimitations: string;
  ethicalConsiderations: string;
  biasFairness: string;

  /* Training Data */
  datasetName: string;
  datasetSize: string;
  datasetDescription: string;
  preprocessingSteps: string;
}

interface ModelCardPreviewProps {
  cardData: ModelCardData;
  isOpen: boolean;
  onClose: () => void;
}

/* ------------------------------------------------------------------ */
/*  Section helper                                                     */
/* ------------------------------------------------------------------ */

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-6">
      <h3 className="text-base font-semibold text-gray-900 border-b border-gray-200 pb-1 mb-2">
        {title}
      </h3>
      {children}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div className="mb-1.5">
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
        {label}
      </span>
      <p className="text-sm text-gray-700 whitespace-pre-wrap">{value}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function ModelCardPreview({
  cardData,
  isOpen,
  onClose,
}: ModelCardPreviewProps) {
  /* SSR guard — portal target doesn't exist on server */
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);

  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  React.useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [isOpen, onClose]);

  if (!isOpen || !mounted) return null;

  const d = cardData;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Panel — wider for publication-style card */}
      <div className="relative z-10 w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-lg bg-white shadow-xl mx-4">
        {/* Header */}
        <div className="sticky top-0 z-20 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Model Card Preview
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

        {/* Body — publication style */}
        <div className="px-8 py-6">
          {/* Title block */}
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900">
              {d.modelName || "Untitled Model"}
            </h1>
            {d.version && (
              <p className="text-sm text-gray-500 mt-1">
                Version {d.version}
              </p>
            )}
            {(d.framework || d.license) && (
              <div className="flex items-center justify-center gap-3 mt-2 text-xs text-gray-400">
                {d.framework && <span>{d.framework}</span>}
                {d.framework && d.license && <span>|</span>}
                {d.license && <span>{d.license}</span>}
              </div>
            )}
          </div>

          {/* Model Details */}
          <Section title="Model Details">
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              <Field label="Type" value={d.modelType} />
              <Field label="Training Date" value={d.trainingDate} />
              <Field label="Framework" value={d.framework} />
              <Field label="License" value={d.license} />
            </div>
            <Field label="Architecture" value={d.architecture} />
          </Section>

          {/* Intended Use */}
          <Section title="Intended Use">
            <Field label="Primary Use Cases" value={d.primaryUseCases} />
            <Field label="Out-of-Scope Uses" value={d.outOfScope} />
            <Field label="Target Users" value={d.targetUsers} />
          </Section>

          {/* Performance Metrics */}
          {d.metrics.length > 0 && (
            <Section title="Performance Metrics">
              <div className="overflow-x-auto">
                <table className="w-full text-sm border border-gray-200 rounded">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left px-3 py-2 font-medium text-gray-600">
                        Metric
                      </th>
                      <th className="text-left px-3 py-2 font-medium text-gray-600">
                        Value
                      </th>
                      <th className="text-left px-3 py-2 font-medium text-gray-600">
                        Dataset
                      </th>
                      <th className="text-left px-3 py-2 font-medium text-gray-600">
                        Notes
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.metrics.map((m, idx) => (
                      <tr
                        key={idx}
                        className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}
                      >
                        <td className="px-3 py-1.5 text-gray-800">
                          {m.name}
                        </td>
                        <td className="px-3 py-1.5 font-mono text-gray-900">
                          {m.value}
                        </td>
                        <td className="px-3 py-1.5 text-gray-600">
                          {m.dataset}
                        </td>
                        <td className="px-3 py-1.5 text-gray-500">
                          {m.notes}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>
          )}

          {/* Limitations & Risks */}
          <Section title="Limitations & Risks">
            <Field label="Known Limitations" value={d.knownLimitations} />
            <Field
              label="Ethical Considerations"
              value={d.ethicalConsiderations}
            />
            <Field label="Bias & Fairness" value={d.biasFairness} />
          </Section>

          {/* Training Data */}
          <Section title="Training Data">
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              <Field label="Dataset Name" value={d.datasetName} />
              <Field label="Dataset Size" value={d.datasetSize} />
            </div>
            <Field label="Description" value={d.datasetDescription} />
            <Field label="Preprocessing Steps" value={d.preprocessingSteps} />
          </Section>
        </div>
      </div>
    </div>,
    document.body,
  );
}
