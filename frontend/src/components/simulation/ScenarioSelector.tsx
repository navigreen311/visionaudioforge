"use client";

import React, { useState } from "react";
import Card from "@/components/ui/Card";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ScenarioConfig {
  scenarioId: string;
  label: string;
  eventCount: number;
  durationS: number;
  noiseLevel: number;
  confidenceThreshold: number;
  randomSeed: number;
}

interface ScenarioMeta {
  id: string;
  label: string;
  icon: string;
  description: string;
  expectedOutcomes: string[];
}

// ---------------------------------------------------------------------------
// Scenario definitions
// ---------------------------------------------------------------------------

const SCENARIOS: ScenarioMeta[] = [
  {
    id: "intrusion_detection",
    label: "Intrusion Detection",
    icon: "shield",
    description: "Simulates unauthorized entry events across perimeter zones.",
    expectedOutcomes: [
      "Person detected in restricted zone",
      "Alert triggered within 2s",
      "Bounding-box overlay on feed",
    ],
  },
  {
    id: "vehicle_tracking",
    label: "Vehicle Tracking",
    icon: "truck",
    description: "Tracks vehicles entering, moving through, and exiting monitored areas.",
    expectedOutcomes: [
      "Vehicle ID assigned on entry",
      "Speed estimation per frame",
      "License plate OCR attempted",
    ],
  },
  {
    id: "crowd_monitoring",
    label: "Crowd Monitoring",
    icon: "users",
    description: "Monitors crowd density and detects abnormal gatherings.",
    expectedOutcomes: [
      "Crowd count estimated per frame",
      "Density heatmap generated",
      "Threshold alert on overcrowding",
    ],
  },
  {
    id: "package_abandoned",
    label: "Package Abandoned",
    icon: "package",
    description: "Detects stationary objects left unattended beyond a time threshold.",
    expectedOutcomes: [
      "Object detected as stationary",
      "Timer started after 30s stillness",
      "Alert if unattended > 60s",
    ],
  },
  {
    id: "audio_anomaly",
    label: "Audio Anomaly",
    icon: "volume",
    description: "Identifies unusual audio patterns such as glass breaking or gunshots.",
    expectedOutcomes: [
      "Audio classified per 1s window",
      "Anomaly score computed",
      "Alert on high-severity audio event",
    ],
  },
  {
    id: "ocr_document",
    label: "OCR Document",
    icon: "file-text",
    description: "Processes document frames for text extraction and verification.",
    expectedOutcomes: [
      "Text regions detected",
      "OCR confidence per region",
      "Document type classified",
    ],
  },
  {
    id: "multi_zone_handoff",
    label: "Multi-Zone Handoff",
    icon: "layers",
    description: "Tests object re-identification as targets move between camera zones.",
    expectedOutcomes: [
      "Re-ID match across zones",
      "Handoff latency measured",
      "Track continuity score",
    ],
  },
  {
    id: "system_stress",
    label: "System Stress",
    icon: "zap",
    description: "Pushes the pipeline to maximum throughput to find bottlenecks.",
    expectedOutcomes: [
      "Throughput measured (fps)",
      "Latency percentiles captured",
      "Memory / CPU usage logged",
    ],
  },
];

// ---------------------------------------------------------------------------
// Icon helper (simple SVG icons to avoid external deps)
// ---------------------------------------------------------------------------

function ScenarioIcon({ name }: { name: string }) {
  const iconMap: Record<string, React.ReactNode> = {
    shield: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
      </svg>
    ),
    truck: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12" />
      </svg>
    ),
    users: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
      </svg>
    ),
    package: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
      </svg>
    ),
    volume: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
      </svg>
    ),
    "file-text": (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
    ),
    layers: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M6.429 9.75L2.25 12l4.179 2.25m0-4.5l5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L12 12.75 6.429 9.75m11.142 0l4.179 2.25L12 17.25 2.25 12l4.179-2.25m11.142 0l4.179 2.25L12 22.5l-9.75-5.25 4.179-2.25" />
      </svg>
    ),
    zap: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
      </svg>
    ),
  };
  return <>{iconMap[name] ?? iconMap.shield}</>;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface ScenarioSelectorProps {
  onSelect: (config: ScenarioConfig) => void;
  disabled?: boolean;
}

