"use client";

import { API_BASE_URL } from "@/lib/api";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import BeforeAfterViewer from "@/components/transform/BeforeAfterViewer";
import { saveToTransformHistory } from "@/components/transform/TransformHistory";
import type { TransformHistoryEntry } from "@/components/transform/TransformHistory";

// Dynamic imports for components created by other agents (with fallbacks)
const OperationControls = dynamic(
  () => import("@/components/transform/OperationControls"),
  { loading: () => <div className="animate-pulse h-20 bg-gray-100 rounded-lg" />, ssr: false },
);
const ProcessingProgress = dynamic(
  () => import("@/components/transform/ProcessingProgress"),
  { loading: () => null, ssr: false },
);
const AudioTransformStudio = dynamic(
  () => import("@/components/transform/AudioTransformStudio"),
  { loading: () => <div className="animate-pulse h-40 bg-gray-100 rounded-lg" />, ssr: false },
);
const BatchTransformTab = dynamic(
  () => import("@/components/transform/BatchTransformTab"),
  { loading: () => <div className="animate-pulse h-40 bg-gray-100 rounded-lg" />, ssr: false },
);
const PresetsTab = dynamic(
  () => import("@/components/transform/PresetsTab"),
  { loading: () => <div className="animate-pulse h-40 bg-gray-100 rounded-lg" />, ssr: false },
);
const TransformExportPanel = dynamic(
  () => import("@/components/transform/TransformExportPanel"),
  { loading: () => null, ssr: false },
);
const TransformHistory = dynamic(
  () => import("@/components/transform/TransformHistory"),
  { loading: () => null, ssr: false },
);

const API_BASE = API_BASE_URL;

type VideoMode = "background-remove" | "super-resolution" | "style" | "auto-crop" | "color-grade" | "subtitle" | "inpaint" | "smart-crop" | "interpolate" | "highlight";
type AudioMode = "denoise" | "silence-remove" | "pitch-shift" | "time-stretch" | "eq" | "chain" | "voice-convert" | "chapters" | "noise-profile" | "tts";

const BG_METHODS = ["threshold", "grabcut"] as const;
const STYLES = ["sketch", "edges", "cartoon", "oil_painting"] as const;
const ASPECTS = ["16:9", "4:3", "1:1", "9:16"] as const;
const EQ_PRESETS = ["flat", "voice", "music", "podcast"] as const;
const COLOR_GRADE_PRESETS = ["cinematic", "vintage", "high_contrast", "bw_dramatic"] as const;
const VOICE_PRESETS = ["male_deep", "female_high", "robotic", "whisper"] as const;
const SUBTITLE_POSITIONS = ["top", "center", "bottom"] as const;
const SMART_CROP_METHODS = ["center_of_mass", "face", "rule_of_thirds"] as const;

interface PresetInfo {
  description: string;
  operations: Array<Record<string, unknown>>;
}

