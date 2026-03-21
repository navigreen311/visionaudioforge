"use client";

import React, { useCallback, useEffect, useRef } from "react";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PipelineManifest {
  name: string;
  nodes: number;
  description: string;
}

interface AlertRuleManifest {
  name: string;
  condition: string;
  severity: string;
}

interface PackRequirements {
  storage: string;
  modules: string[];
  conflicts: string[];
}

export interface VerticalPackDetail {
  slug: string;
  name: string;
  icon: string;
  description: string;
  category: string;
  pipelineCount: number;
  alertPresetCount: number;
  pipelines: PipelineManifest[];
  alertRules: AlertRuleManifest[];
  dashboards: string[];
  models: string[];
  sampleData: string[];
  requirements: PackRequirements;
}

interface PackDetailPanelProps {
  pack: VerticalPackDetail | null;
  isOpen: boolean;
  onClose: () => void;
  onInstall: (slug: string) => void;
}

// ---------------------------------------------------------------------------
// Severity badge variant helper
// ---------------------------------------------------------------------------

function severityVariant(severity: string): string {
  switch (severity.toLowerCase()) {
    case "critical":
      return "error";
    case "high":
    case "warning":
      return "warning";
    case "medium":
    case "info":
      return "info";
    default:
      return "neutral";
  }
}

// ---------------------------------------------------------------------------
// Section heading
// ---------------------------------------------------------------------------

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
      {children}
    </h3>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PackDetailPanel({
  pack,
  isOpen,
  onClose,
  onInstall,
}: PackDetailPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // ---- Body scroll lock ----
  useEffect(() => {
    if (!isOpen) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [isOpen]);

  // ---- Escape key handler ----
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!isOpen) return;
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleKeyDown]);

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  // ---- Render ----
  if (!pack) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/30 transition-opacity duration-300 ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={handleBackdropClick}
        role="presentation"
      />

      {/* Slide-over panel */}
      <div
        ref={panelRef}
        className={`fixed inset-y-0 right-0 z-50 flex w-[480px] max-w-full flex-col bg-white shadow-2xl transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
        role="dialog"
        aria-modal="true"
        aria-label="Pack details"
      >
        {/* ========== Header ========== */}
        <div className="flex items-start justify-between gap-3 border-b border-gray-200 px-5 py-4">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <span className="text-3xl">{pack.icon}</span>
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-gray-900 truncate">
                {pack.name}
              </h2>
              <Badge variant="info">{pack.category}</Badge>
            </div>
          </div>
          <button
            type="button"
            className="mt-1 rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            onClick={onClose}
            aria-label="Close panel"
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
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
          {/* Description */}
          <p className="text-sm text-gray-600 leading-relaxed">
            {pack.description}
          </p>

          {/* ========== Pipelines ========== */}
          {pack.pipelines.length > 0 && (
            <section>
              <SectionHeading>
                Pipelines ({pack.pipelines.length})
              </SectionHeading>
              <ul className="space-y-2">
                {pack.pipelines.map((p) => (
                  <li
                    key={p.name}
                    className="rounded-md border border-gray-100 bg-gray-50 p-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-900">
                        {p.name}
                      </span>
                      <span className="text-xs text-gray-400">
                        {p.nodes} node{p.nodes !== 1 ? "s" : ""}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{p.description}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* ========== Alert Rules ========== */}
          {pack.alertRules.length > 0 && (
            <section>
              <SectionHeading>
                Alert Rules ({pack.alertRules.length})
              </SectionHeading>
              <ul className="space-y-2">
                {pack.alertRules.map((rule) => (
                  <li
                    key={rule.name}
                    className="flex items-center justify-between rounded-md border border-gray-100 bg-gray-50 p-3"
                  >
                    <div className="min-w-0">
                      <span className="text-sm font-medium text-gray-900">
                        {rule.name}
                      </span>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {rule.condition}
                      </p>
                    </div>
                    <Badge variant={severityVariant(rule.severity)}>
                      {rule.severity}
                    </Badge>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* ========== Dashboards ========== */}
          {pack.dashboards.length > 0 && (
            <section>
              <SectionHeading>
                Dashboards ({pack.dashboards.length})
              </SectionHeading>
              <ul className="space-y-1">
                {pack.dashboards.map((d) => (
                  <li
                    key={d}
                    className="flex items-center gap-2 text-sm text-gray-700"
                  >
                    <svg
                      className="h-4 w-4 text-gray-400 shrink-0"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                      />
                    </svg>
                    {d}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* ========== Models ========== */}
          {pack.models.length > 0 && (
            <section>
              <SectionHeading>Models ({pack.models.length})</SectionHeading>
              <ul className="space-y-1">
                {pack.models.map((m) => (
                  <li
                    key={m}
                    className="flex items-center gap-2 text-sm text-gray-700"
                  >
                    <svg
                      className="h-4 w-4 text-gray-400 shrink-0"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                      />
                    </svg>
                    {m}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* ========== Sample Data ========== */}
          {pack.sampleData.length > 0 && (
            <section>
              <SectionHeading>
                Sample Data ({pack.sampleData.length})
              </SectionHeading>
              <ul className="space-y-1">
                {pack.sampleData.map((s) => (
                  <li
                    key={s}
                    className="flex items-center gap-2 text-sm text-gray-700"
                  >
                    <svg
                      className="h-4 w-4 text-gray-400 shrink-0"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
                      />
                    </svg>
                    {s}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* ========== Requirements ========== */}
          <section>
            <SectionHeading>Requirements</SectionHeading>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Storage</dt>
                <dd className="font-medium text-gray-900">
                  {pack.requirements.storage}
                </dd>
              </div>
              {pack.requirements.modules.length > 0 && (
                <div>
                  <dt className="text-gray-500 mb-1">Required Modules</dt>
                  <dd className="flex flex-wrap gap-1">
                    {pack.requirements.modules.map((mod) => (
                      <Badge key={mod} variant="info">
                        {mod}
                      </Badge>
                    ))}
                  </dd>
                </div>
              )}
              {pack.requirements.conflicts.length > 0 && (
                <div>
                  <dt className="text-gray-500 mb-1">Conflicts With</dt>
                  <dd className="flex flex-wrap gap-1">
                    {pack.requirements.conflicts.map((c) => (
                      <Badge key={c} variant="warning">
                        {c}
                      </Badge>
                    ))}
                  </dd>
                </div>
              )}
            </dl>
          </section>
        </div>

        {/* ========== Footer ========== */}
        <div className="border-t border-gray-200 px-5 py-3 bg-gray-50 flex justify-end gap-3">
          <Button variant="ghost" size="md" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={() => onInstall(pack.slug)}
          >
            Install Pack
          </Button>
        </div>
      </div>
    </>
  );
}
