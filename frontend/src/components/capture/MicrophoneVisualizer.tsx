"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AudioDeviceInfo {
  deviceId: string;
  label: string;
}

type ChannelMode = "mono" | "stereo";

interface MicrophoneVisualizerProps {
  /** Optional callback when recording completes */
  onRecordingComplete?: (blob: Blob) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DB_MIN = -60;
const DB_MAX = 0;
const GREEN_THRESHOLD = -20; // dB
const AMBER_THRESHOLD = -6; // dB

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function MicrophoneVisualizer({
  onRecordingComplete,
}: MicrophoneVisualizerProps) {
  const router = useRouter();

  // Device & stream state
  const [devices, setDevices] = useState<AudioDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const [channelMode, setChannelMode] = useState<ChannelMode>("mono");
  const [sampleRate, setSampleRate] = useState<number>(0);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [streamActive, setStreamActive] = useState(false);

  // Recording state
  const [recording, setRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);

  // Refs for Web Audio / animation
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const rafRef = useRef<number>(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const levelCanvasRef = useRef<HTMLCanvasElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const peakDbRef = useRef<number>(DB_MIN);
  const peakDecayRef = useRef<number>(0);

  // -----------------------------------------------------------------------
  // Enumerate devices
  // -----------------------------------------------------------------------

  const enumerateAudioDevices = useCallback(async () => {
    try {
      const allDevices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs: AudioDeviceInfo[] = allDevices
        .filter((d) => d.kind === "audioinput")
        .map((d) => ({
          deviceId: d.deviceId,
          label: d.label || `Microphone (${d.deviceId.slice(0, 6)})`,
        }));
      setDevices(audioInputs);
      if (audioInputs.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(audioInputs[0].deviceId);
      }
    } catch {
      // Permission not yet granted; will populate after first getUserMedia.
    }
  }, [selectedDeviceId]);

  useEffect(() => {
    enumerateAudioDevices();
  }, [enumerateAudioDevices]);

  // -----------------------------------------------------------------------
  // Start / stop audio stream
  // -----------------------------------------------------------------------

  const stopStream = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    rafRef.current = 0;

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;

    sourceNodeRef.current?.disconnect();
    sourceNodeRef.current = null;
    analyserRef.current = null;

    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    setStreamActive(false);
    setRecording(false);
    setSampleRate(0);
  }, []);

