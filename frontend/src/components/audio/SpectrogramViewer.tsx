"use client";

import React, { useCallback, useRef, useState } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

export interface SpectrogramParams {
  n_fft: number;
  hop_length: number;
  window: "hann" | "hamming" | "blackman";
  n_mels?: number;
}

export interface SpectrogramStats {
  n_frames: number;
  n_freq_bins: number;
  duration: number;
  db_min: number;
  db_max: number;
}

interface SpectrogramViewerProps {
  imageSrc: string | null;
  onReanalyze: (params: SpectrogramParams) => void;
  stats?: SpectrogramStats | null;
  /** When true, shows the n_mels dropdown (for Mel spectrogram tab) */
  showMelControls?: boolean;
}

const N_FFT_OPTIONS = [512, 1024, 2048, 4096] as const;
const HOP_LENGTH_OPTIONS = [128, 256, 512] as const;
const WINDOW_OPTIONS: { label: string; value: SpectrogramParams["window"] }[] = [
  { label: "Hann", value: "hann" },
  { label: "Hamming", value: "hamming" },
  { label: "Blackman", value: "blackman" },
];
const N_MELS_OPTIONS = [32, 64, 128, 256] as const;

const MIN_SCALE = 0.5;
const MAX_SCALE = 5;

export default function SpectrogramViewer({
  imageSrc,
  onReanalyze,
  stats,
  showMelControls = false,
}: SpectrogramViewerProps) {
  // Transform state
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const translateStart = useRef({ x: 0, y: 0 });

  // Controls state
  const [nFft, setNFft] = useState<number>(2048);
  const [hopLength, setHopLength] = useState<number>(512);
  const [window, setWindow] = useState<SpectrogramParams["window"]>("hann");
  const [nMels, setNMels] = useState<number>(128);

  const containerRef = useRef<HTMLDivElement>(null);

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.15 : 0.15;
      setScale((prev) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, prev + delta)));
    },
    [],
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      setIsDragging(true);
      dragStart.current = { x: e.clientX, y: e.clientY };
      translateStart.current = { ...translate };
    },
    [translate],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      setTranslate({
        x: translateStart.current.x + dx,
        y: translateStart.current.y + dy,
      });
    },
    [isDragging],
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDoubleClick = useCallback(() => {
    setScale(1);
    setTranslate({ x: 0, y: 0 });
  }, []);

  const handleReanalyze = useCallback(() => {
    const params: SpectrogramParams = {
      n_fft: nFft,
      hop_length: hopLength,
      window,
    };
    if (showMelControls) {
      params.n_mels = nMels;
    }
    onReanalyze(params);
  }, [nFft, hopLength, window, nMels, showMelControls, onReanalyze]);

  if (!imageSrc) {
    return (
      <Card title="Spectrogram Viewer">
        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
          <svg
            className="mb-3 h-12 w-12"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <p className="text-sm font-medium">No spectrogram available</p>
          <p className="mt-1 text-xs">Upload an audio file and run analysis to view</p>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Spectrogram Viewer">
      <div className="space-y-4">
        {/* Controls row */}
        <div className="flex flex-wrap items-end gap-3">
          <SelectControl
            label="n_fft"
            value={nFft}
            onChange={(v) => setNFft(Number(v))}
            options={N_FFT_OPTIONS.map((v) => ({ label: String(v), value: v }))}
          />
          <SelectControl
            label="hop_length"
            value={hopLength}
            onChange={(v) => setHopLength(Number(v))}
            options={HOP_LENGTH_OPTIONS.map((v) => ({ label: String(v), value: v }))}
          />
          <SelectControl
            label="Window"
            value={window}
            onChange={(v) => setWindow(v as SpectrogramParams["window"])}
            options={WINDOW_OPTIONS.map((o) => ({ label: o.label, value: o.value }))}
          />
          {showMelControls && (
            <SelectControl
              label="n_mels"
              value={nMels}
              onChange={(v) => setNMels(Number(v))}
              options={N_MELS_OPTIONS.map((v) => ({ label: String(v), value: v }))}
            />
          )}
          <Button size="sm" onClick={handleReanalyze}>
            Re-analyze
          </Button>
        </div>

        {/* Pannable / zoomable image container */}
        <div
          ref={containerRef}
          className={`relative overflow-hidden rounded-lg border border-gray-200 bg-gray-900 ${
            isDragging ? "cursor-grabbing" : "cursor-grab"
          }`}
          style={{ height: 420 }}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onDoubleClick={handleDoubleClick}
        >
          <div
            style={{
              transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
              transformOrigin: "center center",
              transition: isDragging ? "none" : "transform 0.15s ease-out",
            }}
            className="flex h-full w-full items-center justify-center"
          >
            <img
              src={imageSrc}
              alt="Spectrogram"
              className="max-h-full max-w-full object-contain select-none"
              draggable={false}
            />
          </div>

          {/* Zoom indicator */}
          <div className="absolute bottom-2 right-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white tabular-nums">
            {Math.round(scale * 100)}% &middot; scroll to zoom &middot; double-click to reset
          </div>
        </div>

        {/* Stats display */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <StatBadge label="Frames" value={String(stats.n_frames)} />
            <StatBadge label="Freq Bins" value={String(stats.n_freq_bins)} />
            <StatBadge label="Duration" value={`${stats.duration.toFixed(2)}s`} />
            <StatBadge label="dB Min" value={`${stats.db_min.toFixed(1)} dB`} />
            <StatBadge label="dB Max" value={`${stats.db_max.toFixed(1)} dB`} />
          </div>
        )}
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Helper sub-components                                               */
/* ------------------------------------------------------------------ */

interface SelectControlProps {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  options: { label: string; value: string | number }[];
}

function SelectControl({ label, value, onChange, options }: SelectControlProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm text-gray-700 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
      >
        {options.map((opt) => (
          <option key={String(opt.value)} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function StatBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-center">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-sm font-semibold text-gray-900 tabular-nums">{value}</p>
    </div>
  );
}
