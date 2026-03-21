"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import Modal from "@/components/ui/Modal";
import type { StreamSourceType, AddStreamPayload } from "@/lib/api";
import { addStream } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type SourceKind = "webcam" | "screen" | "rtsp" | "phone";

interface AIToggles {
  objectDetection: boolean;
  motionDetection: boolean;
  ocr: boolean;
  audioAnalysis: boolean;
}

interface AddStreamModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStreamAdded?: () => void;
}

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const SOURCE_OPTIONS: {
  kind: SourceKind;
  label: string;
  apiType: StreamSourceType;
  icon: React.ReactNode;
}[] = [
  {
    kind: "webcam",
    label: "Webcam",
    apiType: "camera",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    kind: "screen",
    label: "Screen",
    apiType: "screen",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    kind: "rtsp",
    label: "RTSP",
    apiType: "rtsp",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.858 15.355-5.858 21.213 0" />
      </svg>
    ),
  },
  {
    kind: "phone",
    label: "Phone",
    apiType: "camera",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    ),
  },
];

const ZONES = [
  "Lobby",
  "Parking Lot",
  "Warehouse",
  "Server Room",
  "Perimeter",
  "Loading Dock",
  "Office",
  "Rooftop",
];

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function AddStreamModal({
  isOpen,
  onClose,
  onStreamAdded,
}: AddStreamModalProps) {
  const [sourceKind, setSourceKind] = useState<SourceKind>("webcam");
  const [name, setName] = useState("");
  const [zone, setZone] = useState(ZONES[0]);
  const [rtspUrl, setRtspUrl] = useState("");
  const [rtspUser, setRtspUser] = useState("");
  const [rtspPass, setRtspPass] = useState("");
  const [webcamDeviceId, setWebcamDeviceId] = useState("");
  const [webcamDevices, setWebcamDevices] = useState<MediaDeviceInfo[]>([]);
  const [aiToggles, setAiToggles] = useState<AIToggles>({
    objectDetection: true,
    motionDetection: true,
    ocr: false,
    audioAnalysis: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const previewRef = useRef<HTMLVideoElement>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  /* ---- Enumerate webcam devices ---- */
  const enumerateDevices = useCallback(async () => {
    try {
      // Need to request permission first to get labels
      const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
      tempStream.getTracks().forEach((t) => t.stop());

      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = devices.filter((d) => d.kind === "videoinput");
      setWebcamDevices(videoInputs);
      if (videoInputs.length > 0 && !webcamDeviceId) {
        setWebcamDeviceId(videoInputs[0].deviceId);
      }
    } catch {
      // Permission denied or no devices
      setWebcamDevices([]);
    }
  }, [webcamDeviceId]);

  useEffect(() => {
    if (isOpen && sourceKind === "webcam") {
      enumerateDevices();
    }
  }, [isOpen, sourceKind, enumerateDevices]);

  /* ---- Clean up preview stream on close ---- */
  const stopPreview = useCallback(() => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    if (previewRef.current) {
      previewRef.current.srcObject = null;
    }
  }, []);

  useEffect(() => {
    if (!isOpen) {
      stopPreview();
    }
    return () => stopPreview();
  }, [isOpen, stopPreview]);

  /* ---- Start webcam preview ---- */
  const startWebcamPreview = useCallback(async () => {
    stopPreview();
    if (!webcamDeviceId) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: { exact: webcamDeviceId } },
      });
      mediaStreamRef.current = stream;
      if (previewRef.current) {
        previewRef.current.srcObject = stream;
      }
    } catch {
      // ignore preview failures
    }
  }, [webcamDeviceId, stopPreview]);

  /* ---- Start screen share preview ---- */
  const startScreenPreview = useCallback(async () => {
    stopPreview();
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      mediaStreamRef.current = stream;
      if (previewRef.current) {
        previewRef.current.srcObject = stream;
      }
      // User may stop sharing via browser UI
      stream.getVideoTracks()[0]?.addEventListener("ended", () => {
        stopPreview();
      });
    } catch {
      // user cancelled or not supported
    }
  }, [stopPreview]);

  /* ---- Toggle AI feature ---- */
  const toggleAI = (key: keyof AIToggles) => {
    setAiToggles((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  /* ---- Reset form ---- */
  const resetForm = useCallback(() => {
    setName("");
    setZone(ZONES[0]);
    setRtspUrl("");
    setRtspUser("");
    setRtspPass("");
    setSourceKind("webcam");
    setAiToggles({
      objectDetection: true,
      motionDetection: true,
      ocr: false,
      audioAnalysis: false,
    });
    setError("");
  }, []);

  /* ---- Submit handler ---- */
  const handleConnect = async () => {
    if (!name.trim()) {
      setError("Stream name is required");
      return;
    }
    if (sourceKind === "rtsp" && !rtspUrl.trim()) {
      setError("RTSP URL is required");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const sourceOpt = SOURCE_OPTIONS.find((s) => s.kind === sourceKind);
      const payload: AddStreamPayload = {
        name: name.trim(),
        source_type: sourceOpt?.apiType ?? "camera",
      };

      if (sourceKind === "rtsp") {
        let fullUrl = rtspUrl.trim();
        if (rtspUser) {
          const urlObj = new URL(fullUrl);
          urlObj.username = rtspUser;
          urlObj.password = rtspPass;
          fullUrl = urlObj.toString();
        }
        payload.url = fullUrl;
      }

      await addStream(payload);
      stopPreview();
      resetForm();
      onStreamAdded?.();
      onClose();
    } catch {
      setError("Failed to connect stream. Check configuration and try again.");
    } finally {
      setLoading(false);
    }
  };

  /* ---- Per-source config section ---- */
  const renderSourceConfig = () => {
    switch (sourceKind) {
      case "webcam":
        return (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Camera Device
              </label>
              <select
                value={webcamDeviceId}
                onChange={(e) => setWebcamDeviceId(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                {webcamDevices.length === 0 && (
                  <option value="">No cameras detected</option>
                )}
                {webcamDevices.map((d) => (
                  <option key={d.deviceId} value={d.deviceId}>
                    {d.label || `Camera ${d.deviceId.slice(0, 8)}`}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={startWebcamPreview}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Preview Camera
            </button>
          </div>
        );

      case "screen":
        return (
          <div className="space-y-3">
            <p className="text-sm text-gray-500">
              Click below to select a screen, window, or tab to share.
            </p>
            <button
              type="button"
              onClick={startScreenPreview}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Select Display Source
            </button>
          </div>
        );

      case "rtsp":
        return (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                RTSP URL
              </label>
              <input
                type="text"
                value={rtspUrl}
                onChange={(e) => setRtspUrl(e.target.value)}
                placeholder="rtsp://192.168.1.100:554/stream1"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Username <span className="text-gray-400">(optional)</span>
                </label>
                <input
                  type="text"
                  value={rtspUser}
                  onChange={(e) => setRtspUser(e.target.value)}
                  placeholder="admin"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password <span className="text-gray-400">(optional)</span>
                </label>
                <input
                  type="password"
                  value={rtspPass}
                  onChange={(e) => setRtspPass(e.target.value)}
                  placeholder="********"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>
            </div>
          </div>
        );

      case "phone":
        return (
          <div className="flex flex-col items-center gap-3 py-4">
            <div className="h-40 w-40 rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 flex items-center justify-center">
              <div className="text-center">
                <svg
                  className="h-12 w-12 text-gray-300 mx-auto mb-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"
                  />
                </svg>
                <span className="text-xs text-gray-400">QR Code</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 text-center max-w-xs">
              Scan this QR code with the VisonAudioForge mobile app to stream
              from your phone camera.
            </p>
          </div>
        );
    }
  };

  const aiToggleItems: { key: keyof AIToggles; label: string; description: string }[] = [
    { key: "objectDetection", label: "Object Detection", description: "Detect & classify objects" },
    { key: "motionDetection", label: "Motion Detection", description: "Track movement patterns" },
    { key: "ocr", label: "OCR", description: "Read text in frame" },
    { key: "audioAnalysis", label: "Audio Analysis", description: "Analyze audio stream" },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add Stream"
      footer={
        <>
          <button
            onClick={() => {
              stopPreview();
              resetForm();
              onClose();
            }}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConnect}
            disabled={loading}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {loading ? "Connecting..." : "Connect Stream"}
          </button>
        </>
      }
    >
      <div className="space-y-5">
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* ---- Source type buttons ---- */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Source Type
          </label>
          <div className="grid grid-cols-4 gap-2">
            {SOURCE_OPTIONS.map((opt) => (
              <button
                key={opt.kind}
                type="button"
                onClick={() => {
                  stopPreview();
                  setSourceKind(opt.kind);
                }}
                className={`flex flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-sm font-medium transition-colors ${
                  sourceKind === opt.kind
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {opt.icon}
                <span className="text-xs">{opt.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* ---- Per-source config ---- */}
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          {renderSourceConfig()}
        </div>

        {/* ---- Preview area (webcam/screen) ---- */}
        {(sourceKind === "webcam" || sourceKind === "screen") && (
          <div className="rounded-lg overflow-hidden bg-black aspect-video">
            <video
              ref={previewRef}
              autoPlay
              muted
              playsInline
              className="h-full w-full object-contain"
            />
          </div>
        )}

        {/* ---- Name field ---- */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Stream Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Front Entrance Camera"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* ---- Zone dropdown ---- */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Zone
          </label>
          <select
            value={zone}
            onChange={(e) => setZone(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            {ZONES.map((z) => (
              <option key={z} value={z}>
                {z}
              </option>
            ))}
          </select>
        </div>

        {/* ---- AI Toggles ---- */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            AI Features
          </label>
          <div className="grid grid-cols-2 gap-2">
            {aiToggleItems.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => toggleAI(item.key)}
                className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-left transition-colors ${
                  aiToggles[item.key]
                    ? "border-brand-500 bg-brand-50"
                    : "border-gray-200 bg-white"
                }`}
              >
                <div
                  className={`h-4 w-4 rounded-sm border flex items-center justify-center flex-shrink-0 ${
                    aiToggles[item.key]
                      ? "border-brand-600 bg-brand-600"
                      : "border-gray-300"
                  }`}
                >
                  {aiToggles[item.key] && (
                    <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-700 block leading-tight">
                    {item.label}
                  </span>
                  <span className="text-xs text-gray-400 leading-tight">
                    {item.description}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
}
