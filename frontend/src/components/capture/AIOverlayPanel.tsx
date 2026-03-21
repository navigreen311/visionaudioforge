"use client";

import { useState, useCallback } from "react";

export interface OverlaySettings {
  objectDetection: boolean;
  motionHeatmap: boolean;
  ocrText: boolean;
  opticalFlow: boolean;
  analysisMode: "low-latency" | "high-accuracy";
  confidenceThreshold: number;
}

interface AIOverlayPanelProps {
  onSettingsChange: (settings: OverlaySettings) => void;
}

const DEFAULT_SETTINGS: OverlaySettings = {
  objectDetection: false,
  motionHeatmap: false,
  ocrText: false,
  opticalFlow: false,
  analysisMode: "low-latency",
  confidenceThreshold: 50,
};

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

export default function AIOverlayPanel({ onSettingsChange }: AIOverlayPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [settings, setSettings] = useState<OverlaySettings>(DEFAULT_SETTINGS);

  const updateSettings = useCallback(
    (patch: Partial<OverlaySettings>) => {
      setSettings((prev) => {
        const next = { ...prev, ...patch };
        onSettingsChange(next);
        return next;
      });
    },
    [onSettingsChange]
  );

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        type="button"
        onClick={() => setCollapsed((prev) => !prev)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-800 hover:bg-gray-750 transition-colors"
      >
        <h3 className="text-sm font-semibold text-white tracking-wide uppercase">
          AI Overlay
        </h3>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${
            collapsed ? "-rotate-90" : "rotate-0"
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
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
                onClick={() => updateSettings({ analysisMode: "low-latency" })}
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
                onClick={() => updateSettings({ analysisMode: "high-accuracy" })}
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
                updateSettings({ confidenceThreshold: Number(e.target.value) })
              }
              className="w-full h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-[#185FA5]"
            />
            <div className="flex justify-between text-[10px] text-gray-600">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
