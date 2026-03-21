"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AudioDevice {
  deviceId: string;
  label: string;
}

interface LiveStats {
  currentDb: number;
  peakDb: number;
  dominantFrequency: number;
  estimatedPitch: number;
}

type MicPermissionState = "prompt" | "denied" | "granted" | "error";

// ---------------------------------------------------------------------------
// Viridis-style 256-entry colormap (dark blue -> green -> yellow -> white)
// ---------------------------------------------------------------------------

function buildViridisLut(): Uint8Array {
  const lut = new Uint8Array(256 * 3);

  // Control points: index -> [r, g, b]
  const stops: [number, number, number, number][] = [
    [0, 13, 8, 135], // dark blue
    [64, 46, 80, 154], // blue-purple
    [96, 30, 130, 76], // teal
    [128, 53, 183, 41], // green
    [170, 163, 210, 30], // yellow-green
    [210, 249, 228, 33], // yellow
    [240, 253, 253, 150], // light yellow
    [255, 255, 255, 255], // white
  ];

  for (let i = 0; i < 256; i++) {
    let lower = stops[0];
    let upper = stops[stops.length - 1];
    for (let s = 0; s < stops.length - 1; s++) {
      if (i >= stops[s][0] && i <= stops[s + 1][0]) {
        lower = stops[s];
        upper = stops[s + 1];
        break;
      }
    }
    const range = upper[0] - lower[0] || 1;
    const t = (i - lower[0]) / range;
    lut[i * 3] = Math.round(lower[1] + t * (upper[1] - lower[1]));
    lut[i * 3 + 1] = Math.round(lower[2] + t * (upper[2] - lower[2]));
    lut[i * 3 + 2] = Math.round(lower[3] + t * (upper[3] - lower[3]));
  }
  return lut;
}

const VIRIDIS_LUT = buildViridisLut();

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const FFT_SIZE = 2048;
const CANVAS_WIDTH = 600;
const CANVAS_HEIGHT = 200;
const DRAW_INTERVAL_MS = 50;
const VISIBLE_SECONDS = 10;
const COLUMNS = Math.ceil((VISIBLE_SECONDS * 1000) / DRAW_INTERVAL_MS);
const AXIS_PADDING_LEFT = 40;
const AXIS_PADDING_BOTTOM = 20;
const DB_FLOOR = -100;
const DB_CEIL = 0;
const PEAK_HOLD_DECAY_MS = 1500;
const CAPTURE_DURATION_S = 5;

// ---------------------------------------------------------------------------
// Utility: autocorrelation-based pitch estimation
// ---------------------------------------------------------------------------

