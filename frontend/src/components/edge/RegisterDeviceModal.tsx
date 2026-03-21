'use client';

import { useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type DeviceType = 'jetson' | 'raspi' | 'x86' | 'mobile';

const DEVICE_TYPES: { value: DeviceType; label: string }[] = [
  { value: 'jetson', label: 'NVIDIA Jetson' },
  { value: 'raspi', label: 'Raspberry Pi' },
  { value: 'x86', label: 'x86 Server' },
  { value: 'mobile', label: 'Mobile Device' },
];

interface RegisteredDevice {
  id: string;
  name: string;
  device_type: string;
  location: string | null;
  api_key: string;
}

interface RegisterDeviceModalProps {
  open: boolean;
  onClose: () => void;
  onRegistered: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RegisterDeviceModal({
  open,
  onClose,
  onRegistered,
}: RegisterDeviceModalProps) {
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [deviceType, setDeviceType] = useState<DeviceType>('jetson');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RegisteredDevice | null>(null);
  const [copied, setCopied] = useState(false);

  if (!open) return null;

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('Device name is required');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/edge/devices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          location: location.trim() || null,
          device_type: deviceType,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data: RegisteredDevice = await res.json();
      setResult(data);
      onRegistered();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Registration failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopyKey = async () => {
    if (!result?.api_key) return;
    await navigator.clipboard.writeText(result.api_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setName('');
    setLocation('');
    setDeviceType('jetson');
    setError(null);
    setResult(null);
    setCopied(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">
          Register New Device
        </h2>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {result ? (
          /* Success view — show the API key once */
          <div className="space-y-4">
            <div className="rounded-lg border border-green-200 bg-green-50 p-4">
              <p className="text-sm font-medium text-green-800">
                Device registered successfully!
              </p>
              <p className="mt-1 text-xs text-green-600">
                Device ID: {result.id}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Key (shown once — save it now)
              </label>
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-xs font-mono text-gray-800 break-all">
                  {result.api_key}
                </code>
                <button
                  onClick={handleCopyKey}
                  className="shrink-0 rounded-lg border border-gray-300 px-3 py-2 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>

            <button
              onClick={handleClose}
              className="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
            >
              Done
            </button>
          </div>
        ) : (
          /* Registration form */
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Device Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., warehouse-cam-01"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g., Building A, Floor 2"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Device Type
              </label>
              <select
                value={deviceType}
                onChange={(e) => setDeviceType(e.target.value as DeviceType)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
              >
                {DEVICE_TYPES.map((dt) => (
                  <option key={dt.value} value={dt.value}>
                    {dt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={handleClose}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="flex-1 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? 'Registering...' : 'Register'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
