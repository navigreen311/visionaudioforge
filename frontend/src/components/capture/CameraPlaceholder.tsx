"use client";

import { useState, useCallback } from "react";

interface VideoDevice {
  deviceId: string;
  label: string;
}

interface CameraPlaceholderProps {
  onDeviceSelect: (deviceId: string) => void;
}

export default function CameraPlaceholder({
  onDeviceSelect,
}: CameraPlaceholderProps) {
  const [devices, setDevices] = useState<VideoDevice[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestPermission = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      // Stop all tracks immediately — we only needed permission
      stream.getTracks().forEach((track) => track.stop());

      const allDevices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = allDevices
        .filter((d) => d.kind === "videoinput")
        .map((d) => ({
          deviceId: d.deviceId,
          label: d.label || `Camera ${d.deviceId.slice(0, 8)}`,
        }));

      setDevices(videoDevices);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to access camera";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[320px] gap-6 p-8">
      {/* Camera icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="64"
        height="64"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-gray-400"
      >
        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
        <circle cx="12" cy="13" r="4" />
      </svg>

      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-700">
          No camera connected
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          Click Start to connect your camera
        </p>
      </div>

      {error && (
        <p className="text-sm text-red-500 text-center max-w-xs">{error}</p>
      )}

      <button
        onClick={requestPermission}
        disabled={loading}
        className="px-5 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
      >
        {loading ? "Requesting..." : "Request Camera Permission"}
      </button>

      {/* Device list */}
      {devices.length > 0 && (
        <div className="w-full max-w-sm space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Available Cameras
          </p>
          {devices.map((device) => (
            <button
              key={device.deviceId}
              onClick={() => onDeviceSelect(device.deviceId)}
              className="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:border-brand-500 hover:bg-brand-50 transition-colors"
            >
              <span className="text-sm font-medium text-gray-800">
                {device.label}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