export default function TransformPage() {
  // --- shared state ---
  const [tab, setTab] = useState<"audio" | "video" | "batch" | "presets">("video");
  const [mode, setMode] = useState<VideoMode>("background-remove");
  const [audioMode, setAudioMode] = useState<AudioMode>("denoise");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- source image ---
  const [srcFile, setSrcFile] = useState<File | null>(null);
  const [srcPreview, setSrcPreview] = useState<string | null>(null);

  // --- result ---
  const [resultB64, setResultB64] = useState<string | null>(null);
  const [meta, setMeta] = useState<Record<string, unknown> | null>(null);
  const [processingTimeMs, setProcessingTimeMs] = useState<number | null>(null);

  // Params emitted by OperationControls (see the TODO at its render site).
  const [operationParams, setOperationParams] = useState<Record<string, unknown>>({});
  void operationParams;

  // Track which dynamic components are available
  const [hasOperationControls, setHasOperationControls] = useState(false);
  const [hasTransformHistory, setHasTransformHistory] = useState(false);
  const [hasTransformExportPanel, setHasTransformExportPanel] = useState(false);

  useEffect(() => {
    import("@/components/transform/OperationControls").then(() => setHasOperationControls(true)).catch(() => {});
    import("@/components/transform/TransformHistory").then(() => setHasTransformHistory(true)).catch(() => {});
    import("@/components/transform/TransformExportPanel").then(() => setHasTransformExportPanel(true)).catch(() => {});
  }, []);

  // --- per-mode options ---
  const [bgMethod, setBgMethod] = useState<string>("threshold");
  const [srScale, setSrScale] = useState<number>(2);
  const [stylePreset, setStylePreset] = useState<string>("sketch");
  const [aspect, setAspect] = useState<string>("16:9");

  // --- advanced options ---
  const [colorGradePreset, setColorGradePreset] = useState<string>("cinematic");
  const [subtitleText, setSubtitleText] = useState<string>("");
  const [subtitlePosition, setSubtitlePosition] = useState<string>("bottom");
  const [voicePreset, setVoicePreset] = useState<string>("male_deep");
  const [chapterResult, setChapterResult] = useState<Record<string, unknown> | null>(null);
  const [noiseResult, setNoiseResult] = useState<Record<string, unknown> | null>(null);
  const [maskFile, setMaskFile] = useState<File | null>(null);
  const [smartCropSize, setSmartCropSize] = useState<string>("200x200");
  const [smartCropMethod, setSmartCropMethod] = useState<string>("center_of_mass");
  const [ttsText, setTtsText] = useState<string>("");
  const [ttsVoice, setTtsVoice] = useState<string>("default");
  const [fontScale, setFontScale] = useState<number>(1.0);

  // --- batch state ---
  const [batchFiles, setBatchFiles] = useState<File[]>([]);
  const [batchType, setBatchType] = useState<"audio" | "video">("video");
  const [batchOperation, setBatchOperation] = useState<string>("color_grade");
  const [batchParams, setBatchParams] = useState<string>('{"preset": "cinematic"}');
  const [batchResults, setBatchResults] = useState<Record<string, unknown> | null>(null);

  // --- presets state ---
  const [presets, setPresets] = useState<{ audio: Record<string, PresetInfo>; video: Record<string, PresetInfo> } | null>(null);

  const fileRef = useRef<HTMLInputElement>(null);
  const maskRef = useRef<HTMLInputElement>(null);
  const batchFileRef = useRef<HTMLInputElement>(null);

  // ---- load presets on mount ----
  useEffect(() => {
    fetch(`${API_BASE}/api/transform/presets`)
      .then((r) => r.json())
      .then((data) => setPresets(data))
      .catch(() => {});
  }, []);

  // ---- file select ----
  const onFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setSrcFile(file);
    setResultB64(null);
    setMeta(null);
    setError(null);
    if (file) {
      const reader = new FileReader();
      reader.onload = () => setSrcPreview(reader.result as string);
      reader.readAsDataURL(file);
    } else {
      setSrcPreview(null);
    }
  }, []);

  // ---- run transform ----
  const run = useCallback(async () => {
    if (!srcFile) return;
    setLoading(true);
    setError(null);
    setResultB64(null);
    setMeta(null);
    setChapterResult(null);
    setNoiseResult(null);
    setProcessingTimeMs(null);
    const startTime = performance.now();
    try {
      const form = new FormData();
      form.append("file", srcFile);

      let endpoint = "";
      if (mode === "background-remove") {
        endpoint = "/api/transform/video/background-remove";
        form.append("method", bgMethod);
      } else if (mode === "super-resolution") {
        endpoint = "/api/transform/video/super-resolution";
        form.append("scale", String(srScale));
      } else if (mode === "style") {
        endpoint = "/api/transform/video/style";
        form.append("style", stylePreset);
      } else if (mode === "color-grade") {
        endpoint = "/api/transform/video/color-grade";
        form.append("preset", colorGradePreset);
      } else if (mode === "subtitle") {
        endpoint = "/api/transform/video/subtitle";
        form.append("text", subtitleText);
        form.append("position", subtitlePosition);
        form.append("font_scale", String(fontScale));
      } else if (mode === "inpaint") {
        endpoint = "/api/transform/video/inpaint";
        if (maskFile) form.append("mask", maskFile);
      } else if (mode === "smart-crop") {
        endpoint = "/api/transform/video/smart-crop";
        form.append("target_size", smartCropSize);
        form.append("method", smartCropMethod);
      } else {
        endpoint = "/api/transform/video/auto-crop";
        form.append("aspect", aspect);
      }

      const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST", body: form });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const json = await res.json();
      const outputB64 = json.image ?? json.thumbnail ?? null;
      setResultB64(outputB64);
      setMeta(json);
      setProcessingTimeMs(json.processing_time_ms ?? (performance.now() - startTime));

      // Save to transform history
      if (outputB64) {
        saveToTransformHistory({
          operationName: mode,
          thumbnail: `data:image/png;base64,${outputB64.slice(0, 200)}`,
          inputFilename: srcFile.name,
          outputB64,
          outputFilename: `transform-${mode}-result.png`,
        });
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [srcFile, mode, bgMethod, srScale, stylePreset, aspect, colorGradePreset, subtitleText, subtitlePosition, maskFile, smartCropSize, smartCropMethod, fontScale]);

  // ---- run audio transform ----
  const runAudio = useCallback(async () => {
    setLoading(true);
    setError(null);
    setChapterResult(null);
    setNoiseResult(null);
    setMeta(null);
    try {
      if (audioMode === "tts") {
        // TTS uses JSON body, no file upload
        const res = await fetch(`${API_BASE}/api/transform/audio/tts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: ttsText, voice: ttsVoice }),
        });
        if (!res.ok) throw new Error(`API error ${res.status}`);
        const json = await res.json();
        setMeta(json);
        return;
      }

      if (!srcFile) return;
      const form = new FormData();
      form.append("file", srcFile);

      let endpoint = "";
      if (audioMode === "voice-convert") {
        endpoint = "/api/transform/audio/voice-convert";
        form.append("target_voice", voicePreset);
      } else if (audioMode === "chapters") {
        endpoint = "/api/transform/audio/chapters";
      } else if (audioMode === "noise-profile") {
        endpoint = "/api/transform/audio/noise-profile";
      } else {
        endpoint = `/api/transform/audio/${audioMode}`;
      }

      const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST", body: form });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const json = await res.json();

      if (audioMode === "chapters") {
        setChapterResult(json);
      } else if (audioMode === "noise-profile") {
        setNoiseResult(json);
      }
      setMeta(json);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [srcFile, audioMode, voicePreset, ttsText, ttsVoice]);

  // ---- run batch transform ----
  const runBatch = useCallback(async () => {
    if (batchFiles.length === 0) return;
    setLoading(true);
    setError(null);
    setBatchResults(null);
    try {
      const form = new FormData();
      for (const f of batchFiles) {
        form.append("files", f);
      }

      if (batchType === "audio") {
        form.append("operations", batchParams);
        const res = await fetch(`${API_BASE}/api/transform/audio/batch`, { method: "POST", body: form });
        if (!res.ok) throw new Error(`API error ${res.status}`);
        setBatchResults(await res.json());
      } else {
        form.append("operation", batchOperation);
        form.append("params", batchParams);
        const res = await fetch(`${API_BASE}/api/transform/video/batch`, { method: "POST", body: form });
        if (!res.ok) throw new Error(`API error ${res.status}`);
        setBatchResults(await res.json());
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [batchFiles, batchType, batchOperation, batchParams]);

  // ---- download helper ----
  const download = useCallback(() => {
    if (!resultB64) return;
    const link = document.createElement("a");
    link.href = `data:image/png;base64,${resultB64}`;
    link.download = `transform-${mode}-result.png`;
    link.click();
  }, [resultB64, mode]);

  const resultSrc = resultB64 ? `data:image/png;base64,${resultB64}` : null;

  // ---- restore from history ----
  const handleHistoryRestore = useCallback((entry: TransformHistoryEntry) => {
    if (entry.outputB64) {
      setResultB64(entry.outputB64);
    }
    setError(null);
  }, []);

  // ---- chain transform: feed current output back as input ----
  const handleChainTransform = useCallback(() => {
    if (!resultB64) return;
    // Convert base64 result to a File so it can be used as the next input
    const byteString = atob(resultB64);
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteString.length; i++) ia[i] = byteString.charCodeAt(i);
    const blob = new Blob([ab], { type: "image/png" });
    const file = new File([blob], `chained-${mode}-result.png`, { type: "image/png" });
    setSrcFile(file);
    setSrcPreview(`data:image/png;base64,${resultB64}`);
    setResultB64(null);
    setMeta(null);
    setProcessingTimeMs(null);
  }, [resultB64, mode]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Transform Studio</h1>
        <p className="text-gray-500 mt-1">Style transfer, media transformation, batch processing, and presets.</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-2 border-b border-gray-200">
        {(
          [
            ["audio", "Audio"],
            ["video", "Video / Image"],
            ["batch", "Batch Transform"],
            ["presets", "Presets"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              tab === key
                ? "border-transparent text-gray-500 hover:text-gray-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
            style={tab === key ? { borderColor: "#185FA5", color: "#185FA5" } : undefined}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Audio tab content */}
      {tab === "audio" && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-2">
            {(
              [
                ["denoise", "Denoise"],
                ["silence-remove", "Remove Silence"],
                ["pitch-shift", "Pitch Shift"],
                ["time-stretch", "Time Stretch"],
                ["eq", "Equalizer"],
                ["chain", "Chain"],
                ["voice-convert", "Voice Conversion"],
                ["chapters", "Auto-Chapter"],
                ["noise-profile", "Noise Profile"],
                ["tts", "Text to Speech"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setAudioMode(key)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  audioMode === key
                    ? "bg-brand-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* TTS mode — no file upload needed */}
          {audioMode === "tts" && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <p className="text-sm text-gray-600">Generate placeholder audio from text (stub — integrate a real TTS service for production).</p>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700">Text:</label>
                <input
                  type="text"
                  value={ttsText}
                  onChange={(e) => setTtsText(e.target.value)}
                  placeholder="Enter text to synthesize..."
                  className="flex-1 rounded border-gray-300 text-sm px-3 py-1 border"
                />
              </div>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700">Voice:</label>
                <input
                  type="text"
                  value={ttsVoice}
                  onChange={(e) => setTtsVoice(e.target.value)}
                  placeholder="default"
                  className="rounded border-gray-300 text-sm px-3 py-1 border w-40"
                />
              </div>
            </div>
          )}

          {/* Audio file upload (not needed for TTS) */}
          {audioMode !== "tts" && (
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-brand-400 transition"
            >
              <input
                ref={fileRef}
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={onFileChange}
              />
              {srcFile ? (
                <p className="text-gray-700 font-medium">{srcFile.name}</p>
              ) : (
                <p className="text-gray-400">Click to upload an audio file</p>
              )}
            </div>
          )}

          {/* Voice Conversion options */}
          {audioMode === "voice-convert" && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <label className="text-sm font-medium text-gray-700">Voice Preset:</label>
              <div className="flex flex-wrap gap-2">
                {VOICE_PRESETS.map((v) => (
                  <button
                    key={v}
                    onClick={() => setVoicePreset(v)}
                    className={`px-3 py-1 rounded text-sm capitalize ${
                      voicePreset === v ? "bg-brand-600 text-white" : "bg-gray-200 text-gray-700"
                    }`}
                  >
                    {v.replace("_", " ")}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Auto-Chapter info */}
          {audioMode === "chapters" && (
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-600">
                Detects long silences in audio and splits into chapters automatically.
              </p>
            </div>
          )}

          {/* Noise Profile info */}
          {audioMode === "noise-profile" && (
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-600">
                Analyzes the noise characteristics of your audio and provides recommendations.
              </p>
            </div>
          )}

          {/* Run audio button */}
          <button
            onClick={runAudio}
            disabled={(audioMode !== "tts" && !srcFile) || loading}
            className="px-6 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-brand-700 transition"
          >
            {loading ? "Processing..." : "Transform Audio"}
          </button>

          {/* Chapter results */}
          {chapterResult && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-2">
              <h3 className="text-lg font-semibold text-gray-900">Chapters Detected</h3>
              <p className="text-sm text-gray-600">Total: {(chapterResult as Record<string, unknown>).total_chapters as number}</p>
              <div className="space-y-1">
                {((chapterResult as Record<string, unknown>).chapters as Array<Record<string, unknown>>)?.map((ch) => (
                  <div key={ch.chapter as number} className="flex gap-4 text-sm text-gray-700 bg-white rounded p-2">
                    <span className="font-medium">Ch. {ch.chapter as number}</span>
                    <span>{ch.start_s as number}s - {ch.end_s as number}s</span>
                    <span className="text-gray-400">({ch.duration_s as number}s)</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Noise profile results */}
          {noiseResult && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-2">
              <h3 className="text-lg font-semibold text-gray-900">Noise Analysis</h3>
              <div className="text-sm text-gray-700 space-y-1">
                <p>Noise Floor: {(noiseResult as Record<string, unknown>).noise_floor_db as number} dB</p>
                <p>SNR Estimate: {(noiseResult as Record<string, unknown>).snr_estimate_db as number} dB</p>
                <p>Dominant Frequencies: {((noiseResult as Record<string, unknown>).dominant_noise_freqs as number[])?.join(", ")} Hz</p>
                <p className="mt-2 font-medium text-brand-600">{(noiseResult as Record<string, unknown>).recommendation as string}</p>
              </div>
            </div>
          )}

          {/* TTS result */}
          {audioMode === "tts" && meta && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-2">
              <h3 className="text-lg font-semibold text-gray-900">TTS Result</h3>
              <div className="text-sm text-gray-700 space-y-1">
                <p>Voice: {(meta as Record<string, unknown>).voice as string}</p>
                <p>Text Length: {(meta as Record<string, unknown>).text_length as number} chars</p>
                <p>Processing Time: {Number((meta as Record<string, unknown>).processing_time_ms).toFixed(1)} ms</p>
                {(meta as Record<string, unknown>).audio ? (
                  <audio controls className="mt-2">
                    <source src={`data:audio/wav;base64,${(meta as Record<string, unknown>).audio as string}`} type="audio/wav" />
                  </audio>
                ) : null}
              </div>
            </div>
          )}

          {/* Generic audio info */}
          {!chapterResult && !noiseResult && audioMode !== "voice-convert" && audioMode !== "chapters" && audioMode !== "noise-profile" && audioMode !== "tts" && (
            <div className="bg-gray-50 rounded-lg p-6 text-center">
              <p className="text-gray-500 text-sm">
                Audio transform mode: <span className="font-medium">{audioMode}</span>
              </p>
              <p className="text-gray-400 text-xs mt-2">
                Upload an audio file and apply transforms via the API at <code>/api/transform/audio/{audioMode}</code>
              </p>
            </div>
          )}
        </div>
      )}

      {/* Video / Image tab content — 2-column split-pane layout */}
      {tab === "video" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* ── Left column: controls ── */}
          <div className="space-y-4">
            {/* Mode selector */}
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ["background-remove", "Background Remove"],
                  ["super-resolution", "Super Resolution"],
                  ["style", "Style Transfer"],
                  ["auto-crop", "Auto Crop"],
                  ["color-grade", "Color Grade"],
                  ["subtitle", "Subtitle"],
                  ["inpaint", "Inpaint"],
                  ["smart-crop", "Smart Crop"],
                  ["interpolate", "Frame Interpolate"],
                  ["highlight", "Highlight Clip"],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => { setMode(key); setResultB64(null); setMeta(null); setProcessingTimeMs(null); }}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                    mode === key
                      ? "text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                  style={mode === key ? { backgroundColor: "#185FA5" } : undefined}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Upload dropzone */}
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-blue-400 transition"
            >
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={onFileChange}
              />
              {srcPreview ? (
                <img src={srcPreview} alt="Source" className="mx-auto max-h-48 rounded" />
              ) : (
                <p className="text-gray-400">Click or drag an image here to upload</p>
              )}
            </div>

            {/* Placeholder for OperationControls (created by other agents) */}
            {hasOperationControls ? (
              // TODO(ws-c): OperationControls emits a generic params bag, but this
              // page drives requests off the per-mode state below (bgMethod,
              // srScale, ...). The emitted params are captured but not yet folded
              // into the request payload — wiring them up is a behavioural change
              // left to the transform owner.
              <OperationControls operation={mode} onParamsChange={setOperationParams} />
            ) : (
              /* Inline mode-specific options (existing controls) */
              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                {mode === "background-remove" && (
                  <div className="flex items-center gap-3">
                    <label className="text-sm font-medium text-gray-700">Method:</label>
                    <select
                      value={bgMethod}
                      onChange={(e) => setBgMethod(e.target.value)}
                      className="rounded border-gray-300 text-sm"
                    >
                      {BG_METHODS.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>
                )}

                {mode === "super-resolution" && (
                  <div className="flex items-center gap-3">
                    <label className="text-sm font-medium text-gray-700">Scale:</label>
                    {[2, 4].map((s) => (
                      <button
                        key={s}
                        onClick={() => setSrScale(s)}
                        className={`px-3 py-1 rounded text-sm ${
                          srScale === s ? "text-white" : "bg-gray-200 text-gray-700"
                        }`}
                        style={srScale === s ? { backgroundColor: "#185FA5" } : undefined}
                      >
                        {s}x
                      </button>
                    ))}
                  </div>
                )}

                {mode === "style" && (
                  <div className="flex items-center gap-3 flex-wrap">
                    <label className="text-sm font-medium text-gray-700">Style:</label>
                    {STYLES.map((s) => (
                      <button
                        key={s}
                        onClick={() => setStylePreset(s)}
                        className={`px-3 py-1 rounded text-sm capitalize ${
                          stylePreset === s ? "text-white" : "bg-gray-200 text-gray-700"
                        }`}
                        style={stylePreset === s ? { backgroundColor: "#185FA5" } : undefined}
                      >
                        {s.replace("_", " ")}
                      </button>
                    ))}
                  </div>
                )}

                {mode === "auto-crop" && (
                  <div className="flex items-center gap-3">
                    <label className="text-sm font-medium text-gray-700">Aspect Ratio:</label>
                    <select
                      value={aspect}
                      onChange={(e) => setAspect(e.target.value)}
                      className="rounded border-gray-300 text-sm"
                    >
                      {ASPECTS.map((a) => (
                        <option key={a} value={a}>{a}</option>
                      ))}
                    </select>
                  </div>
                )}

                {mode === "color-grade" && (
                  <div className="flex items-center gap-3 flex-wrap">
                    <label className="text-sm font-medium text-gray-700">Preset:</label>
                    {COLOR_GRADE_PRESETS.map((p) => (
                      <button
                        key={p}
                        onClick={() => setColorGradePreset(p)}
                        className={`px-3 py-1 rounded text-sm capitalize ${
                          colorGradePreset === p ? "text-white" : "bg-gray-200 text-gray-700"
                        }`}
                        style={colorGradePreset === p ? { backgroundColor: "#185FA5" } : undefined}
                      >
                        {p.replace("_", " ")}
                      </button>
                    ))}
                  </div>
                )}

                {mode === "subtitle" && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <label className="text-sm font-medium text-gray-700">Text:</label>
                      <input
                        type="text"
                        value={subtitleText}
                        onChange={(e) => setSubtitleText(e.target.value)}
                        placeholder="Enter subtitle text..."
                        className="flex-1 rounded border-gray-300 text-sm px-3 py-1 border"
                      />
                    </div>
                    <div className="flex items-center gap-3">
                      <label className="text-sm font-medium text-gray-700">Position:</label>
                      {SUBTITLE_POSITIONS.map((pos) => (
                        <button
                          key={pos}
                          onClick={() => setSubtitlePosition(pos)}
                          className={`px-3 py-1 rounded text-sm capitalize ${
                            subtitlePosition === pos ? "text-white" : "bg-gray-200 text-gray-700"
                          }`}
                          style={subtitlePosition === pos ? { backgroundColor: "#185FA5" } : undefined}
                        >
                          {pos}
                        </button>
                      ))}
                    </div>
                    <div className="flex items-center gap-3">
                      <label className="text-sm font-medium text-gray-700">Font Scale:</label>
                      <input
                        type="number"
                        value={fontScale}
                        onChange={(e) => setFontScale(Number(e.target.value))}
                        min={0.5}
                        max={5}
                        step={0.1}
                        className="rounded border-gray-300 text-sm px-3 py-1 border w-24"
                      />
                    </div>
                  </div>
                )}

                {mode === "inpaint" && (
                  <div className="space-y-3">
                    <p className="text-sm text-gray-600">Upload a mask image where white pixels indicate areas to inpaint.</p>
                    <div className="flex items-center gap-3">
                      <label className="text-sm font-medium text-gray-700">Mask:</label>
                      <input
                        ref={maskRef}
                        type="file"
                        accept="image/*"
                        className="text-sm"
                        onChange={(e) => setMaskFile(e.target.files?.[0] ?? null)}
                      />
                    </div>
                  </div>
                )}

                {mode === "smart-crop" && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <label className="text-sm font-medium text-gray-700">Target Size (WxH):</label>
                      <input
                        type="text"
                        value={smartCropSize}
                        onChange={(e) => setSmartCropSize(e.target.value)}
                        placeholder="200x200"
                        className="rounded border-gray-300 text-sm px-3 py-1 border w-32"
                      />
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                      <label className="text-sm font-medium text-gray-700">Method:</label>
                      {SMART_CROP_METHODS.map((m) => (
                        <button
                          key={m}
                          onClick={() => setSmartCropMethod(m)}
                          className={`px-3 py-1 rounded text-sm capitalize ${
                            smartCropMethod === m ? "text-white" : "bg-gray-200 text-gray-700"
                          }`}
                          style={smartCropMethod === m ? { backgroundColor: "#185FA5" } : undefined}
                        >
                          {m.replace(/_/g, " ")}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {mode === "interpolate" && (
                  <div className="rounded-lg p-3" style={{ backgroundColor: "#FEF3C7" }}>
                    <p className="text-sm" style={{ color: "#92400E" }}>Frame interpolation requires two frames. Use the API directly at <code>/api/transform/video/interpolate</code> with frame1 and frame2 uploads.</p>
                  </div>
                )}

                {mode === "highlight" && (
                  <div className="rounded-lg p-3" style={{ backgroundColor: "#FEF3C7" }}>
                    <p className="text-sm" style={{ color: "#92400E" }}>Highlight clip selection requires multiple frames with scores. Use the API directly at <code>/api/transform/video/highlight</code> with multiple files and a scores JSON array.</p>
                  </div>
                )}
              </div>
            )}

            {/* Transform button */}
            {mode !== "interpolate" && mode !== "highlight" && (
              <button
                onClick={run}
                disabled={!srcFile || loading}
                className="w-full px-6 py-2.5 text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:opacity-90 transition"
                style={{ backgroundColor: "#185FA5" }}
              >
                {loading ? "Processing..." : "Transform"}
              </button>
            )}

            {/* Processing progress (created by other agents) */}
            {loading && <ProcessingProgress isProcessing={loading} />}

            {/* Error */}
            {error && (
              <div className="border px-4 py-3 rounded-lg text-sm" style={{ backgroundColor: "#FEF2F2", borderColor: "#FECACA", color: "#A32D2D" }}>
                {error}
              </div>
            )}

            {/* Transform History */}
            {hasTransformHistory && <TransformHistory onRestore={handleHistoryRestore} />}
          </div>

          {/* ── Right column: results viewer ── */}
          <div className="space-y-4">
            {/* BeforeAfterViewer */}
            <BeforeAfterViewer
              originalSrc={srcPreview ?? undefined}
              transformedSrc={resultSrc ?? undefined}
              originalInfo={
                meta?.original_size
                  ? {
                      width: (meta.original_size as number[])[0],
                      height: (meta.original_size as number[])[1],
                      size: srcFile ? `${(srcFile.size / 1024).toFixed(1)} KB` : "",
                    }
                  : undefined
              }
              transformedInfo={
                meta?.output_size
                  ? {
                      width: (meta.output_size as number[])[0],
                      height: (meta.output_size as number[])[1],
                      size: resultB64 ? `${(Math.ceil(resultB64.length * 0.75) / 1024).toFixed(1)} KB` : "",
                    }
                  : undefined
              }
            />

            {/* Output stats row */}
            {meta && resultSrc && (
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg bg-gray-50 p-3 text-center">
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Processing Time</p>
                  <p className="mt-1 text-lg font-semibold text-gray-900">
                    {processingTimeMs != null ? `${processingTimeMs.toFixed(1)} ms` : "—"}
                  </p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3 text-center">
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Dimensions</p>
                  <p className="mt-1 text-lg font-semibold text-gray-900">
                    {meta.output_size
                      ? (meta.output_size as number[]).join(" x ")
                      : meta.cropped_size
                        ? (meta.cropped_size as number[]).join(" x ")
                        : "—"}
                  </p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3 text-center">
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">File Size</p>
                  <p className="mt-1 text-lg font-semibold text-gray-900">
                    {resultB64 ? `${(Math.ceil(resultB64.length * 0.75) / 1024).toFixed(1)} KB` : "—"}
                  </p>
                </div>
              </div>
            )}

            {/* Download button */}
            {resultSrc && (
              <button
                onClick={download}
                className="w-full px-4 py-2 bg-gray-800 text-white rounded-lg text-sm font-medium hover:bg-gray-900 transition"
              >
                Download Result
              </button>
            )}

            {/* Export Panel (visible after transform completes) */}
            {hasTransformExportPanel && (
              <TransformExportPanel
                outputB64={resultB64 ?? undefined}
                outputFilename={`transform-${mode}-result.png`}
                onChainTransform={handleChainTransform}
                isVisible={!!resultSrc}
              />
            )}
          </div>
        </div>
      )}

      {/* Batch Transform tab */}
      {tab === "batch" && (
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Batch Transform</h2>
            <p className="text-sm text-gray-500 mt-1">Upload multiple files and apply the same transform to all of them in parallel.</p>
          </div>

          {/* Batch type selector */}
          <div className="flex gap-2">
            <button
              onClick={() => setBatchType("audio")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                batchType === "audio" ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              Audio Batch
            </button>
            <button
              onClick={() => setBatchType("video")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                batchType === "video" ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              Video Batch
            </button>
          </div>

          {/* Batch file upload */}
          <div
            onClick={() => batchFileRef.current?.click()}
            className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-brand-400 transition"
          >
            <input
              ref={batchFileRef}
              type="file"
              accept={batchType === "audio" ? "audio/*" : "image/*"}
              multiple
              className="hidden"
              onChange={(e) => {
                const files = Array.from(e.target.files ?? []);
                setBatchFiles(files);
                setBatchResults(null);
              }}
            />
            {batchFiles.length > 0 ? (
              <p className="text-gray-700 font-medium">{batchFiles.length} file(s) selected</p>
            ) : (
              <p className="text-gray-400">Click to upload multiple {batchType === "audio" ? "audio" : "image"} files</p>
            )}
          </div>

          {/* Batch options */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            {batchType === "video" && (
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700">Operation:</label>
                <select
                  value={batchOperation}
                  onChange={(e) => setBatchOperation(e.target.value)}
                  className="rounded border-gray-300 text-sm"
                >
                  <option value="color_grade">Color Grade</option>
                  <option value="smart_crop">Smart Crop</option>
                  <option value="subtitle">Subtitle</option>
                  <option value="style">Style Transfer</option>
                  <option value="super_resolution">Super Resolution</option>
                  <option value="background_remove">Background Remove</option>
                </select>
              </div>
            )}
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700">
                {batchType === "audio" ? "Operations (JSON array):" : "Params (JSON object):"}
              </label>
              <textarea
                value={batchParams}
                onChange={(e) => setBatchParams(e.target.value)}
                className="w-full rounded border-gray-300 text-sm px-3 py-2 border font-mono"
                rows={3}
                placeholder={batchType === "audio" ? '[{"op": "denoise"}]' : '{"preset": "cinematic"}'}
              />
            </div>
          </div>

          <button
            onClick={runBatch}
            disabled={batchFiles.length === 0 || loading}
            className="px-6 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-brand-700 transition"
          >
            {loading ? "Processing..." : "Run Batch"}
          </button>

          {/* Batch results */}
          {batchResults && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-2">
              <h3 className="text-lg font-semibold text-gray-900">Batch Results</h3>
              <p className="text-sm text-gray-600">
                Processed {(batchResults as Record<string, unknown>).total_files as number} files in{" "}
                {Number((batchResults as Record<string, unknown>).processing_time_ms).toFixed(1)} ms
              </p>
              <div className="space-y-2">
                {((batchResults as Record<string, unknown>).results as Array<Record<string, unknown>>)?.map((r, i) => (
                  <div key={i} className={`p-3 rounded text-sm ${r.status === "ok" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
                    <span className="font-medium">File {i + 1}:</span>{" "}
                    {r.status === "ok" ? "Success" : `Error: ${r.error}`}
                    {r.image ? (
                      <img
                        src={`data:image/png;base64,${r.image as string}`}
                        alt={`Result ${i + 1}`}
                        className="mt-2 max-h-32 rounded"
                      />
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
        </div>
      )}

      {/* Presets tab */}
      {tab === "presets" && (
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Transform Presets</h2>
            <p className="text-sm text-gray-500 mt-1">Pre-configured transform chains for common workflows. Click a preset to auto-configure.</p>
          </div>

          {presets ? (
            <>
              {/* Audio presets */}
              <div className="space-y-3">
                <h3 className="text-md font-semibold text-gray-800">Audio Presets</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {Object.entries(presets.audio).map(([name, preset]) => (
                    <button
                      key={name}
                      onClick={() => {
                        setTab("batch");
                        setBatchType("audio");
                        setBatchParams(JSON.stringify(preset.operations, null, 2));
                      }}
                      className="text-left p-4 bg-white border border-gray-200 rounded-lg hover:border-brand-400 hover:shadow-sm transition"
                    >
                      <h4 className="font-medium text-gray-900 capitalize">{name.replace(/_/g, " ")}</h4>
                      <p className="text-sm text-gray-500 mt-1">{preset.description}</p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {preset.operations.map((op, i) => (
                          <span key={i} className="inline-block px-2 py-0.5 bg-brand-50 text-brand-700 rounded text-xs font-medium">
                            {(op as Record<string, unknown>).op as string}
                          </span>
                        ))}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Video presets */}
              <div className="space-y-3">
                <h3 className="text-md font-semibold text-gray-800">Video Presets</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {Object.entries(presets.video).map(([name, preset]) => (
                    <button
                      key={name}
                      onClick={() => {
                        setTab("batch");
                        setBatchType("video");
                        const firstOp = preset.operations[0] as Record<string, unknown>;
                        setBatchOperation((firstOp.op as string) ?? "color_grade");
                        const { op, ...rest } = firstOp;
                        setBatchParams(JSON.stringify(rest, null, 2));
                      }}
                      className="text-left p-4 bg-white border border-gray-200 rounded-lg hover:border-brand-400 hover:shadow-sm transition"
                    >
                      <h4 className="font-medium text-gray-900 capitalize">{name.replace(/_/g, " ")}</h4>
                      <p className="text-sm text-gray-500 mt-1">{preset.description}</p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {preset.operations.map((op, i) => (
                          <span key={i} className="inline-block px-2 py-0.5 bg-purple-50 text-purple-700 rounded text-xs font-medium">
                            {(op as Record<string, unknown>).op as string}
                          </span>
                        ))}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p className="text-gray-400 text-sm">Loading presets...</p>
          )}
        </div>
      )}
    </div>
  );
}
