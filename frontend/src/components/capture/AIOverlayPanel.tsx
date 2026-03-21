"use client";

import {
  useState,
  useCallback,
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
} from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface OverlaySettings {
  objectDetection: boolean;
  motionHeatmap: boolean;
  ocrText: boolean;
  opticalFlow: boolean;
  analysisMode: "low-latency" | "high-accuracy";
  confidenceThreshold: number;
}

interface Detection {
  bbox: [number, number, number, number];
  class_name: string;
  confidence: number;
}

interface OCRRegion {
  text: string;
  bbox: [number, number, number, number];
  confidence?: number;
}

interface MotionVector {
  x: number;
  y: number;
  dx: number;
  dy: number;
}

export interface AnalyzeFrameResponse {
  detections: Detection[];
  ocr_regions: OCRRegion[];
  motion_vectors: MotionVector[];
}

export interface AIOverlayPanelHandle {
  /** Supply a video element for automatic frame capture. */
  attachVideo: (video: HTMLVideoElement) => void;
  /** Detach and stop frame capture. */
  detachVideo: () => void;
}

interface AIOverlayPanelProps {
  onSettingsChange?: (settings: OverlaySettings) => void;
  /** API base URL. Defaults to http://localhost:8001 */
  apiBaseUrl?: string;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULT_SETTINGS: OverlaySettings = {
  objectDetection: false,
  motionHeatmap: false,
  ocrText: false,
  opticalFlow: false,
  analysisMode: "low-latency",
  confidenceThreshold: 50,
};

const API_BASE = "http://localhost:8001";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildOverlayList(s: OverlaySettings): string[] {
  const list: string[] = [];
  if (s.objectDetection) list.push("detection");
  if (s.motionHeatmap) list.push("motion");
  if (s.ocrText) list.push("ocr");
  if (s.opticalFlow) list.push("optical_flow");
  return list;
}

function hasActiveOverlay(s: OverlaySettings): boolean {
  return s.objectDetection || s.motionHeatmap || s.ocrText || s.opticalFlow;
}

/** Capture a video frame as a base64 string (no data-url prefix). */
function captureFrameB64(
  video: HTMLVideoElement,
  canvas: HTMLCanvasElement
): string | null {
  if (video.readyState < 2) return null;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  ctx.drawImage(video, 0, 0);
  const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
  // strip the "data:image/jpeg;base64," prefix
  return dataUrl.split(",")[1] ?? null;
}

// ---------------------------------------------------------------------------
// Drawing helpers
// ---------------------------------------------------------------------------

const DETECTION_COLOR = "#00FF88";
const OCR_COLOR = "#FF9900";

function drawResults(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  data: AnalyzeFrameResponse
) {
  ctx.clearRect(0, 0, width, height);

  // -- Detections (bounding boxes) --
  for (const det of data.detections) {
    const [x, y, w, h] = det.bbox;
    ctx.strokeStyle = DETECTION_COLOR;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);

    const label = `${det.class_name} ${(det.confidence * 100).toFixed(0)}%`;
    ctx.font = "bold 12px monospace";
    const metrics = ctx.measureText(label);
    const labelH = 16;

    ctx.fillStyle = DETECTION_COLOR;
    ctx.fillRect(x, y - labelH, metrics.width + 8, labelH);

    ctx.fillStyle = "#000";
    ctx.fillText(label, x + 4, y - 4);
  }

  // -- OCR regions --
  for (const region of data.ocr_regions) {
    const [x, y, w, h] = region.bbox;
    ctx.strokeStyle = OCR_COLOR;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.strokeRect(x, y, w, h);
    ctx.setLineDash([]);

    const text =
      region.text.length > 40 ? region.text.slice(0, 37) + "..." : region.text;
    ctx.font = "11px monospace";
    const metrics = ctx.measureText(text);
    const labelH = 14;

    ctx.fillStyle = "rgba(0,0,0,0.7)";
    ctx.fillRect(x, y + h, metrics.width + 8, labelH + 2);

    ctx.fillStyle = OCR_COLOR;
    ctx.fillText(text, x + 4, y + h + labelH - 2);
  }
}

// ---------------------------------------------------------------------------
// ToggleSwitch sub-component
// ---------------------------------------------------------------------------

