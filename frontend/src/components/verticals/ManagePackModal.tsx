"use client";

import { useState, useEffect } from "react";

import api from "@/lib/api";
import Modal from "@/components/ui/Modal";
import Badge from "@/components/ui/Badge";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PackInfo {
  id: string;
  name: string;
  modules: string[];
  version: string;
}

interface ModuleState {
  name: string;
  enabled: boolean;
}

interface ManagePackModalProps {
  isOpen: boolean;
  onClose: () => void;
  pack: PackInfo;
  onUninstalled?: () => void;
  onSaved?: () => void;
}

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

const LS_KEY_PREFIX = "vaf_install_";
const LS_MODULES_PREFIX = "vaf_modules_";

function loadModuleStates(packId: string, modules: string[]): ModuleState[] {
  if (typeof window === "undefined") {
    return modules.map((m) => ({ name: m, enabled: true }));
  }
  const raw = localStorage.getItem(`${LS_MODULES_PREFIX}${packId}`);
  if (raw) {
    try {
      const saved = JSON.parse(raw) as Record<string, boolean>;
      return modules.map((m) => ({
        name: m,
        enabled: saved[m] !== false,
      }));
    } catch {
      // fall through
    }
  }
  return modules.map((m) => ({ name: m, enabled: true }));
}

function saveModuleStates(packId: string, states: ModuleState[]) {
  const map: Record<string, boolean> = {};
  for (const s of states) {
    map[s.name] = s.enabled;
  }
  localStorage.setItem(`${LS_MODULES_PREFIX}${packId}`, JSON.stringify(map));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ManagePackModal({
  isOpen,
  onClose,
  pack,
  onUninstalled,
  onSaved,
}: ManagePackModalProps) {
  const [modules, setModules] = useState<ModuleState[]>([]);
  const [saving, setSaving] = useState(false);
  const [confirmUninstall, setConfirmUninstall] = useState(false);
  const [uninstalling, setUninstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // ---- Init module states ----
  useEffect(() => {
    if (isOpen && pack) {
      setModules(loadModuleStates(pack.id, pack.modules));
      setConfirmUninstall(false);
      setError(null);
      setSaved(false);
    }
  }, [isOpen, pack]);

  // ---- Toggle module ----
  const toggleModule = (idx: number) => {
    setModules((prev) =>
      prev.map((m, i) => (i === idx ? { ...m, enabled: !m.enabled } : m))
    );
    setSaved(false);
  };

  // ---- Save changes ----
  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const enabledModules = modules
        .filter((m) => m.enabled)
        .map((m) => m.name);

      await api.patch(`/api/verticals/install/${pack.id}`, {
        enabled_modules: enabledModules,
      });

      saveModuleStates(pack.id, modules);
      setSaved(true);
      onSaved?.();
    } catch {
      setError("Failed to save changes.");
    } finally {
      setSaving(false);
    }
  };

  // ---- Uninstall ----
  const handleUninstall = async () => {
    setUninstalling(true);
    setError(null);
    try {
      await api.delete(`/api/verticals/install/${pack.id}`);
      // Clean localStorage
      localStorage.removeItem(`${LS_KEY_PREFIX}${pack.id}`);
      localStorage.removeItem(`${LS_MODULES_PREFIX}${pack.id}`);
      onUninstalled?.();
    } catch {
      setError("Failed to uninstall pack.");
      setUninstalling(false);
    }
  };

  // ---- Render ----
  const enabledCount = modules.filter((m) => m.enabled).length;

  const footer = confirmUninstall ? (
    <>
      <button
        onClick={() => setConfirmUninstall(false)}
        className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
        disabled={uninstalling}
      >
        Cancel
      </button>
      <button
        onClick={handleUninstall}
        disabled={uninstalling}
        className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md disabled:opacity-50 transition-colors"
      >
        {uninstalling ? "Uninstalling..." : "Confirm Uninstall"}
      </button>
    </>
  ) : (
    <>
      <button
        onClick={() => setConfirmUninstall(true)}
        className="px-4 py-2 text-sm text-red-600 hover:text-red-700 mr-auto"
      >
        Uninstall
      </button>
      <button
        onClick={onClose}
        className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
      >
        Cancel
      </button>
      <button
        onClick={handleSave}
        disabled={saving}
        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50 transition-colors"
      >
        {saving ? "Saving..." : "Save Changes"}
      </button>
    </>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={confirmUninstall ? `Uninstall ${pack.name}?` : `Manage ${pack.name}`}
      footer={footer}
    >
      {confirmUninstall ? (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">
            This will remove all modules, pipelines, and alert rules associated
            with <span className="font-medium">{pack.name}</span>.
          </p>
          <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            <p className="text-xs text-red-700">
              This action cannot be undone. Any custom configurations for this
              pack will be lost.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Pack info */}
          <div className="flex items-center gap-2">
            <Badge variant="success">v{pack.version}</Badge>
            <span className="text-xs text-gray-500">
              {enabledCount}/{modules.length} modules enabled
            </span>
          </div>

          {/* Module toggles */}
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Installed Components
            </h4>
            <div className="space-y-2">
              {modules.map((mod, idx) => (
                <div
                  key={mod.name}
                  className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-2.5"
                >
                  <span className="text-sm text-gray-700">{mod.name}</span>
                  <button
                    onClick={() => toggleModule(idx)}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                      mod.enabled ? "bg-blue-600" : "bg-gray-300"
                    }`}
                    role="switch"
                    aria-checked={mod.enabled}
                  >
                    <span
                      className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                        mod.enabled ? "translate-x-4" : "translate-x-0.5"
                      }`}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Feedback */}
          {saved && (
            <p className="text-sm text-green-600 bg-green-50 rounded-lg px-3 py-2">
              Changes saved successfully.
            </p>
          )}
          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </div>
      )}
    </Modal>
  );
}
