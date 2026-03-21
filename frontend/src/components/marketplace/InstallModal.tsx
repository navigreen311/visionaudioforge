"use client";

import { useState, useEffect, useCallback, useRef } from "react";

import api from "@/lib/api";
import Modal from "@/components/ui/Modal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PluginDependency {
  name: string;
  version: string;
}

interface PluginInstallInfo {
  id: string;
  name: string;
  description: string;
  version: string;
  latestVersion?: string;
  category: string;
  author: string;
  additions: string[];
  dependencies: PluginDependency[];
}

type InstallStep = "downloading" | "registering" | "done";

interface InstallStatusResponse {
  status: "pending" | "in_progress" | "completed" | "failed";
  step: InstallStep;
  progress: number;
  error?: string;
}

interface InstallModalProps {
  isOpen: boolean;
  onClose: () => void;
  pluginId: string;
  pluginName: string;
  pluginDescription: string;
  pluginVersion: string;
  pluginCategory: string;
  pluginAuthor: string;
  /** When set, modal shows update flow instead of fresh install. */
  updateFromVersion?: string;
  onInstalled?: () => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const INSTALL_STEPS: { key: InstallStep; label: string }[] = [
  { key: "downloading", label: "Downloading plugin" },
  { key: "registering", label: "Registering with pipeline" },
  { key: "done", label: "Done" },
];

/** Simulated additions per category (used when API call fails or for preview). */
const CATEGORY_ADDITIONS: Record<string, string[]> = {
  vision: ["Vision processing node", "Model weights"],
  audio: ["Audio processing node", "Codec support"],
  transform: ["Transform pipeline node"],
  integration: ["Integration connector", "Webhook handler"],
  analytics: ["Analytics dashboard widget", "Report template"],
  pipeline_node: ["Custom pipeline node"],
  model: ["Model adapter", "Inference endpoint"],
};

/** Simulated dependencies per category. */
const CATEGORY_DEPS: Record<string, PluginDependency[]> = {
  vision: [{ name: "opencv-python", version: ">=4.8" }],
  audio: [{ name: "librosa", version: ">=0.10" }],
  transform: [],
  integration: [],
  analytics: [{ name: "pandas", version: ">=2.0" }],
  pipeline_node: [],
  model: [{ name: "torch", version: ">=2.0" }],
};

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className ?? "h-5 w-5 text-green-500"}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

function SpinnerIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className ?? "h-5 w-5 text-brand-500 animate-spin"}
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
  );
}

