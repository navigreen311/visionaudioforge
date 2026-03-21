"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Button from "@/components/ui/Button";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AugmentConfig {
  whiteNoise: { enabled: boolean; snrDb: number };
  pinkNoise: { enabled: boolean; amplitude: number };
  timeStretch: { enabled: boolean; rate: number };
  pitchShift: { enabled: boolean; semitones: number };
  timeShift: { enabled: boolean; shiftPct: number };
  frequencyMask: { enabled: boolean; maskSizePct: number };
}

interface AugmentationStudioProps {
  originalFile: File | null;
  onAugment: (config: AugmentConfig) => void;
  augmentedAudioB64: string | null;
  /** Base64-encoded spectrogram PNG of the original audio */
  originalSpectrogramB64: string | null;
  /** Base64-encoded spectrogram PNG of the augmented audio */
  augmentedSpectrogramB64: string | null;
}

// ---------------------------------------------------------------------------
// Defaults & helpers
// ---------------------------------------------------------------------------

const DEFAULT_CONFIG: AugmentConfig = {
  whiteNoise: { enabled: false, snrDb: 20 },
  pinkNoise: { enabled: false, amplitude: 0.01 },
  timeStretch: { enabled: false, rate: 1.0 },
  pitchShift: { enabled: false, semitones: 0 },
  timeShift: { enabled: false, shiftPct: 0 },
  frequencyMask: { enabled: false, maskSizePct: 0 },
};