function ToggleSwitch({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between py-2 cursor-pointer group">
      <span className="text-sm font-medium text-gray-200 group-hover:text-white transition-colors">
        {label}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[#185FA5] focus:ring-offset-2 focus:ring-offset-gray-900 ${
          checked ? "bg-[#185FA5]" : "bg-gray-600"
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
            checked ? "translate-x-4" : "translate-x-0"
          }`}
        />
      </button>
    </label>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const AIOverlayPanel = forwardRef<AIOverlayPanelHandle, AIOverlayPanelProps>(
  function AIOverlayPanel({ onSettingsChange, apiBaseUrl }, ref) {
    const [collapsed, setCollapsed] = useState(false);
    const [settings, setSettings] = useState<OverlaySettings>(DEFAULT_SETTINGS);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [latestResult, setLatestResult] =
      useState<AnalyzeFrameResponse | null>(null);

    // Refs
    const videoRef = useRef<HTMLVideoElement | null>(null);
    const scratchCanvasRef = useRef<HTMLCanvasElement | null>(null);
    const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const frameCountRef = useRef(0);
    const settingsRef = useRef(settings);
    const baseUrl = apiBaseUrl ?? API_BASE;

    // Keep settingsRef in sync
    useEffect(() => {
      settingsRef.current = settings;
    }, [settings]);

    // -----------------------------------------------------------------------
    // Settings updater
    // -----------------------------------------------------------------------
    const updateSettings = useCallback(
      (patch: Partial<OverlaySettings>) => {
        setSettings((prev) => {
          const next = { ...prev, ...patch };
          onSettingsChange?.(next);
          return next;
        });
      },
      [onSettingsChange]
    );

    // -----------------------------------------------------------------------
    // API call
    // -----------------------------------------------------------------------
    const analyzeFrame = useCallback(
      async (frameB64: string) => {
        const s = settingsRef.current;
        const overlays = buildOverlayList(s);
        if (overlays.length === 0) return;

        setLoading(true);
        setError(null);

        try {
          const res = await fetch(`${baseUrl}/api/capture/analyze-frame`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              frame_b64: frameB64,
              overlays,
              threshold: s.confidenceThreshold / 100,
            }),
          });

          if (!res.ok) {
            const detail = await res.text();
            throw new Error(`API ${res.status}: ${detail}`);
          }

          const data: AnalyzeFrameResponse = await res.json();
          setLatestResult(data);

          // Draw on overlay canvas
          const canvas = overlayCanvasRef.current;
          const video = videoRef.current;
          if (canvas && video) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext("2d");
            if (ctx) {
              drawResults(ctx, canvas.width, canvas.height, data);
            }
          }
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : "Analysis failed";
          setError(msg);
        } finally {
          setLoading(false);
        }
      },
      [baseUrl]
    );

    // -----------------------------------------------------------------------
    // Frame capture loop
    // -----------------------------------------------------------------------
    const startLoop = useCallback(() => {
      // Clear any existing interval
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }

      const s = settingsRef.current;
      if (!hasActiveOverlay(s) || !videoRef.current) return;

      // Create scratch canvas once
      if (!scratchCanvasRef.current) {
        scratchCanvasRef.current = document.createElement("canvas");
      }

      // Low-latency: ~6 fps (every 5th frame @ 30fps ~ 167ms)
      // High-accuracy: ~30 fps (every frame ~ 33ms)
      const intervalMs = s.analysisMode === "low-latency" ? 167 : 33;

      frameCountRef.current = 0;

      intervalRef.current = setInterval(() => {
        frameCountRef.current += 1;
        const currentSettings = settingsRef.current;

        // In low-latency mode, only process every 5th tick
        if (
          currentSettings.analysisMode === "low-latency" &&
          frameCountRef.current % 5 !== 0
        ) {
          return;
        }

        if (!hasActiveOverlay(currentSettings)) return;

        const video = videoRef.current;
        const scratch = scratchCanvasRef.current;
        if (!video || !scratch) return;

        const b64 = captureFrameB64(video, scratch);
        if (b64) {
          analyzeFrame(b64);
        }
      }, intervalMs);
    }, [analyzeFrame]);

    const stopLoop = useCallback(() => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      // Clear overlay canvas
      const canvas = overlayCanvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext("2d");
        ctx?.clearRect(0, 0, canvas.width, canvas.height);
      }
      setLatestResult(null);
    }, []);

    // Restart loop when settings change
    useEffect(() => {
      if (hasActiveOverlay(settings) && videoRef.current) {
        startLoop();
      } else {
        stopLoop();
      }
    }, [
      settings.objectDetection,
      settings.motionHeatmap,
      settings.ocrText,
      settings.opticalFlow,
      settings.analysisMode,
      settings.confidenceThreshold,
      startLoop,
      stopLoop,
    ]);

    // Clean up on unmount
    useEffect(() => {
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }, []);

    // -----------------------------------------------------------------------
    // Imperative handle
    // -----------------------------------------------------------------------
    useImperativeHandle(ref, () => ({
      attachVideo(video: HTMLVideoElement) {
        videoRef.current = video;
        if (hasActiveOverlay(settingsRef.current)) {
          startLoop();
        }
      },
      detachVideo() {
        stopLoop();
        videoRef.current = null;
      },
    }));

    // -----------------------------------------------------------------------
    // Summary counts
    // -----------------------------------------------------------------------
    const detectionCount = latestResult?.detections.length ?? 0;
    const ocrCount = latestResult?.ocr_regions.length ?? 0;
    const anyActive = hasActiveOverlay(settings);

    // -----------------------------------------------------------------------
    // Render
    // -----------------------------------------------------------------------
    return (
      <>
        {/* Canvas overlay — positioned absolutely over the video feed */}
        <canvas
          ref={overlayCanvasRef}
          className="absolute inset-0 w-full h-full pointer-events-none"
          style={{ zIndex: 20 }}
        />

        {/* Panel */}
        <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
          {/* Header */}
          <button
            type="button"
            onClick={() => setCollapsed((prev) => !prev)}
            className="w-full flex items-center justify-between px-4 py-3 bg-gray-800 hover:bg-gray-750 transition-colors"
          >
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-white tracking-wide uppercase">
                AI Overlay
              </h3>
              {anyActive && (
                <span className="flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-green-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                </span>
              )}
              {loading && (
                <span className="text-[10px] text-blue-400 font-mono">
                  analyzing...
                </span>
              )}
            </div>
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${
                collapsed ? "-rotate-90" : "rotate-0"
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          {/* Collapsible Body */}
          {!collapsed && (
            <div className="px-4 py-3 space-y-4">
              {/* Feature Toggles */}
              <div className="space-y-1">
                <ToggleSwitch
                  label="Object Detection"
                  checked={settings.objectDetection}
                  onChange={(v) => updateSettings({ objectDetection: v })}
                />
                <ToggleSwitch
                  label="Motion Heatmap"
                  checked={settings.motionHeatmap}
                  onChange={(v) => updateSettings({ motionHeatmap: v })}
                />
                <ToggleSwitch
                  label="OCR Text"
                  checked={settings.ocrText}
                  onChange={(v) => updateSettings({ ocrText: v })}
                />
                <ToggleSwitch
                  label="Optical Flow"
                  checked={settings.opticalFlow}
                  onChange={(v) => updateSettings({ opticalFlow: v })}
                />
              </div>

              {/* Divider */}
              <div className="border-t border-gray-700" />

              {/* Analysis Mode */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Analysis Mode
                </span>
                <div className="flex rounded-lg overflow-hidden border border-gray-700">
                  <button
                    type="button"
                    onClick={() =>
                      updateSettings({ analysisMode: "low-latency" })
                    }
                    className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
                      settings.analysisMode === "low-latency"
                        ? "bg-[#185FA5] text-white"
                        : "bg-gray-800 text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    Low Latency
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      updateSettings({ analysisMode: "high-accuracy" })
                    }
                    className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
                      settings.analysisMode === "high-accuracy"
                        ? "bg-[#185FA5] text-white"
                        : "bg-gray-800 text-gray-400 hover:text-gray-200"
                    }`}
                  >
                    High Accuracy
                  </button>
                </div>
                <p className="text-[11px] text-gray-500">
                  {settings.analysisMode === "low-latency"
                    ? "Analyzes every 5th frame for faster performance"
                    : "Analyzes every frame for maximum accuracy"}
                </p>
              </div>

              {/* Divider */}
              <div className="border-t border-gray-700" />

              {/* Confidence Threshold */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Confidence Threshold
                  </span>
                  <span className="text-sm font-mono font-bold text-[#185FA5]">
                    {settings.confidenceThreshold}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={1}
                  value={settings.confidenceThreshold}
                  onChange={(e) =>
                    updateSettings({
                      confidenceThreshold: Number(e.target.value),
                    })
                  }
                  className="w-full h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-[#185FA5]"
                />
                <div className="flex justify-between text-[10px] text-gray-600">
                  <span>0%</span>
                  <span>50%</span>
                  <span>100%</span>
                </div>
              </div>

              {/* Divider */}
              <div className="border-t border-gray-700" />

              {/* Status / Results Summary */}
              <div className="space-y-1">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Live Results
                </span>
                {!anyActive && (
                  <p className="text-xs text-gray-500 italic">
                    Enable an overlay to start analysis
                  </p>
                )}
                {anyActive && !latestResult && !error && (
                  <p className="text-xs text-gray-500 italic">
                    Waiting for frames...
                  </p>
                )}
                {anyActive && latestResult && (
                  <div className="flex gap-3 text-xs">
                    {settings.objectDetection && (
                      <span className="text-green-400">
                        {detectionCount} detection
                        {detectionCount !== 1 ? "s" : ""}
                      </span>
                    )}
                    {settings.ocrText && (
                      <span className="text-orange-400">
                        {ocrCount} text region{ocrCount !== 1 ? "s" : ""}
                      </span>
                    )}
                  </div>
                )}
                {error && (
                  <p className="text-xs text-red-400 truncate" title={error}>
                    {error}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </>
    );
  }
);

export default AIOverlayPanel;
