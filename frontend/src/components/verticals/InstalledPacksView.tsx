"use client";

import { useState, useEffect, useCallback } from "react";

import api from "@/lib/api";
import Badge from "@/components/ui/Badge";
import ManagePackModal from "@/components/verticals/ManagePackModal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface InstalledPack {
  id: string;
  name: string;
  description: string;
  modules: string[];
  version: string;
  installedAt: string;
  hasUpdate: boolean;
  latestVersion?: string;
}

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

const LS_KEY_PREFIX = "vaf_install_";

function loadInstalledFromStorage(): Record<string, InstalledPack> {
  if (typeof window === "undefined") return {};
  const result: Record<string, InstalledPack> = {};
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key?.startsWith(LS_KEY_PREFIX)) {
      try {
        const raw = JSON.parse(localStorage.getItem(key) ?? "");
        const packId = key.replace(LS_KEY_PREFIX, "");
        result[packId] = {
          id: packId,
          name: raw.packName ?? packId,
          description: "",
          modules: raw.modules ?? [],
          version: raw.version ?? "1.0.0",
          installedAt: raw.installedAt ?? new Date().toISOString(),
          hasUpdate: false,
        };
      } catch {
        // skip corrupt entries
      }
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function InstalledPacksView() {
  const [packs, setPacks] = useState<InstalledPack[]>([]);
  const [loading, setLoading] = useState(true);
  const [managePackId, setManagePackId] = useState<string | null>(null);
  const [managePack, setManagePack] = useState<InstalledPack | null>(null);

  // ---- Fetch installed packs ----
  const fetchPacks = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Record<string, unknown>[]>(
        "/api/verticals/installed"
      );

      // Merge server data with localStorage
      const stored = loadInstalledFromStorage();
      const merged: InstalledPack[] = [];
      const seenIds = new Set<string>();

      for (const item of data) {
        const id = item.id as string;
        seenIds.add(id);
        const local = stored[id];
        merged.push({
          id,
          name: item.name as string,
          description: (item.description as string) ?? "",
          modules: (item.modules as string[]) ?? [],
          version: local?.version ?? "1.0.0",
          installedAt: local?.installedAt ?? new Date().toISOString(),
          hasUpdate: Math.random() > 0.6, // STUB: simulate update availability
          latestVersion: "1.1.0",
        });
      }

      // Include localStorage-only entries (offline installs)
      for (const [id, pack] of Object.entries(stored)) {
        if (!seenIds.has(id)) {
          merged.push(pack);
        }
      }

      setPacks(merged);
    } catch {
      // Fall back to localStorage only
      const stored = loadInstalledFromStorage();
      setPacks(Object.values(stored));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPacks();
  }, [fetchPacks]);

  // ---- Open manage modal ----
  const openManage = (pack: InstalledPack) => {
    setManagePackId(pack.id);
    setManagePack(pack);
  };

  const handleUpdate = async (packId: string) => {
    try {
      await api.post("/api/verticals/install", { pack_id: packId });
      // Update localStorage version
      const key = `${LS_KEY_PREFIX}${packId}`;
      const raw = localStorage.getItem(key);
      if (raw) {
        const parsed = JSON.parse(raw);
        parsed.version = "1.1.0";
        localStorage.setItem(key, JSON.stringify(parsed));
      }
      await fetchPacks();
    } catch {
      // handle error
    }
  };

  const handleUninstalled = () => {
    setManagePackId(null);
    setManagePack(null);
    fetchPacks();
  };

  // ---- Render ----
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <svg
          className="animate-spin h-6 w-6 text-blue-500"
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
      </div>
    );
  }

  if (packs.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="mx-auto h-12 w-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
          <svg
            className="h-6 w-6 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
            />
          </svg>
        </div>
        <h3 className="text-sm font-medium text-gray-900">
          No packs installed
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          Browse the marketplace to install your first vertical pack.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {packs.map((pack) => (
          <div
            key={pack.id}
            className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900">
                {pack.name}
              </h3>
              <div className="flex items-center gap-1.5">
                <Badge variant="success">Installed</Badge>
                {pack.hasUpdate && (
                  <Badge variant="warning">Update Available</Badge>
                )}
              </div>
            </div>

            {/* Meta */}
            <div className="space-y-1 mb-4">
              <p className="text-xs text-gray-500">
                Version {pack.version}
              </p>
              <p className="text-xs text-gray-500">
                Installed{" "}
                {new Date(pack.installedAt).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              </p>
              <p className="text-xs text-gray-400">
                {pack.modules.length} module(s)
              </p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 border-t border-gray-100 pt-3">
              <button
                onClick={() => openManage(pack)}
                className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
              >
                Manage
              </button>
              {pack.hasUpdate && (
                <button
                  onClick={() => handleUpdate(pack.id)}
                  className="px-3 py-1.5 text-xs font-medium text-white bg-amber-500 hover:bg-amber-600 rounded-md transition-colors"
                >
                  Update to {pack.latestVersion}
                </button>
              )}
              <button
                onClick={() => openManage(pack)}
                className="px-3 py-1.5 text-xs font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded-md transition-colors ml-auto"
              >
                Uninstall
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Manage Modal */}
      {managePack && (
        <ManagePackModal
          isOpen={!!managePackId}
          onClose={() => {
            setManagePackId(null);
            setManagePack(null);
          }}
          pack={managePack}
          onUninstalled={handleUninstalled}
          onSaved={fetchPacks}
        />
      )}
    </>
  );
}