function stepIndex(step: InstallStep): number {
  return INSTALL_STEPS.findIndex((s) => s.key === step);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function InstallModal({
  isOpen,
  onClose,
  pluginId,
  pluginName,
  pluginDescription,
  pluginVersion,
  pluginCategory,
  pluginAuthor,
  updateFromVersion,
  onInstalled,
}: InstallModalProps) {
  const isUpdate = !!updateFromVersion;

  const [phase, setPhase] = useState<"confirm" | "progress" | "success">(
    "confirm",
  );
  const [info, setInfo] = useState<PluginInstallInfo | null>(null);
  const [installId, setInstallId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<InstallStep>("downloading");
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ---- Build install info on open ----
  useEffect(() => {
    if (!isOpen) return;
    setPhase("confirm");
    setError(null);
    setCurrentStep("downloading");
    setInstallId(null);

    // Build preview info from props + category defaults
    const additions =
      CATEGORY_ADDITIONS[pluginCategory] ?? ["Plugin module"];
    const dependencies = CATEGORY_DEPS[pluginCategory] ?? [];

    setInfo({
      id: pluginId,
      name: pluginName,
      description: pluginDescription,
      version: pluginVersion,
      latestVersion: isUpdate ? pluginVersion : undefined,
      category: pluginCategory,
      author: pluginAuthor,
      additions,
      dependencies,
    });
  }, [
    isOpen,
    pluginId,
    pluginName,
    pluginDescription,
    pluginVersion,
    pluginCategory,
    pluginAuthor,
    isUpdate,
  ]);

  // ---- Poll install status ----
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!installId) return;

    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get<InstallStatusResponse>(
          `/api/marketplace/plugins/${pluginId}/install/status`,
        );
        setCurrentStep(data.step);

        if (data.status === "completed") {
          stopPolling();
          setPhase("success");
          onInstalled?.();
        } else if (data.status === "failed") {
          stopPolling();
          setError(data.error ?? "Installation failed.");
        }
      } catch {
        stopPolling();
        setError("Lost connection to install service.");
      }
    }, 800);

    return stopPolling;
  }, [installId, stopPolling, pluginId, onInstalled]);

  // ---- Kick off install / update ----
  const handleInstall = async () => {
    setPhase("progress");
    setError(null);
    setCurrentStep("downloading");

    try {
      const endpoint = isUpdate
        ? `/api/marketplace/plugins/${pluginId}/update`
        : `/api/marketplace/plugins/${pluginId}/install`;

      const { data } = await api.post<{ install_id: string }>(endpoint);
      setInstallId(data.install_id);
    } catch {
      setError(
        isUpdate ? "Failed to start update." : "Failed to start installation.",
      );
    }
  };

  // ---- Close & cleanup ----
  const handleClose = () => {
    stopPolling();
    onClose();
  };

  // ---- Render: Step 1 — Confirm ----
  const currentStepIdx = stepIndex(currentStep);

  const renderConfirm = () => (
    <div className="space-y-4">
      {/* Update badge */}
      {isUpdate && (
        <div className="flex items-center gap-2 rounded-lg bg-blue-50 border border-blue-200 px-3 py-2">
          <svg
            className="h-4 w-4 text-blue-500 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          <span className="text-sm font-medium text-blue-700">
            Updating v{updateFromVersion} → v{pluginVersion}
          </span>
        </div>
      )}

      {/* Description */}
      <p className="text-sm text-gray-600">{info?.description}</p>

      {/* Metadata */}
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span>v{info?.version}</span>
        <span>by {info?.author}</span>
        <span className="capitalize">{info?.category?.replace("_", " ")}</span>
      </div>

      {/* What gets added */}
      {info && info.additions.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            What gets added
          </h4>
          <ul className="space-y-1">
            {info.additions.map((item) => (
              <li
                key={item}
                className="flex items-center gap-2 text-sm text-gray-700"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-brand-500 flex-shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Dependencies */}
      {info && info.dependencies.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Dependencies
          </h4>
          <div className="flex flex-wrap gap-2">
            {info.dependencies.map((dep) => (
              <span
                key={dep.name}
                className="inline-flex items-center gap-1 rounded-md bg-gray-100 px-2 py-1 text-xs text-gray-600 font-mono"
              >
                {dep.name}
                <span className="text-gray-400">{dep.version}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
          {error}
        </p>
      )}
    </div>
  );

  // ---- Render: Step 2 — Progress ----
  const renderProgress = () => (
    <div className="space-y-3">
      {isUpdate && (
        <p className="text-xs text-gray-500 mb-2">
          Updating v{updateFromVersion} → v{pluginVersion}
        </p>
      )}

      {INSTALL_STEPS.map((step, idx) => {
        const isDone = idx < currentStepIdx || currentStep === "done";
        const isCurrent = idx === currentStepIdx && currentStep !== "done";

        return (
          <div
            key={step.key}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              isCurrent
                ? "bg-blue-50 border border-blue-200"
                : isDone
                  ? "bg-green-50 border border-green-200"
                  : "bg-gray-50 border border-gray-100"
            }`}
          >
            {isDone ? (
              <CheckIcon className="h-5 w-5 text-green-500 flex-shrink-0" />
            ) : isCurrent ? (
              <SpinnerIcon className="h-5 w-5 text-brand-500 animate-spin flex-shrink-0" />
            ) : (
              <div className="h-5 w-5 rounded-full border-2 border-gray-300 flex-shrink-0" />
            )}
            <span
              className={`text-sm font-medium ${
                isDone
                  ? "text-green-700"
                  : isCurrent
                    ? "text-blue-700"
                    : "text-gray-400"
              }`}
            >
              {step.label}
            </span>
          </div>
        );
      })}

      {error && (
        <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 mt-2">
          {error}
        </p>
      )}
    </div>
  );

  // ---- Render: Step 3 — Success ----
  const renderSuccess = () => (
    <div className="text-center space-y-4 py-4">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
        <CheckIcon className="h-7 w-7 text-green-600" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-gray-900">
          {isUpdate ? "Updated!" : "Installed!"}
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          {pluginName} v{pluginVersion} is ready to use.
        </p>
      </div>
      <div className="flex flex-col gap-2">
        <a
          href="/pipeline"
          className="text-sm text-brand-600 hover:text-brand-800 hover:underline"
        >
          Use in Pipeline
        </a>
        <a
          href="/marketplace"
          className="text-sm text-gray-500 hover:text-gray-700 hover:underline"
        >
          Back to Marketplace
        </a>
      </div>
    </div>
  );

  // ---- Footer buttons ----
  const footer =
    phase === "confirm" ? (
      <>
        <button
          onClick={handleClose}
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
        >
          Cancel
        </button>
        <button
          onClick={handleInstall}
          disabled={!!error}
          className="px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md disabled:opacity-50 transition-colors"
        >
          {isUpdate ? "Update Plugin" : "Install Plugin"}
        </button>
      </>
    ) : phase === "success" ? (
      <button
        onClick={handleClose}
        className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors"
      >
        Close
      </button>
    ) : null;

  const modalTitle = isUpdate
    ? `Update ${pluginName}`
    : phase === "confirm"
      ? `Install ${pluginName}`
      : phase === "progress"
        ? isUpdate
          ? "Updating..."
          : "Installing..."
        : "Complete";

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={modalTitle} footer={footer}>
      {phase === "confirm" && renderConfirm()}
      {phase === "progress" && renderProgress()}
      {phase === "success" && renderSuccess()}
    </Modal>
  );
}
