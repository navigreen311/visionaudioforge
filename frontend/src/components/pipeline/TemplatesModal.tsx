"use client";

import { useState } from "react";

import {
  PIPELINE_TEMPLATES,
  PipelineTemplate,
} from "@/lib/pipeline-templates";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TemplatesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (template: PipelineTemplate) => void;
  canvasEmpty?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const CATEGORY_COLOR: Record<string, string> = {
  Vision: "bg-blue-100 text-blue-700",
  Audio: "bg-purple-100 text-purple-700",
  Transform: "bg-orange-100 text-orange-700",
  Monitoring: "bg-yellow-100 text-yellow-700",
  Reporting: "bg-teal-100 text-teal-700",
  Evidence: "bg-red-100 text-red-700",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TemplatesModal({
  isOpen,
  onClose,
  onSelect,
  canvasEmpty = true,
}: TemplatesModalProps) {
  const [confirmTemplate, setConfirmTemplate] =
    useState<PipelineTemplate | null>(null);

  if (!isOpen) return null;

  const handleUseTemplate = (template: PipelineTemplate) => {
    if (!canvasEmpty) {
      setConfirmTemplate(template);
    } else {
      onSelect(template);
      onClose();
    }
  };

  const confirmHandler = () => {
    if (confirmTemplate) {
      onSelect(confirmTemplate);
      setConfirmTemplate(null);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">
              Pipeline Templates
            </h2>
            <p className="text-sm text-gray-500 mt-0.5">
              Start with a pre-built pipeline and customize it to your needs
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
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

        {/* Grid */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {PIPELINE_TEMPLATES.map((template) => (
              <div
                key={template.key}
                className="flex flex-col border border-gray-200 rounded-lg p-4 hover:border-brand-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-sm font-semibold text-gray-800 leading-snug">
                    {template.name}
                  </h3>
                  <span
                    className={`ml-2 flex-shrink-0 inline-block px-2 py-0.5 text-xs font-medium rounded ${
                      CATEGORY_COLOR[template.category] ??
                      "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {template.category}
                  </span>
                </div>

                <p className="text-xs text-gray-500 leading-relaxed flex-1 mb-3">
                  {template.description}
                </p>

                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-1 text-xs text-gray-400 bg-gray-50 px-2 py-0.5 rounded">
                    {template.nodes.length} node
                    {template.nodes.length !== 1 ? "s" : ""}
                  </span>
                  <button
                    onClick={() => handleUseTemplate(template)}
                    className="px-3 py-1.5 text-xs font-medium text-white bg-brand-600 hover:bg-brand-700 rounded transition-colors"
                  >
                    Use template
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Confirm overwrite dialog */}
      {confirmTemplate && (
        <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h3 className="text-base font-semibold text-gray-800 mb-2">
              Replace current pipeline?
            </h3>
            <p className="text-sm text-gray-600 mb-5">
              The canvas is not empty. Using &quot;{confirmTemplate.name}&quot;
              will replace your current nodes and edges. Continue?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmTemplate(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={confirmHandler}
                className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
              >
                Replace
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