export default function ScenarioSelector({ onSelect, disabled = false }: ScenarioSelectorProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [eventCount, setEventCount] = useState(10);
  const [durationS, setDurationS] = useState(30);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [noiseLevel, setNoiseLevel] = useState(0.1);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5);
  const [randomSeed, setRandomSeed] = useState(42);

  const selectedScenario = SCENARIOS.find((s) => s.id === selected);

  function handleRun() {
    if (!selected) return;
    onSelect({
      scenarioId: selected,
      label: selectedScenario?.label ?? selected,
      eventCount,
      durationS,
      noiseLevel,
      confidenceThreshold,
      randomSeed,
    });
  }

  return (
    <div className="space-y-6">
      {/* Scenario cards grid */}
      <Card title="Choose a Scenario">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {SCENARIOS.map((s) => {
            const isSelected = selected === s.id;
            return (
              <button
                key={s.id}
                type="button"
                disabled={disabled}
                onClick={() => setSelected(s.id)}
                className={`relative flex items-start gap-3 rounded-lg border-2 p-4 text-left transition-all ${
                  isSelected
                    ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500"
                    : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50"
                } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
              >
                {/* Check indicator */}
                {isSelected && (
                  <span className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full bg-blue-500 text-white">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </span>
                )}
                <div className={`flex-shrink-0 mt-0.5 ${isSelected ? "text-blue-600" : "text-gray-400"}`}>
                  <ScenarioIcon name={s.icon} />
                </div>
                <div className="min-w-0">
                  <p className={`text-sm font-semibold ${isSelected ? "text-blue-900" : "text-gray-900"}`}>
                    {s.label}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{s.description}</p>
                </div>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Expected outcomes */}
      {selectedScenario && (
        <Card title="Expected Outcomes">
          <ul className="space-y-1.5">
            {selectedScenario.expectedOutcomes.map((outcome) => (
              <li key={outcome} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="mt-0.5 flex-shrink-0 h-4 w-4 rounded-full bg-green-100 text-green-600 flex items-center justify-center">
                  <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                </span>
                {outcome}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Event count & duration controls */}
      {selected && (
        <Card title="Simulation Parameters">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Event Count: {eventCount}
              </label>
              <input
                type="range"
                className="w-full"
                min={1}
                max={100}
                step={1}
                value={eventCount}
                onChange={(e) => setEventCount(parseInt(e.target.value, 10))}
                disabled={disabled}
              />
              <div className="flex justify-between text-xs text-gray-400">
                <span>1</span><span>50</span><span>100</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Duration: {durationS}s
              </label>
              <input
                type="range"
                className="w-full"
                min={5}
                max={300}
                step={5}
                value={durationS}
                onChange={(e) => setDurationS(parseInt(e.target.value, 10))}
                disabled={disabled}
              />
              <div className="flex justify-between text-xs text-gray-400">
                <span>5s</span><span>150s</span><span>300s</span>
              </div>
            </div>
          </div>

          {/* Advanced settings (collapsible) */}
          <div className="mt-4 border-t border-gray-200 pt-4">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-1 text-sm font-medium text-gray-600 hover:text-gray-900"
            >
              <svg
                className={`w-4 h-4 transition-transform ${showAdvanced ? "rotate-90" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
              Advanced Settings
            </button>

            {showAdvanced && (
              <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Noise Level: {noiseLevel.toFixed(2)}
                  </label>
                  <input
                    type="range"
                    className="w-full"
                    min={0}
                    max={1}
                    step={0.01}
                    value={noiseLevel}
                    onChange={(e) => setNoiseLevel(parseFloat(e.target.value))}
                    disabled={disabled}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Confidence Threshold: {confidenceThreshold.toFixed(2)}
                  </label>
                  <input
                    type="range"
                    className="w-full"
                    min={0}
                    max={1}
                    step={0.01}
                    value={confidenceThreshold}
                    onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                    disabled={disabled}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Random Seed</label>
                  <input
                    type="number"
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                    value={randomSeed}
                    onChange={(e) => setRandomSeed(parseInt(e.target.value, 10) || 0)}
                    disabled={disabled}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Run button */}
          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={handleRun}
              disabled={disabled || !selected}
              className="inline-flex items-center gap-2 rounded-lg border border-transparent bg-brand-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Run Simulation
            </button>
          </div>
        </Card>
      )}
    </div>
  );
}
