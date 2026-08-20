"use client";

import { API_BASE_URL, wsBaseUrl } from "@/lib/api";

import { useState, useRef, useCallback, useEffect } from "react";
import SourceSwitcher, {
  type SourceType,
} from "@/components/capture/SourceSwitcher";
import CaptureControls from "@/components/capture/CaptureControls";
import LiveFeedPanel from "@/components/capture/LiveFeedPanel";
import MultiCamGrid, {
  type CaptureSource,
} from "@/components/capture/MultiCamGrid";
import RTSPConnectPanel from "@/components/capture/RTSPConnectPanel";
import RecordingControls from "@/components/capture/RecordingControls";
import AIOverlayPanel, {
  type OverlaySettings,
} from "@/components/capture/AIOverlayPanel";
import StreamHealthBar, {
  type StreamStats,
} from "@/components/capture/StreamHealthBar";
import SnapshotStrip, {
  type Snapshot,
} from "@/components/capture/SnapshotStrip";
import MicrophoneVisualizer from "@/components/capture/MicrophoneVisualizer";
import CameraPlaceholder from "@/components/capture/CameraPlaceholder";
import AnalysisModeSelector, {
  type AnalysisMode,
} from "@/components/capture/AnalysisModeSelector";
import LiveResultsSidebar, {
  type AnalysisResults,
} from "@/components/capture/LiveResultsSidebar";
import CopilotInline from "@/components/capture/CopilotInline";
import { authenticatedWsUrl } from "@/lib/session";

interface AnalysisResult {
  frame_id: number;
  timestamp: string;
  analysis: {
    brightness: number;
    motion_detected: boolean;
    resolution: [number, number];
  };
  detections: { label: string; bbox: [number, number, number, number]; confidence: number }[];
}

interface RTSPInfo {
  url: string;
  width: number;
  height: number;
  fps: number;
  codec: string;
}

type ConnectionStatus = "disconnected" | "connecting" | "connected";

const API_BASE = API_BASE_URL;

