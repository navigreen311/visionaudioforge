'use client';

import { useCallback, useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type DeviceStatus = 'online' | 'offline' | 'updating' | 'idle';

interface Device {
  id: string;
  name: string;
  location: string | null;
  device_type: string;
  model_deployed: string | null;
  model_version: string | null;
  latest_version: string | null;
  status: DeviceStatus;
  last_heartbeat: number;
}

const STATUS_STYLES: Record<DeviceStatus, string> = {
  online: 'bg-green-100 text-green-700',
  offline: 'bg-red-100 text-red-700',
  updating: 'bg-blue-100 text-blue-700 animate-pulse',
  idle: 'bg-gray-100 text-gray-500',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DeviceFleet() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmUpdate, setConfirmUpdate] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/edge/devices`);
      if (!res.ok) throw new Error(await res.text());
      const data: Device[] = await res.json();
      setDevices(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load devices');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  const handlePushUpdate = async (deviceId: string) => {
    setUpdating(deviceId);
    setConfirmUpdate(null);
    try {
      const res = await fetch(`${API}/api/edge/devices/${deviceId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(await res.text());
      await fetchDevices();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Update push failed');
    } finally {
      setUpdating(null);
    }
  };

  const handleRemove = async (deviceId: string) => {
    try {
      const res = await fetch(`${API}/api/edge/devices/${deviceId}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error(await res.text());
      setDevices((prev) => prev.filter((d) => d.id !== deviceId));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Remove failed');
    }
  };

  const formatLastSeen = (ts: number) => {
    const diff = Math.floor(Date.now() / 1000 - ts);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return new Date(ts * 1000).toLocaleDateString();
  };

  const isOutdated = (d: Device) =>
    d.model_version !== null &&
    d.latest_version !== null &&
    d.model_version !== d.latest_version;

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">Device Fleet</h2>
        <button
          onClick={fetchDevices}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            Dismiss
          </button>
        </div>
      )}

      {loading ? (
        <p className="text-sm text-gray-400">Loading devices...</p>
      ) : devices.length === 0 ? (
        <p className="text-sm text-gray-400">
          No devices registered. Use the Register Device button to add one.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="px-3 py-2 text-left font-medium text-gray-600">
                  Device Name
                </th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">
                  Location
                </th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">
                  Model Deployed
                </th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">
                  Version
                </th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">
                  Status
                </th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">
                  Last Seen
                </th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {devices.map((device) => {
                const status = (device.status ?? 'idle') as DeviceStatus;
                const outdated = isOutdated(device);
                return (
                  <tr
                    key={device.id}
                    className="border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="px-3 py-2 font-medium text-gray-800">
                      {device.name}
                    </td>
                    <td className="px-3 py-2 text-gray-600">
                      {device.location ?? '-'}
                    </td>
                    <td className="px-3 py-2 text-gray-600">
                      {device.model_deployed ?? '-'}
                    </td>
                    <td className="px-3 py-2">
                      <span className="text-gray-700">
                        {device.model_version ?? '-'}
                      </span>
                      {outdated && (
                        <span className="ml-2 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                          Update available
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-500'
                        }`}
                      >
                        {status.charAt(0).toUpperCase() + status.slice(1)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-600">
                      {formatLastSeen(device.last_heartbeat)}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        {/* Push Update with confirmation */}
                        {confirmUpdate === device.id ? (
                          <span className="flex items-center gap-1">
                            <span className="text-xs text-gray-500">
                              Confirm?
                            </span>
                            <button
                              onClick={() => handlePushUpdate(device.id)}
                              disabled={updating === device.id}
                              className="text-xs font-medium text-green-600 hover:underline disabled:opacity-50"
                            >
                              {updating === device.id ? 'Pushing...' : 'Yes'}
                            </button>
                            <button
                              onClick={() => setConfirmUpdate(null)}
                              className="text-xs text-gray-400 hover:underline"
                            >
                              No
                            </button>
                          </span>
                        ) : (
                          <button
                            onClick={() => setConfirmUpdate(device.id)}
                            className="text-xs text-brand-600 hover:underline"
                          >
                            Push Update
                          </button>
                        )}
                        <button
                          onClick={() =>
                            window.open(
                              `${API}/api/edge/devices/${device.id}/logs`,
                              '_blank',
                            )
                          }
                          className="text-xs text-blue-600 hover:underline"
                        >
                          View Logs
                        </button>
                        <button
                          onClick={() => handleRemove(device.id)}
                          className="text-xs text-red-500 hover:underline"
                        >
                          Remove
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
    </section>
  );
}