  const startStream = useCallback(async () => {
    stopStream();
    setPermissionDenied(false);
    setRecordedBlob(null);

    try {
      const constraints: MediaStreamConstraints = {
        audio: {
          deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,
          channelCount: channelMode === "stereo" ? 2 : 1,
        },
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      // Re-enumerate now that permission is granted (labels become available)
      await enumerateAudioDevices();

      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      setSampleRate(audioCtx.sampleRate);

      const source = audioCtx.createMediaStreamSource(stream);
      sourceNodeRef.current = source;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.8;
      source.connect(analyser);
      analyserRef.current = analyser;

      setStreamActive(true);
      peakDbRef.current = DB_MIN;
      drawLoop();
    } catch (err: unknown) {
      const isDenied =
        err instanceof DOMException &&
        (err.name === "NotAllowedError" || err.name === "PermissionDeniedError");
      if (isDenied) {
        setPermissionDenied(true);
      }
    }
  }, [selectedDeviceId, channelMode, stopStream, enumerateAudioDevices]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopStream();
    };
  }, [stopStream]);

  // -----------------------------------------------------------------------
  // Visualization draw loop
  // -----------------------------------------------------------------------

  const drawLoop = useCallback(() => {
    const analyser = analyserRef.current;
    const waveCanvas = canvasRef.current;
    const lvlCanvas = levelCanvasRef.current;
    if (!analyser || !waveCanvas || !lvlCanvas) return;

    const waveCtx = waveCanvas.getContext("2d");
    const lvlCtx = lvlCanvas.getContext("2d");
    if (!waveCtx || !lvlCtx) return;

    // Capture references into local constants so the inner render closure
    // does not need non-null assertions on every animation frame.
    const _analyser = analyser;
    const _waveCanvas = waveCanvas;
    const _lvlCanvas = lvlCanvas;
    const _waveCtx = waveCtx;
    const _lvlCtx = lvlCtx;

    const bufferLength = _analyser.fftSize;
    const timeDomain = new Float32Array(bufferLength);

    function render() {
      rafRef.current = requestAnimationFrame(render);
      _analyser.getFloatTimeDomainData(timeDomain);

      // --- Oscilloscope waveform ---
      const w = _waveCanvas.width;
      const h = _waveCanvas.height;
      _waveCtx.fillStyle = "#111827";
      _waveCtx.fillRect(0, 0, w, h);

      _waveCtx.lineWidth = 2;
      _waveCtx.strokeStyle = "#3b82f6";
      _waveCtx.beginPath();

      const sliceWidth = w / bufferLength;
      let x = 0;
      for (let i = 0; i < bufferLength; i++) {
        const v = timeDomain[i];
        const y = ((v + 1) / 2) * h;
        if (i === 0) {
          _waveCtx.moveTo(x, y);
        } else {
          _waveCtx.lineTo(x, y);
        }
        x += sliceWidth;
      }
      _waveCtx.stroke();

      // Center line
      _waveCtx.strokeStyle = "rgba(255,255,255,0.15)";
      _waveCtx.lineWidth = 1;
      _waveCtx.beginPath();
      _waveCtx.moveTo(0, h / 2);
      _waveCtx.lineTo(w, h / 2);
      _waveCtx.stroke();

      // --- dB level bar ---
      let rms = 0;
      for (let i = 0; i < bufferLength; i++) {
        rms += timeDomain[i] * timeDomain[i];
      }
      rms = Math.sqrt(rms / bufferLength);
      const db = rms > 0 ? 20 * Math.log10(rms) : DB_MIN;
      const clampedDb = Math.max(DB_MIN, Math.min(DB_MAX, db));

      // Peak hold with decay
      if (clampedDb > peakDbRef.current) {
        peakDbRef.current = clampedDb;
        peakDecayRef.current = 0;
      } else {
        peakDecayRef.current += 1;
        if (peakDecayRef.current > 30) {
          peakDbRef.current = Math.max(clampedDb, peakDbRef.current - 0.5);
        }
      }

      const lw = _lvlCanvas.width;
      const lh = _lvlCanvas.height;
      _lvlCtx.fillStyle = "#1f2937";
      _lvlCtx.fillRect(0, 0, lw, lh);

      const normalised = (clampedDb - DB_MIN) / (DB_MAX - DB_MIN);
      const barHeight = normalised * lh;
      const barY = lh - barHeight;

      // Draw bar with color zones
      const greenH = ((GREEN_THRESHOLD - DB_MIN) / (DB_MAX - DB_MIN)) * lh;
      const amberH = ((AMBER_THRESHOLD - DB_MIN) / (DB_MAX - DB_MIN)) * lh;

      // Green zone
      const greenBarH = Math.min(barHeight, greenH);
      if (greenBarH > 0) {
        _lvlCtx.fillStyle = "#22c55e";
        _lvlCtx.fillRect(0, lh - greenBarH, lw, greenBarH);
      }

      // Amber zone
      if (barHeight > greenH) {
        const aH = Math.min(barHeight - greenH, amberH - greenH);
        if (aH > 0) {
          _lvlCtx.fillStyle = "#f59e0b";
          _lvlCtx.fillRect(0, lh - greenH - aH, lw, aH);
        }
      }

      // Red zone
      if (barHeight > amberH) {
        const rH = barHeight - amberH;
        _lvlCtx.fillStyle = "#ef4444";
        _lvlCtx.fillRect(0, barY, lw, rH);
      }

      // Peak indicator line
      const peakNorm = (peakDbRef.current - DB_MIN) / (DB_MAX - DB_MIN);
      const peakY = lh - peakNorm * lh;
      _lvlCtx.strokeStyle = "#ffffff";
      _lvlCtx.lineWidth = 2;
      _lvlCtx.beginPath();
      _lvlCtx.moveTo(0, peakY);
      _lvlCtx.lineTo(lw, peakY);
      _lvlCtx.stroke();

      // dB label
      _lvlCtx.fillStyle = "#e5e7eb";
      _lvlCtx.font = "11px monospace";
      _lvlCtx.textAlign = "center";
      _lvlCtx.fillText(`${clampedDb.toFixed(1)} dB`, lw / 2, lh - 4);
    }

    render();
  }, []);

  // -----------------------------------------------------------------------
  // Recording
  // -----------------------------------------------------------------------

  const handleStartRecording = useCallback(() => {
    const stream = streamRef.current;
    if (!stream) return;

    chunksRef.current = [];
    const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });

    recorder.ondataavailable = (e: BlobEvent) => {
      if (e.data.size > 0) {
        chunksRef.current.push(e.data);
      }
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      setRecordedBlob(blob);
      onRecordingComplete?.(blob);
    };

    recorder.start(250); // collect data every 250ms
    mediaRecorderRef.current = recorder;
    setRecording(true);
  }, [onRecordingComplete]);

  const handleStopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  }, []);

  // -----------------------------------------------------------------------
  // Send to Audio Analysis
  // -----------------------------------------------------------------------

  const handleSendToAnalysis = useCallback(() => {
    if (!recordedBlob) return;
    const blobUrl = URL.createObjectURL(recordedBlob);
    sessionStorage.setItem("capture_audio_blob", blobUrl);
    router.push("/audio?autoload=1");
  }, [recordedBlob, router]);

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="space-y-4">
      {/* Permission denied banner */}
      {permissionDenied && (
        <div className="flex items-center gap-2 px-4 py-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
          <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M18.364 5.636a9 9 0 11-12.728 0M12 9v4m0 4h.01"
            />
          </svg>
          <span>
            Microphone permission was denied. Please allow microphone access in your browser
            settings and reload the page.
          </span>
        </div>
      )}

      {/* Device selector + controls row */}
      <div className="flex flex-wrap items-end gap-4">
        {/* Device selector */}
        <div className="flex-1 min-w-[200px]">
          <label htmlFor="mic-device" className="block text-sm font-medium text-gray-700 mb-1">
            Input Device
          </label>
          <select
            id="mic-device"
            value={selectedDeviceId}
            onChange={(e) => setSelectedDeviceId(e.target.value)}
            disabled={streamActive}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-brand-500 focus:border-brand-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            {devices.length === 0 && (
              <option value="">No devices found</option>
            )}
            {devices.map((d) => (
              <option key={d.deviceId} value={d.deviceId}>
                {d.label}
              </option>
            ))}
          </select>
        </div>

        {/* Mono / Stereo toggle */}
        <div>
          <span className="block text-sm font-medium text-gray-700 mb-1">Channels</span>
          <div className="flex border border-gray-300 rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => setChannelMode("mono")}
              disabled={streamActive}
              className={`px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${
                channelMode === "mono"
                  ? "bg-brand-600 text-white"
                  : "bg-white text-gray-700 hover:bg-gray-50"
              }`}
            >
              Mono
            </button>
            <button
              type="button"
              onClick={() => setChannelMode("stereo")}
              disabled={streamActive}
              className={`px-3 py-2 text-sm font-medium transition-colors border-l border-gray-300 disabled:cursor-not-allowed ${
                channelMode === "stereo"
                  ? "bg-brand-600 text-white"
                  : "bg-white text-gray-700 hover:bg-gray-50"
              }`}
            >
              Stereo
            </button>
          </div>
        </div>

        {/* Sample rate display */}
        {sampleRate > 0 && (
          <div className="text-sm text-gray-500">
            <span className="font-medium">{sampleRate}</span> Hz
          </div>
        )}
      </div>

      {/* Start / Stop stream button */}
      <div className="flex items-center gap-3">
        {streamActive ? (
          <button
            onClick={stopStream}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
          >
            Stop Microphone
          </button>
        ) : (
          <button
            onClick={startStream}
            disabled={devices.length === 0}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-brand-600 hover:bg-brand-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Start Microphone
          </button>
        )}
      </div>

      {/* Visualizer area */}
      <div className="flex gap-3">
        {/* Oscilloscope waveform */}
        <canvas
          ref={canvasRef}
          width={640}
          height={160}
          className="flex-1 h-[160px] rounded-lg border border-gray-700 bg-gray-900"
        />

        {/* dB level bar */}
        <canvas
          ref={levelCanvasRef}
          width={48}
          height={160}
          className="w-12 h-[160px] rounded-lg border border-gray-700 bg-gray-800"
        />
      </div>

      {!streamActive && (
        <p className="text-sm text-gray-500 text-center">
          Click &quot;Start Microphone&quot; to begin monitoring audio levels.
        </p>
      )}

      {/* Record controls */}
      {streamActive && (
        <div className="flex items-center gap-3">
          {recording ? (
            <button
              onClick={handleStopRecording}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
            >
              <span className="w-3 h-3 rounded-full bg-white animate-pulse" />
              Stop Recording
            </button>
          ) : (
            <button
              onClick={handleStartRecording}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-700 transition-colors"
            >
              <span className="w-3 h-3 rounded-full bg-red-500" />
              Record
            </button>
          )}
        </div>
      )}

      {/* Send to Audio Analysis */}
      {recordedBlob && !recording && (
        <div className="flex items-center gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <span className="text-sm text-blue-700">
            Recording ready ({(recordedBlob.size / 1024).toFixed(1)} KB)
          </span>
          <button
            onClick={handleSendToAnalysis}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors"
          >
            Send to Audio Analysis
          </button>
        </div>
      )}
    </div>
  );
}