function estimatePitch(
  timeDomainData: Float32Array,
  sampleRate: number
): number {
  const size = timeDomainData.length;
  const halfSize = Math.floor(size / 2);

  // Find first zero crossing to skip the initial peak
  let firstZero = 0;
  for (let i = 1; i < halfSize; i++) {
    if (timeDomainData[i - 1] >= 0 && timeDomainData[i] < 0) {
      firstZero = i;
      break;
    }
  }

  // Autocorrelation
  let bestOffset = -1;
  let bestCorrelation = 0;
  const minPeriod = Math.floor(sampleRate / 5000); // up to 5kHz
  const maxPeriod = Math.floor(sampleRate / 50); // down to 50Hz

  for (
    let offset = Math.max(minPeriod, firstZero);
    offset < Math.min(maxPeriod, halfSize);
    offset++
  ) {
    let correlation = 0;
    for (let i = 0; i < halfSize; i++) {
      correlation += timeDomainData[i] * timeDomainData[i + offset];
    }
    if (correlation > bestCorrelation) {
      bestCorrelation = correlation;
      bestOffset = offset;
    }
  }

  if (bestOffset < 1) return 0;
  return sampleRate / bestOffset;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function LiveMicSpectrogram() {
  // State
  const [active, setActive] = useState(false);
  const [permissionState, setPermissionState] =
    useState<MicPermissionState>("prompt");
  const [devices, setDevices] = useState<AudioDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const [stats, setStats] = useState<LiveStats>({
    currentDb: DB_FLOOR,
    peakDb: DB_FLOOR,
    dominantFrequency: 0,
    estimatedPitch: 0,
  });
  const [capturing, setCapturing] = useState(false);
  const [captureStatus, setCaptureStatus] = useState<string>("");

  // Refs
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const spectrogramCanvasRef = useRef<HTMLCanvasElement>(null);
  const levelCanvasRef = useRef<HTMLCanvasElement>(null);
  const drawIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const rafRef = useRef<number>(0);
  const peakDbRef = useRef<number>(DB_FLOOR);
  const peakHoldTimeRef = useRef<number>(0);
  const peakHoldValueRef = useRef<number>(DB_FLOOR);

  // Spectrogram column buffer: each column is Uint8Array of freq bin count
  const spectrogramBufferRef = useRef<Uint8Array[]>([]);

  // ---------------------------------------------------------------------------
  // Enumerate audio devices
  // ---------------------------------------------------------------------------

  const enumerateAudioDevices = useCallback(async () => {
    try {
      const allDevices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = allDevices
        .filter((d) => d.kind === "audioinput")
        .map((d, i) => ({
          deviceId: d.deviceId,
          label: d.label || `Microphone ${i + 1}`,
        }));
      setDevices(audioInputs);
      if (audioInputs.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(audioInputs[0].deviceId);
      }
    } catch {
      // Devices may not be enumerable before permission grant
    }
  }, [selectedDeviceId]);

  useEffect(() => {
    enumerateAudioDevices();
  }, [enumerateAudioDevices]);

  // ---------------------------------------------------------------------------
  // Drawing: spectrogram column + level meter
  // ---------------------------------------------------------------------------

  const drawSpectrogram = useCallback(() => {
    const analyser = analyserRef.current;
    const canvas = spectrogramCanvasRef.current;
    const levelCanvas = levelCanvasRef.current;
    if (!analyser || !canvas || !levelCanvas) return;

    const ctx = canvas.getContext("2d");
    const levelCtx = levelCanvas.getContext("2d");
    if (!ctx || !levelCtx) return;

    const binCount = analyser.frequencyBinCount;
    const freqData = new Float32Array(binCount);
    const timeDomainData = new Float32Array(analyser.fftSize);

    analyser.getFloatFrequencyData(freqData);
    analyser.getFloatTimeDomainData(timeDomainData);

    // --- Compute stats ---
    let maxMag = -Infinity;
    let dominantBin = 0;
    for (let i = 0; i < binCount; i++) {
      if (freqData[i] > maxMag) {
        maxMag = freqData[i];
        dominantBin = i;
      }
    }

    const sampleRate = audioCtxRef.current?.sampleRate ?? 44100;
    const dominantFreq = (dominantBin * sampleRate) / analyser.fftSize;
    const currentDb = maxMag;
    const pitch = estimatePitch(timeDomainData, sampleRate);

    const now = performance.now();
    if (currentDb > peakDbRef.current) {
      peakDbRef.current = currentDb;
    }
    if (currentDb > peakHoldValueRef.current) {
      peakHoldValueRef.current = currentDb;
      peakHoldTimeRef.current = now;
    } else if (now - peakHoldTimeRef.current > PEAK_HOLD_DECAY_MS) {
      peakHoldValueRef.current = currentDb;
      peakHoldTimeRef.current = now;
    }

    setStats({
      currentDb: Math.max(currentDb, DB_FLOOR),
      peakDb: Math.max(peakDbRef.current, DB_FLOOR),
      dominantFrequency: dominantFreq,
      estimatedPitch: pitch,
    });

    // --- Build column (map dB to 0-255) ---
    const column = new Uint8Array(binCount);
    for (let i = 0; i < binCount; i++) {
      const db = Math.max(DB_FLOOR, Math.min(DB_CEIL, freqData[i]));
      const normalized = (db - DB_FLOOR) / (DB_CEIL - DB_FLOOR);
      column[i] = Math.round(normalized * 255);
    }

    const buffer = spectrogramBufferRef.current;
    buffer.push(column);
    if (buffer.length > COLUMNS) {
      buffer.shift();
    }

    // --- Draw spectrogram ---
    const plotW = canvas.width - AXIS_PADDING_LEFT;
    const plotH = canvas.height - AXIS_PADDING_BOTTOM;

    ctx.fillStyle = "#111827";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const colWidth = Math.max(1, plotW / COLUMNS);
    for (let c = 0; c < buffer.length; c++) {
      const col = buffer[c];
      const x = AXIS_PADDING_LEFT + c * colWidth;
      const rowHeight = plotH / col.length;

      for (let r = 0; r < col.length; r++) {
        const val = col[r];
        const ri = val * 3;
        ctx.fillStyle = `rgb(${VIRIDIS_LUT[ri]},${VIRIDIS_LUT[ri + 1]},${VIRIDIS_LUT[ri + 2]})`;
        // Frequency bins go low->high, canvas Y goes top->down, so invert
        const y = plotH - (r + 1) * rowHeight;
        ctx.fillRect(x, y, Math.ceil(colWidth), Math.ceil(rowHeight));
      }
    }

    // --- Axes labels ---
    ctx.fillStyle = "#9ca3af";
    ctx.font = "10px monospace";
    ctx.textAlign = "right";

    // Y axis: frequency labels
    const nyquist = sampleRate / 2;
    const freqLabels = [0, 2000, 4000, 6000, 8000, 10000, nyquist];
    for (const freq of freqLabels) {
      if (freq > nyquist) continue;
      const yPos = plotH - (freq / nyquist) * plotH;
      if (yPos < 8 || yPos > plotH - 2) continue;
      const label =
        freq >= 1000
          ? `${(freq / 1000).toFixed(0)}k`
          : freq.toString();
      ctx.fillText(label, AXIS_PADDING_LEFT - 4, yPos + 3);
    }

    // X axis: time labels
    ctx.textAlign = "center";
    const totalCols = buffer.length;
    for (let s = 0; s <= VISIBLE_SECONDS; s += 2) {
      const colIndex = Math.round((s / VISIBLE_SECONDS) * COLUMNS);
      if (colIndex > totalCols) continue;
      const xPos = AXIS_PADDING_LEFT + colIndex * colWidth;
      const timeLabel = `-${VISIBLE_SECONDS - s}s`;
      ctx.fillText(timeLabel, xPos, canvas.height - 4);
    }

    // --- Level meter ---
    const lw = levelCanvas.width;
    const lh = levelCanvas.height;
    levelCtx.fillStyle = "#111827";
    levelCtx.fillRect(0, 0, lw, lh);

    const dbNorm = Math.max(
      0,
      Math.min(1, (currentDb - DB_FLOOR) / (DB_CEIL - DB_FLOOR))
    );
    const peakNorm = Math.max(
      0,
      Math.min(
        1,
        (peakHoldValueRef.current - DB_FLOOR) / (DB_CEIL - DB_FLOOR)
      )
    );

    const barHeight = dbNorm * lh;
    const meterX = 8;
    const meterW = lw - 16;

    // Draw bar from bottom with green/amber/red zones
    for (let y = lh; y > lh - barHeight; y--) {
      const fraction = (lh - y) / lh;
      if (fraction < 0.6) {
        levelCtx.fillStyle = "#22c55e";
      } else if (fraction < 0.85) {
        levelCtx.fillStyle = "#f59e0b";
      } else {
        levelCtx.fillStyle = "#ef4444";
      }
      levelCtx.fillRect(meterX, y, meterW, 1);
    }

    // Peak hold indicator
    const peakY = lh - peakNorm * lh;
    levelCtx.fillStyle = "#ffffff";
    levelCtx.fillRect(meterX, peakY - 1, meterW, 2);

    // Zone labels
    levelCtx.fillStyle = "#6b7280";
    levelCtx.font = "9px monospace";
    levelCtx.textAlign = "center";
    const cx = lw / 2;
    levelCtx.fillText("0", cx, 12);
    levelCtx.fillText(`${DB_FLOOR}`, cx, lh - 4);
  }, []);

  // ---------------------------------------------------------------------------
  // Start / Stop mic
  // ---------------------------------------------------------------------------

  const startMic = useCallback(async () => {
    setPermissionState("prompt");
    setCaptureStatus("");
    try {
      const constraints: MediaStreamConstraints = {
        audio: selectedDeviceId
          ? { deviceId: { exact: selectedDeviceId } }
          : true,
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = FFT_SIZE;
      analyser.smoothingTimeConstant = 0.3;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Reset state
      spectrogramBufferRef.current = [];
      peakDbRef.current = DB_FLOOR;
      peakHoldValueRef.current = DB_FLOOR;

      setActive(true);
      setPermissionState("granted");

      // Re-enumerate devices (labels become available after permission grant)
      await enumerateAudioDevices();

      // Start draw interval
      drawIntervalRef.current = setInterval(drawSpectrogram, DRAW_INTERVAL_MS);
    } catch (err: unknown) {
      const state: MicPermissionState =
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "denied"
          : "error";
      setPermissionState(state);
    }
  }, [selectedDeviceId, drawSpectrogram, enumerateAudioDevices]);

  const stopMic = useCallback(() => {
    if (drawIntervalRef.current !== null) {
      clearInterval(drawIntervalRef.current);
      drawIntervalRef.current = null;
    }
    cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    audioCtxRef.current?.close();
    streamRef.current = null;
    audioCtxRef.current = null;
    analyserRef.current = null;
    setActive(false);
  }, []);

  // ---------------------------------------------------------------------------
  // Capture 5-second sample
  // ---------------------------------------------------------------------------

  const captureSample = useCallback(async () => {
    const stream = streamRef.current;
    if (!stream || capturing) return;

    setCapturing(true);
    setCaptureStatus("Recording 5 seconds...");

    const mediaRecorder = new MediaRecorder(stream);
    const chunks: Blob[] = [];

    mediaRecorder.ondataavailable = (e: BlobEvent) => {
      if (e.data.size > 0) chunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      setCaptureStatus("Uploading for analysis...");
      const blob = new Blob(chunks, { type: "audio/webm" });
      const formData = new FormData();
      formData.append("file", blob, "mic-capture.webm");
      formData.append(
        "operations",
        JSON.stringify(["waveform", "stft", "mfcc"])
      );

      try {
        const response = await fetch("/api/audio/analyze", {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }
        setCaptureStatus("Analysis complete! Check results panel.");
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : "Unknown error during upload";
        setCaptureStatus(`Upload failed: ${msg}`);
      } finally {
        setCapturing(false);
      }
    };

    mediaRecorder.start();
    setTimeout(() => {
      if (mediaRecorder.state === "recording") {
        mediaRecorder.stop();
      }
    }, CAPTURE_DURATION_S * 1000);
  }, [capturing]);

  // ---------------------------------------------------------------------------
  // Request permission (after denial)
  // ---------------------------------------------------------------------------

  const requestPermission = useCallback(async () => {
    setPermissionState("prompt");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
      setPermissionState("granted");
      await enumerateAudioDevices();
    } catch {
      setPermissionState("denied");
    }
  }, [enumerateAudioDevices]);

  // ---------------------------------------------------------------------------
  // Cleanup on unmount
  // ---------------------------------------------------------------------------

  useEffect(() => {
    return () => {
      if (drawIntervalRef.current !== null) {
        clearInterval(drawIntervalRef.current);
      }
      cancelAnimationFrame(rafRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      audioCtxRef.current?.close();
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  const formatHz = (hz: number): string => {
    if (hz >= 1000) return `${(hz / 1000).toFixed(2)} kHz`;
    return `${hz.toFixed(1)} Hz`;
  };

  const formatDb = (db: number): string => {
    if (db <= DB_FLOOR) return `${DB_FLOOR} dB`;
    return `${db.toFixed(1)} dB`;
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-4">
      {/* Permission denied banner */}
      {(permissionState === "denied" || permissionState === "error") && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-700 mb-2">
            {permissionState === "denied"
              ? "Microphone access was denied. Please allow microphone access in your browser settings, or click below to try again."
              : "An error occurred while accessing the microphone. Please check your device and try again."}
          </p>
          <Button variant="danger" size="sm" onClick={requestPermission}>
            Request Permission
          </Button>
        </div>
      )}

      {/* Controls row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Device selector */}
        {devices.length > 0 && (
          <select
            value={selectedDeviceId}
            onChange={(e) => setSelectedDeviceId(e.target.value)}
            disabled={active}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
          >
            {devices.map((d) => (
              <option key={d.deviceId} value={d.deviceId}>
                {d.label}
              </option>
            ))}
          </select>
        )}

        {/* Start / Stop toggle */}
        {!active ? (
          <Button onClick={startMic}>Start Mic</Button>
        ) : (
          <Button variant="danger" onClick={stopMic}>
            Stop Mic
          </Button>
        )}

        {active && (
          <>
            <span className="flex items-center gap-2 text-sm text-green-600">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
              </span>
              Live
            </span>

            <Button
              variant="secondary"
              size="sm"
              onClick={captureSample}
              loading={capturing}
              disabled={capturing}
            >
              Capture 5s Sample
            </Button>
          </>
        )}

        {captureStatus && (
          <span className="text-sm text-gray-600">{captureStatus}</span>
        )}
      </div>

      {/* Spectrogram + Level meter */}
      <Card title="STFT Spectrogram">
        <div className="flex gap-3">
          <div className="flex-1 min-w-0">
            <canvas
              ref={spectrogramCanvasRef}
              width={CANVAS_WIDTH}
              height={CANVAS_HEIGHT}
              className="w-full h-[200px] rounded-lg bg-gray-900"
            />
          </div>
          <div className="flex-shrink-0">
            <canvas
              ref={levelCanvasRef}
              width={40}
              height={CANVAS_HEIGHT}
              className="h-[200px] rounded-lg bg-gray-900"
            />
            <p className="text-center text-xs text-gray-500 mt-1">dB</p>
          </div>
        </div>
      </Card>

      {/* Stats row */}
      <Card title="Live Audio Stats">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Current dB
            </p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">
              {formatDb(stats.currentDb)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Peak dB
            </p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">
              {formatDb(stats.peakDb)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Dominant Freq
            </p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">
              {formatHz(stats.dominantFrequency)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Est. Pitch
            </p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">
              {stats.estimatedPitch > 0
                ? formatHz(stats.estimatedPitch)
                : "--"}
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
