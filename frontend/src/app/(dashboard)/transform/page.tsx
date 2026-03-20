"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import axios from "axios";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TransformStep {
  id: string;
  op: string;
  params: Record<string, number | string>;
}

interface TransformResult {
  audio: string; // base64 wav
  format: string;
  original_duration_s: number;
  output_duration_s: number;
  operations_applied: string[];
  processing_time_ms: number;
}

const OP_OPTIONS = [
  { value: "denoise", label: "Denoise" },
  { value: "silence", label: "Remove Silence" },
  { value: "pitch", label: "Pitch Shift" },
  { value: "stretch", label: "Time Stretch" },
  { value: "loudness", label: "Normalize Loudness" },
  { value: "eq", label: "Equalizer" },
  { value: "enhance", label: "Speech Enhance" },
] as const;

const DEFAULT_PARAMS: Record<string, Record<string, number | string>> = {
  denoise: {},
  silence: { threshold_db: -40, min_silence_ms: 500 },
  pitch: { semitones: 0 },
  stretch: { rate: 1.0 },
  loudness: { target_lufs: -14 },
  eq: { preset: "flat" },
  enhance: {},
};

const PRESETS: Record<string, TransformStep[]> = {
  podcast: [{ id: "1", op: "enhance", params: {} }],
  voice: [
    { id: "1", op: "denoise", params: {} },
    { id: "2", op: "loudness", params: { target_lufs: -14 } },
    { id: "3", op: "eq", params: { preset: "voice" } },
  ],
  music: [
    { id: "1", op: "loudness", params: { target_lufs: -14 } },
    { id: "2", op: "eq", params: { preset: "music" } },
  ],
};

// ---------------------------------------------------------------------------
// Waveform canvas
// ---------------------------------------------------------------------------

