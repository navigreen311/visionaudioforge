"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import { createAPIKey, type APIKeyCreatePayload, type APIKeyCreated, type APIKeyScope } from "@/lib/api";

// ---------------------------------------------------------------------------
// Scope definitions by module
// ---------------------------------------------------------------------------

interface ScopeModuleConfig {
  module: string;
  label: string;
  permissions: { value: string; label: string }[];
}

const SCOPE_MODULES: ScopeModuleConfig[] = [
  {
    module: "assets",
    label: "Assets",
    permissions: [
      { value: "read", label: "Read" },
      { value: "write", label: "Write" },
      { value: "delete", label: "Delete" },
    ],
  },
  {
    module: "pipelines",
    label: "Pipelines",
    permissions: [
      { value: "read", label: "Read" },
      { value: "write", label: "Write" },
      { value: "execute", label: "Execute" },
    ],
  },
  {
    module: "alerts",
    label: "Alerts",
    permissions: [
      { value: "read", label: "Read" },
      { value: "write", label: "Write" },
    ],
  },
  {
    module: "models",
    label: "Models",
    permissions: [
      { value: "read", label: "Read" },
      { value: "write", label: "Write" },
      { value: "deploy", label: "Deploy" },
    ],
  },
  {
    module: "admin",
    label: "Admin",
    permissions: [{ value: "full", label: "Full Access" }],
  },
];

const EXPIRATION_OPTIONS: { value: number | null; label: string }[] = [
  { value: null, label: "Never" },
  { value: 30, label: "30 days" },
  { value: 60, label: "60 days" },
  { value: 90, label: "90 days" },
  { value: 180, label: "180 days" },
  { value: 365, label: "1 year" },
];

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------

interface ScopeSelection {
  [module: string]: Set<string>;
}

function emptyScopes(): ScopeSelection {
  const s: ScopeSelection = {};
  for (const m of SCOPE_MODULES) {
    s[m.module] = new Set();
  }
  return s;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CreateAPIKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (result: APIKeyCreated) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CreateAPIKeyModal({
  isOpen,
  onClose,
  onCreated,
}: CreateAPIKeyModalProps) {
  const [name, setName] = useState("");
  const [expiresInDays, setExpiresInDays] = useState<number | null>(90);
  const [scopes, setScopes] = useState<ScopeSelection>(emptyScopes);

  // Reset on open
  useEffect(() => {
    if (isOpen) {
      setName("");
      setExpiresInDays(90);
      setScopes(emptyScopes());
    }
  }, [isOpen]);

  const togglePermission = useCallback(
    (module: string, permission: string) => {
      setScopes((prev) => {
        const next = { ...prev };
        const perms = new Set(prev[module]);
        if (perms.has(permission)) {
          perms.delete(permission);
        } else {
          perms.add(permission);
        }
        next[module] = perms;
        return next;
      });
    },
    [],
  );

  const buildPayload = useCallback((): APIKeyCreatePayload => {
    const scopeList: APIKeyScope[] = [];
    for (const [module, perms] of Object.entries(scopes)) {
      if (perms.size > 0) {
        scopeList.push({ module, permissions: Array.from(perms) });
      }
    }
    return {
      name: name.trim(),
      scopes: scopeList,
      expires_in_days: expiresInDays,
    };
  }, [name, scopes, expiresInDays]);

  const mutation = useMutation({
    mutationFn: (payload: APIKeyCreatePayload) => createAPIKey(payload),
    onSuccess: (result) => onCreated(result),
  });

  const handleCreate = useCallback(() => {
    mutation.mutate(buildPayload());
  }, [mutation, buildPayload]);

  const hasScopes = Object.values(scopes).some((s) => s.size > 0);
  const canCreate = name.trim().length > 0 && hasScopes;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create API Key"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            loading={mutation.isPending}
            disabled={!canCreate}
          >
            Create Key
          </Button>
        </>
      }
    >
      <div className="space-y-5 max-h-[70vh] overflow-y-auto pr-1">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Key Name
          </label>
          <input
            type="text"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            placeholder="e.g. CI/CD Pipeline"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        {/* Expiration */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Expiration
          </label>
          <select
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            value={expiresInDays ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              setExpiresInDays(val === "" ? null : Number(val));
            }}
          >
            {EXPIRATION_OPTIONS.map((opt) => (
              <option key={opt.label} value={opt.value ?? ""}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Scopes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Scopes
          </label>
          <div className="space-y-3">
            {SCOPE_MODULES.map((mod) => (
              <div
                key={mod.module}
                className="rounded border border-gray-200 p-3 bg-gray-50"
              >
                <p className="text-sm font-semibold text-gray-800 mb-2">
                  {mod.label}
                </p>
                <div className="flex flex-wrap gap-2">
                  {mod.permissions.map((perm) => {
                    const active = scopes[mod.module]?.has(perm.value) ?? false;
                    return (
                      <button
                        key={perm.value}
                        type="button"
                        onClick={() =>
                          togglePermission(mod.module, perm.value)
                        }
                        className={`rounded-md px-3 py-1 text-xs font-medium border transition-colors ${
                          active
                            ? "bg-brand-600 text-white border-brand-600"
                            : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                        }`}
                      >
                        {perm.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Mutation error */}
        {mutation.isError && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            Failed to create API key. Please try again.
          </div>
        )}
      </div>
    </Modal>
  );
}
