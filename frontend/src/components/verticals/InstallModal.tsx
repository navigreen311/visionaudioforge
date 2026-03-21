"use client";

import { useState, useEffect, useCallback, useRef } from "react";

import api from "@/lib/api";
import Modal from "@/components/ui/Modal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PackManifest {
  id: string;
  name: string;
  description: string;
  modules: string[];
  models: string[];
  configs: string[];
  pipelines: string[];
  totalResources: number;
}

type InstallStep =
  | "downloading"
  | "installing_pipelines"
  | "configuring_alerts"
  | "setting_up"
  | "done";

interface InstallStatus {
  status: "pending" | "in_progress" | "completed" | "failed";
  step: InstallStep;
  progress: number;
  error?: string;
}

interface InstallModalProps {
  isOpen: boolean;
  onClose: () => void;
  packId: string;
  packName: string;
  onInstalled?: () => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const INSTALL_STEPS: { key: InstallStep; label: string }[] = [
  { key: "downloading", label: "Downloading resources" },
  { key: "installing_pipelines", label: "Installing pipelines" },
  { key: "configuring_alerts", label: "Configuring alerts" },
  { key: "setting_up", label: "Setting up environment" },
  { key: "done", label: "Done" },
];

const WARNINGS = [
  "This will install additional pipelines and alert rules.",
  "Existing configurations will not be overwritten.",
  "You can uninstall or manage modules at any time.",
];

const LS_KEY_PREFIX = "vaf_install_";

// ---------------------------------------------------------------------------
// Helpers
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
      className={className ?? "h-5 w-5 text-blue-500 animate-spin"}
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
  packId,
  packName,
  onInstalled,
}: InstallModalProps) {
  const [phase, setPhase] = useState<"preview" | "progress" | "success">(
    "preview"
  );
  const [manifest, setManifest] = useState<PackManifest | null>(null);
  const [loadingManifest, setLoadingManifest] = useState(false);
  const [installId, setInstallId] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<InstallStep>("downloading");
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ---- Fetch manifest on open ----
  useEffect(() => {
    if (!isOpen || !packId) return;
    setPhase("preview");
    setError(null);
    setCurrentStep("downloading");
    setInstallId(null);
    setLoadingManifest(true);

    (async () => {
      try {
        const [packRes, resourceRes] = await Promise.all([
          api.get(`/api/verticals/packs/${packId}`),
          api.get(`/api/verticals/packs/${packId}/resources`),
        ]);
        const pack = packRes.data as Record<string, unknown>;
        const res = resourceRes.data as Record<string, unknown>;
        setManifest({
          id: pack.id as string,
          name: pack.name as string,
          description: pack.description as string,
          modules: pack.modules as string[],
          models: res.models as string[],
          configs: res.configs as string[],
          pipelines: res.pipelines as string[],
          totalResources: res.total_resources as number,
        });
      } catch {
        setError("Failed to load pack details.");
      } finally {
        setLoadingManifest(false);
      }
    })();
  }, [isOpen, packId]);

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
        const { data } = await api.get<InstallStatus>(
          `/api/verticals/install/${installId}/status`
        );
        setCurrentStep(data.step);

        if (data.status === "completed") {
          stopPolling();
          setPhase("success");
          // Persist to localStorage
          localStorage.setItem(
            `${LS_KEY_PREFIX}${packId}`,
            JSON.stringify({
              packId,
              packName,
              installedAt: new Date().toISOString(),
              version: "1.0.0",
              modules: manifest?.modules ?? [],
            })
          );
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
  }, [installId, stopPolling, packId, packName, manifest, onInstalled]);

  // ---- Kick off install ----
  const handleInstall = async () => {
    setPhase("progress");
    setError(null);
    setCurrentStep("downloading");

    try {
      const { data } = await api.post<{ install_id: string }>(
        "/api/verticals/install",
        { pack_id: packId }
      );
      setInstallId(data.install_id);
    } catch {
      setError("Failed to start installation.");
    }
  };

  // ---- Handle close & cleanup ----
  const handleClose = () => {
    stopPolling();
    onClose();
  };

  // ---- Render helpers ----
  const currentStepIdx = stepIndex(currentStep);

  const renderPreview = () => (
    <div className="space-y-4">
      {loadingManifest ? (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <SpinnerIcon className="h-4 w-4 text-blue-500 animate-spin" />
          Loading pack manifest...
        </div>
      ) : manifest ? (
        <>
          <p className="text-sm text-gray-600">{manifest.description}</p>

          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
              What gets installed
            </h4>
            <ul className="space-y-1">
              {manifest.modules.map((m) => (
                <li key={m} className="flex items-center gap-2 text-sm text-gray-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-500 flex-shrink-0" />
                  {m}
                </li>
              ))}
              <li className="flex items-center gap-2 text-sm text-gray-700">
                <span className="h-1.5 w-1.5 rounded-full bg-purple-500 flex-shrink-0" />
                {manifest.models.length} model(s), {manifest.pipelines.length} pipeline(s), {manifest.configs.length} config(s)
              </li>
            </ul>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 space-y-1">
            {WARNINGS.map((w) => (
              <p key={w} className="text-xs text-amber-700 flex items-start gap-1.5">
                <span className="mt-0.5 flex-shrink-0">&#9888;</span>
                {w}
              </p>
            ))}
          </div>
        </>
      ) : null}

      {error && (
        <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
          {error}
        </p>
      )}
    </div>
  );

  const renderProgress = () => (
    <div className="space-y-3">
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
              <SpinnerIcon className="h-5 w-5 text-blue-500 animate-spin flex-shrink-0" />
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

  const renderSuccess = () => (
    <div className="text-center space-y-4 py-4">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
        <CheckIcon className="h-7 w-7 text-green-600" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-gray-900">
          {packName} installed
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          All modules, pipelines, and alerts are ready.
        </p>
      </div>
      <div className="flex flex-col gap-2">
        <a
          href="/pipeline"
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
        >
          View pipelines
        </a>
        <a
          href="/alerts"
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
        >
          View alerts
        </a>
        <a
          href="/verticals/installed"
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
        >
          Manage installed packs
        </a>
      </div>
    </div>
  );

  // ---- Footer buttons ----
  const footer =
    phase === "preview" ? (
      <>
        <button
          onClick={handleClose}
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
        >
          Cancel
        </button>
        <button
          onClick={handleInstall}
          disabled={loadingManifest || !!error}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50 transition-colors"
        >
          Install Pack
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

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={
        phase === "preview"
          ? `Install ${packName}`
          : phase === "progress"
          ? "Installing..."
          : "Installation Complete"
      }
      footer={footer}
    >
      {phase === "preview" && renderPreview()}
      {phase === "progress" && renderProgress()}
      {phase === "success" && renderSuccess()}
    </Modal>
  );
}
