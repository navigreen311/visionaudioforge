"use client";

import { useCallback, useRef, useState } from "react";
import BeforeAfterSlider from "@/components/transform/BeforeAfterSlider";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type VideoMode = "background-remove" | "super-resolution" | "style" | "auto-crop";
type AudioMode = "denoise" | "silence-remove" | "pitch-shift" | "time-stretch" | "eq" | "chain";

const BG_METHODS = ["threshold", "grabcut"] as const;
const STYLES = ["sketch", "edges", "cartoon", "oil_painting"] as const;
const ASPECTS = ["16:9", "4:3", "1:1", "9:16"] as const;
const EQ_PRESETS = ["flat", "voice", "music", "podcast"] as const;

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

  const fileRef = useRef<HTMLInputElement>(null);

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
  }, [srcFile, mode, bgMethod, srScale, stylePreset, aspect]);

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
          <div className="bg-gray-50 rounded-lg p-6 text-center">
            <p className="text-gray-500 text-sm">
              Audio transform mode: <span className="font-medium">{audioMode}</span>
            </p>
            <p className="text-gray-400 text-xs mt-2">
              Upload an audio file and apply transforms via the API at <code>/api/transform/audio/{audioMode}</code>
            </p>
          </div>
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
