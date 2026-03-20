"use client";

import { useCallback, useRef, useState } from "react";
import BeforeAfterSlider from "@/components/transform/BeforeAfterSlider";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type VideoMode = "background-remove" | "super-resolution" | "style" | "auto-crop" | "color-grade" | "subtitle" | "inpaint";
type AudioMode = "denoise" | "silence-remove" | "pitch-shift" | "time-stretch" | "eq" | "chain" | "voice-convert" | "chapters" | "noise-profile";

const BG_METHODS = ["threshold", "grabcut"] as const;
const STYLES = ["sketch", "edges", "cartoon", "oil_painting"] as const;
const ASPECTS = ["16:9", "4:3", "1:1", "9:16"] as const;
const EQ_PRESETS = ["flat", "voice", "music", "podcast"] as const;
const COLOR_GRADE_PRESETS = ["cinematic", "vintage", "high_contrast", "bw_dramatic"] as const;
const VOICE_PRESETS = ["male_deep", "female_high", "robotic", "whisper"] as const;
const SUBTITLE_POSITIONS = ["top", "center", "bottom"] as const;

export default function TransformPage() {
  // --- shared state ---
  const [tab, setTab] = useState<"audio" | "video">("video");
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

  const fileRef = useRef<HTMLInputElement>(null);
  const maskRef = useRef<HTMLInputElement>(null);

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
      } else if (mode === "inpaint") {
        endpoint = "/api/transform/video/inpaint";
        if (maskFile) form.append("mask", maskFile);
      } else {
        endpoint = "/api/transform/video/auto-crop";
        form.append("aspect", aspect);
      }

      const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST", body: form });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const json = await res.json();
      setResultB64(json.image ?? json.thumbnail ?? null);
      setMeta(json);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [srcFile, mode, bgMethod, srScale, stylePreset, aspect, colorGradePreset, subtitleText, subtitlePosition, maskFile]);

  // ---- run audio transform ----
  const runAudio = useCallback(async () => {
    if (!srcFile) return;
    setLoading(true);
    setError(null);
    setChapterResult(null);
    setNoiseResult(null);
    setMeta(null);
    try {
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
  }, [srcFile, audioMode, voicePreset]);

  // ---- download helper ----
  const download = useCallback(() => {
    if (!resultB64) return;
    const link = document.createElement("a");
    link.href = `data:image/png;base64,${resultB64}`;
    link.download = `transform-${mode}-result.png`;
    link.click();
  }, [resultB64, mode]);

  const resultSrc = resultB64 ? `data:image/png;base64,${resultB64}` : null;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Transform Studio</h1>
        <p className="text-gray-500 mt-1">Style transfer and media transformation tools.</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-2 border-b border-gray-200">
        <button
          onClick={() => setTab("audio")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            tab === "audio"
              ? "border-brand-600 text-brand-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Audio
        </button>
        <button
          onClick={() => setTab("video")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
            tab === "video"
              ? "border-brand-600 text-brand-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Video / Image
        </button>
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

          {/* Audio file upload */}
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
            disabled={!srcFile || loading}
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

          {/* Generic audio info */}
          {!chapterResult && !noiseResult && audioMode !== "voice-convert" && audioMode !== "chapters" && audioMode !== "noise-profile" && (
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

      {/* Video tab content */}
      {tab === "video" && <>
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
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => { setMode(key); setResultB64(null); setMeta(null); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              mode === key
                ? "bg-brand-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Upload zone */}
      <div
        onClick={() => fileRef.current?.click()}
        className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-brand-400 transition"
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

      {/* Mode-specific options */}
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
                  srScale === s ? "bg-brand-600 text-white" : "bg-gray-200 text-gray-700"
                }`}
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
                  stylePreset === s ? "bg-brand-600 text-white" : "bg-gray-200 text-gray-700"
                }`}
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
                  colorGradePreset === p ? "bg-brand-600 text-white" : "bg-gray-200 text-gray-700"
                }`}
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
                    subtitlePosition === pos ? "bg-brand-600 text-white" : "bg-gray-200 text-gray-700"
                  }`}
                >
                  {pos}
                </button>
              ))}
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

        {/* Run button */}
        <button
          onClick={run}
          disabled={!srcFile || loading}
          className="px-6 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-brand-700 transition"
        >
          {loading ? "Processing..." : "Transform"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {srcPreview && resultSrc && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Result</h3>

          <BeforeAfterSlider beforeSrc={srcPreview} afterSrc={resultSrc} />

          {/* Metadata */}
          {meta && (
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600 space-y-1">
              {meta.processing_time_ms != null && (
                <p>Processing time: {Number(meta.processing_time_ms).toFixed(1)} ms</p>
              )}
              {meta.original_size && (
                <p>Original size: {(meta.original_size as number[]).join(" x ")}</p>
              )}
              {meta.output_size && (
                <p>Output size: {(meta.output_size as number[]).join(" x ")}</p>
              )}
              {meta.cropped_size && (
                <p>Cropped size: {(meta.cropped_size as number[]).join(" x ")}</p>
              )}
            </div>
          )}

          {/* Download */}
          <button
            onClick={download}
            className="px-4 py-2 bg-gray-800 text-white rounded-lg text-sm font-medium hover:bg-gray-900 transition"
          >
            Download Result
          </button>
        </div>
      )}
      </>}
    </div>
  );
}