function randomInRange(min: number, max: number, step: number): number {
  const steps = Math.round((max - min) / step);
  return Math.round((min + Math.random() * steps * step) * 1000) / 1000;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

// ---------------------------------------------------------------------------
// Slider row
// ---------------------------------------------------------------------------

interface AugmentRowProps {
  label: string;
  enabled: boolean;
  onToggle: (v: boolean) => void;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  unit?: string;
}

function AugmentRow({
  label,
  enabled,
  onToggle,
  value,
  onChange,
  min,
  max,
  step,
  unit = "",
}: AugmentRowProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
      <label className="flex items-center gap-2 cursor-pointer select-none min-w-[150px]">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onToggle(e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
        />
        <span className="text-sm font-medium text-gray-800">{label}</span>
      </label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={!enabled}
        className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer disabled:opacity-40"
      />
      <span className="text-xs text-gray-600 min-w-[60px] text-right tabular-nums">
        {value}
        {unit}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Simple audio player
// ---------------------------------------------------------------------------

interface MiniPlayerProps {
  label: string;
  src: string | null;
  highlight?: boolean;
  audioRef?: React.RefObject<HTMLAudioElement | null>;
}

function MiniPlayer({ label, src, highlight = false, audioRef: externalRef }: MiniPlayerProps) {
  const internalRef = useRef<HTMLAudioElement>(null);
  const audioRef = externalRef || internalRef;
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const toggle = useCallback(() => {
    const el = audioRef.current;
    if (!el || !src) return;
    if (playing) {
      el.pause();
    } else {
      el.play();
    }
    setPlaying(!playing);
  }, [playing, src, audioRef]);

  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    const onTime = () => setCurrentTime(el.currentTime);
    const onMeta = () => setDuration(el.duration);
    const onEnded = () => setPlaying(false);
    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onMeta);
    el.addEventListener("ended", onEnded);
    return () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onMeta);
      el.removeEventListener("ended", onEnded);
    };
  }, [src, audioRef]);

  return (
    <div
      className={`rounded-lg border p-4 ${
        highlight
          ? "border-brand-500 bg-brand-50 ring-2 ring-brand-300"
          : "border-gray-200 bg-white"
      }`}
    >
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
        {label}
      </p>
      {src ? (
        <>
          <audio ref={audioRef} src={src} preload="metadata" />
          <div className="flex items-center gap-3">
            <button
              onClick={toggle}
              className="flex items-center justify-center h-9 w-9 rounded-full bg-brand-600 text-white hover:bg-brand-700 transition-colors flex-shrink-0"
              aria-label={playing ? "Pause" : "Play"}
            >
              {playing ? (
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="4" width="4" height="16" />
                  <rect x="14" y="4" width="4" height="16" />
                </svg>
              ) : (
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              )}
            </button>
            <span className="text-sm text-gray-700 tabular-nums">
              {formatTime(currentTime)} / {formatTime(duration || 0)}
            </span>
          </div>
        </>
      ) : (
        <p className="text-sm text-gray-400">No audio loaded</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mini spectrogram
// ---------------------------------------------------------------------------

interface MiniSpectrogramProps {
  label: string;
  b64: string | null;
}

function MiniSpectrogram({ label, b64 }: MiniSpectrogramProps) {
  return (
    <div className="flex-1 min-w-0">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
        {label}
      </p>
      {b64 ? (
        <img
          src={`data:image/png;base64,${b64}`}
          alt={`${label} spectrogram`}
          className="w-full h-32 object-contain rounded-md border border-gray-200 bg-gray-900"
        />
      ) : (
        <div className="w-full h-32 rounded-md border border-gray-200 bg-gray-100 flex items-center justify-center">
          <span className="text-xs text-gray-400">No spectrogram</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function AugmentationStudio({
  originalFile,
  onAugment,
  augmentedAudioB64,
  originalSpectrogramB64,
  augmentedSpectrogramB64,
}: AugmentationStudioProps) {
  const [config, setConfig] = useState<AugmentConfig>(DEFAULT_CONFIG);
  const [abMode, setAbMode] = useState(false);
  const [abSide, setAbSide] = useState<"A" | "B">("A");
  const abTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const originalAudioRef = useRef<HTMLAudioElement | null>(null);
  const augmentedAudioRef = useRef<HTMLAudioElement | null>(null);

  // --- original file URL ---
  const originalUrl = useMemo(() => {
    if (!originalFile) return null;
    return URL.createObjectURL(originalFile);
  }, [originalFile]);

  // cleanup
  useEffect(() => {
    return () => {
      if (originalUrl) URL.revokeObjectURL(originalUrl);
    };
  }, [originalUrl]);

  // --- augmented blob URL ---
  const augmentedUrl = useMemo(() => {
    if (!augmentedAudioB64) return null;
    const byteChars = atob(augmentedAudioB64);
    const byteNumbers = new Uint8Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) {
      byteNumbers[i] = byteChars.charCodeAt(i);
    }
    const blob = new Blob([byteNumbers], { type: "audio/wav" });
    return URL.createObjectURL(blob);
  }, [augmentedAudioB64]);

  useEffect(() => {
    return () => {
      if (augmentedUrl) URL.revokeObjectURL(augmentedUrl);
    };
  }, [augmentedUrl]);

  // --- A/B toggle timer with playback switching ---
  useEffect(() => {
    if (abMode) {
      abTimerRef.current = setInterval(() => {
        setAbSide((prev) => {
          const next = prev === "A" ? "B" : "A";
          // Pause current, play next
          if (next === "A") {
            augmentedAudioRef.current?.pause();
            originalAudioRef.current?.play();
          } else {
            originalAudioRef.current?.pause();
            augmentedAudioRef.current?.play();
          }
          return next;
        });
      }, 3000);
      // Start playing the current side immediately
      if (abSide === "A") {
        originalAudioRef.current?.play();
      } else {
        augmentedAudioRef.current?.play();
      }
    } else {
      if (abTimerRef.current) clearInterval(abTimerRef.current);
      setAbSide("A");
      originalAudioRef.current?.pause();
      augmentedAudioRef.current?.pause();
    }
    return () => {
      if (abTimerRef.current) clearInterval(abTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abMode]);

  // --- config helpers ---
  const update = <K extends keyof AugmentConfig>(
    key: K,
    patch: Partial<AugmentConfig[K]>,
  ) => {
    setConfig((prev) => ({
      ...prev,
      [key]: { ...prev[key], ...patch },
    }));
  };

  const randomizeAll = () => {
    setConfig({
      whiteNoise: {
        enabled: Math.random() > 0.5,
        snrDb: randomInRange(5, 40, 1),
      },
      pinkNoise: {
        enabled: Math.random() > 0.5,
        amplitude: randomInRange(0.001, 0.1, 0.001),
      },
      timeStretch: {
        enabled: Math.random() > 0.5,
        rate: randomInRange(0.5, 2.0, 0.05),
      },
      pitchShift: {
        enabled: Math.random() > 0.5,
        semitones: randomInRange(-6, 6, 1),
      },
      timeShift: {
        enabled: Math.random() > 0.5,
        shiftPct: randomInRange(0, 30, 1),
      },
      frequencyMask: {
        enabled: Math.random() > 0.5,
        maskSizePct: randomInRange(0, 30, 1),
      },
    });
  };

  const reset = () => setConfig(DEFAULT_CONFIG);

  return (
    <div className="flex flex-col lg:flex-row gap-6">
      {/* ---- Left: Controls ---- */}
      <div className="lg:w-1/2 space-y-3">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
          Augmentation Controls
        </h3>

        <AugmentRow
          label="White Noise"
          enabled={config.whiteNoise.enabled}
          onToggle={(v) => update("whiteNoise", { enabled: v })}
          value={config.whiteNoise.snrDb}
          onChange={(v) => update("whiteNoise", { snrDb: v })}
          min={5}
          max={40}
          step={1}
          unit=" dB"
        />

        <AugmentRow
          label="Pink Noise"
          enabled={config.pinkNoise.enabled}
          onToggle={(v) => update("pinkNoise", { enabled: v })}
          value={config.pinkNoise.amplitude}
          onChange={(v) => update("pinkNoise", { amplitude: v })}
          min={0.001}
          max={0.1}
          step={0.001}
        />

        <AugmentRow
          label="Time Stretch"
          enabled={config.timeStretch.enabled}
          onToggle={(v) => update("timeStretch", { enabled: v })}
          value={config.timeStretch.rate}
          onChange={(v) => update("timeStretch", { rate: v })}
          min={0.5}
          max={2.0}
          step={0.05}
          unit="x"
        />

        <AugmentRow
          label="Pitch Shift"
          enabled={config.pitchShift.enabled}
          onToggle={(v) => update("pitchShift", { enabled: v })}
          value={config.pitchShift.semitones}
          onChange={(v) => update("pitchShift", { semitones: v })}
          min={-6}
          max={6}
          step={1}
          unit=" st"
        />

        <AugmentRow
          label="Time Shift"
          enabled={config.timeShift.enabled}
          onToggle={(v) => update("timeShift", { enabled: v })}
          value={config.timeShift.shiftPct}
          onChange={(v) => update("timeShift", { shiftPct: v })}
          min={0}
          max={30}
          step={1}
          unit="%"
        />

        <AugmentRow
          label="Frequency Mask"
          enabled={config.frequencyMask.enabled}
          onToggle={(v) => update("frequencyMask", { enabled: v })}
          value={config.frequencyMask.maskSizePct}
          onChange={(v) => update("frequencyMask", { maskSizePct: v })}
          min={0}
          max={30}
          step={1}
          unit="%"
        />

        <div className="flex gap-2 pt-2">
          <Button variant="secondary" size="sm" onClick={randomizeAll}>
            Randomize All
          </Button>
          <Button variant="ghost" size="sm" onClick={reset}>
            Reset
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => onAugment(config)}
            disabled={!originalFile}
          >
            Apply Augmentation
          </Button>
        </div>
      </div>

      {/* ---- Right: A/B Comparison ---- */}
      <div className="lg:w-1/2 space-y-4">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
          A/B Comparison
        </h3>

        <MiniPlayer
          label="Original (A)"
          src={originalUrl}
          highlight={abMode && abSide === "A"}
          audioRef={originalAudioRef}
        />
        <MiniPlayer
          label="Augmented (B)"
          src={augmentedUrl}
          highlight={abMode && abSide === "B"}
          audioRef={augmentedAudioRef}
        />

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={abMode}
              onChange={(e) => setAbMode(e.target.checked)}
              disabled={!augmentedUrl}
              className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-sm text-gray-700">A/B Listen</span>
          </label>
          {abMode && (
            <span
              className={`inline-flex items-center justify-center h-7 w-7 rounded-full text-sm font-bold transition-colors ${
                abSide === "A"
                  ? "bg-blue-100 text-blue-700"
                  : "bg-purple-100 text-purple-700"
              }`}
            >
              {abSide}
            </span>
          )}
        </div>

        {/* ---- Side-by-side spectrograms ---- */}
        <div className="flex gap-3">
          <MiniSpectrogram label="Original" b64={originalSpectrogramB64} />
          <MiniSpectrogram label="Augmented" b64={augmentedSpectrogramB64} />
        </div>
      </div>
    </div>
  );
}