function Waveform({ audioData, label }: { audioData: Float32Array | null; label: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#1e293b";
    ctx.fillRect(0, 0, w, h);

    if (!audioData || audioData.length === 0) {
      ctx.fillStyle = "#64748b";
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(label, w / 2, h / 2);
      return;
    }

    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 1;
    ctx.beginPath();
    const step = Math.max(1, Math.floor(audioData.length / w));
    for (let i = 0; i < w; i++) {
      const idx = i * step;
      let min = 1.0,
        max = -1.0;
      for (let j = 0; j < step && idx + j < audioData.length; j++) {
        const v = audioData[idx + j];
        if (v < min) min = v;
        if (v > max) max = v;
      }
      const yMin = ((1 - max) / 2) * h;
      const yMax = ((1 - min) / 2) * h;
      ctx.moveTo(i, yMin);
      ctx.lineTo(i, yMax);
    }
    ctx.stroke();

    ctx.fillStyle = "#94a3b8";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(label, 8, 16);
  }, [audioData, label]);

  return (
    <canvas
      ref={canvasRef}
      width={600}
      height={120}
      className="w-full rounded border border-slate-700"
    />
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function TransformPage() {
  const [tab, setTab] = useState<"audio" | "video">("audio");

  // Audio state
  const [file, setFile] = useState<File | null>(null);
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [originalData, setOriginalData] = useState<Float32Array | null>(null);
  const [resultData, setResultData] = useState<Float32Array | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [result, setResult] = useState<TransformResult | null>(null);
  const [steps, setSteps] = useState<TransformStep[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"preset" | "custom">("preset");

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Decode uploaded file for waveform display
  const handleFile = useCallback(async (f: File) => {
    setFile(f);
    setResult(null);
    setResultData(null);
    setResultUrl(null);
    setError(null);
    const url = URL.createObjectURL(f);
    setOriginalUrl(url);

    try {
      const arrayBuf = await f.arrayBuffer();
      const actx = new AudioContext();
      const decoded = await actx.decodeAudioData(arrayBuf);
      setOriginalData(decoded.getChannelData(0));
      actx.close();
    } catch {
      setOriginalData(null);
    }
  }, []);

  // Apply transforms
  const handleApply = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setResultData(null);
    setResultUrl(null);

    const form = new FormData();
    form.append("file", file);
    const ops = steps.map((s) => ({ op: s.op, params: s.params }));
    form.append("operations", JSON.stringify(ops));

    try {
      const resp = await axios.post<TransformResult>("/api/transform/audio", form);
      const data = resp.data;
      setResult(data);

      // Decode result for waveform
      const raw = atob(data.audio);
      const bytes = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
      const blob = new Blob([bytes], { type: "audio/wav" });
      setResultUrl(URL.createObjectURL(blob));

      try {
        const actx = new AudioContext();
        const decoded = await actx.decodeAudioData(bytes.buffer);
        setResultData(decoded.getChannelData(0));
        actx.close();
      } catch {
        setResultData(null);
      }
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err) && err.response?.data?.detail
          ? String(err.response.data.detail)
          : "Transform request failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [file, steps]);

  // Step management
  const addStep = () => {
    const op = "denoise";
    setSteps((prev) => [
      ...prev,
      { id: crypto.randomUUID(), op, params: { ...DEFAULT_PARAMS[op] } },
    ]);
  };

  const removeStep = (id: string) => setSteps((prev) => prev.filter((s) => s.id !== id));

  const updateStep = (id: string, field: string, value: string | number) => {
    setSteps((prev) =>
      prev.map((s) => {
        if (s.id !== id) return s;
        if (field === "op") {
          return { ...s, op: value as string, params: { ...DEFAULT_PARAMS[value as string] } };
        }
        return { ...s, params: { ...s.params, [field]: value } };
      }),
    );
  };

  const moveStep = (idx: number, dir: -1 | 1) => {
    setSteps((prev) => {
      const next = [...prev];
      const target = idx + dir;
      if (target < 0 || target >= next.length) return prev;
      [next[idx], next[target]] = [next[target], next[idx]];
      return next;
    });
  };

  const applyPreset = (key: string) => {
    setSteps(PRESETS[key].map((s) => ({ ...s, id: crypto.randomUUID() })));
    setMode("custom"); // allow editing after preset load
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Transform Studio</h1>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-700 pb-2">
        <button
          onClick={() => setTab("audio")}
          className={`px-4 py-2 rounded-t font-medium ${
            tab === "audio"
              ? "bg-sky-600 text-white"
              : "bg-slate-800 text-slate-400 hover:text-white"
          }`}
        >
          Audio Transform
        </button>
        <button
          onClick={() => setTab("video")}
          className={`px-4 py-2 rounded-t font-medium ${
            tab === "video"
              ? "bg-sky-600 text-white"
              : "bg-slate-800 text-slate-400 hover:text-white"
          }`}
        >
          Video Transform
        </button>
      </div>

      {/* Video tab placeholder */}
      {tab === "video" && (
        <div className="text-center text-slate-500 py-20 border border-dashed border-slate-700 rounded-lg">
          Video Transform will be available in WS-18.
        </div>
      )}

      {/* Audio tab */}
      {tab === "audio" && (
        <div className="space-y-6">
          {/* Upload zone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const f = e.dataTransfer.files?.[0];
              if (f) handleFile(f);
            }}
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center cursor-pointer hover:border-sky-500 transition"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
              }}
            />
            {file ? (
              <p className="text-sky-400">{file.name}</p>
            ) : (
              <p className="text-slate-400">
                Drag &amp; drop an audio file here, or click to browse
              </p>
            )}
          </div>

          {/* Original waveform */}
          <Waveform audioData={originalData} label="Original" />

          {/* Original player */}
          {originalUrl && (
            <audio controls src={originalUrl} className="w-full" />
          )}

          {/* Transform chain builder */}
          <div className="bg-slate-800 rounded-lg p-4 space-y-4">
            <h2 className="text-lg font-semibold text-white">Transform Chain</h2>

            {/* Preset buttons */}
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => applyPreset("podcast")}
                className="px-3 py-1.5 text-sm rounded bg-emerald-700 hover:bg-emerald-600 text-white"
              >
                Podcast Cleanup
              </button>
              <button
                onClick={() => applyPreset("voice")}
                className="px-3 py-1.5 text-sm rounded bg-emerald-700 hover:bg-emerald-600 text-white"
              >
                Voice Enhancement
              </button>
              <button
                onClick={() => applyPreset("music")}
                className="px-3 py-1.5 text-sm rounded bg-emerald-700 hover:bg-emerald-600 text-white"
              >
                Music Master
              </button>
              <button
                onClick={() => {
                  setSteps([]);
                  setMode("custom");
                }}
                className="px-3 py-1.5 text-sm rounded bg-slate-700 hover:bg-slate-600 text-white"
              >
                Custom
              </button>
            </div>

            {/* Steps list */}
            <div className="space-y-2">
              {steps.map((step, idx) => (
                <div
                  key={step.id}
                  className="flex items-center gap-2 bg-slate-900 rounded p-2 flex-wrap"
                >
                  <span className="text-slate-500 text-xs w-6">{idx + 1}.</span>
                  <select
                    value={step.op}
                    onChange={(e) => updateStep(step.id, "op", e.target.value)}
                    className="bg-slate-700 text-white text-sm rounded px-2 py-1"
                  >
                    {OP_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>

                  {/* Param editors */}
                  {Object.entries(step.params).map(([k, v]) => (
                    <label key={k} className="flex items-center gap-1 text-sm text-slate-300">
                      {k}:
                      {k === "preset" ? (
                        <select
                          value={String(v)}
                          onChange={(e) => updateStep(step.id, k, e.target.value)}
                          className="bg-slate-700 text-white text-sm rounded px-2 py-1 w-24"
                        >
                          {["flat", "voice", "music", "podcast"].map((p) => (
                            <option key={p} value={p}>
                              {p}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="number"
                          step="any"
                          value={v}
                          onChange={(e) =>
                            updateStep(step.id, k, parseFloat(e.target.value) || 0)
                          }
                          className="bg-slate-700 text-white text-sm rounded px-2 py-1 w-20"
                        />
                      )}
                    </label>
                  ))}

                  {/* Move / remove */}
                  <div className="ml-auto flex gap-1">
                    <button
                      onClick={() => moveStep(idx, -1)}
                      disabled={idx === 0}
                      className="text-slate-400 hover:text-white disabled:opacity-30 text-xs px-1"
                    >
                      Up
                    </button>
                    <button
                      onClick={() => moveStep(idx, 1)}
                      disabled={idx === steps.length - 1}
                      className="text-slate-400 hover:text-white disabled:opacity-30 text-xs px-1"
                    >
                      Down
                    </button>
                    <button
                      onClick={() => removeStep(step.id)}
                      className="text-red-400 hover:text-red-300 text-xs px-1"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={addStep}
              className="text-sm text-sky-400 hover:text-sky-300"
            >
              + Add Step
            </button>
          </div>

          {/* Apply button */}
          <button
            onClick={handleApply}
            disabled={!file || steps.length === 0 || loading}
            className="w-full py-3 rounded-lg font-semibold bg-sky-600 hover:bg-sky-500 text-white disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "Processing..." : "Apply Transforms"}
          </button>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          {/* Result */}
          {result && (
            <div className="space-y-4 bg-slate-800 rounded-lg p-4">
              <h2 className="text-lg font-semibold text-white">Result</h2>
              <div className="grid grid-cols-2 gap-4 text-sm text-slate-300">
                <div>Original: {result.original_duration_s.toFixed(2)}s</div>
                <div>Output: {result.output_duration_s.toFixed(2)}s</div>
                <div>Ops: {result.operations_applied.join(" -> ")}</div>
                <div>Time: {result.processing_time_ms.toFixed(0)}ms</div>
              </div>

              {/* Side-by-side waveforms */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Waveform audioData={originalData} label="Before" />
                <Waveform audioData={resultData} label="After" />
              </div>

              {/* Players */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {originalUrl && (
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Original</p>
                    <audio controls src={originalUrl} className="w-full" />
                  </div>
                )}
                {resultUrl && (
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Transformed</p>
                    <audio controls src={resultUrl} className="w-full" />
                  </div>
                )}
              </div>

              {/* Download */}
              {resultUrl && (
                <a
                  href={resultUrl}
                  download="transformed.wav"
                  className="inline-block px-4 py-2 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-medium"
                >
                  Download Transformed Audio
                </a>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
