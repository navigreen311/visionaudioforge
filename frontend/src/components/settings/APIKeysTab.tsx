"use client";

import React, { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import CreateAPIKeyModal from "./CreateAPIKeyModal";
import KeyRevealModal from "./KeyRevealModal";
import {
  listAPIKeys,
  revokeAPIKey,
  type APIKeyRead,
  type APIKeyCreated,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Scope color map
// ---------------------------------------------------------------------------

const SCOPE_COLORS: Record<string, string> = {
  assets: "bg-blue-100 text-blue-800",
  pipelines: "bg-purple-100 text-purple-800",
  alerts: "bg-yellow-100 text-yellow-800",
  models: "bg-green-100 text-green-800",
  admin: "bg-red-100 text-red-800",
};

function scopeColor(module: string): string {
  return SCOPE_COLORS[module] ?? "bg-gray-100 text-gray-800";
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function maskKey(prefix: string): string {
  // prefix is like "vaf_prod_a1b2c3" — append mask
  return `${prefix}${"\\u2022".repeat(4)}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function isExpired(expiresAt: string | null): boolean {
  if (!expiresAt) return false;
  return new Date(expiresAt) < new Date();
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function APIKeysTab() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [revealKey, setRevealKey] = useState<APIKeyCreated | null>(null);
  const [confirmRevokeId, setConfirmRevokeId] = useState<string | null>(null);

  // ---- Queries ----
  const {
    data: keys = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["api-keys"],
    queryFn: listAPIKeys,
  });

  const invalidate = useCallback(
    () => queryClient.invalidateQueries({ queryKey: ["api-keys"] }),
    [queryClient],
  );

  // ---- Mutations ----
  const revokeMutation = useMutation({
    mutationFn: revokeAPIKey,
    onSuccess: () => {
      setConfirmRevokeId(null);
      invalidate();
    },
  });

  // ---- Handlers ----
  const handleCreated = useCallback(
    (result: APIKeyCreated) => {
      setCreateOpen(false);
      setRevealKey(result);
      invalidate();
    },
    [invalidate],
  );

  const handleCopy = useCallback(async (prefix: string) => {
    try {
      await navigator.clipboard.writeText(prefix);
    } catch {
      // silent
    }
  }, []);

  const handleConfirmRevoke = useCallback(
    (keyId: string) => {
      revokeMutation.mutate(keyId);
    },
    [revokeMutation],
  );

  // ---- Render ----
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">API Keys</h2>
        <Button onClick={() => setCreateOpen(true)}>+ New API Key</Button>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load API keys. Please try again.
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && keys.length === 0 && (
        <EmptyState
          title="No API keys"
          description="Create your first API key to authenticate external integrations."
          action={{ label: "+ New API Key", onClick: () => setCreateOpen(true) }}
        />
      )}

      {/* Table */}
      {!isLoading && !isError && keys.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Key
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Scopes
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Last Used
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Expires
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {keys.map((key) => (
                <tr
                  key={key.id}
                  className={`hover:bg-gray-50 transition-colors ${
                    isExpired(key.expires_at) ? "opacity-60" : ""
                  }`}
                >
                  {/* Name */}
                  <td className="whitespace-nowrap px-4 py-3">
                    <span className="text-sm font-medium text-gray-900">
                      {key.name}
                    </span>
                  </td>

                  {/* Key (masked) */}
                  <td className="whitespace-nowrap px-4 py-3">
                    <code className="rounded bg-gray-100 px-2 py-1 text-xs font-mono text-gray-700">
                      {maskKey(key.key_prefix)}
                    </code>
                  </td>

                  {/* Scopes */}
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {key.scopes.map((scope) => (
                        <span
                          key={scope.module}
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${scopeColor(scope.module)}`}
                          title={scope.permissions.join(", ")}
                        >
                          {scope.module}
                        </span>
                      ))}
                    </div>
                  </td>

                  {/* Last Used */}
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                    {formatDate(key.last_used_at)}
                  </td>

                  {/* Expires */}
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    {isExpired(key.expires_at) ? (
                      <Badge variant="error">Expired</Badge>
                    ) : (
                      <span className="text-gray-500">
                        {key.expires_at ? formatDate(key.expires_at) : "Never"}
                      </span>
                    )}
                  </td>

                  {/* Actions */}
                  <td className="whitespace-nowrap px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(key.key_prefix)}
                        title="Copy key prefix"
                      >
                        Copy
                      </Button>

                      {confirmRevokeId === key.id ? (
                        <div className="flex items-center gap-1">
                          <Button
                            variant="danger"
                            size="sm"
                            loading={revokeMutation.isPending}
                            onClick={() => handleConfirmRevoke(key.id)}
                          >
                            Confirm
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setConfirmRevokeId(null)}
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setConfirmRevokeId(key.id)}
                        >
                          <span className="text-red-600">Revoke</span>
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Modal */}
      <CreateAPIKeyModal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={handleCreated}
      />

      {/* Key Reveal Modal */}
      {revealKey && (
        <KeyRevealModal
          isOpen={true}
          onClose={() => setRevealKey(null)}
          fullKey={revealKey.key}
          keyName={revealKey.name}
        />
      )}
    </div>
  );
}