export default function CapturePage() {
  const [activeSource, setActiveSource] = useState<SourceType>("camera");
  const [isCapturing, setIsCapturing] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [frameCount, setFrameCount] = useState(0);
  const [fps, setFps] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);

  // RTSP state
  const [rtspUrl, setRtspUrl] = useState("");
  const [rtspInfo, setRtspInfo] = useState<RTSPInfo | null>(null);
  const [rtspConnecting, setRtspConnecting] = useState(false);
  const [rtspError, setRtspError] = useState<string | null>(null);

  // Multi-cam state
  const [multiCamSources, setMultiCamSources] = useState<CaptureSource[]>([]);
  const [addSourceType, setAddSourceType] = useState("webcam");
  const [workspaceId] = useState("default");

  // Recording state
  const [recordingId, setRecordingId] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);

  // New component state
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("balanced");
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [overlaySettings, setOverlaySettings] = useState<OverlaySettings | null>(null);
  const [liveResults, setLiveResults] = useState<AnalysisResults | null>(null);
  const [selectedCameraDeviceId, setSelectedCameraDeviceId] = useState<string | undefined>(undefined);
  const [streamStats, setStreamStats] = useState<StreamStats>({
    fps: 0,
    latency: 0,
    bitrate: 0,
    droppedFrames: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const fpsCounterRef = useRef(0);
  const fpsIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCapture();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // FPS counter
  useEffect(() => {
    if (isCapturing) {
      fpsIntervalRef.current = setInterval(() => {
        setFps(fpsCounterRef.current);
        fpsCounterRef.current = 0;
      }, 1000);
    } else {
      if (fpsIntervalRef.current) clearInterval(fpsIntervalRef.current);
      setFps(0);
    }
    return () => {
      if (fpsIntervalRef.current) clearInterval(fpsIntervalRef.current);
    };
  }, [isCapturing]);

  const connectWebSocket = useCallback(() => {
    const sessionId = crypto.randomUUID();
    const wsUrl =
      wsBaseUrl();
    // The handshake is authenticated like every other request; a browser
    // WebSocket cannot send an Authorization header, so the token rides in the
    // query string. Read here rather than at module scope so it is the token
    // that is current when the socket actually opens.
    const ws = new WebSocket(
      authenticatedWsUrl(`${wsUrl}/ws/live/stream/${sessionId}`),
    );

    setConnectionStatus("connecting");

    ws.onopen = () => setConnectionStatus("connected");
    ws.onclose = () => setConnectionStatus("disconnected");
    ws.onerror = () => setConnectionStatus("disconnected");

    ws.onmessage = (event) => {
      try {
        const data: AnalysisResult = JSON.parse(event.data);
        setAnalysisResult(data);
        setFrameCount(data.frame_id);
        fpsCounterRef.current++;

        // Populate live results sidebar from analysis data
        setLiveResults({
          detections: data.detections.map((d) => ({
            label: d.label,
            confidence: d.confidence,
            bbox: [...d.bbox],
          })),
          ocr_regions: [],
          motion_vectors: data.analysis.motion_detected
            ? [{ direction: "detected", magnitude: 1 }]
            : [],
        });

        // Update stream stats
        setStreamStats((prev) => ({
          ...prev,
          fps: fpsCounterRef.current,
        }));
      } catch {
        // ignore parse errors
      }
    };

    wsRef.current = ws;
  }, []);

  const disconnectWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionStatus("disconnected");
  }, []);

  const startCapture = useCallback(async () => {
    try {
      let mediaStream: MediaStream;

      if (activeSource === "camera") {
        mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
      } else if (activeSource === "screen") {
        mediaStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      } else if (activeSource === "microphone") {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } else {
        // RTSP and multicam don't use browser MediaStream
        setIsCapturing(true);
        setFrameCount(0);
        setStartTime(Date.now());
        setAnalysisResult(null);
        return;
      }

      setStream(mediaStream);
      setIsCapturing(true);
      setFrameCount(0);
      setStartTime(Date.now());
      setAnalysisResult(null);

      if (activeSource !== "microphone") {
        connectWebSocket();
      }
    } catch (err) {
      console.error("Failed to start capture:", err);
    }
  }, [activeSource, connectWebSocket]);

  const stopCapture = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
    disconnectWebSocket();
    setIsCapturing(false);
    setStartTime(null);
  }, [stream, disconnectWebSocket]);

  const handleSnapshot = useCallback(async () => {
    // Client-side snapshot from video element
    const video = document.querySelector("video");
    if (video) {
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(video, 0, 0);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.95);

      // Download
      const link = document.createElement("a");
      link.download = `snapshot-${Date.now()}.jpg`;
      link.href = dataUrl;
      link.click();

      // Add to snapshot strip
      setSnapshots((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          dataUrl,
          timestamp: new Date().toISOString(),
        },
      ]);
    }

    // Also trigger server-side snapshot
    try {
      await fetch(`${API_BASE}/api/capture/snapshot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: "current" }),
      });
    } catch {
      // server snapshot is best-effort
    }
  }, []);

  const handleFrame = useCallback(
    (base64: string) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ frame: base64 }));
      }
    },
    []
  );

  const handleSourceChange = useCallback(
    (source: SourceType) => {
      if (isCapturing) stopCapture();
      setActiveSource(source);
    },
    [isCapturing, stopCapture]
  );

  // RTSP connect
  const handleRtspConnect = useCallback(async () => {
    if (!rtspUrl.trim()) return;
    setRtspConnecting(true);
    setRtspError(null);
    try {
      const res = await fetch(`${API_BASE}/api/capture/rtsp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: rtspUrl }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Connection failed");
      }
      const info: RTSPInfo = await res.json();
      setRtspInfo(info);
    } catch (err: unknown) {
      setRtspError(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setRtspConnecting(false);
    }
  }, [rtspUrl]);

  // Multi-cam: add source
  const handleAddSource = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/capture/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_id: workspaceId,
          source_type: addSourceType,
          config: {},
        }),
      });
      if (res.ok) {
        // Refresh sources
        const listRes = await fetch(
          `${API_BASE}/api/capture/sources?workspace_id=${workspaceId}`
        );
        if (listRes.ok) {
          const data = await listRes.json();
          setMultiCamSources(data.sources || []);
        }
      }
    } catch {
      // ignore
    }
  }, [workspaceId, addSourceType]);

  // Multi-cam: switch primary
  const handleSwitchSource = useCallback(
    async (sourceId: string) => {
      try {
        await fetch(`${API_BASE}/api/capture/sources/${sourceId}/switch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ workspace_id: workspaceId }),
        });
        // Refresh
        const listRes = await fetch(
          `${API_BASE}/api/capture/sources?workspace_id=${workspaceId}`
        );
        if (listRes.ok) {
          const data = await listRes.json();
          setMultiCamSources(data.sources || []);
        }
      } catch {
        // ignore
      }
    },
    [workspaceId]
  );

  // Multi-cam: remove source
  const handleRemoveSource = useCallback(
    async (sourceId: string) => {
      try {
        // Remove via switch then re-list (no dedicated DELETE endpoint for now)
        setMultiCamSources((prev) =>
          prev.filter((s) => s.source_id !== sourceId)
        );
      } catch {
        // ignore
      }
    },
    []
  );

  // Recording controls
  const handleRecordStart = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/capture/record/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: "current", fps: 30 }),
      });
      if (res.ok) {
        const data = await res.json();
        setRecordingId(data.recording_id);
        setIsRecording(true);
      }
    } catch {
      // ignore
    }
  }, []);

  const handleRecordStop = useCallback(async () => {
    if (!recordingId) return;
    try {
      await fetch(`${API_BASE}/api/capture/record/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recording_id: recordingId }),
      });
    } catch {
      // ignore
    } finally {
      setRecordingId(null);
      setIsRecording(false);
    }
  }, [recordingId]);

  // CopilotInline: grab current frame as base64 for AI chat
  const getFrameBase64 = useCallback(() => {
    const video = document.querySelector("video");
    if (!video) return null;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.8);
  }, []);

  // Camera device selection
  const handleDeviceSelect = useCallback((deviceId: string) => {
    setSelectedCameraDeviceId(deviceId);
  }, []);

  // Snapshot strip helpers
  const handleDeleteSnapshot = useCallback((id: string) => {
    setSnapshots((prev) => prev.filter((s) => s.id !== id));
  }, []);

  const handleClearAllSnapshots = useCallback(() => {
    setSnapshots([]);
  }, []);

  const elapsed = startTime ? Math.floor((Date.now() - startTime) / 1000) : 0;
  const minutes = Math.floor(elapsed / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (elapsed % 60).toString().padStart(2, "0");

  // Re-render timer
  useEffect(() => {
    if (!isCapturing) return;
    const id = setInterval(() => {
      // force re-render for elapsed timer
      setStartTime((prev) => prev);
    }, 1000);
    return () => clearInterval(id);
  }, [isCapturing]);

  // Load multi-cam sources on tab switch
  useEffect(() => {
    if (activeSource === "multicam") {
      fetch(`${API_BASE}/api/capture/sources?workspace_id=${workspaceId}`)
        .then((r) => r.json())
        .then((data) => setMultiCamSources(data.sources || []))
        .catch(() => {});
    }
  }, [activeSource, workspaceId]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live Capture</h1>
          <p className="text-gray-500 text-sm mt-1">
            Capture video, screen, audio, or RTSP streams for real-time AI analysis
          </p>
        </div>
        <div className="flex items-center gap-4">
          <AnalysisModeSelector
            value={analysisMode}
            onChange={setAnalysisMode}
          />
          <RecordingControls
            isCapturing={isCapturing}
            onRecordStart={handleRecordStart}
            onRecordStop={handleRecordStop}
            onSnapshot={handleSnapshot}
          />
          <CaptureControls
            isCapturing={isCapturing}
            onStart={startCapture}
            onStop={stopCapture}
            onSnapshot={handleSnapshot}
          />
        </div>
      </div>

      {/* Recording indicator */}
      {isRecording && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
          <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
          <span className="text-red-700 font-medium text-sm">
            Recording in progress...
          </span>
        </div>
      )}

      {/* Source Tabs */}
      <SourceSwitcher activeSource={activeSource} onChange={handleSourceChange} />

      {/* RTSP Tab Content */}
      {activeSource === "rtsp" && (
        <RTSPConnectPanel
          onConnect={(fullUrl) => {
            setRtspUrl(fullUrl);
            handleRtspConnect();
          }}
          onDisconnect={() => {
            setRtspInfo(null);
            setRtspError(null);
          }}
        />
      )}

      {/* Multi-Cam Tab Content */}
      {activeSource === "multicam" && (
        <div className="space-y-4">
          <MultiCamGrid
            sources={multiCamSources}
            onSourceClick={handleSwitchSource}
            onRemoveSource={handleRemoveSource}
          />
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Feed / Audio Panel */}
        <div className="lg:col-span-2 space-y-4">
          {activeSource === "microphone" ? (
            <MicrophoneVisualizer
              onRecordingComplete={(blob) => {
                // Download the recorded audio
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `recording-${Date.now()}.webm`;
                a.click();
                URL.revokeObjectURL(url);
              }}
            />
          ) : activeSource === "rtsp" || activeSource === "multicam" ? null : (
            <>
              {isCapturing ? (
                <LiveFeedPanel
                  sourceType={activeSource}
                  stream={stream}
                  analysisResult={analysisResult}
                  onFrame={handleFrame}
                />
              ) : (
                <CameraPlaceholder
                  onDeviceSelect={handleDeviceSelect}
                  selectedDeviceId={selectedCameraDeviceId}
                />
              )}
            </>
          )}

          {/* Stream Health Bar — shown when capturing non-audio sources */}
          {isCapturing && activeSource !== "microphone" && (
            <StreamHealthBar
              stats={streamStats}
              onReconnect={() => {
                disconnectWebSocket();
                connectWebSocket();
              }}
            />
          )}

          {/* Snapshot Strip */}
          <SnapshotStrip
            snapshots={snapshots}
            onCapture={handleSnapshot}
            onDelete={handleDeleteSnapshot}
            onClearAll={handleClearAllSnapshots}
          />
        </div>

        {/* Sidebar -- Stats, Analysis & Sources */}
        <div className="space-y-4">
          {/* AI Overlay Panel */}
          <AIOverlayPanel
            onSettingsChange={(settings) => setOverlaySettings(settings)}
            apiBaseUrl={API_BASE}
          />

          {/* Live Results Sidebar */}
          <LiveResultsSidebar
            results={liveResults}
            isLoading={isCapturing && !liveResults}
          />

          {/* Status Bar */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 space-y-3">
            <h3 className="text-sm font-medium text-gray-700">Session Status</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Connection</span>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      connectionStatus === "connected"
                        ? "bg-green-500"
                        : connectionStatus === "connecting"
                        ? "bg-yellow-500 animate-pulse"
                        : "bg-gray-400"
                    }`}
                  />
                  <span className="font-medium capitalize">{connectionStatus}</span>
                </div>
              </div>
              <div>
                <span className="text-gray-500">FPS</span>
                <p className="font-medium mt-0.5">{fps}</p>
              </div>
              <div>
                <span className="text-gray-500">Frames</span>
                <p className="font-medium mt-0.5">{frameCount}</p>
              </div>
              <div>
                <span className="text-gray-500">Duration</span>
                <p className="font-medium mt-0.5">
                  {isCapturing ? `${minutes}:${seconds}` : "--:--"}
                </p>
              </div>
            </div>
          </div>

          {/* Source List Sidebar */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 space-y-3">
            <h3 className="text-sm font-medium text-gray-700">Capture Sources</h3>
            <div className="flex gap-2">
              <select
                value={addSourceType}
                onChange={(e) => setAddSourceType(e.target.value)}
                className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
              >
                <option value="webcam">Webcam</option>
                <option value="screen">Screen</option>
                <option value="rtsp">RTSP</option>
                <option value="file">File</option>
              </select>
              <button
                onClick={handleAddSource}
                className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Add
              </button>
            </div>
            <ul className="space-y-1.5">
              {multiCamSources.map((s) => (
                <li
                  key={s.source_id}
                  className="flex items-center justify-between py-1.5 px-2 bg-gray-50 rounded-lg text-sm"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        s.status === "active" ? "bg-green-500" : "bg-gray-400"
                      }`}
                    />
                    <span className="font-medium">{s.source_type}</span>
                    {s.is_primary && (
                      <span className="text-[10px] bg-brand-100 text-brand-700 px-1.5 py-0.5 rounded">
                        PRIMARY
                      </span>
                    )}
                  </div>
                  <span className="text-gray-400 text-xs font-mono">
                    {s.source_id.slice(0, 8)}
                  </span>
                </li>
              ))}
              {multiCamSources.length === 0 && (
                <li className="text-gray-400 text-sm py-1">No sources added</li>
              )}
            </ul>
          </div>

          {/* Analysis Results */}
          {analysisResult && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 space-y-3">
              <h3 className="text-sm font-medium text-gray-700">
                Frame Analysis
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Brightness</span>
                  <span className="font-medium">
                    {analysisResult.analysis.brightness.toFixed(1)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-yellow-400 h-2 rounded-full transition-all"
                    style={{
                      width: `${(analysisResult.analysis.brightness / 255) * 100}%`,
                    }}
                  />
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Motion</span>
                  <span
                    className={`font-medium ${
                      analysisResult.analysis.motion_detected
                        ? "text-red-600"
                        : "text-green-600"
                    }`}
                  >
                    {analysisResult.analysis.motion_detected
                      ? "Detected"
                      : "None"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Resolution</span>
                  <span className="font-medium">
                    {analysisResult.analysis.resolution[0]}x
                    {analysisResult.analysis.resolution[1]}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Detections */}
          {analysisResult &&
            analysisResult.detections.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 space-y-3">
                <h3 className="text-sm font-medium text-gray-700">
                  Detections ({analysisResult.detections.length})
                </h3>
                <ul className="space-y-1 text-sm">
                  {analysisResult.detections.map((d, i) => (
                    <li
                      key={i}
                      className="flex justify-between py-1 border-b border-gray-50 last:border-0"
                    >
                      <span>{d.label}</span>
                      <span className="text-gray-500">
                        {(d.confidence * 100).toFixed(0)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

          {/* Copilot Inline Chat */}
          <CopilotInline getFrameBase64={getFrameBase64} />
        </div>
      </div>
    </div>
  );
}
