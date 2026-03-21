"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ----------------------------------------------------------------
// Types
// ----------------------------------------------------------------

type PresetRange = "1h" | "6h" | "24h" | "7d";

interface CustomRange {
  from: string; // ISO datetime-local value
  to: string;
}

export interface TimeRange {
  preset: PresetRange | "custom";
  custom?: CustomRange;
}

type RefreshInterval = 30 | 60 | 300 | 0; // 0 = manual

export interface TimeRangeSelectorProps {
  range: TimeRange;
  onRangeChange: (range: TimeRange) => void;
  onRefresh: () => void;
}

// ----------------------------------------------------------------
// Constants
// ----------------------------------------------------------------

const PRESETS: { label: string; value: PresetRange }[] = [
  { label: "1h", value: "1h" },
  { label: "6h", value: "6h" },
  { label: "24h", value: "24h" },
  { label: "7d", value: "7d" },
];

const INTERVALS: { label: string; value: RefreshInterval }[] = [
  { label: "30s", value: 30 },
  { label: "1m", value: 60 },
  { label: "5m", value: 300 },
  { label: "Manual", value: 0 },
];

// ----------------------------------------------------------------
// Component
// ----------------------------------------------------------------

export default function TimeRangeSelector({
  range,
  onRangeChange,
  onRefresh,
}: TimeRangeSelectorProps) {
  const [showCustom, setShowCustom] = useState(range.preset === "custom");
  const [customFrom, setCustomFrom] = useState(range.custom?.from ?? "");
  const [customTo, setCustomTo] = useState(range.custom?.to ?? "");
  const [interval, setInterval] = useState<RefreshInterval>(60);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof globalThis.setInterval> | null>(null);
  const tickRef = useRef<ReturnType<typeof globalThis.setInterval> | null>(null);

  // -- Auto-refresh timer --
  const scheduleRefresh = useCallback(
    (seconds: number) => {
      // clear previous
      if (timerRef.current) clearInterval(timerRef.current);
      if (seconds === 0) {
        timerRef.current = null;
        return;
      }
      timerRef.current = globalThis.setInterval(() => {
        onRefresh();
        setLastRefresh(new Date());
        setElapsed(0);
      }, seconds * 1000);
    },
    [onRefresh],
  );

  // Tick elapsed every second
  useEffect(() => {
    tickRef.current = globalThis.setInterval(() => {
      setElapsed(Math.floor((Date.now() - lastRefresh.getTime()) / 1000));
    }, 1000);
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, [lastRefresh]);

  // Start/restart auto-refresh when interval changes
  useEffect(() => {
    scheduleRefresh(interval);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [interval, scheduleRefresh]);

  // -- Handlers --
  const handlePreset = (preset: PresetRange) => {
    setShowCustom(false);
    onRangeChange({ preset });
    setLastRefresh(new Date());
    setElapsed(0);
  };

  const handleCustomToggle = () => {
    setShowCustom(true);
    onRangeChange({
      preset: "custom",
      custom: { from: customFrom, to: customTo },
    });
  };

  const applyCustom = () => {
    onRangeChange({
      preset: "custom",
      custom: { from: customFrom, to: customTo },
    });
    setLastRefresh(new Date());
    setElapsed(0);
  };

  const handleManualRefresh = () => {
    onRefresh();
    setLastRefresh(new Date());
    setElapsed(0);
  };

  // -- Render --
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-3">
        {/* Preset pills */}
        <div className="flex gap-1">
          {PRESETS.map((p) => (
            <button
              key={p.value}
              onClick={() => handlePreset(p.value)}
              className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
                range.preset === p.value && !showCustom
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {p.label}
            </button>
          ))}
          <button
            onClick={handleCustomToggle}
            className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
              showCustom
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Custom
          </button>
        </div>

        {/* Separator */}
        <div className="h-6 w-px bg-gray-300" />

        {/* Auto-refresh controls */}
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>Last updated: {elapsed}s ago</span>
          <select
            value={interval}
            onChange={(e) => setInterval(Number(e.target.value) as RefreshInterval)}
            className="rounded border border-gray-300 bg-white px-2 py-1 text-sm"
          >
            {INTERVALS.map((iv) => (
              <option key={iv.value} value={iv.value}>
                {iv.label}
              </option>
            ))}
          </select>
          <button
            onClick={handleManualRefresh}
            className="rounded bg-gray-100 px-2 py-1 text-sm font-medium text-gray-700 hover:bg-gray-200 transition-colors"
            title="Refresh now"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Custom date pickers */}
      {showCustom && (
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">From</label>
            <input
              type="datetime-local"
              value={customFrom}
              onChange={(e) => setCustomFrom(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">To</label>
            <input
              type="datetime-local"
              value={customTo}
              onChange={(e) => setCustomTo(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1 text-sm"
            />
          </div>
          <button
            onClick={applyCustom}
            className="rounded bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            Apply
          </button>
        </div>
      )}
    </div>
  );
}
