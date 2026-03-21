'use client';

import { useState, useEffect, useCallback } from 'react';
import { PluginConfigModal } from './PluginConfigModal';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface InstalledPlugin {
  id: string;
  name: string;
  version: string;
  latest_version: string;
  category: string;
  description: string;
  author: string;
  status: 'active' | 'inactive' | 'error';
  used_in_pipelines: number;
  config: Record<string, string | number | boolean>;
  installed_at: string;
  updated_at: string;
}

interface InstalledListResponse {
  total_installed: number;
  updates_available: number;
  used_in_pipelines: number;
  plugins: InstalledPlugin[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUS_DOT: Record<string, string> = {
  active: 'bg-green-500',
  inactive: 'bg-gray-400',
  error: 'bg-red-500',
};

const STATUS_LABEL: Record<string, string> = {
  active: 'Active',
  inactive: 'Inactive',
  error: 'Error',
};

const CATEGORY_COLORS: Record<string, string> = {
  vision: 'bg-purple-100 text-purple-700',
  audio: 'bg-blue-100 text-blue-700',
  transform: 'bg-green-100 text-green-700',
  pipeline_node: 'bg-yellow-100 text-yellow-700',
  integration: 'bg-pink-100 text-pink-700',
  analytics: 'bg-indigo-100 text-indigo-700',
  model: 'bg-red-100 text-red-700',
};

// ---------------------------------------------------------------------------
// Seed data (fallback when backend is unreachable)
// ---------------------------------------------------------------------------

function seedData(): InstalledListResponse {
  const now = new Date().toISOString();
  const plugins: InstalledPlugin[] = [
    {
      id: 'seed-1',
      name: 'YOLO Detector',
      version: '1.2.0',
      latest_version: '1.3.0',
      category: 'vision',
      description: 'Object detection with YOLOv8',
      author: 'VAF Team',
      status: 'active',
      used_in_pipelines: 3,
      config: { confidence_threshold: 0.65, nms_iou: 0.45 },
      installed_at: now,
      updated_at: now,
    },
    {
      id: 'seed-2',
      name: 'Whisper Transcriber',
      version: '2.0.0',
      latest_version: '2.0.0',
      category: 'audio',
      description: 'Speech-to-text with Whisper',
      author: 'VAF Team',
      status: 'active',
      used_in_pipelines: 2,
      config: { language: 'en', beam_size: 5 },
      installed_at: now,
      updated_at: now,
    },
    {
      id: 'seed-3',
      name: 'Slack Notifier',
      version: '1.0.0',
      latest_version: '1.0.0',
      category: 'integration',
      description: 'Send alerts to Slack',
      author: 'VAF Team',
      status: 'inactive',
      used_in_pipelines: 0,
      config: { webhook_url: '', channel: '#alerts' },
      installed_at: now,
      updated_at: now,
    },
  ];

  return {
    total_installed: plugins.length,
    updates_available: plugins.filter((p) => p.version !== p.latest_version).length,
    used_in_pipelines: plugins.filter((p) => p.used_in_pipelines > 0).length,
    plugins,
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function InstalledTab() {
  const [data, setData] = useState<InstalledListResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Modal state
  const [configPlugin, setConfigPlugin] = useState<InstalledPlugin | null>(null);
  const [uninstallPlugin, setUninstallPlugin] = useState<InstalledPlugin | null>(null);

  // Fetch installed plugins
  const fetchInstalled = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/marketplace/installed');
      if (!res.ok) throw new Error('fetch failed');
      const json: InstalledListResponse = await res.json();
      setData(json);
    } catch {
      setData(seedData());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInstalled();
  }, [fetchInstalled]);

  // Handlers
  const handleSaveConfig = async (
    pluginId: string,
    config: Record<string, string | number | boolean>,
  ) => {
    try {
      await fetch(`/api/marketplace/plugins/${pluginId}/config`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config }),
      });
    } catch {
      // swallow — optimistic update
    }
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        plugins: prev.plugins.map((p) =>
          p.id === pluginId ? { ...p, config, updated_at: new Date().toISOString() } : p,
        ),
      };
    });
    setConfigPlugin(null);
  };

  const handleConfirmUninstall = async (pluginId: string) => {
    try {
      await fetch(`/api/marketplace/plugins/${pluginId}`, { method: 'DELETE' });
    } catch {
      // swallow
    }
    setData((prev) => {
      if (!prev) return prev;
      const plugins = prev.plugins.filter((p) => p.id !== pluginId);
      return {
        total_installed: plugins.length,
        updates_available: plugins.filter((p) => p.version !== p.latest_version).length,
        used_in_pipelines: plugins.filter((p) => p.used_in_pipelines > 0).length,
        plugins,
      };
    });
    setUninstallPlugin(null);
  };

  const handleUpdateAll = async () => {
    if (!data) return;
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        updates_available: 0,
        plugins: prev.plugins.map((p) => ({ ...p, version: p.latest_version })),
      };
    });
  };

  // Render
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (!data || data.plugins.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-gray-400">
        No plugins installed yet. Browse the marketplace to get started.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          <span className="font-semibold text-gray-900">{data.total_installed}</span> installed
          {data.updates_available > 0 && (
            <>
              {' \u00B7 '}
              <span className="font-semibold text-amber-600">{data.updates_available}</span>{' '}
              update{data.updates_available !== 1 ? 's' : ''}
            </>
          )}
          {' \u00B7 '}
          <span className="font-semibold text-gray-900">{data.used_in_pipelines}</span> used in
          pipelines
        </p>

        {data.updates_available > 0 && (
          <button
            onClick={handleUpdateAll}
            className="rounded-lg bg-amber-500 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-amber-600"
          >
            Update All
          </button>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-xs font-medium uppercase tracking-wider text-gray-500">
              <th className="px-4 py-3">Plugin</th>
              <th className="px-4 py-3">Version</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Used In</th>
              <th className="px-4 py-3">Last Updated</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.plugins.map((plugin) => {
              const hasUpdate = plugin.version !== plugin.latest_version;
              return (
                <tr key={plugin.id} className="hover:bg-gray-50 transition-colors">
                  {/* Plugin */}
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-gray-900">{plugin.name}</p>
                      <p className="text-xs text-gray-400">{plugin.author}</p>
                    </div>
                  </td>

                  {/* Version */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="text-gray-700">v{plugin.version}</span>
                    {hasUpdate && (
                      <span className="ml-2 inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                        v{plugin.latest_version}
                      </span>
                    )}
                  </td>

                  {/* Category */}
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                        CATEGORY_COLORS[plugin.category] ?? 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {plugin.category}
                    </span>
                  </td>

                  {/* Status */}
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-1.5">
                      <span
                        className={`inline-block h-2 w-2 rounded-full ${STATUS_DOT[plugin.status] ?? 'bg-gray-300'}`}
                      />
                      <span className="text-gray-700">
                        {STATUS_LABEL[plugin.status] ?? plugin.status}
                      </span>
                    </span>
                  </td>

                  {/* Used In */}
                  <td className="px-4 py-3">
                    {plugin.used_in_pipelines > 0 ? (
                      <span className="inline-flex items-center rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700">
                        {plugin.used_in_pipelines} pipeline{plugin.used_in_pipelines !== 1 ? 's' : ''}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">--</span>
                    )}
                  </td>

                  {/* Last Updated */}
                  <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                    {new Date(plugin.updated_at).toLocaleDateString()}
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setConfigPlugin(plugin)}
                        className="rounded-lg border border-gray-300 px-3 py-1 text-xs text-gray-600 transition-colors hover:bg-gray-50"
                      >
                        Configure
                      </button>
                      {hasUpdate && (
                        <button
                          onClick={() =>
                            setData((prev) => {
                              if (!prev) return prev;
                              return {
                                ...prev,
                                updates_available: Math.max(prev.updates_available - 1, 0),
                                plugins: prev.plugins.map((p) =>
                                  p.id === plugin.id
                                    ? { ...p, version: p.latest_version }
                                    : p,
                                ),
                              };
                            })
                          }
                          className="rounded-lg border border-amber-300 px-3 py-1 text-xs text-amber-700 transition-colors hover:bg-amber-50"
                        >
                          Update
                        </button>
                      )}
                      <button
                        onClick={() => setUninstallPlugin(plugin)}
                        className="rounded-lg border border-red-200 px-3 py-1 text-xs text-red-600 transition-colors hover:bg-red-50"
                      >
                        Uninstall
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Config Modal */}
      {configPlugin && (
        <PluginConfigModal
          plugin={configPlugin}
          onSave={(cfg) => handleSaveConfig(configPlugin.id, cfg)}
          onClose={() => setConfigPlugin(null)}
        />
      )}

      {/* Uninstall Confirm Dialog */}
      {uninstallPlugin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900">Uninstall Plugin</h3>
            <p className="mt-2 text-sm text-gray-600">
              Are you sure you want to uninstall{' '}
              <span className="font-semibold">{uninstallPlugin.name}</span>?
              {uninstallPlugin.used_in_pipelines > 0 && (
                <span className="mt-1 block text-amber-600">
                  This plugin is used in {uninstallPlugin.used_in_pipelines} pipeline
                  {uninstallPlugin.used_in_pipelines !== 1 ? 's' : ''}. Removing it may break
                  those pipelines.
                </span>
              )}
            </p>
            <div className="mt-5 flex justify-end gap-3">
              <button
                onClick={() => setUninstallPlugin(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleConfirmUninstall(uninstallPlugin.id)}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
              >
                Uninstall
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
