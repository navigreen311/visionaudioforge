"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import SourceSwitcher, {
  type SourceType,
} from "@/components/capture/SourceSwitcher";
import CaptureControls from "@/components/capture/CaptureControls";
import LiveFeedPanel from "@/components/capture/LiveFeedPanel";
import AudioMeter from "@/components/capture/AudioMeter";

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

type ConnectionStatus = "disconnected" | "connecting" | "connected";

export default function CapturePage() {
  const [activeSource, setActiveSource] = useState<SourceType>("camera");
  const [isCapturing, setIsCapturing] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [frameCount, setFrameCount] = useState(0);
  const [fps, setFps] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);

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
      process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    const ws = new WebSocket(`${wsUrl}/ws/live/stream/${sessionId}`);

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
      } else {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
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

  const handleSnapshot = useCallback(() => {
    // Create a download link from current video frame
    const video = document.querySelector("video");
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    const link = document.createElement("a");
    link.download = `snapshot-${Date.now()}.jpg`;
    link.href = canvas.toDataURL("image/jpeg", 0.95);
    link.click();
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live Capture</h1>
          <p className="text-gray-500 text-sm mt-1">
            Capture video, screen, or audio for real-time AI analysis
          </p>
        </div>
        <CaptureControls
          isCapturing={isCapturing}
          onStart={startCapture}
          onStop={stopCapture}
          onSnapshot={handleSnapshot}
        />
      </div>

      {/* Source Tabs */}
      <SourceSwitcher activeSource={activeSource} onChange={handleSourceChange} />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Feed / Audio Panel */}
        <div className="lg:col-span-2">
          {activeSource === "microphone" ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-sm font-medium text-gray-700 mb-4">
                Audio Monitor
              </h3>
              <AudioMeter stream={stream} />
            </div>
          ) : (
            <LiveFeedPanel
              sourceType={activeSource}
              stream={stream}
              analysisResult={analysisResult}
              onFrame={handleFrame}
            />
          )}

          {!isCapturing && activeSource !== "microphone" && (
            <div className="flex items-center justify-center bg-gray-900 rounded-lg" style={{ aspectRatio: "16/9" }}>
              <p className="text-gray-400">
                Click <span className="font-medium text-white">Start</span> to begin {activeSource} capture
              </p>
            </div>
          )}
        </div>

        {/* Sidebar — Stats & Analysis */}
        <div className="space-y-4">
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
        </div>
      </div>
    </div>
  );
}
