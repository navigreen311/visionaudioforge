"use client";

export type SourceType = "camera" | "screen" | "microphone" | "rtsp" | "multicam";

interface SourceSwitcherProps {
  activeSource: SourceType;
  onChange: (source: SourceType) => void;
}

const tabs: { key: SourceType; label: string; icon: string }[] = [
  { key: "camera", label: "Camera", icon: "🎥" },
  { key: "screen", label: "Screen", icon: "🖥️" },
  { key: "microphone", label: "Microphone", icon: "🎙️" },
  { key: "rtsp", label: "RTSP", icon: "📡" },
  { key: "multicam", label: "Multi-Cam", icon: "📺" },
];

export default function SourceSwitcher({ activeSource, onChange }: SourceSwitcherProps) {
  return (
    <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeSource === tab.key
              ? "bg-white text-brand-700 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          <span>{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </div>
  );
}
