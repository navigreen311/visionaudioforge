'use client';

import { API_BASE_URL } from "@/lib/api";

import { useCallback, useEffect, useState } from 'react';

const API = API_BASE_URL;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ExportStatus = 'completed' | 'failed' | 'expired';

interface ExportRecord {
  id: string;
  model_id: string;
  format: string;
  created_at: number;
  file_size_mb: number;
  status: ExportStatus;
}

const STATUS_STYLES: Record<ExportStatus, string> = {
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  expired: 'bg-gray-100 text-gray-500',
};

const STATUS_LABELS: Record<ExportStatus, string> = {
  completed: 'Complete',
  failed: 'Failed',
  expired: 'Expired',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ExportHistory() {
  const [exports, setExports] = useState<ExportRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  const fetchExports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/edge/exports`);
      if (!res.ok) throw new Error(await res.text());
      const data: ExportRecord[] = await res.json();
      setExports(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load exports');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchExports();
  }, [fetchExports]);

  const handleRedownload = (exportId: string, format: string) => {
    window.open(
      `${API}/api/edge/exports/${exportId}/download?format=${format}`,
      '_blank',
    );
  };

  const handleReexport = async (record: ExportRecord) => {
    try {
      const res = await fetch(`${API}/api/edge/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_id: record.model_id,
          format: record.format,
          optimize: true,
          quantize: false,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      await fetchExports();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Re-export failed');
    }
  };

  const handleDelete = async (exportId: string) => {
    try {
      const res = await fetch(`${API}/api/edge/exports/${exportId}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error(await res.text());
      setExports((prev) => prev.filter((ex) => ex.id !== exportId));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Delete failed');
    }
  };

  const formatDate = (ts: number) => {
    return new Date(ts * 1000).toLocaleString();
  };

  return (
    <section className="rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Header / Collapse Toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex w-full items-center justify-between px-6 py-4 text-left"
      >
        <h2 className="text-lg font-semibold text-gray-800">Export History</h2>
        <svg
          className={`h-5 w-5 text-gray-400 transition-transform ${
            collapsed ? '' : 'rotate-180'
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {!collapsed && (
        <div className="px-6 pb-6">
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
              <button
                onClick={() => setError(null)}
                className="ml-2 underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {loading ? (
            <p className="text-sm text-gray-400">Loading exports...</p>
          ) : exports.length === 0 ? (
            <p className="text-sm text-gray-400">
              No exports yet. Export a model to see history here.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="px-3 py-2 text-left font-medium text-gray-600">
                      Model
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600">
                      Format
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600">
                      Date
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600">
                      File Size
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600">
                      Status
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {exports.map((record) => {
                    const status = (record.status ?? 'completed') as ExportStatus;
                    return (
                      <tr
                        key={record.id}
                        className="border-b border-gray-100 hover:bg-gray-50"
                      >
                        <td className="px-3 py-2 font-medium text-gray-800">
                          {record.model_id}
                        </td>
                        <td className="px-3 py-2 uppercase text-gray-700">
                          {record.format}
                        </td>
                        <td className="px-3 py-2 text-gray-600">
                          {formatDate(record.created_at)}
                        </td>
                        <td className="px-3 py-2 text-gray-600">
                          {record.file_size_mb} MB
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                              STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-500'
                            }`}
                          >
                            {STATUS_LABELS[status] ?? status}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex gap-2">
                            {status === 'completed' && (
                              <button
                                onClick={() =>
                                  handleRedownload(record.id, record.format)
                                }
                                className="text-xs text-brand-600 hover:underline"
                              >
                                Re-download
                              </button>
                            )}
                            <button
                              onClick={() => handleReexport(record)}
                              className="text-xs text-blue-600 hover:underline"
                            >
                              Re-export
                            </button>
                            <button
                              onClick={() => handleDelete(record.id)}
                              className="text-xs text-red-500 hover:underline"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
